# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Autonomous SEO agent system for **spioniro.ru**. Seven Claude-powered agents (one Orchestrator + six workers) cover the full SEO lifecycle: audit, content creation, link building, technical optimization, analytics, and AI-search visibility. Russian language: all prompts, generated content, and outreach are in Russian.

## Common commands

```bash
# Bring up the full stack (Postgres 16 + Redis 7 + FastAPI + Celery worker + Celery beat)
cp .env.example .env  # set LLM key + Yandex/Google tokens
docker-compose up -d
# Dashboard: http://localhost:8000     Swagger: http://localhost:8000/docs

# Tests (PYTHONPATH is required because the package layout has no installed entrypoint)
PYTHONPATH=. pytest tests/ -v
PYTHONPATH=. pytest tests/test_geo_optimizer.py::test_name -v   # single test
PYTHONPATH=. pytest --cov=src tests/                            # with coverage

# Lint / typecheck (configured in pyproject.toml — ruff strict-ish, mypy strict)
ruff check src/ tests/
ruff format src/ tests/
mypy src/

# Run a one-off Celery task locally (workers must be up)
docker-compose exec celery-worker celery -A src.workers.celery_app call src.workers.tasks.collect_positions

# DB migrations (Alembic configured at alembic.ini → src/db/migrations)
alembic revision --autogenerate -m "msg"
alembic upgrade head

# Seed scripts
PYTHONPATH=. python scripts/seed_keywords.py
PYTHONPATH=. python scripts/seed_competitors.py
```

## Architecture (the parts that span files)

### Orchestrator + 6 workers, coordinated through Celery + an in-process event bus

`src/core/orchestrator.py` is itself a `BaseAgent`. Once a week (Mon 09:00 MSK) it pulls KPI rollups from `DailyKPI`, asks Claude to produce a JSON plan, and writes new `Task` rows tagged with the target `AgentType`. A daily dispatch task (09:30) flips `created → queued`. The orchestrator also subscribes to the in-process `EventBus` (`src/core/event_bus.py`) and reacts to `TASK_APPROVED` by **auto-publishing the article, cross-posting to Dzen, then enqueueing a `collect_positions` task**. Anything externally visible (publish, outreach) flows through this approval-then-event chain — do not bypass it.

### Task lifecycle (single source of truth: `src/config/constants.py::TaskStatus`)

`created → queued → running → {completed | needs_approval | failed | retry | error}`. `BaseAgent.run_task` (`src/core/base_agent.py`) handles the state machine, including a 3-attempt retry policy with exponential backoff. If `execute_task` returns `{"requires_approval": True}`, the task lands in `needs_approval` for human review via the dashboard's `/api/approvals` endpoints.

### LLM client is provider-agnostic

`src/core/claude_client.py` (`ClaudeClient`) speaks **either Anthropic direct or OpenRouter** — picked from `LLM_PROVIDER` env (`auto` falls back to whichever key is set). It enforces a per-process daily token budget (`CLAUDE_MAX_TOKENS_PER_DAY`, default 500k) and retries with exponential backoff on rate limits / API errors. All agents call `self.ask_claude(...)` from `BaseAgent` — never instantiate the SDK directly.

### Content pipeline (the most complex flow)

`src/agents/content_engine/pipeline.py::ContentPipeline.run_for_cluster` chains: SERP pre-analysis → `writer.write_article` → `factchecker.check` → `seo_optimizer.generate_meta` + `check_seo_quality` → `utm_constructor.build_article_utm_links` → save `Article(status="draft")` → return `requires_approval=True`. The writer applies **antidetect rules** (15 forbidden phrases in `src/config/constants.py::ANTIDETECT_FORBIDDEN_PHRASES`) and **GEO scoring** (1–5, see `GEO_SCORING`); higher-GEO content types like `FAQ` and `GLOSSARY` are favored because they extract better in AI Overviews / YandexGPT.

### Celery beat schedule (timezone: Europe/Moscow)

Defined in `src/workers/celery_app.py`. Each entry calls a thin sync wrapper in `src/workers/tasks.py` that does `asyncio.new_event_loop().run_until_complete(...)` — this is how sync Celery talks to the all-async codebase. When adding a scheduled job, add **both** the beat entry and the task wrapper, and use `_get_<agent>_agent()` helpers so deps (`ClaudeClient`, `TaskManager`, `get_session`) are constructed per-task.

### Database layer

SQLAlchemy 2.x async via `asyncpg`. `src/db/session.py` exposes `get_session` (an async-context-manager factory) — agents and pipelines accept it as `session_factory` and call `async with self._session_factory() as session:`. Models live under `src/models/` (Task, Article, Keyword, KeywordCluster, DailyKPI, Backlink, SiteAudit). Migrations live in `src/db/migrations/` (Alembic).

### Dashboard

`src/dashboard/app.py` is a single FastAPI app serving an inline HTMX/HTML dashboard at `/` plus a JSON API under `/api/*` (tasks, approvals, articles, keywords, clusters, KPI). Approvals call `src/core/approval_manager.py`, which publishes `TASK_APPROVED` on the event bus — that's what triggers the orchestrator's auto-publish flow above.

## Conventions worth knowing

- Python **3.12+**, async everywhere (`asyncpg`, `httpx`); never block the event loop in agent code.
- New agents subclass `BaseAgent` and implement `execute_task` + `get_capabilities`. Set `agent_type = AgentType.X` from `src/config/constants.py`.
- `mypy` is configured in **strict** mode and `ruff` runs `E,F,I,N,W,UP` with line-length 100 — keep both clean.
- Russian-language strings in prompts and user-facing UI are intentional, not a localization gap. Keep them in Russian.
- `pytest-asyncio` is in `auto` mode — async test functions don't need a marker.

## Environment

Required env vars (see `.env.example`): `DATABASE_URL`, `REDIS_URL`, **one of** `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` (with matching `LLM_PROVIDER`), plus Yandex/Google tokens (`GSC_*`, `YANDEX_*`, `XMLRIVER_*`, `INDEXNOW_KEY`, `SPIONIRO_API_KEY`) for the data-collection tools in `src/tools/`. KPI goals (`GOAL_MONTHLY_VISITORS`, `GOAL_MONTHLY_REGISTRATIONS`) are read by the orchestrator when generating weekly plans.

> ⚠️ `.env.example` currently contains what looks like a **real OpenRouter API key** (committed in `597ebf9`). Treat it as leaked, rotate it, and replace the value with a placeholder before any further commits.
