"""User persistence queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_oid(session: AsyncSession, oid: str) -> User | None:
    result = await session.execute(select(User).where(User.external_auth_id == oid))
    return result.scalar_one_or_none()
