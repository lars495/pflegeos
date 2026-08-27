from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.models.audit import AuditLog

async def log_action(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict | None = None,
) -> None:
    audit_entry = AuditLog(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    session.add(audit_entry)
