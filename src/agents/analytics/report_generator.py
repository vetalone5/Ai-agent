import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.kpi import DailyKPI, WeeklyReport
from src.models.task import Task

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, session_factory: Any, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._claude = claude_client

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Generate comprehensive weekly report with AI summary."""
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)

        kpi_data = await self._get_kpi_range(week_start, now)
        task_stats = await self._get_task_stats(week_start, now)

        snapshot = {
            "period": f"{week_start.date()} — {now.date()}",
            "kpi": kpi_data,
            "tasks": task_stats,
            "goals": {
                "monthly_visitors": settings.goal_monthly_visitors,
                "monthly_registrations": settings.goal_monthly_registrations,
            },
        }

        summary = await self._generate_ai_summary(snapshot)
        report = await self._save_report(week_start, now, summary, task_stats, snapshot)

        logger.info("Weekly report generated: %s", snapshot["period"])
        return report

    async def _get_kpi_range(self, start: datetime, end: datetime) -> dict[str, Any]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    func.sum(DailyKPI.total_visitors).label("total_visitors"),
                    func.sum(DailyKPI.organic_visitors).label("organic_visitors"),
                    func.sum(DailyKPI.registrations).label("registrations"),
                    func.avg(DailyKPI.bounce_rate).label("avg_bounce_rate"),
                    func.avg(DailyKPI.avg_session_duration).label("avg_duration"),
                    func.max(DailyKPI.keywords_top10).label("keywords_top10"),
                    func.max(DailyKPI.ai_citations_count).label("ai_citations"),
                ).where(DailyKPI.date.between(start, end))
            )
            row = result.one_or_none()
            if not row:
                return {}
            return {
                "total_visitors": row.total_visitors or 0,
                "organic_visitors": row.organic_visitors or 0,
                "registrations": row.registrations or 0,
                "avg_bounce_rate": round(row.avg_bounce_rate or 0, 2),
                "avg_duration": round(row.avg_duration or 0, 1),
                "keywords_top10": row.keywords_top10 or 0,
                "ai_citations": row.ai_citations or 0,
            }

    async def _get_task_stats(self, start: datetime, end: datetime) -> dict[str, int]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Task.status, func.count(Task.id))
                .where(Task.created_at.between(start, end))
                .group_by(Task.status)
            )
            stats = dict(result.all())
            return {
                "completed": stats.get("completed", 0),
                "failed": stats.get("failed", 0) + stats.get("error", 0),
                "pending": stats.get("created", 0) + stats.get("queued", 0),
                "awaiting_approval": stats.get("needs_approval", 0),
            }

    async def _generate_ai_summary(self, snapshot: dict[str, Any]) -> str:
        try:
            return await self._claude.complete(
                system_prompt=(
                    "Ты — SEO-аналитик. Напиши краткий еженедельный отчёт на русском языке. "
                    "Укажи: что было достигнуто, какие проблемы, что делать дальше. "
                    "Формат: 3-5 пунктов, кратко и по делу."
                ),
                user_prompt=f"Данные за неделю:\n{snapshot}",
                max_tokens=1000,
                temperature=0.5,
            )
        except Exception as e:
            logger.error("AI summary generation failed: %s", e)
            return "Автоматическая генерация отчёта недоступна."

    async def _save_report(
        self,
        week_start: datetime,
        week_end: datetime,
        summary: str,
        task_stats: dict[str, int],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            report = WeeklyReport(
                week_start=week_start,
                week_end=week_end,
                summary=summary,
                tasks_completed=task_stats.get("completed", 0),
                tasks_failed=task_stats.get("failed", 0),
                kpi_snapshot=snapshot.get("kpi"),
            )
            session.add(report)
            await session.commit()
            return {"id": report.id, "summary": summary, "kpi": snapshot.get("kpi")}
