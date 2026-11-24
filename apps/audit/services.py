from .models import AuditEntry


def record(*, actor, action: str, object_type: str, object_id, data=None) -> AuditEntry:
    """Записать событие. Вызывать внутри транзакции изменения: откатится вместе с ним."""
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        data=data or {},
    )
