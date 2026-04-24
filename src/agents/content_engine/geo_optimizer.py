"""GEO optimization for AI citation (answer-first, quotable sentences, FAQ blocks)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

GEO_SYSTEM_PROMPT = """Ты оптимизируешь текст для цитирования нейросетями (Яндекс Нейро, ChatGPT, GigaChat).

Правила GEO-оптимизации:

1. ANSWER-FIRST: После каждого H2 — прямой ответ в 40-60 слов. Не «давайте разберёмся», а сразу факт.

2. QUOTABLE SENTENCES: Каждый 150-200 слов вставляй самодостаточную фразу с цифрой или фактом.
   Пример: «По данным 2025 года, 67% поисковых запросов в Яндексе сопровождаются нейросетевым ответом.»

3. ФАКТИЧЕСКАЯ ПЛОТНОСТЬ: Статистика, цифра или конкретный факт каждые 150-200 слов.

4. FAQ-БЛОК: В конце статьи — 5-8 вопросов с ответами 40-80 слов каждый. Каждый ответ самодостаточен.

5. ОПРЕДЕЛЕНИЯ: Первое упоминание термина — дай чёткое определение в 1-2 предложения.

6. СТРУКТУРИРОВАННЫЕ ДАННЫЕ: Списки, таблицы, пошаговые инструкции — нейросети их парсят лучше.

7. ПРЯМЫЕ УТВЕРЖДЕНИЯ: «X — это Y, который Z» вместо размытых «X может быть связан с Y».

8. АВТОРИТЕТНЫЕ ИСТОЧНИКИ: Ссылки на исследования, данные отрасли, экспертные мнения.
"""

FAQ_PROMPT_TEMPLATE = """Сгенерируй FAQ-блок из {count} вопросов по теме: {topic}

Требования:
- Вопросы начинаются с «Что», «Как», «Зачем», «Сколько», «Какой», «Почему»
- Каждый ответ: 40-80 слов, самодостаточный (можно вырвать из контекста и он будет понятен)
- Включай конкретные цифры или факты в каждый ответ
- Формат: ## Часто задаваемые вопросы\\n\\n### Вопрос?\\nОтвет.
"""


def build_geo_instructions(geo_score: int, content_type: str) -> str:
    """Build GEO optimization instructions based on score."""
    if geo_score <= 2:
        return "Минимальная GEO: прямой ответ после первого H2, 1 FAQ в конце."

    if geo_score == 3:
        return (
            "Средняя GEO: answer-first после каждого H2 (40-60 слов), "
            "quotable sentences каждые 200 слов, FAQ 3-5 вопросов."
        )

    if geo_score == 4:
        return (
            "Высокая GEO: answer-first после КАЖДОГО H2 (40-60 слов), "
            "quotable sentence каждые 150 слов с цифрами, "
            "определения всех терминов, FAQ 5-7 вопросов (40-80 слов каждый), "
            "таблица сравнения если уместна."
        )

    return (
        "Максимальная GEO: answer-first ОБЯЗАТЕЛЬНО после каждого H2, "
        "quotable sentence каждые 100-150 слов, "
        "чёткие определения всех терминов в первом упоминании, "
        "FAQ 7-10 вопросов (40-80 слов, самодостаточных), "
        "списки и таблицы через каждые 300-400 слов, "
        "прямые утверждения вместо размытых формулировок."
    )


def check_geo_quality(text: str, geo_score: int) -> list[dict[str, str]]:
    """Check if text meets GEO optimization standards."""
    issues = []
    word_count = len(text.split())

    if geo_score >= 3:
        if "?" not in text.split("\n")[-20:]:
            issues.append({"type": "no_faq", "detail": "No FAQ section found at the end"})

    if geo_score >= 4:
        sections = text.split("## ")
        for section in sections[1:]:
            lines = section.strip().split("\n")
            if lines:
                first_para = " ".join(lines[1:3]) if len(lines) > 1 else ""
                if len(first_para.split()) < 20:
                    title = lines[0][:40]
                    issues.append({"type": "no_answer_first", "detail": f"Section '{title}' lacks answer-first paragraph"})

    if geo_score >= 4:
        import re
        numbers = re.findall(r'\d+[%$€₽]|\d+\.\d+|\d{2,}', text)
        expected = word_count // 200
        if len(numbers) < expected:
            issues.append({"type": "low_fact_density", "detail": f"Found {len(numbers)} facts, expected {expected}+"})

    return issues
