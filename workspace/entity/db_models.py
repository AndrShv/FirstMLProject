import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import UUID, func, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class DBUser(BaseModel):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )

    email: Mapped[str] = mapped_column(
        String(255), index=True, unique=True, nullable=False
    )
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
