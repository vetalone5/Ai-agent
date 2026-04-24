import logging
from typing import Any

from src.config.constants import AgentType
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AIVisibilityAgent(BaseAgent):
    agent_type = AgentType.AI_VISIBILITY

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.ai_visibility.entity_optimizer import EntityOptimizer
        from src.agents.ai_visibility.kyu_strategy import KyuStrategy
        from src.agents.ai_visibility.spioniro_client import SpioniroTracker

        self.tracker = SpioniroTracker()
        self.kyu = KyuStrategy(session_factory, claude_client)
        self.entity = EntityOptimizer(claude_client)

    async def get_capabilities(self) -> list[str]:
        return [
            "visibility_report",
            "check_keywords",
            "generate_kyu_questions",
            "generate_kyu_answer",
            "audit_entity",
            "generate_wikidata",
            "generate_org_schema",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")
        data = task_data.get("data", {})

        if task_type == "visibility_report":
            return await self.tracker.get_full_visibility_report()

        elif task_type == "check_keywords":
            keywords = data.get("keywords", [])
            platform = data.get("platform", "yandex_gpt")
            return await self.tracker.check_keyword_batch(keywords, platform)

        elif task_type == "generate_kyu_questions":
            questions = await self.kyu.generate_questions(limit=data.get("limit", 20))
            return {"questions": questions, "count": len(questions)}

        elif task_type == "generate_kyu_answer":
            answer = await self.kyu.generate_answer(
                question=data["question"],
                keyword=data.get("keyword", ""),
                article_url=data.get("article_url", ""),
            )
            return {"answer": answer, "requires_approval": True}

        elif task_type == "audit_entity":
            return await self.entity.audit_entity_presence()

        elif task_type == "generate_wikidata":
            return await self.entity.generate_wikidata_entry()

        elif task_type == "generate_org_schema":
            schema = await self.entity.generate_organization_schema()
            return {"schema": schema}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
