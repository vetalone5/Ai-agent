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
    "collect-positions-daily": {
        "task": "src.workers.tasks.collect_positions",
        "schedule": crontab(hour=6, minute=0),
    },
    "collect-traffic-daily": {
        "task": "src.workers.tasks.collect_traffic",
        "schedule": crontab(hour=8, minute=0),
    },
    "full-audit-weekly": {
        "task": "src.workers.tasks.run_full_audit",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),
    },
    "orchestrator-plan-weekly": {
        "task": "src.workers.tasks.orchestrator_plan",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    "weekly-report": {
        "task": "src.workers.tasks.generate_weekly_report",
        "schedule": crontab(hour=17, minute=0, day_of_week=5),
    },
}
