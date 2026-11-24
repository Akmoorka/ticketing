import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record as audit_record
from apps.notifications.services import queue_email

from . import selectors
from .exceptions import (
    InvalidInvitation,
    InvitationNotForUser,
    LastOwner,
    MemberNotFound,
    OrganizationNotFound,
    RoleNotAllowed,
    SlugTaken,
)
from .models import Invitation, Membership, Organization

INVITATION_TTL = timedelta(hours=72)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@transaction.atomic
def organization_create(*, user, name: str, slug: str) -> Organization:
    """Создать организацию в статусе pending; создатель становится owner."""
    slug = slug.strip().lower()
    if Organization.objects.filter(slug=slug).exists():
        raise SlugTaken(slug)
    try:
        with transaction.atomic():  # savepoint на случай гонки двух запросов
            org = Organization.objects.create(name=name.strip(), slug=slug)
    except IntegrityError:
        raise SlugTaken(slug)
    Membership.objects.create(user=user, organization=org, role=Membership.Role.OWNER)
    return org


@transaction.atomic
def invitation_create(*, actor, organization_id, email: str, role: str) -> Invitation:
    """Пригласить по email. Только owner; не-участнику организация «не видна» (404)."""
    membership = selectors.membership_for(actor, organization_id)
    if membership is None:
        raise OrganizationNotFound()
    if membership.role != Membership.Role.OWNER:
        raise RoleNotAllowed()
    token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        organization=membership.organization,
        email=email.strip().lower(),
        role=role,
        token_hash=hash_token(token),
        invited_by=actor,
        expires_at=timezone.now() + INVITATION_TTL,
    )
    queue_email(
        dedup_key=f"invitation:{invitation.pk}",
        to=invitation.email,
        subject=f"Приглашение в «{membership.organization.name}»",
        body=(
            f"Вас приглашают в «{membership.organization.name}» "
            f"с ролью «{invitation.get_role_display()}».\n"
            f"Код приглашения:\n{token}\n\nДействует 72 часа."
        ),
    )
    return invitation


@transaction.atomic
def invitation_accept(*, user, token: str) -> Membership:
    """Принять приглашение. Токен одноразовый; email должен совпасть и быть подтверждён."""
    invitation = (
        Invitation.objects.select_for_update()
        .select_related("organization")
        .filter(token_hash=hash_token(token))
        .first()
    )
    now = timezone.now()
    if invitation is None or invitation.accepted_at is not None or invitation.expires_at <= now:
        raise InvalidInvitation()
    if user.email_verified_at is None or user.email.lower() != invitation.email:
        raise InvitationNotForUser()
    if Membership.objects.filter(user=user, organization=invitation.organization).exists():
        raise InvalidInvitation()  # уже участник: приглашение смысла не имеет
    membership = Membership.objects.create(
        user=user, organization=invitation.organization, role=invitation.role
    )
    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at"])
    return membership


def _lock_owners_and_check_actor(*, actor, organization_id):
    """Заблокировать строки владельцев (против гонки) и проверить, что actor сам owner."""
    owners = list(
        Membership.objects.select_for_update().filter(
            organization_id=organization_id, role=Membership.Role.OWNER
        )
    )
    actor_membership = selectors.membership_for(actor, organization_id)
    if actor_membership is None:
        raise OrganizationNotFound()
    if actor_membership.role != Membership.Role.OWNER:
        raise RoleNotAllowed()
    return owners


@transaction.atomic
def member_change_role(*, actor, organization_id, user_id, role: str) -> Membership:
    owners = _lock_owners_and_check_actor(actor=actor, organization_id=organization_id)
    target = Membership.objects.filter(organization_id=organization_id, user_id=user_id).first()
    if target is None:
        raise MemberNotFound()
    if target.role == role:
        return target
    if target.role == Membership.Role.OWNER and len(owners) <= 1:
        raise LastOwner()
    old_role = target.role
    target.role = role
    target.save(update_fields=["role"])
    audit_record(
        actor=actor,
        action="member.role_changed",
        object_type="membership",
        object_id=target.pk,
        data={"organization_id": organization_id, "user_id": user_id, "from": old_role, "to": role},
    )
    return target


@transaction.atomic
def member_remove(*, actor, organization_id, user_id) -> None:
    owners = _lock_owners_and_check_actor(actor=actor, organization_id=organization_id)
    target = Membership.objects.filter(organization_id=organization_id, user_id=user_id).first()
    if target is None:
        raise MemberNotFound()
    if target.role == Membership.Role.OWNER and len(owners) <= 1:
        raise LastOwner()
    membership_id, old_role = target.pk, target.role
    target.delete()
    audit_record(
        actor=actor,
        action="member.removed",
        object_type="membership",
        object_id=membership_id,
        data={"organization_id": organization_id, "user_id": user_id, "role": old_role},
    )
