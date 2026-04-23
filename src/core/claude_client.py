import asyncio
import logging
from datetime import date, datetime, timezone

import anthropic

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model
        self._max_retries = settings.claude_max_retries
        self._retry_delay = settings.claude_retry_delay
        self._daily_limit = settings.claude_max_tokens_per_day
        self._tokens_used_today: int = 0
        self._usage_date: date = datetime.now(timezone.utc).date()

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

        raise RuntimeError(f"Claude API failed after {self._max_retries} attempts: {last_error}")

    @property
    def tokens_used_today(self) -> int:
        return self._tokens_used_today

    @property
    def tokens_remaining_today(self) -> int:
        return max(0, self._daily_limit - self._tokens_used_today)
