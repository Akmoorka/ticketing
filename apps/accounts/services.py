from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.services import queue_email

from .exceptions import EmailAlreadyRegistered, InvalidVerificationToken
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
