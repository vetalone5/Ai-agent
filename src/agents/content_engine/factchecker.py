"""Factchecking: verify names, descriptions, links, data freshness."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


FACTCHECK_PROMPT = """Ты — фактчекер. Проверь текст статьи на фактические ошибки.

Проверь:
1. Названия компаний, продуктов, сервисов — написаны правильно?
2. Цифры и статистика — выглядят правдоподобно? Не устарели?
3. Описания функций/возможностей — соответствуют реальности?
4. Ссылки и источники — выглядят живыми?
5. Даты — актуальны для {year} года?

Если нашёл ошибку, верни JSON-список:
[{{"line": "цитата из текста", "issue": "описание проблемы", "fix": "предложенное исправление"}}]

Если ошибок нет, верни пустой список: []
"""


class FactChecker:
    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client

    async def check(self, text: str, content_type: str) -> list[dict[str, str]]:
        """Run factcheck on article text."""
        issues = self._basic_checks(text)

        if content_type in ("review", "rating", "comparison", "resource_list"):
            ai_issues = await self._ai_factcheck(text)
            issues.extend(ai_issues)

        return issues

    def _basic_checks(self, text: str) -> list[dict[str, str]]:
        issues = []

        years = re.findall(r'20\d{2}', text)
        old_years = [y for y in years if int(y) < 2024]
        if old_years:
            issues.append({
                "type": "outdated_year",
                "detail": f"References to old years: {set(old_years)}. Verify data is current.",
            })

        urls = re.findall(r'https?://[^\s\)\"]+', text)
        for url in urls:
            if any(dead in url for dead in ["example.com", "test.com", "placeholder"]):
                issues.append({"type": "placeholder_url", "detail": f"Placeholder URL: {url}"})

        big_numbers = re.findall(r'\d{6,}', text)
        for num in big_numbers:
            if int(num) > 10_000_000_000:
                issues.append({"type": "suspicious_number", "detail": f"Very large number: {num}"})

        return issues

    async def _ai_factcheck(self, text: str) -> list[dict[str, str]]:
        try:
            from datetime import datetime
            year = datetime.now().year
            prompt = FACTCHECK_PROMPT.format(year=year)
            response = await self._claude.complete(
                system_prompt=prompt,
                user_prompt=f"Текст для проверки:\n\n{text[:6000]}",
                max_tokens=1000,
                temperature=0.2,
            )
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return []
        except Exception as e:
            logger.warning("AI factcheck failed: %s", e)
            return []
