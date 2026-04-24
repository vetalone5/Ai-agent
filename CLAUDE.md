# SEO Agents — spioniro.ru

Autonomous SEO agent system for spioniro.ru. 7 AI agents powered by Claude API manage the full SEO lifecycle: audit, content creation, link building, technical optimization, analytics, and AI visibility.

## Quick start

```bash
cp .env.example .env  # fill in API keys
docker-compose up -d  # PostgreSQL 16, Redis 7, app, celery worker + beat
# App: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

## Architecture

```
Orchestrator → dispatches tasks to 6 worker agents
             → reads KPI from Analytics
             → creates weekly plan via Claude

Agents: SEO Audit | Content Engine | Link Building | Technical SEO | Analytics | AI Visibility
Storage: PostgreSQL (11 tables) | Redis (queues, cache)
Scheduler: Celery Beat (18 tasks)
Dashboard: FastAPI + HTMX
```

## Project structure

- `src/config/` — settings.py (env vars), constants.py (enums, GEO scores, antidetect phrases)
- `src/core/` — base_agent.py, orchestrator.py, claude_client.py, task_manager.py, event_bus.py, approval_manager.py
- `src/agents/` — 6 agent directories, each with agent.py + modules
- `src/tools/` — 10 API clients (GSC, YWM, Metrica, Wordstat, IndexNow, PSI, spioniro, crawler, publisher, alerting)
- `src/models/` — SQLAlchemy models (Task, Keyword, KeywordCluster, Article, Position, etc.)
- `src/schemas/` — Pydantic schemas for API
- `src/dashboard/` — FastAPI app with HTML dashboard
- `src/workers/` — Celery app + task definitions
- `tests/` — pytest suite

## Key conventions

- Python 3.12+, async everywhere (asyncpg, httpx)
- All agents inherit from `BaseAgent` (src/core/base_agent.py)
- Tasks follow lifecycle: created → queued → running → completed/needs_approval/failed
- Anything that publishes externally requires human approval via dashboard
- Content pipeline uses 15 antidetect rules and GEO optimization (1-5 score)
- Russian language: all prompts, content, outreach in Russian

## Running tests

```bash
PYTHONPATH=. pytest tests/ -v
```

## Environment variables

All config via `.env` — see `.env.example`. Required:
- `DATABASE_URL`, `REDIS_URL` — infrastructure
- `ANTHROPIC_API_KEY` — Claude API for all agents
- Yandex/Google API tokens — for data collection

## Celery schedule (MSK timezone)

Daily: positions (06:00), traffic (08:00), dispatch (09:30)
Mon: audit (03:00), sitemap (05:00), orchestrator plan (09:00)
Tue: competitors (10:00), content health (11:00)
Wed: keywords (10:00), GEO metrics (15:00), AI visibility (15:00)
Thu: behavioral (10:00)
Fri: backlinks (10:00), report (17:00)
Sat: CWV (04:00), AI visibility (15:00)
Bi-monthly: AI probing (1st, 15th)
