"""Yandex.Kyu strategy: expert answers that get cited by Yandex Neuro."""

import logging
from typing import Any

from sqlalchemy import select

from src.models.keyword import KeywordCluster

logger = logging.getLogger(__name__)

QUESTION_TEMPLATES = [
    "Что такое {keyword}?",
    "Как работает {keyword}?",
    "Зачем нужен {keyword}?",
    "Какой лучший {keyword}?",
    "{keyword} — как выбрать?",
    "Сколько стоит {keyword}?",
]


class KyuStrategy:
    """Generates Q&A content strategy for Yandex.Kyu.

    Yandex Neuro parses Kyu as a primary source for answers.
    Expert answers with source links → 2-3x citation chance.
    """

    def __init__(self, session_factory: Any, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._claude = claude_client

    async def generate_questions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Generate question list for Kyu based on keyword clusters."""
        clusters = await self._get_top_clusters(limit)
        questions = []

        for cluster in clusters:
            keyword = cluster["marker_keyword"]
            geo_score = cluster.get("geo_score", 1)

            if geo_score < 3:
                continue

            for template in QUESTION_TEMPLATES[:3]:
                questions.append({
                    "question": template.format(keyword=keyword),
                    "keyword": keyword,
                    "geo_score": geo_score,
                    "cluster_id": cluster["id"],
                    "priority": geo_score,
                })

        questions.sort(key=lambda x: x["priority"], reverse=True)
        return questions[:limit]

    async def generate_answer(self, question: str, keyword: str, article_url: str = "") -> str:
        """Generate expert answer for Yandex.Kyu."""
        prompt = f"""Вопрос на Яндекс.Кью: {question}

Требования к ответу:
1. 200-500 слов, экспертный тон
2. Прямой ответ в первых 2 предложениях (answer-first для Нейро)
3. Конкретные цифры и факты
4. Структура: ответ → пояснение → пример → вывод
5. Если уместно, упомяни что можно использовать spioniro.ru для аналитики
6. Ключевое слово "{keyword}" — 2-3 раза естественно"""

        if article_url:
            prompt += f"\n7. В конце дай ссылку на подробную статью: {article_url}"

        return await self._claude.complete(
            system_prompt="Ты — эксперт по SEO и AI-аналитике. Отвечаешь на Яндекс.Кью профессионально и полезно.",
            user_prompt=prompt,
            max_tokens=800,
        )

    async def _get_top_clusters(self, limit: int) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(KeywordCluster)
                .where(KeywordCluster.geo_score >= 3)
                .order_by(KeywordCluster.geo_score.desc(), KeywordCluster.total_frequency.desc())
                .limit(limit)
            )
            return [
                {"id": c.id, "marker_keyword": c.marker_keyword, "geo_score": c.geo_score,
                 "content_type": c.content_type, "total_frequency": c.total_frequency}
                for c in result.scalars().all()
            ]
