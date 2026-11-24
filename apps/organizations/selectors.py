from .models import Membership


def membership_for(user, organization_id):
    """Членство пользователя в организации или None."""
    return (
        Membership.objects.select_related("organization")
        .filter(user=user, organization_id=organization_id)
        .first()
    )
