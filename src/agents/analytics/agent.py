import logging
from typing import Any

from src.config.constants import AgentType
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AnalyticsAgent(BaseAgent):
    agent_type = AgentType.ANALYTICS

    def __init__(self, claude_client: Any, task_manager: Any, session_factory: Any) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory

        from src.agents.analytics.behavioral_analyzer import BehavioralAnalyzer
        from src.agents.analytics.geo_metrics import GeoMetricsCollector
        from src.agents.analytics.position_tracker import PositionTracker
        from src.agents.analytics.report_generator import ReportGenerator
        from src.agents.analytics.traffic_analyzer import TrafficAnalyzer

        self.positions = PositionTracker(session_factory)
        self.traffic = TrafficAnalyzer(session_factory)
        self.behavioral = BehavioralAnalyzer(session_factory, task_manager)
        self.geo = GeoMetricsCollector(session_factory)
        self.reports = ReportGenerator(session_factory, claude_client)

    async def get_capabilities(self) -> list[str]:
        return [
            "collect_positions",
            "collect_traffic",
            "analyze_behavioral",
            "collect_geo_metrics",
            "generate_weekly_report",
            "get_utm_report",
        ]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")

        if task_type == "collect_positions":
            result = await self.positions.collect_positions()
            return {"status": "ok", "counts": result}

        elif task_type == "collect_traffic":
            result = await self.traffic.collect_daily_traffic()
            return {"status": "ok", "metrics": result}

        elif task_type == "analyze_behavioral":
            result = await self.behavioral.analyze_and_create_tasks()
            return {"status": "ok", **result}

        elif task_type == "collect_geo_metrics":
            result = await self.geo.collect_ai_citations()
            return {"status": "ok", **result}

        elif task_type == "generate_weekly_report":
            result = await self.reports.generate_weekly_report()
            return {"status": "ok", **result}

        elif task_type == "get_utm_report":
            result = await self.traffic.get_utm_report()
            return {"status": "ok", "utm_data": result}

        else:
            raise ValueError(f"Unknown task type: {task_type}")
