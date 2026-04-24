import logging
from typing import Any

from src.config.constants import AgentType
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SEOAuditAgent(BaseAgent):
    agent_type = AgentType.SEO_AUDIT

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.seo_audit.competitor_analysis import CompetitorAnalyzer
        from src.agents.seo_audit.crawler import SiteCrawler
        from src.agents.seo_audit.keyword_research import KeywordResearcher
        from src.agents.seo_audit.serp_analyzer import SerpAnalyzer

        self.crawler = SiteCrawler(session_factory, task_manager)
        self.keywords = KeywordResearcher(session_factory)
        self.competitors = CompetitorAnalyzer(session_factory, claude_client)
        self.serp = SerpAnalyzer(claude_client)

    async def get_capabilities(self) -> list[str]:
        return [
            "full_crawl",
            "keyword_research",
            "competitor_analysis",
            "content_gap_analysis",
            "serp_analysis",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")
        data = task_data.get("data", {})

        if task_type == "full_crawl":
            return await self.crawler.run_full_crawl()

        elif task_type == "keyword_research":
            seeds = data.get("seed_queries")
            return await self.keywords.run_full_research(seeds)

        elif task_type == "competitor_analysis":
            results = await self.competitors.analyze_all()
            return {"status": "ok", "competitors": len(results)}

        elif task_type == "content_gap_analysis":
            return await self.competitors.find_content_gaps()

        elif task_type == "serp_analysis":
            queries = data.get("queries", [])
            results = await self.serp.analyze_batch(queries)
            return {"status": "ok", "analyzed": len(results), "results": results}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
