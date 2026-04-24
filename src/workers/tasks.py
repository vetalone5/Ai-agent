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


def _get_deps():
    from src.core.claude_client import ClaudeClient
    from src.core.task_manager import TaskManager
    from src.db.session import get_session
    return ClaudeClient(), TaskManager(get_session), get_session


def _get_analytics_agent():
    from src.agents.analytics.agent import AnalyticsAgent
    claude, task_mgr, session = _get_deps()
    return AnalyticsAgent(claude, task_mgr, session)


def _get_seo_audit_agent():
    from src.agents.seo_audit.agent import SEOAuditAgent
    claude, task_mgr, session = _get_deps()
    return SEOAuditAgent(claude, task_mgr, session)


def _get_technical_seo_agent():
    from src.agents.technical_seo.agent import TechnicalSEOAgent
    claude, task_mgr, session = _get_deps()
    return TechnicalSEOAgent(claude, task_mgr, session)


# --- Analytics Agent tasks ---

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


@app.task(name="src.workers.tasks.generate_weekly_report")
def generate_weekly_report():
    logger.info("Generating weekly report...")
    agent = _get_analytics_agent()
    result = _run_async(agent.reports.generate_weekly_report())
    logger.info("Report generated: %s", result.get("summary", "")[:100])
    return result


# --- SEO Audit Agent tasks ---

@app.task(name="src.workers.tasks.run_full_audit")
def run_full_audit():
    logger.info("Running full site audit (crawl + issues)...")
    agent = _get_seo_audit_agent()
    result = _run_async(agent.crawler.run_full_crawl())
    logger.info("Audit complete: %s", result)
    return result


@app.task(name="src.workers.tasks.run_keyword_research")
def run_keyword_research():
    logger.info("Running keyword research...")
    agent = _get_seo_audit_agent()
    result = _run_async(agent.keywords.run_full_research())
    logger.info("Keyword research: %s", result)
    return result


@app.task(name="src.workers.tasks.run_competitor_analysis")
def run_competitor_analysis():
    logger.info("Analyzing competitors...")
    agent = _get_seo_audit_agent()
    result = _run_async(agent.competitors.analyze_all())
    logger.info("Competitor analysis: %d competitors", len(result))
    return {"count": len(result)}


# --- Technical SEO Agent tasks ---

@app.task(name="src.workers.tasks.update_sitemap")
def update_sitemap():
    logger.info("Updating sitemap.xml...")
    agent = _get_technical_seo_agent()
    result = _run_async(agent.sitemap.generate_sitemap())
    logger.info("Sitemap updated: %d chars", len(result))
    return {"size": len(result)}


@app.task(name="src.workers.tasks.check_cwv")
def check_cwv():
    from src.config.settings import settings
    logger.info("Checking Core Web Vitals...")
    agent = _get_technical_seo_agent()
    urls = [settings.target_site_url, f"{settings.target_site_url}/blog"]
    result = _run_async(agent.cwv.check_urls(urls))
    logger.info("CWV check: %d URLs analyzed", len(result))
    return {"urls_checked": len(result)}


# --- Link Building Agent tasks ---

def _get_link_building_agent():
    from src.agents.link_building.agent import LinkBuildingAgent
    claude, task_mgr, session = _get_deps()
    return LinkBuildingAgent(claude, task_mgr, session)


@app.task(name="src.workers.tasks.check_backlinks")
def check_backlinks():
    logger.info("Checking backlink health...")
    agent = _get_link_building_agent()
    result = _run_async(agent.backlinks.check_all_backlinks())
    logger.info("Backlink check: %s", result)
    return result


# --- AI Visibility Agent tasks ---

def _get_ai_visibility_agent():
    from src.agents.ai_visibility.agent import AIVisibilityAgent
    claude, task_mgr, session = _get_deps()
    return AIVisibilityAgent(claude, task_mgr, session)


@app.task(name="src.workers.tasks.check_ai_visibility")
def check_ai_visibility():
    logger.info("Checking AI visibility...")
    agent = _get_ai_visibility_agent()
    result = _run_async(agent.tracker.get_full_visibility_report())
    logger.info("AI visibility: %s", result)
    return result


# --- Orchestrator ---

def _get_orchestrator():
    from src.core.orchestrator import Orchestrator
    from src.core.event_bus import EventBus
    claude, task_mgr, session = _get_deps()
    return Orchestrator(claude, task_mgr, session, EventBus())


@app.task(name="src.workers.tasks.orchestrator_plan")
def orchestrator_plan():
    logger.info("Running orchestrator weekly planning...")
    orch = _get_orchestrator()
    result = _run_async(orch.create_weekly_plan())
    logger.info("Plan created: %d tasks", result.get("tasks_created", 0))
    return result


@app.task(name="src.workers.tasks.orchestrator_dispatch")
def orchestrator_dispatch():
    logger.info("Dispatching pending tasks...")
    orch = _get_orchestrator()
    result = _run_async(orch.dispatch_pending_tasks())
    logger.info("Dispatched: %s", result)
    return result
