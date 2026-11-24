class SlugTaken(Exception):
    """Организация с таким slug уже есть."""


class OrganizationNotFound(Exception):
    """Организации нет или пользователь в ней не участник (для клиента это 404)."""


class RoleNotAllowed(Exception):
    """Участник видит объект, но его роль не разрешает действие (403)."""


class InvalidInvitation(Exception):
    """Токен неверный, просрочен или уже использован."""


class InvitationNotForUser(Exception):
    """Приглашение выписано на другой email или email пользователя не подтверждён."""


class MemberNotFound(Exception):
    """В организации нет такого участника (404)."""


class LastOwner(Exception):
    """Нельзя удалить или понизить последнего владельца организации (409)."""
