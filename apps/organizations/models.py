from django.conf import settings
from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        MANAGER = "manager", "Менеджер"
        CHECKER = "checker", "Контролёр"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="uniq_membership_user_org"
            )
        ]
