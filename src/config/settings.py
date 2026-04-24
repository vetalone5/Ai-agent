from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://seo_agents:seo_agents@localhost:5432/seo_agents"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM API (supports Anthropic direct or OpenRouter)
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_provider: str = "auto"  # "anthropic", "openrouter", or "auto" (picks whichever key is set)
    # Models — can be ANY OpenRouter model, not only Claude:
    # Cheap alternatives: deepseek/deepseek-chat-v3-0324, moonshotai/kimi-k2
    # See https://openrouter.ai/models for full list
    claude_model: str = "claude-sonnet-4-20250514"
    claude_model_cheap: str = "claude-haiku-4-5-20251001"
    claude_max_tokens_per_day: int = 500_000
    claude_max_retries: int = 3
    claude_retry_delay: float = 2.0

    # Cost control
    cost_monthly_budget_usd: float = 10.0
    enable_prompt_cache: bool = True

    # Google Search Console
    gsc_service_account_json: str = ""
    gsc_site_url: str = "https://spioniro.ru"

    # Yandex Webmaster
    yandex_webmaster_token: str = ""
    yandex_webmaster_user_id: str = ""
    yandex_webmaster_host_id: str = "https:spioniro.ru:443"

    # Yandex.Metrica
    yandex_metrica_token: str = ""
    yandex_metrica_counter_id: str = ""

    # XMLRiver (Wordstat + SERP parsing)
    xmlriver_user: str = ""
    xmlriver_key: str = ""

    # IndexNow
    indexnow_key: str = ""

    # spioniro.ru API
    spioniro_api_url: str = "https://api.spioniro.ru"
    spioniro_api_key: str = ""

    # Target site
    target_site_url: str = "https://spioniro.ru"
    target_site_name: str = "Spioniro"

    # Business goals
    goal_monthly_visitors: int = 10_000
    goal_monthly_registrations: int = 500

    # Agent budgets (tokens per task)
    budget_content_article: int = 50_000
    budget_audit_full: int = 20_000
    budget_orchestrator_plan: int = 10_000

    # Task execution
    task_max_retries: int = 3
    task_retry_backoff: float = Field(default=2.0, description="Exponential backoff base in seconds")
    approval_timeout_hours: int = 72


settings = Settings()
