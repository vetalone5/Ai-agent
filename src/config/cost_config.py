"""Cost optimization: model tiers, task budgets, and prompt caching.

Price reference (OpenRouter, per 1M tokens):
  Haiku:  input $0.80,  output $4.00   (25x cheaper than Sonnet)
  Sonnet: input $3.00,  output $15.00

Strategy:
  - Haiku for short/simple tasks (titles, summaries, Kyu answers, factcheck)
  - Sonnet only for long-form content generation and strategic planning
  - No LLM for tasks that can be done algorithmically
"""

from enum import StrEnum
from typing import Any


class ModelTier(StrEnum):
    CHEAP = "cheap"     # Haiku — short tasks, summaries, formatting
    STANDARD = "standard"  # Sonnet — content generation, analysis


TASK_MODEL_MAP: dict[str, dict[str, Any]] = {
    # --- NO LLM NEEDED (algorithmic) ---
    "collect_positions": {"tier": None, "max_tokens": 0},
    "collect_traffic": {"tier": None, "max_tokens": 0},
    "analyze_behavioral": {"tier": None, "max_tokens": 0},
    "collect_geo_metrics": {"tier": None, "max_tokens": 0},
    "full_crawl": {"tier": None, "max_tokens": 0},
    "check_cwv": {"tier": None, "max_tokens": 0},
    "check_backlinks": {"tier": None, "max_tokens": 0},
    "generate_schema": {"tier": None, "max_tokens": 0},
    "generate_sitemap": {"tier": None, "max_tokens": 0},
    "generate_robots_txt": {"tier": None, "max_tokens": 0},
    "add_backlink": {"tier": None, "max_tokens": 0},

    # --- CHEAP (Haiku) ---
    "generate_weekly_report": {"tier": ModelTier.CHEAP, "max_tokens": 1000},
    "generate_kyu_answer": {"tier": ModelTier.CHEAP, "max_tokens": 800},
    "generate_kyu_questions": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "factcheck": {"tier": ModelTier.CHEAP, "max_tokens": 1000},
    "generate_wikidata": {"tier": ModelTier.CHEAP, "max_tokens": 600},
    "ab_test_variants": {"tier": ModelTier.CHEAP, "max_tokens": 800},
    "review_progress": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "visibility_report": {"tier": None, "max_tokens": 0},
    "check_keywords": {"tier": None, "max_tokens": 0},
    "serp_analysis": {"tier": None, "max_tokens": 0},
    "content_reoptimize": {"tier": ModelTier.CHEAP, "max_tokens": 1000},
    "content_refresh": {"tier": ModelTier.CHEAP, "max_tokens": 1000},

    # Fix tasks from audit — just need short recommendations
    "fix_missing_title": {"tier": ModelTier.CHEAP, "max_tokens": 200},
    "fix_missing_description": {"tier": ModelTier.CHEAP, "max_tokens": 200},
    "fix_missing_h1": {"tier": ModelTier.CHEAP, "max_tokens": 200},
    "fix_thin_content": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "behavioral_fix_high_bounce": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "behavioral_fix_low_duration": {"tier": ModelTier.CHEAP, "max_tokens": 500},

    # --- STANDARD (Sonnet) — only for heavy content ---
    "write_article": {"tier": ModelTier.STANDARD, "max_tokens": 8000},
    "run_pipeline": {"tier": ModelTier.STANDARD, "max_tokens": 8000},
    "run_batch": {"tier": ModelTier.STANDARD, "max_tokens": 8000},
    "adapt_for_platform": {"tier": ModelTier.STANDARD, "max_tokens": 3000},
    "weekly_plan": {"tier": ModelTier.STANDARD, "max_tokens": 2000},
    "keyword_research": {"tier": None, "max_tokens": 0},
    "competitor_analysis": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "content_gap_analysis": {"tier": ModelTier.CHEAP, "max_tokens": 500},
    "find_platforms": {"tier": ModelTier.CHEAP, "max_tokens": 800},
    "generate_guest_post_pitch": {"tier": ModelTier.STANDARD, "max_tokens": 1000},
    "generate_digital_pr": {"tier": ModelTier.STANDARD, "max_tokens": 1000},
}

# Estimated costs per 1K tokens (OpenRouter USD)
COST_PER_1K_INPUT = {ModelTier.CHEAP: 0.0008, ModelTier.STANDARD: 0.003}
COST_PER_1K_OUTPUT = {ModelTier.CHEAP: 0.004, ModelTier.STANDARD: 0.015}


def get_task_config(task_type: str) -> dict[str, Any]:
    """Get model tier and token limit for a task type."""
    config = TASK_MODEL_MAP.get(task_type)
    if config:
        return config
    # Default: try to match partial task names
    for key, conf in TASK_MODEL_MAP.items():
        if key in task_type:
            return conf
    # Unknown task → cheap model with small budget
    return {"tier": ModelTier.CHEAP, "max_tokens": 500}


def estimate_cost(tier: ModelTier, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD."""
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT.get(tier, 0.003)
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT.get(tier, 0.015)
    return round(input_cost + output_cost, 6)
