"""Tests for antidetect text quality checks."""

from src.agents.content_engine.antidetect import check_antidetect


def test_forbidden_phrases_detected():
    text = "В современном мире очень важно следить за SEO. Подводя итоги, можно сказать что SEO работает."
    issues = check_antidetect(text)
    phrases_found = [i for i in issues if i["type"] == "forbidden_phrase"]
    assert len(phrases_found) >= 2


def test_clean_text_passes():
    text = (
        "Мы протестировали 15 инструментов за последние полгода. "
        "Честно говоря, результаты удивили. Вот что выяснилось.\n\n"
        "Первый инструмент показал рост на 34% за месяц. Это много.\n\n"
        "А вы замечали, как быстро меняются алгоритмы?\n\n"
        "По нашему опыту, самое важное — это регулярность. "
        "Один наш клиент получил 500 переходов за неделю."
    )
    issues = check_antidetect(text)
    phrases = [i for i in issues if i["type"] == "forbidden_phrase"]
    assert len(phrases) == 0


def test_low_variance_detected():
    text = ". ".join(["Это предложение из пяти слов"] * 30) + "."
    issues = check_antidetect(text)
    variance_issues = [i for i in issues if i["type"] == "low_variance"]
    assert len(variance_issues) > 0


def test_no_questions_detected():
    text = "Текст без вопросов, просто длинный абзац. " * 200
    issues = check_antidetect(text)
    q_issues = [i for i in issues if i["type"] == "no_questions"]
    assert len(q_issues) > 0
