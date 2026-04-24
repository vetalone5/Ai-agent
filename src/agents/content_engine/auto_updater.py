"""Content auto-updater: detects position drops and re-optimizes articles.

Google's Information Gain Score penalizes stale content.
Yandex weights freshness heavily for informational queries.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select

from src.config.constants import AgentType, TaskPriority
from src.core.task_manager import TaskManager
from src.models.article import Article, ArticleMetrics

logger = logging.getLogger(__name__)

POSITION_DROP_THRESHOLD = 5
TRAFFIC_DROP_THRESHOLD = 30
STALE_CONTENT_DAYS = 180


class ContentAutoUpdater:
    """Monitors published articles and triggers re-optimization when metrics drop."""

    def __init__(self, session_factory: Any, task_manager: TaskManager, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._tasks = task_manager
        self._claude = claude_client

    async def scan_and_update(self) -> dict[str, Any]:
        """Full scan: check all published articles for performance drops."""
        articles = await self._get_published_articles()
        issues_found = 0
        tasks_created = 0

        for article in articles:
            problems = await self._check_article_health(article)
            if problems:
                issues_found += len(problems)
                task_id = await self._create_update_task(article, problems)
                if task_id:
                    tasks_created += 1

        stale = await self._find_stale_content()
        for article in stale:
            task_id = await self._create_freshness_task(article)
            if task_id:
                tasks_created += 1
                issues_found += 1

        logger.info("Auto-updater: scanned %d articles, %d issues, %d tasks",
                     len(articles), issues_found, tasks_created)
        return {"articles_scanned": len(articles), "issues": issues_found, "tasks_created": tasks_created}

    async def generate_update_plan(self, article_id: int, problems: list[dict[str, Any]]) -> str:
        """Use Claude to generate a specific update plan for an article."""
        async with self._session_factory() as session:
            result = await session.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()
            if not article:
                return "Article not found"

        problems_str = "\n".join(f"- {p['type']}: {p['detail']}" for p in problems)
        prompt = f"""Статья: "{article.title}" (slug: {article.slug})
Ключевое слово: {article.marker_keyword}
Текущий объём: {article.word_count} слов
GEO-скор: {article.geo_score}

Обнаруженные проблемы:
{problems_str}

Первые 500 символов контента:
{article.content_md[:500]}

Предложи конкретный план обновления:
1. Что добавить/убрать/изменить
2. Какие разделы обновить
3. Какие свежие данные включить
4. Нужно ли менять структуру

Формат: нумерованный список, до 10 пунктов."""

        return await self._claude.complete(
            system_prompt="Ты — SEO-специалист. Анализируешь падение позиций и предлагаешь план обновления.",
            user_prompt=prompt,
            max_tokens=1000,
        )

    async def _check_article_health(self, article: dict[str, Any]) -> list[dict[str, Any]]:
        """Check if article has position/traffic drops."""
        problems = []
        article_id = article["id"]

        metrics = await self._get_recent_metrics(article_id)
        if len(metrics) < 2:
            return problems

        latest = metrics[0]
        previous = metrics[-1]

        if latest.get("position_yandex") and previous.get("position_yandex"):
            drop = latest["position_yandex"] - previous["position_yandex"]
            if drop >= POSITION_DROP_THRESHOLD:
                problems.append({
                    "type": "position_drop_yandex",
                    "detail": f"Yandex position dropped from {previous['position_yandex']} to {latest['position_yandex']}",
                    "severity": "high" if drop >= 10 else "medium",
                })

        if latest.get("position_google") and previous.get("position_google"):
            drop = latest["position_google"] - previous["position_google"]
            if drop >= POSITION_DROP_THRESHOLD:
                problems.append({
                    "type": "position_drop_google",
                    "detail": f"Google position dropped from {previous['position_google']} to {latest['position_google']}",
                    "severity": "high" if drop >= 10 else "medium",
                })

        if previous.get("page_views", 0) > 0:
            traffic_change = ((latest.get("page_views", 0) - previous["page_views"]) / previous["page_views"]) * 100
            if traffic_change <= -TRAFFIC_DROP_THRESHOLD:
                problems.append({
                    "type": "traffic_drop",
                    "detail": f"Traffic dropped {abs(traffic_change):.0f}% ({previous['page_views']} → {latest.get('page_views', 0)})",
                    "severity": "high",
                })

        if latest.get("bounce_rate", 0) > 75:
            problems.append({
                "type": "high_bounce",
                "detail": f"Bounce rate {latest['bounce_rate']:.1f}%",
                "severity": "medium",
            })

        return problems

    async def _find_stale_content(self) -> list[dict[str, Any]]:
        """Find articles not updated in STALE_CONTENT_DAYS."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_CONTENT_DAYS)
        async with self._session_factory() as session:
            result = await session.execute(
                select(Article)
                .where(and_(
                    Article.status == "published",
                    Article.updated_at < cutoff,
                ))
                .limit(20)
            )
            return [
                {"id": a.id, "title": a.title, "slug": a.slug,
                 "marker_keyword": a.marker_keyword, "updated_at": a.updated_at}
                for a in result.scalars().all()
            ]

    async def _create_update_task(self, article: dict[str, Any], problems: list[dict[str, Any]]) -> int | None:
        try:
            highest_severity = min(
                (p["severity"] for p in problems),
                key=lambda s: {"high": 0, "medium": 1, "low": 2}.get(s, 3),
            )
            priority = TaskPriority.HIGH if highest_severity == "high" else TaskPriority.MEDIUM
            return await self._tasks.create_task(
                task_type="content_reoptimize",
                agent_type=AgentType.CONTENT_ENGINE,
                priority=priority,
                data={
                    "article_id": article["id"],
                    "title": article.get("title", ""),
                    "problems": problems,
                },
                created_by=AgentType.ANALYTICS,
            )
        except Exception as e:
            logger.error("Failed to create update task: %s", e)
            return None

    async def _create_freshness_task(self, article: dict[str, Any]) -> int | None:
        try:
            return await self._tasks.create_task(
                task_type="content_refresh",
                agent_type=AgentType.CONTENT_ENGINE,
                priority=TaskPriority.LOW,
                data={
                    "article_id": article["id"],
                    "title": article.get("title", ""),
                    "reason": f"Not updated since {article.get('updated_at', 'unknown')}",
                },
                created_by=AgentType.ANALYTICS,
            )
        except Exception as e:
            logger.error("Failed to create freshness task: %s", e)
            return None

    async def _get_published_articles(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Article).where(Article.status == "published")
            )
            return [
                {"id": a.id, "title": a.title, "slug": a.slug,
                 "marker_keyword": a.marker_keyword, "geo_score": a.geo_score}
                for a in result.scalars().all()
            ]

    async def _get_recent_metrics(self, article_id: int, limit: int = 4) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArticleMetrics)
                .where(ArticleMetrics.article_id == article_id)
                .order_by(ArticleMetrics.date.desc())
                .limit(limit)
            )
            return [
                {
                    "page_views": m.page_views, "bounce_rate": m.bounce_rate,
                    "position_yandex": m.position_yandex, "position_google": m.position_google,
                    "avg_time_on_page": m.avg_time_on_page,
                }
                for m in result.scalars().all()
            ]
