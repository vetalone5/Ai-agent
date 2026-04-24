import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """LLM client supporting both Anthropic direct API and OpenRouter."""

    def __init__(self) -> None:
        provider = self._detect_provider()
        self._provider = provider
        self._max_retries = settings.claude_max_retries
        self._retry_delay = settings.claude_retry_delay
        self._daily_limit = settings.claude_max_tokens_per_day
        self._tokens_used_today: int = 0
        self._usage_date: date = datetime.now(timezone.utc).date()

        if provider == "openrouter":
            self._api_key = settings.openrouter_api_key
            self._base_url = settings.openrouter_base_url
            self._model = f"anthropic/{settings.claude_model}"
            self._client: Any = None
            logger.info("LLM provider: OpenRouter (model: %s)", self._model)
        else:
            self._api_key = settings.anthropic_api_key
            self._base_url = "https://api.anthropic.com"
            self._model = settings.claude_model
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            logger.info("LLM provider: Anthropic direct (model: %s)", self._model)

    @staticmethod
    def _detect_provider() -> str:
        if settings.llm_provider == "openrouter":
            return "openrouter"
        if settings.llm_provider == "anthropic":
            return "anthropic"
        if settings.openrouter_api_key:
            return "openrouter"
        if settings.anthropic_api_key:
            return "anthropic"
        return "anthropic"

    def _check_budget(self, estimated_tokens: int) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._usage_date:
            self._tokens_used_today = 0
            self._usage_date = today

        if self._tokens_used_today + estimated_tokens > self._daily_limit:
            raise RuntimeError(
                f"Daily token budget exceeded: {self._tokens_used_today}/{self._daily_limit}"
            )

    def _track_usage(self, input_tokens: int, output_tokens: int) -> None:
        self._tokens_used_today += input_tokens + output_tokens
        logger.debug(
            "Token usage: +%d (in: %d, out: %d), daily total: %d/%d",
            input_tokens + output_tokens,
            input_tokens,
            output_tokens,
            self._tokens_used_today,
            self._daily_limit,
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._check_budget(max_tokens)

        if self._provider == "openrouter":
            return await self._complete_openrouter(system_prompt, user_prompt, max_tokens, temperature)
        return await self._complete_anthropic(system_prompt, user_prompt, max_tokens, temperature)

    async def _complete_anthropic(
        self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        import anthropic

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
                self._track_usage(response.usage.input_tokens, response.usage.output_tokens)
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_blocks)

            except anthropic.RateLimitError as e:
                last_error = e
                wait = self._retry_delay * (2 ** (attempt - 1))
                logger.warning("Rate limited (attempt %d/%d), waiting %.1fs", attempt, self._max_retries, wait)
                await asyncio.sleep(wait)

            except anthropic.APIError as e:
                last_error = e
                if attempt < self._max_retries:
                    wait = self._retry_delay * (2 ** (attempt - 1))
                    logger.warning("API error (attempt %d/%d): %s, retrying in %.1fs", attempt, self._max_retries, e, wait)
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"Anthropic API failed after {self._max_retries} attempts: {last_error}")

    async def _complete_openrouter(
        self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """Call LLM via OpenRouter (OpenAI-compatible API)."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as http:
                    response = await http.post(
                        f"{self._base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": settings.target_site_url,
                            "X-Title": "SEO Agents",
                        },
                        json={
                            "model": self._model,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                    )

                if response.status_code == 429:
                    last_error = RuntimeError(f"Rate limited: {response.text}")
                    wait = self._retry_delay * (2 ** (attempt - 1))
                    logger.warning("OpenRouter rate limited (attempt %d/%d), waiting %.1fs", attempt, self._max_retries, wait)
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                usage = data.get("usage", {})
                self._track_usage(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                )

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError(f"No choices in response: {data}")

                return choices[0].get("message", {}).get("content", "")

            except httpx.HTTPStatusError as e:
                last_error = e
                if attempt < self._max_retries:
                    wait = self._retry_delay * (2 ** (attempt - 1))
                    logger.warning("OpenRouter HTTP error (attempt %d/%d): %s", attempt, self._max_retries, e)
                    await asyncio.sleep(wait)
                else:
                    raise

            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    wait = self._retry_delay * (2 ** (attempt - 1))
                    logger.warning("OpenRouter error (attempt %d/%d): %s", attempt, self._max_retries, e)
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"OpenRouter API failed after {self._max_retries} attempts: {last_error}")

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def tokens_used_today(self) -> int:
        return self._tokens_used_today

    @property
    def tokens_remaining_today(self) -> int:
        return max(0, self._daily_limit - self._tokens_used_today)
