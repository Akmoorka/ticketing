class EmailAlreadyRegistered(Exception):
    """Пользователь с таким email уже есть."""


class InvalidVerificationToken(Exception):
    """Токен подтверждения испорчен, просрочен или больше не подходит."""
