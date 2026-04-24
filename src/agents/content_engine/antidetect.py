"""15 rules for human-like text that bypasses AI detectors."""

import re
from src.config.constants import ANTIDETECT_FORBIDDEN_PHRASES

ANTIDETECT_SYSTEM_PROMPT = """Ты — опытный SEO-копирайтер. Пиши ЧЕЛОВЕЧНЫМ языком. Строго следуй этим правилам:

1. ВАРИАТИВНОСТЬ ДЛИНЫ: чередуй короткие (5-10 слов) и длинные (25-35 слов) предложения. Никогда больше 3 предложений одной длины подряд.

2. РАЗГОВОРНЫЕ ВСТАВКИ: вставляй «честно говоря», «на практике», «по нашему опыту», «если коротко» — минимум 2-3 раза на 1000 слов.

3. АВТОРСКАЯ ПОЗИЦИЯ: используй «мы протестировали», «я считаю», «по нашим данным». Не прячься за безличными конструкциями.

4. КОНКРЕТИКА ВМЕСТО АБСТРАКЦИЙ: вместо «значительно улучшилось» — «выросло на 34% за 2 месяца». Цифры и факты.

5. ЭМОЦИОНАЛЬНЫЕ АКЦЕНТЫ: «удивительно, но», «самое интересное —», «вот что действительно важно». 1-2 на 500 слов.

6. РИТОРИЧЕСКИЕ ВОПРОСЫ: вставляй вопросы к читателю. «Знакомо?», «А вы замечали?». 1-2 на раздел.

7. ПРЯМЫЕ ЦИТАТЫ: когда ссылаешься на источники, используй точные цитаты в кавычках.

8. НЕИДЕАЛЬНОСТЬ: допускай сознательно «шероховатый» стиль. Начинай предложения с «И», «Но», «А ведь».

9. КОНКРЕТНЫЕ ПРИМЕРЫ: каждый тезис подкрепляй реальным примером или числом.

10. АБЗАЦЫ РАЗНОЙ ДЛИНЫ: 1 предложение, потом 3-4, потом 2. Не делай все абзацы одинаковыми.

11. МАРКИРОВАННЫЕ И НУМЕРОВАННЫЕ СПИСКИ: используй, но разбавляй текстом. Не больше 2 списков подряд.

12. ПОДЗАГОЛОВКИ-ВОПРОСЫ: часть H2/H3 формулируй как вопросы. «Зачем нужна GEO-оптимизация?»

13. МИКРОИСТОРИИ: вставляй мини-кейсы 2-3 предложения. «Один наш клиент...», «В прошлом году мы...».

14. ПЕРЕХОДЫ МЕЖДУ РАЗДЕЛАМИ: естественные связки, а не формальные. «Окей, разобрались с теорией. Теперь к практике.»

15. ЗАПРЕЩЁННЫЕ ФРАЗЫ: НИКОГДА не используй эти маркеры ИИ:
""" + "\n".join(f"- {p}" for p in ANTIDETECT_FORBIDDEN_PHRASES)


def check_antidetect(text: str) -> list[dict[str, str]]:
    """Check text for AI markers and return list of issues."""
    issues = []

    for phrase in ANTIDETECT_FORBIDDEN_PHRASES:
        if phrase.lower() in text.lower():
            issues.append({"type": "forbidden_phrase", "detail": f"Found: '{phrase}'"})

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if sentences:
        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        if variance < 15:
            issues.append({"type": "low_variance", "detail": f"Sentence length variance too low: {variance:.1f}"})

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        p_lengths = [len(p.split()) for p in paragraphs]
        if len(set(round(l / 10) for l in p_lengths)) < len(p_lengths) * 0.4:
            issues.append({"type": "uniform_paragraphs", "detail": "Paragraph lengths are too uniform"})

    questions = text.count("?")
    word_count = len(text.split())
    if word_count > 500 and questions < 2:
        issues.append({"type": "no_questions", "detail": "No rhetorical questions found"})

    return issues
