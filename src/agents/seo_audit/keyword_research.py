import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import ContentType, GEO_SCORING
from src.models.keyword import Keyword, KeywordCluster
from src.tools.wordstat_client import WordstatClient

logger = logging.getLogger(__name__)

QUESTION_PREFIXES = ["как", "что такое", "зачем", "почему", "какой", "сколько стоит", "где"]


class KeywordResearcher:
    """Automated keyword research with clustering and GEO-scoring."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._wordstat = WordstatClient()

    async def run_full_research(self, seed_queries: list[str] | None = None) -> dict[str, Any]:
        """Full pipeline: seed → bulk → questions → clean → cluster → score."""
        if not seed_queries:
            seed_queries = await self._get_existing_seeds()

        raw = await self._collect_keywords(seed_queries)
        cleaned = self._clean_keywords(raw)
        await self._save_keywords(cleaned)
        clusters = self._cluster_keywords(cleaned)
        await self._save_clusters(clusters)

        logger.info("Research complete: %d raw → %d clean → %d clusters", len(raw), len(cleaned), len(clusters))
        return {"raw": len(raw), "cleaned": len(cleaned), "clusters": len(clusters)}

    async def _get_existing_seeds(self) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Keyword.query)
                .where(Keyword.source == "seed")
                .order_by(Keyword.frequency.desc())
                .limit(20)
            )
            return [r[0] for r in result.all()]

    async def _collect_keywords(self, seeds: list[str]) -> list[dict[str, Any]]:
        """Phase 4-5 of content factory: bulk + questions + associations."""
        all_kw: list[dict[str, Any]] = []

        bulk = await self._wordstat.wordstat_bulk(seeds)
        all_kw.extend(bulk)

        question_seeds = []
        for seed in seeds[:5]:
            for prefix in QUESTION_PREFIXES:
                question_seeds.append(f"{prefix} {seed}")
        questions = await self._wordstat.wordstat_bulk(question_seeds, include_assoc=False)
        all_kw.extend(questions)

        for seed in seeds[:3]:
            assoc = await self._wordstat.wordstat_assoc(seed)
            all_kw.extend(assoc)

        return all_kw

    def _clean_keywords(self, keywords: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicates, irrelevant, competitor brand queries."""
        seen: set[str] = set()
        cleaned = []
        competitor_brands = {"brand24", "mention", "youscan", "brandanalytics"}

        for kw in keywords:
            query = kw.get("query", "").lower().strip()
            if not query or len(query) < 3:
                continue
            if query in seen:
                continue
            if any(brand in query for brand in competitor_brands):
                continue
            if kw.get("count", 0) < 5:
                continue
            seen.add(query)
            cleaned.append(kw)

        cleaned.sort(key=lambda x: x.get("count", 0), reverse=True)
        return cleaned

    def _cluster_keywords(self, keywords: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group keywords by semantic similarity (simplified: by shared root words)."""
        clusters: dict[str, dict[str, Any]] = {}

        for kw in keywords:
            query = kw.get("query", "")
            words = set(query.lower().split())
            assigned = False

            for cluster_name, cluster in clusters.items():
                marker_words = set(cluster["marker"].lower().split())
                overlap = len(words & marker_words)
                if overlap >= 2 or (overlap >= 1 and len(words) <= 3):
                    cluster["keywords"].append(kw)
                    cluster["total_freq"] += kw.get("count", 0)
                    assigned = True
                    break

            if not assigned:
                clusters[query] = {
                    "marker": query,
                    "keywords": [kw],
                    "total_freq": kw.get("count", 0),
                }

        result = []
        for name, data in clusters.items():
            content_type = self._detect_content_type(name)
            geo_score = GEO_SCORING.get(content_type, 2)
            intent = self._detect_intent(name)
            result.append({
                "name": name,
                "marker": data["marker"],
                "keywords": [k["query"] for k in data["keywords"]],
                "total_frequency": data["total_freq"],
                "content_type": content_type,
                "geo_score": geo_score,
                "intent": intent,
            })

        result.sort(key=lambda x: x["total_frequency"], reverse=True)
        return result

    async def _save_keywords(self, keywords: list[dict[str, Any]]) -> None:
        async with self._session_factory() as session:
            for kw in keywords:
                query = kw.get("query", "")
                existing = await session.execute(select(Keyword).where(Keyword.query == query))
                if existing.scalar_one_or_none():
                    continue
                session.add(Keyword(
                    query=query,
                    frequency=kw.get("count", 0),
                    source=kw.get("source", "wordstat"),
                ))
            await session.commit()

    async def _save_clusters(self, clusters: list[dict[str, Any]]) -> None:
        async with self._session_factory() as session:
            for cl in clusters:
                existing = await session.execute(
                    select(KeywordCluster).where(KeywordCluster.marker_keyword == cl["marker"])
                )
                if existing.scalar_one_or_none():
                    continue
                session.add(KeywordCluster(
                    name=cl["name"],
                    marker_keyword=cl["marker"],
                    total_frequency=cl["total_frequency"],
                    intent_type=cl["intent"],
                    geo_score=cl["geo_score"],
                    content_type=cl.get("content_type"),
                    lsi_keywords=cl["keywords"][:20],
                ))
            await session.commit()

    @staticmethod
    def _detect_content_type(query: str) -> ContentType:
        q = query.lower()
        if any(w in q for w in ["что такое", "определение", "glossar", "термин"]):
            return ContentType.GLOSSARY
        if any(w in q for w in ["как ", "инструкция", "руководство", "пошагов"]):
            return ContentType.GUIDE
        if any(w in q for w in ["рейтинг", "топ ", "лучшие", "top"]):
            return ContentType.RATING
        if any(w in q for w in ["сравнение", " vs ", " или "]):
            return ContentType.COMPARISON
        if any(w in q for w in ["обзор", "review", "отзыв"]):
            return ContentType.REVIEW
        if any(w in q for w in ["зачем", "почему", "стоит ли", "нужен ли"]):
            return ContentType.FAQ
        if any(w in q for w in ["тренд", "прогноз", "будущее"]):
            return ContentType.TRENDS
        if any(w in q for w in ["чеклист", "чек-лист", "checklist"]):
            return ContentType.CHECKLIST
        return ContentType.GUIDE

    @staticmethod
    def _detect_intent(query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["купить", "цена", "стоимость", "тариф", "сервис", "инструмент", "платформа"]):
            return "commercial"
        if any(w in q for w in ["spioniro", "спионир"]):
            return "navigational"
        return "informational"
