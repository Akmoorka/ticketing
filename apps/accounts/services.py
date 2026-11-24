from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.notifications.services import queue_email

from .exceptions import EmailAlreadyRegistered, HasFutureTickets, InvalidVerificationToken
from .models import User

VERIFY_SALT = "accounts.verify-email"
VERIFICATION_MAX_AGE = 60 * 60 * 24  # 24 часа


def make_verification_token(user: User) -> str:
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFY_SALT)


@transaction.atomic
def user_register(*, email: str, password: str) -> User:
    """Создать пользователя и поставить письмо с токеном подтверждения в очередь."""
    email = email.strip().lower()
    validate_password(password)  # ValidationError, если пароль слабый
    if User.objects.filter(email__iexact=email).exists():
        raise EmailAlreadyRegistered(email)
    try:
        with transaction.atomic():  # savepoint: гонка двух регистраций не ломает внешнюю транзакцию
            user = User.objects.create_user(email=email, password=password)
    except IntegrityError:
        raise EmailAlreadyRegistered(email)
    token = make_verification_token(user)
    queue_email(
        dedup_key=f"verify-email:{user.pk}",
        to=user.email,
        subject="Подтвердите email",
        body=f"Код подтверждения email:\n{token}\n\nДействует 24 часа.",
    )
    return user


def verify_email(*, token: str) -> User:
    """Подтвердить email по токену. Токен одноразовый: повтор даёт ошибку."""
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=VERIFICATION_MAX_AGE)
    except signing.BadSignature:  # включает истёкший токен
        raise InvalidVerificationToken()
    user = User.objects.filter(
        pk=data.get("uid"), email=data.get("email"), is_active=True
    ).first()
    if user is None or user.email_verified_at is not None:  # токен одноразовый
        raise InvalidVerificationToken()
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


def _has_future_tickets(user: User) -> bool:
    return any(import_string(path)(user) for path in settings.USER_HAS_FUTURE_TICKETS_CHECKS)


@transaction.atomic
def user_anonymize(*, user: User) -> None:
    """Удалить аккаунт: обезличить, отключить и отозвать все сессии. Записи, связанные с ним, остаются."""
    if _has_future_tickets(user):
        raise HasFutureTickets()
    user.email = f"deleted-{user.pk}@anonymized.invalid"
    user.is_active = False
    user.is_staff = False
    user.is_superuser = False
    user.email_verified_at = None
    user.anonymized_at = timezone.now()
    user.set_unusable_password()
    user.save(
        update_fields=[
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "email_verified_at",
            "anonymized_at",
            "password",
        ]
    )
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
