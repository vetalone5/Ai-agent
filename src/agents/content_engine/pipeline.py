"""13-phase content factory pipeline."""

import logging
from typing import Any

from sqlalchemy import select

from src.config.constants import ContentType, Platform
from src.models.article import Article
from src.models.keyword import KeywordCluster

logger = logging.getLogger(__name__)


class ContentPipeline:
    """Orchestrates the full content creation pipeline from cluster to published article."""

    def __init__(
        self,
        session_factory: Any,
        writer: Any,
        seo_optimizer: Any,
        factchecker: Any,
        platform_adapter: Any,
    ) -> None:
        self._session_factory = session_factory
        self._writer = writer
        self._seo = seo_optimizer
        self._factchecker = factchecker
        self._adapter = platform_adapter

    async def run_for_cluster(self, cluster_id: int) -> dict[str, Any]:
        """Full pipeline for a keyword cluster → article."""
        cluster = await self._get_cluster(cluster_id)
        if not cluster:
            return {"error": f"Cluster {cluster_id} not found"}

        content_type = ContentType(cluster.get("content_type", "guide"))
        keyword = cluster["marker_keyword"]
        lsi = cluster.get("lsi_keywords", [])
        geo_score = cluster.get("geo_score", 2)

        logger.info("Pipeline start: cluster=%d keyword='%s' type=%s geo=%d",
                     cluster_id, keyword, content_type, geo_score)

        # Phase 9: SERP pre-analysis
        serp_data = await self._analyze_serp(keyword)

        # Phase 10: Write article
        article_data = await self._writer.write_article(
            keyword=keyword,
            content_type=content_type,
            lsi_keywords=lsi,
            geo_score=geo_score,
            serp_data=serp_data,
        )

        # Phase 11: Factcheck
        fact_issues = await self._factchecker.check(
            article_data["content_md"], content_type
        )

        # Phase 12: SEO meta + packaging
        from src.agents.content_engine.seo_optimizer import generate_meta, check_seo_quality

        meta = generate_meta(
            title=keyword.title(),
            keyword=keyword,
            content_type=content_type,
            article_text=article_data["content_md"],
        )

        from src.tools.utm_constructor import build_article_utm_links
        utm_links = build_article_utm_links(meta["slug"], keyword)

        article_record = {
            "title": keyword.title(),
            "slug": meta["slug"],
            "h1": meta["h1"],
            "meta_title": meta["meta_title"],
            "meta_description": meta["meta_description"],
            "content_md": article_data["content_md"],
            "word_count": article_data["word_count"],
            "content_type": content_type,
            "cluster_id": cluster_id,
            "marker_keyword": keyword,
            "lsi_keywords": lsi,
            "geo_score": geo_score,
            "platform": Platform.BLOG,
            "status": "draft",
            "utm_links": utm_links,
        }

        seo_issues = check_seo_quality(article_record)

        article_id = await self._save_article(article_record)

        return {
            "article_id": article_id,
            "keyword": keyword,
            "word_count": article_data["word_count"],
            "content_type": content_type,
            "geo_score": geo_score,
            "fact_issues": len(fact_issues),
            "seo_issues": len(seo_issues),
            "antidetect_issues": len(article_data.get("antidetect_issues", [])),
            "geo_issues": len(article_data.get("geo_issues", [])),
            "requires_approval": True,
            "status": "draft",
        }

    async def run_batch(self, cluster_ids: list[int]) -> list[dict[str, Any]]:
        """Run pipeline for multiple clusters (batch of 5-10)."""
        results = []
        for cid in cluster_ids:
            try:
                result = await self.run_for_cluster(cid)
                results.append(result)
            except Exception as e:
                logger.error("Pipeline failed for cluster %d: %s", cid, e)
                results.append({"cluster_id": cid, "error": str(e)})
        return results

    async def _get_cluster(self, cluster_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(KeywordCluster).where(KeywordCluster.id == cluster_id)
            )
            cluster = result.scalar_one_or_none()
            if not cluster:
                return None
            return {
                "id": cluster.id,
                "name": cluster.name,
                "marker_keyword": cluster.marker_keyword,
                "total_frequency": cluster.total_frequency,
                "intent_type": cluster.intent_type,
                "geo_score": cluster.geo_score,
                "content_type": cluster.content_type,
                "lsi_keywords": cluster.lsi_keywords or [],
            }

    async def _analyze_serp(self, keyword: str) -> dict[str, Any] | None:
        """Phase 9: Analyze SERP before writing to understand competition."""
        try:
            from src.agents.seo_audit.serp_analyzer import SerpAnalyzer
            analyzer = SerpAnalyzer(None)
            result = await analyzer.analyze_serp(keyword)
            logger.info("SERP pre-analysis for '%s': competition=%s", keyword, result.get("competitiveness"))
            return result
        except Exception as e:
            logger.warning("SERP pre-analysis failed for '%s': %s", keyword, e)
            return None

    async def _save_article(self, data: dict[str, Any]) -> int:
        async with self._session_factory() as session:
            article = Article(
                title=data["title"],
                slug=data["slug"],
                h1=data["h1"],
                meta_title=data["meta_title"],
                meta_description=data["meta_description"],
                content_md=data["content_md"],
                word_count=data["word_count"],
                content_type=data["content_type"],
                cluster_id=data.get("cluster_id"),
                marker_keyword=data["marker_keyword"],
                lsi_keywords=data.get("lsi_keywords"),
                geo_score=data["geo_score"],
                platform=data["platform"],
                status=data["status"],
                utm_links=data.get("utm_links"),
            )
            session.add(article)
            await session.commit()
            await session.refresh(article)
            logger.info("Article saved: id=%d slug=%s", article.id, article.slug)
            return article.id
