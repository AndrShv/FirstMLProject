from select import select
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncSession

from workspace.entity.db_models import DBUser


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> Optional[DBUser]:
        result = await self.session.scalars(
            select(DBUser).where(DBUser.id == user_id)
        )
        return result.first()

    async def get_user_by_email(self, email: str) -> Optional[DBUser]:
        result = await self.session.scalars(
            select(DBUser).where(DBUser.email == email)
        )
        return result.first()

    async def create_user(self, user: DBUser) -> DBUser:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: DBUser) -> DBUser:
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: DBUser) -> None:
        await self.session.delete(user)
        await self.session.commit()