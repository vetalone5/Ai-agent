import logging
from typing import Any

from src.config.constants import AgentType, ContentType, Platform
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentEngineAgent(BaseAgent):
    agent_type = AgentType.CONTENT_ENGINE

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.content_engine.factchecker import FactChecker
        from src.agents.content_engine.pipeline import ContentPipeline
        from src.agents.content_engine.platform_adapter import PlatformAdapter
        from src.agents.content_engine.seo_optimizer import check_seo_quality
        from src.agents.content_engine.writer import ArticleWriter

        self.writer = ArticleWriter(claude_client)
        self.factchecker = FactChecker(claude_client)
        self.adapter = PlatformAdapter(claude_client)
        self.pipeline = ContentPipeline(
            session_factory=session_factory,
            writer=self.writer,
            seo_optimizer=check_seo_quality,
            factchecker=self.factchecker,
            platform_adapter=self.adapter,
        )

    async def get_capabilities(self) -> list[str]:
        return [
            "write_article",
            "run_pipeline",
            "run_batch",
            "adapt_for_platform",
            "factcheck",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")
        data = task_data.get("data", {})

        if task_type == "write_article":
            result = await self.writer.write_article(
                keyword=data["keyword"],
                content_type=ContentType(data.get("content_type", "guide")),
                lsi_keywords=data.get("lsi_keywords"),
                geo_score=data.get("geo_score", 2),
                serp_data=data.get("serp_data"),
            )
            result["requires_approval"] = True
            return result

        elif task_type == "run_pipeline":
            cluster_id = data.get("cluster_id")
            if not cluster_id:
                raise ValueError("cluster_id required")
            return await self.pipeline.run_for_cluster(cluster_id)

        elif task_type == "run_batch":
            cluster_ids = data.get("cluster_ids", [])
            results = await self.pipeline.run_batch(cluster_ids)
            return {"status": "ok", "articles": results, "requires_approval": True}

        elif task_type == "adapt_for_platform":
            adapted = await self.adapter.adapt(
                article_md=data["content_md"],
                target_platform=Platform(data["platform"]),
                keyword=data["keyword"],
            )
            return {"adapted_content": adapted, "platform": data["platform"], "requires_approval": True}

        elif task_type in ("behavioral_fix_high_bounce", "behavioral_fix_low_duration"):
            recommendation = data.get("recommendation", "")
            url = data.get("url", "")
            analysis = await self.ask_claude(
                system_prompt="Ты — SEO-специалист. Проанализируй проблему и предложи конкретные изменения.",
                user_prompt=f"Проблема на странице {url}: {recommendation}\nПредложи 3-5 конкретных изменений.",
            )
            return {"url": url, "analysis": analysis, "requires_approval": True}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
