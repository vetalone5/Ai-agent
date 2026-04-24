import asyncio
import hashlib
import logging
from collections import OrderedDict
from datetime import date, datetime, timezone
from typing import Any

import httpx

from src.config.cost_config import COST_PER_1K_INPUT, COST_PER_1K_OUTPUT, ModelTier, estimate_cost
from src.config.settings import settings

logger = logging.getLogger(__name__)


class PromptCache:
    """Simple in-memory LRU cache for identical prompt+model combinations."""

    def __init__(self, max_size: int = 200) -> None:
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size
        self.hits = 0
        self.misses = 0

    def _key(self, model: str, system: str, user: str) -> str:
        raw = f"{model}|{system[:200]}|{user[:500]}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, model: str, system: str, user: str) -> str | None:
        k = self._key(model, system, user)
        if k in self._cache:
            self.hits += 1
            self._cache.move_to_end(k)
            return self._cache[k]
        self.misses += 1
        return None

    def put(self, model: str, system: str, user: str, response: str) -> None:
        k = self._key(model, system, user)
        self._cache[k] = response
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


class CostTracker:
    """Tracks spending per agent and per model tier."""

    def __init__(self) -> None:
        self.by_agent: dict[str, float] = {}
        self.by_tier: dict[str, float] = {}
        self.total_usd: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.call_count: int = 0

    def record(self, tier: ModelTier, input_tokens: int, output_tokens: int, agent: str = "") -> float:
        cost = estimate_cost(tier, input_tokens, output_tokens)
        self.total_usd += cost
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1
        self.by_tier[tier] = self.by_tier.get(tier, 0.0) + cost
        if agent:
            self.by_agent[agent] = self.by_agent.get(agent, 0.0) + cost
        return cost

    def get_report(self) -> dict[str, Any]:
        return {
            "total_usd": round(self.total_usd, 4),
            "calls": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "by_tier": {k: round(v, 4) for k, v in self.by_tier.items()},
            "by_agent": {k: round(v, 4) for k, v in self.by_agent.items()},
            "budget_remaining": round(settings.cost_monthly_budget_usd - self.total_usd, 4),
        }


class ClaudeClient:
    """LLM client with model tiers, caching, and cost tracking."""

    def __init__(self) -> None:
        provider = self._detect_provider()
        self._provider = provider
        self._max_retries = settings.claude_max_retries
        self._retry_delay = settings.claude_retry_delay
        self._daily_limit = settings.claude_max_tokens_per_day

        self._models = {
            ModelTier.STANDARD: settings.claude_model,
            ModelTier.CHEAP: settings.claude_model_cheap,
        }

        if provider == "openrouter":
            self._api_key = settings.openrouter_api_key
            self._base_url = settings.openrouter_base_url
            self._client: Any = None
        else:
            self._api_key = settings.anthropic_api_key
            self._base_url = "https://api.anthropic.com"
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

        self._tokens_used_today: int = 0
        self._usage_date: date = datetime.now(timezone.utc).date()
        self.cache = PromptCache() if settings.enable_prompt_cache else None
        self.costs = CostTracker()

        logger.info("LLM: provider=%s, standard=%s, cheap=%s, cache=%s",
                     provider, self._models[ModelTier.STANDARD],
                     self._models[ModelTier.CHEAP],
                     "on" if self.cache else "off")

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

    def _resolve_model(self, tier: ModelTier) -> str:
        model = self._models[tier]
        if self._provider == "openrouter" and "/" not in model:
            return f"anthropic/{model}"
        return model

    def _check_budget(self, estimated_tokens: int) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._usage_date:
            self._tokens_used_today = 0
            self._usage_date = today

        if self._tokens_used_today + estimated_tokens > self._daily_limit:
            raise RuntimeError(
                f"Daily token budget exceeded: {self._tokens_used_today}/{self._daily_limit}"
            )

        if self.costs.total_usd >= settings.cost_monthly_budget_usd:
            raise RuntimeError(
                f"Monthly cost budget exceeded: ${self.costs.total_usd:.2f} / ${settings.cost_monthly_budget_usd:.2f}"
            )

    def _track_usage(self, input_tokens: int, output_tokens: int, tier: ModelTier, agent: str) -> None:
        self._tokens_used_today += input_tokens + output_tokens
        cost = self.costs.record(tier, input_tokens, output_tokens, agent)
        logger.debug(
            "LLM call: tier=%s, tokens=%d+%d, cost=$%.4f, daily_total=%d, monthly=$%.4f",
            tier, input_tokens, output_tokens, cost,
            self._tokens_used_today, self.costs.total_usd,
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tier: ModelTier = ModelTier.STANDARD,
        agent: str = "",
    ) -> str:
        """Generate completion with model tier selection, caching, and cost tracking."""
        self._check_budget(max_tokens)

        if self.cache and temperature <= 0.3:
            model = self._resolve_model(tier)
            cached = self.cache.get(model, system_prompt, user_prompt)
            if cached is not None:
                logger.debug("Cache hit (tier=%s, agent=%s)", tier, agent)
                return cached

        model = self._resolve_model(tier)

        if self._provider == "openrouter":
            result = await self._complete_openrouter(model, system_prompt, user_prompt, max_tokens, temperature, tier, agent)
        else:
            result = await self._complete_anthropic(model, system_prompt, user_prompt, max_tokens, temperature, tier, agent)

        if self.cache and temperature <= 0.3:
            self.cache.put(model, system_prompt, user_prompt, result)

        return result

    async def complete_cheap(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        agent: str = "",
    ) -> str:
        """Shortcut for cheap model calls."""
        return await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            tier=ModelTier.CHEAP,
            agent=agent,
        )

    async def _complete_anthropic(
        self, model: str, system_prompt: str, user_prompt: str,
        max_tokens: int, temperature: float, tier: ModelTier, agent: str,
    ) -> str:
        import anthropic

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=temperature,
                )
                self._track_usage(response.usage.input_tokens, response.usage.output_tokens, tier, agent)
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
                    logger.warning("API error (attempt %d/%d): %s", attempt, self._max_retries, e, wait)
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"Anthropic API failed after {self._max_retries} attempts: {last_error}")

    async def _complete_openrouter(
        self, model: str, system_prompt: str, user_prompt: str,
        max_tokens: int, temperature: float, tier: ModelTier, agent: str,
    ) -> str:
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
                            "model": model,
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
                    logger.warning("OpenRouter rate limited, waiting %.1fs", wait)
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                usage = data.get("usage", {})
                self._track_usage(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    tier, agent,
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
        return self._resolve_model(ModelTier.STANDARD)

    @property
    def tokens_used_today(self) -> int:
        return self._tokens_used_today

    @property
    def tokens_remaining_today(self) -> int:
        return max(0, self._daily_limit - self._tokens_used_today)
