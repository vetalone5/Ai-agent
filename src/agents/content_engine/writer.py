"""Article writer: generates content via Claude with SEO + antidetect + GEO rules."""

import logging
from typing import Any

from src.agents.content_engine.antidetect import ANTIDETECT_SYSTEM_PROMPT, check_antidetect
from src.agents.content_engine.geo_optimizer import (
    GEO_SYSTEM_PROMPT,
    build_geo_instructions,
    check_geo_quality,
)
from src.agents.content_engine.seo_optimizer import SEO_RULES_PROMPT
from src.agents.content_engine.templates import get_template
from src.config.constants import ContentType

logger = logging.getLogger(__name__)


class ArticleWriter:
    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client

    async def write_article(
        self,
        keyword: str,
        content_type: ContentType,
        lsi_keywords: list[str] | None = None,
        geo_score: int = 2,
        serp_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a full article with all optimizations applied."""
        template = get_template(content_type)
        geo_instructions = build_geo_instructions(geo_score, content_type)

        system_prompt = self._build_system_prompt(geo_score)
        user_prompt = self._build_user_prompt(
            keyword, template, lsi_keywords or [], geo_instructions, serp_data
        )

        word_min, word_max = template["word_range"]
        max_tokens = min(word_max * 3, 16000)

        raw_text = await self._claude.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=0.75,
        )

        antidetect_issues = check_antidetect(raw_text)
        if antidetect_issues:
            logger.info("Antidetect issues found: %d, requesting rewrite", len(antidetect_issues))
            raw_text = await self._fix_antidetect(raw_text, antidetect_issues)

        geo_issues = check_geo_quality(raw_text, geo_score)

        return {
            "content_md": raw_text,
            "word_count": len(raw_text.split()),
            "content_type": content_type,
            "keyword": keyword,
            "geo_score": geo_score,
            "antidetect_issues": antidetect_issues,
            "geo_issues": geo_issues,
            "template_used": template["name"],
        }

    def _build_system_prompt(self, geo_score: int) -> str:
        parts = [
            "Ты — экспертный SEO-копирайтер для сайта spioniro.ru (аналитика AI-упоминаний бренда).",
            "Пиши на русском языке.",
            SEO_RULES_PROMPT,
            ANTIDETECT_SYSTEM_PROMPT,
        ]
        if geo_score >= 3:
            parts.append(GEO_SYSTEM_PROMPT)
        return "\n\n".join(parts)

    @staticmethod
    def _build_user_prompt(
        keyword: str,
        template: dict,
        lsi_keywords: list[str],
        geo_instructions: str,
        serp_data: dict[str, Any] | None,
    ) -> str:
        sections = "\n".join(f"- {s}" for s in template["structure"])
        lsi_str = ", ".join(lsi_keywords[:15]) if lsi_keywords else "нет данных"
        word_min, word_max = template["word_range"]

        prompt = f"""Напиши статью типа "{template['name']}" на тему: **{keyword}**

Требования:
- Объём: {word_min}-{word_max} слов
- Формат: Markdown (H1, H2, H3, списки, таблицы)
- LSI-ключевики (вплети естественно): {lsi_str}
- Основной ключевик "{keyword}" — 5-8 раз на 3000 слов

Структура:
{sections}

Подсказка по типу: {template['prompt_hint']}

GEO-оптимизация: {geo_instructions}

E-E-A-T сигналы (ОБЯЗАТЕЛЬНО):
- Experience: "мы протестировали", "по нашему опыту", "за последние N месяцев мы"
- Expertise: ссылки на исследования, конкретные данные отрасли, профессиональная терминология
- Authoritativeness: "команда spioniro.ru проанализировала", упоминание кейсов клиентов
- Trust: указывай источники данных, дату актуальности, оговорки ("результаты могут отличаться")
- Добавь блок "Об авторе" в конце: "Материал подготовлен командой spioniro.ru — сервиса аналитики AI-упоминаний бренда."

Перелинковка: вставь 2-4 внутренние ссылки формата [текст анкора](/blog/slug).
UTM: вставь 2 ссылки на spioniro.ru с CTA.
"""
        if serp_data:
            prompt += f"\nАнализ SERP: конкуренты в топе пишут {serp_data.get('result_types', {})}, "
            prompt += f"уровень конкуренции: {serp_data.get('competitiveness', 'unknown')}.\n"

        return prompt

    async def _fix_antidetect(self, text: str, issues: list[dict[str, str]]) -> str:
        """Ask Claude to fix antidetect issues in the text."""
        issues_str = "\n".join(f"- {i['type']}: {i['detail']}" for i in issues)
        try:
            fixed = await self._claude.complete(
                system_prompt=(
                    "Ты — редактор. Исправь текст, чтобы он не определялся как AI-контент. "
                    "Сохрани весь смысл и SEO-оптимизацию. Верни полный текст."
                ),
                user_prompt=f"Проблемы:\n{issues_str}\n\nТекст:\n{text}",
                max_tokens=len(text.split()) * 3,
            )
            return fixed
        except Exception as e:
            logger.warning("Antidetect fix failed: %s", e)
            return text
