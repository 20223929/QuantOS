"""Persistent state projection model."""

from sqlalchemy import Column, DateTime, String, Text, func

from .base import Base


class StateProjection(Base):
    __tablename__ = "state_projections"

    projection_id = Column(String(128), primary_key=True)
    aggregate_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(String(128), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    state_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
