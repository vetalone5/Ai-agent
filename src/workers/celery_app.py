from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

app = Celery("seo_agents", broker=settings.redis_url, backend=settings.redis_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    # Daily — Analytics Agent
    "collect-positions-daily": {
        "task": "src.workers.tasks.collect_positions",
        "schedule": crontab(hour=6, minute=0),
    },
    "collect-traffic-daily": {
        "task": "src.workers.tasks.collect_traffic",
        "schedule": crontab(hour=8, minute=0),
    },
    "analyze-behavioral-weekly": {
        "task": "src.workers.tasks.analyze_behavioral",
        "schedule": crontab(hour=10, minute=0, day_of_week="1,4"),
    },
    "collect-geo-metrics-weekly": {
        "task": "src.workers.tasks.collect_geo_metrics",
        "schedule": crontab(hour=15, minute=0, day_of_week=3),
    },
    # Weekly — SEO Audit Agent
    "full-audit-weekly": {
        "task": "src.workers.tasks.run_full_audit",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),
    },
    "keyword-research-weekly": {
        "task": "src.workers.tasks.run_keyword_research",
        "schedule": crontab(hour=10, minute=0, day_of_week=3),
    },
    "competitor-analysis-weekly": {
        "task": "src.workers.tasks.run_competitor_analysis",
        "schedule": crontab(hour=10, minute=0, day_of_week=2),
    },
    # Weekly — Technical SEO Agent
    "update-sitemap-weekly": {
        "task": "src.workers.tasks.update_sitemap",
        "schedule": crontab(hour=5, minute=0, day_of_week=1),
    },
    "check-cwv-weekly": {
        "task": "src.workers.tasks.check_cwv",
        "schedule": crontab(hour=4, minute=0, day_of_week=6),
    },
    # Weekly — Orchestrator
    "orchestrator-plan-weekly": {
        "task": "src.workers.tasks.orchestrator_plan",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    # Weekly — Report
    "weekly-report": {
        "task": "src.workers.tasks.generate_weekly_report",
        "schedule": crontab(hour=17, minute=0, day_of_week=5),
    },
}
