from django.db import IntegrityError, transaction

from .exceptions import SlugTaken
from .models import Membership, Organization


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
