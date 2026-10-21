import uuid
from datetime import datetime

from sqlalchemy import Uuid, func, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from workspace.configs.db_config import Base


class DbOutputs(Base):
    __tablename__ = 'ai_outputs'
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    latency: Mapped[float] = mapped_column(nullable=False)

    input_tokens: Mapped[int] = mapped_column(nullable=False)
    output_tokens: Mapped[int] = mapped_column(nullable=False)

    cache_hit: Mapped[bool] = mapped_column(nullable=False, default=False)