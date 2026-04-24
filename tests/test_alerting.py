"""Tests for alerting system."""

import pytest

from src.tools.alerting import AlertManager, TelegramAlerter


@pytest.mark.asyncio
async def test_telegram_dry_run():
    alerter = TelegramAlerter(bot_token="", chat_id="")
    result = await alerter.send("test message")
    assert result is False


@pytest.mark.asyncio
async def test_alert_manager_no_crash():
    tg = TelegramAlerter()
    manager = AlertManager(tg)
    await manager.on_article_published("Test", "https://example.com")
    await manager.on_task_failed(1, "test_task", "some error")
    await manager.on_weekly_report("Test summary")
