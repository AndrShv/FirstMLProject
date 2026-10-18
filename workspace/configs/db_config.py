from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from workspace.configs.settings import settings


class Base(DeclarativeBase):
    pass


_async_engine = None
_session_factory = None


def _get_session_factory():
    global _async_engine, _session_factory
    if _session_factory is None:
        connect_args = {"statement_cache_size": 0}
        if settings.POSTGRES_SERVER not in {"localhost", "127.0.0.1", "postgres", "shop-postgres", "ml-postgres"}:
            connect_args["ssl"] = "require"

        _async_engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
        )
        _session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():

    _get_session_factory()
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
