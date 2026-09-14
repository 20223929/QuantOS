from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ExecutionEventProjectionModel(Base):
    __tablename__ = "execution_event_projections"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_execution_event_projections_event_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    projected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
