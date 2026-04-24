from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DailyKPIResponse(BaseModel):
    id: int
    date: datetime
    organic_visitors: int = 0
    total_visitors: int = 0
    registrations: int = 0
    bounce_rate: float = 0.0
    avg_session_duration: float = 0.0
    pages_per_session: float = 1.0
    keywords_top3: int = 0
    keywords_top10: int = 0
    keywords_top100: int = 0
    indexed_pages_yandex: int = 0
    indexed_pages_google: int = 0
    ai_citations_count: int = 0
    traffic_sources: dict[str, Any] | None = None


class WeeklyReportResponse(BaseModel):
    id: int
    week_start: datetime
    week_end: datetime
    summary: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    articles_published: int = 0
    backlinks_acquired: int = 0
    kpi_snapshot: dict[str, Any] | None = None
    recommendations: dict[str, Any] | None = None


class KPISummary(BaseModel):
    current_month_visitors: int = 0
    current_month_registrations: int = 0
    goal_visitors: int = 10000
    goal_registrations: int = 500
    visitors_progress: float = 0.0
    registrations_progress: float = 0.0
    keywords_top10: int = 0
    ai_citations: int = 0
    avg_bounce_rate: float = 0.0
