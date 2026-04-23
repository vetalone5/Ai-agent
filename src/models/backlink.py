from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Backlink(Base, TimestampMixin):
    __tablename__ = "backlinks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_domain: Mapped[str] = mapped_column(String(300), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    traffic: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_backlinks_domain", "source_domain"),
        Index("ix_backlinks_status", "status"),
    )
