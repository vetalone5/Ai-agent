"""Adapt articles for different publishing platforms."""

import logging
from typing import Any

from src.config.constants import Platform

logger = logging.getLogger(__name__)

PLATFORM_PROMPTS: dict[Platform, str] = {
    Platform.BLOG: (
        "Формат для блога spioniro.ru: полная версия статьи с внутренними ссылками, "
        "schema-разметкой, CTA на регистрацию. Профессиональный, но доступный тон."
    ),
    Platform.VC_RU: (
        "Формат для VC.ru: экспертный стиль, БЕЗ прямой рекламы, мягкий CTA в конце. "
        "Заголовок кликбейтный но не жёлтый. 3000-10000 символов. "
        "Начинай с интригующего тезиса. Абзацы 2-4 предложения."
    ),
    Platform.DZEN: (
        "Формат для Яндекс.Дзен: разговорный стиль, короткие абзацы (1-3 предложения), "
        "кликбейтный заголовок, акцент на дочитываемости. "
        "Первые 2 абзаца — самое интересное (хук). Объём 2000-5000 символов."
    ),
    Platform.HABR: (
        "Формат для Хабр: технический стиль, markdown, данные и графики, "
        "минимум маркетинга, код-примеры если уместно. "
        "Строгая модерация — без PR и пустых обещаний."
    ),
    Platform.TELEGRAM: (
        "Формат для Telegram: выжимка 500-1000 символов + ссылка на полную версию. "
        "Формат: 🔥 заголовок-хук, 3-5 ключевых пунктов, CTA с ссылкой."
    ),
}


class PlatformAdapter:
    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client

    async def adapt(self, article_md: str, target_platform: Platform, keyword: str) -> str:
        """Adapt an article for a specific platform."""
        if target_platform == Platform.BLOG:
            return article_md

        prompt = PLATFORM_PROMPTS.get(target_platform, "")
        response = await self._claude.complete(
            system_prompt=(
                f"Ты — редактор контента. Адаптируй статью для платформы.\n{prompt}"
            ),
            user_prompt=(
                f"Ключевое слово: {keyword}\n\n"
                f"Исходная статья (markdown):\n\n{article_md[:5000]}"
            ),
            max_tokens=3000,
        )
        return response

    def build_utm_link(self, base_url: str, platform: Platform, campaign: str) -> str:
        """Build UTM-tagged link for a platform."""
        source_map = {
            Platform.VC_RU: "vcru",
            Platform.DZEN: "dzen",
            Platform.HABR: "habr",
            Platform.TELEGRAM: "telegram",
            Platform.YANDEX_KYU: "yandex_kyu",
        }
        source = source_map.get(platform, platform.value)
        return f"{base_url}?utm_source={source}&utm_medium=content&utm_campaign={campaign}"
