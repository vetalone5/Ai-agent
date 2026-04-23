import logging

from src.workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="src.workers.tasks.collect_positions")
def collect_positions():
    logger.info("Collecting positions from GSC and Yandex Webmaster...")


@app.task(name="src.workers.tasks.collect_traffic")
def collect_traffic():
    logger.info("Collecting traffic data from Yandex.Metrica...")


@app.task(name="src.workers.tasks.run_full_audit")
def run_full_audit():
    logger.info("Running full site audit...")


@app.task(name="src.workers.tasks.orchestrator_plan")
def orchestrator_plan():
    logger.info("Running orchestrator weekly planning...")


@app.task(name="src.workers.tasks.generate_weekly_report")
def generate_weekly_report():
    logger.info("Generating weekly report...")
