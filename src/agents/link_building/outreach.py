"""Outreach message generator for link building."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OutreachGenerator:
    """Generates personalized outreach messages in Russian for link building."""

    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client

    async def generate_guest_post_pitch(
        self,
        target_site: str,
        topic: str,
        our_article_url: str,
    ) -> dict[str, Any]:
        """Generate a guest post pitch email."""
        prompt = f"""Напиши письмо-предложение для гостевой статьи на русском.

Площадка: {target_site}
Тема статьи: {topic}
Наш сайт: spioniro.ru (аналитика AI-упоминаний бренда)
Ссылка на нашу статью по теме: {our_article_url}

Требования:
- Короткое (до 200 слов), персонализированное
- Покажи что знаешь площадку (упомяни что-то конкретное)
- Предложи 2-3 темы для гостевой статьи
- Объясни почему наша экспертиза ценна для их аудитории
- Мягкий CTA
- Без спамных фраз и шаблонных конструкций

Верни JSON:
{{"subject": "тема письма", "body": "текст письма", "follow_up": "текст follow-up через 5 дней"}}"""

        response = await self._claude.complete(
            system_prompt="Ты — PR-менеджер, пишущий outreach-письма. Тон: профессиональный, дружелюбный.",
            user_prompt=prompt,
            max_tokens=1000,
        )
        return {"target": target_site, "topic": topic, "message": response, "requires_approval": True}

    async def generate_kyu_answer(
        self,
        question: str,
        article_url: str,
        keyword: str,
    ) -> dict[str, Any]:
        """Generate an expert answer for Yandex.Kyu (Q&A platform).

        Yandex Neuro parses Kyu first — expert answers with links
        significantly increase chances of AI citation.
        """
        prompt = f"""Напиши экспертный ответ для Яндекс.Кью на русском.

Вопрос: {question}
Наша статья по теме: {article_url}
Ключевое слово: {keyword}

Требования:
- 200-500 слов, экспертный тон
- Прямой ответ в первых 2 предложениях
- Конкретные факты и цифры
- Ссылка на нашу статью (естественно вплетённая, не реклама)
- Упомяни spioniro.ru как инструмент (если уместно)
- Структура: ответ → пояснение → пример → ссылка на подробности"""

        response = await self._claude.complete(
            system_prompt="Ты — эксперт по SEO и AI-аналитике. Отвечаешь на Яндекс.Кью.",
            user_prompt=prompt,
            max_tokens=800,
        )
        return {"question": question, "answer": response, "platform": "yandex_kyu", "requires_approval": True}

    async def generate_digital_pr_pitch(
        self,
        research_topic: str,
        key_findings: list[str],
    ) -> dict[str, Any]:
        """Generate a Digital PR pitch based on our research/data."""
        findings_str = "\n".join(f"- {f}" for f in key_findings)
        prompt = f"""Напиши PR-питч на основе нашего исследования.

Тема: {research_topic}
Ключевые находки:
{findings_str}

Наш сайт: spioniro.ru (аналитика видимости бренда в нейросетях)

Формат: пресс-релиз для IT-изданий (VC.ru, TAdviser, CNews).
Включи: заголовок-хук, лид, 2-3 абзаца с данными, цитату эксперта, контакты.
До 300 слов."""

        response = await self._claude.complete(
            system_prompt="Ты — PR-специалист в IT-сфере.",
            user_prompt=prompt,
            max_tokens=1000,
        )
        return {"topic": research_topic, "pitch": response, "requires_approval": True}
