from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class DailyKPI(Base, TimestampMixin):
    __tablename__ = "daily_kpi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True)

    organic_visitors: Mapped[int] = mapped_column(Integer, default=0)
    total_visitors: Mapped[int] = mapped_column(Integer, default=0)
    registrations: Mapped[int] = mapped_column(Integer, default=0)
    bounce_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_session_duration: Mapped[float] = mapped_column(Float, default=0.0)
    pages_per_session: Mapped[float] = mapped_column(Float, default=1.0)

    keywords_top3: Mapped[int] = mapped_column(Integer, default=0)
    keywords_top10: Mapped[int] = mapped_column(Integer, default=0)
    keywords_top100: Mapped[int] = mapped_column(Integer, default=0)

    indexed_pages_yandex: Mapped[int] = mapped_column(Integer, default=0)
    indexed_pages_google: Mapped[int] = mapped_column(Integer, default=0)

    ai_citations_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_citations_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    traffic_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_daily_kpi_date", "date"),
    )


class WeeklyReport(Base, TimestampMixin):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    week_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    summary: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0)
    articles_published: Mapped[int] = mapped_column(Integer, default=0)
    backlinks_acquired: Mapped[int] = mapped_column(Integer, default=0)

    kpi_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
