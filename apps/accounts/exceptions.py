class EmailAlreadyRegistered(Exception):
    """Пользователь с таким email уже есть."""


class InvalidVerificationToken(Exception):
    """Токен подтверждения испорчен, просрочен или больше не подходит."""


class HasFutureTickets(Exception):
    """У пользователя есть билеты на будущие мероприятия: аккаунт удалить нельзя."""
