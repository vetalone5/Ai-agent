import asyncio
import logging

from src.workers.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async code from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_analytics_agent():
    from src.core.claude_client import ClaudeClient
    from src.core.task_manager import TaskManager
    from src.db.session import get_session
    from src.agents.analytics.agent import AnalyticsAgent

    claude = ClaudeClient()
    task_mgr = TaskManager(get_session)
    return AnalyticsAgent(claude, task_mgr, get_session)


@app.task(name="src.workers.tasks.collect_positions")
def collect_positions():
    logger.info("Collecting positions from GSC and Yandex Webmaster...")
    agent = _get_analytics_agent()
    result = _run_async(agent.positions.collect_positions())
    logger.info("Positions collected: %s", result)
    return result


@app.task(name="src.workers.tasks.collect_traffic")
def collect_traffic():
    logger.info("Collecting traffic data from Yandex.Metrica...")
    agent = _get_analytics_agent()
    result = _run_async(agent.traffic.collect_daily_traffic())
    logger.info("Traffic collected: %s", result)
    return result


@app.task(name="src.workers.tasks.analyze_behavioral")
def analyze_behavioral():
    logger.info("Analyzing behavioral metrics...")
    agent = _get_analytics_agent()
    result = _run_async(agent.behavioral.analyze_and_create_tasks())
    logger.info("Behavioral analysis: %s", result)
    return result


@app.task(name="src.workers.tasks.collect_geo_metrics")
def collect_geo_metrics():
    logger.info("Collecting GEO metrics from spioniro.ru API...")
    agent = _get_analytics_agent()
    result = _run_async(agent.geo.collect_ai_citations())
    logger.info("GEO metrics: %s", result)
    return result


@app.task(name="src.workers.tasks.run_full_audit")
def run_full_audit():
    logger.info("Running full site audit...")
    # Will be implemented with SEO Audit Agent in Week 3


@app.task(name="src.workers.tasks.orchestrator_plan")
def orchestrator_plan():
    logger.info("Running orchestrator weekly planning...")
    # Will be implemented with Orchestrator in Phase 2


@app.task(name="src.workers.tasks.generate_weekly_report")
def generate_weekly_report():
    logger.info("Generating weekly report...")
    agent = _get_analytics_agent()
    result = _run_async(agent.reports.generate_weekly_report())
    logger.info("Report generated: %s", result.get("summary", "")[:100])
    return result
