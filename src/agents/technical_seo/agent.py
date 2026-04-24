import logging
from typing import Any

from src.config.constants import AgentType
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TechnicalSEOAgent(BaseAgent):
    agent_type = AgentType.TECHNICAL_SEO

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.technical_seo.cwv_monitor import CWVMonitor
        from src.agents.technical_seo.schema_generator import SchemaGenerator
        from src.agents.technical_seo.sitemap_manager import SitemapManager

        self.schema = SchemaGenerator()
        self.sitemap = SitemapManager(session_factory)
        self.cwv = CWVMonitor(task_manager)

    async def get_capabilities(self) -> list[str]:
        return [
            "generate_schema",
            "generate_sitemap",
            "generate_robots_txt",
            "check_cwv",
            "fix_technical_issue",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")
        data = task_data.get("data", {})

        if task_type == "generate_schema":
            schemas = self.schema.generate(data)
            html = self.schema.to_script_tags(schemas)
            return {"schemas": schemas, "html": html, "requires_approval": True}

        elif task_type == "generate_sitemap":
            xml = await self.sitemap.generate_sitemap()
            return {"sitemap_xml": xml, "requires_approval": True}

        elif task_type == "generate_robots_txt":
            txt = await self.sitemap.generate_robots_txt()
            return {"robots_txt": txt, "requires_approval": True}

        elif task_type == "check_cwv":
            urls = data.get("urls", [])
            results = await self.cwv.check_urls(urls)
            return {"status": "ok", "results": results}

        elif task_type.startswith("fix_"):
            analysis = await self.ask_claude(
                system_prompt=(
                    "Ты — технический SEO-специалист. "
                    "Предложи конкретное техническое решение для исправления проблемы."
                ),
                user_prompt=f"Проблема: {task_type}\nДетали: {data}\nПредложи решение.",
            )
            return {"analysis": analysis, "task_type": task_type, "requires_approval": True}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
