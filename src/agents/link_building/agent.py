import logging
from typing import Any

from src.config.constants import AgentType
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LinkBuildingAgent(BaseAgent):
    agent_type = AgentType.LINK_BUILDING

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.link_building.backlink_monitor import BacklinkMonitor
        from src.agents.link_building.outreach import OutreachGenerator
        from src.agents.link_building.platform_finder import PlatformFinder
        from src.agents.link_building.utm_builder import UTMBuilder

        self.platforms = PlatformFinder(session_factory, claude_client)
        self.outreach = OutreachGenerator(claude_client)
        self.backlinks = BacklinkMonitor(session_factory)
        self.utm = UTMBuilder()

    async def get_capabilities(self) -> list[str]:
        return [
            "find_platforms",
            "generate_guest_post_pitch",
            "generate_kyu_answer",
            "generate_digital_pr",
            "check_backlinks",
            "add_backlink",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")
        data = task_data.get("data", {})

        if task_type == "find_platforms":
            return await self.platforms.find_platforms(
                keyword=data.get("keyword", ""),
                content_type=data.get("content_type", "guide"),
            )

        elif task_type == "generate_guest_post_pitch":
            return await self.outreach.generate_guest_post_pitch(
                target_site=data["target_site"],
                topic=data["topic"],
                our_article_url=data.get("article_url", ""),
            )

        elif task_type == "generate_kyu_answer":
            return await self.outreach.generate_kyu_answer(
                question=data["question"],
                article_url=data.get("article_url", ""),
                keyword=data.get("keyword", ""),
            )

        elif task_type == "generate_digital_pr":
            return await self.outreach.generate_digital_pr_pitch(
                research_topic=data["topic"],
                key_findings=data.get("findings", []),
            )

        elif task_type == "check_backlinks":
            return await self.backlinks.check_all_backlinks()

        elif task_type == "add_backlink":
            bl_id = await self.backlinks.add_backlink(
                source_url=data["source_url"],
                target_url=data["target_url"],
                anchor_text=data.get("anchor_text", ""),
                platform=data.get("platform", "other"),
            )
            return {"backlink_id": bl_id, "status": "tracking"}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
