import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.services import queue_email

from . import selectors
from .exceptions import (
    InvalidInvitation,
    InvitationNotForUser,
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
