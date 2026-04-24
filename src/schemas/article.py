from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    h1: str
    meta_title: str
    meta_description: str
    word_count: int = 0
    content_type: str = ""
    marker_keyword: str = ""
    geo_score: int = 1
    platform: str = "blog"
    status: str = "draft"
    published_url: str | None = None
    created_at: datetime | None = None
    published_at: datetime | None = None


class ArticleDetail(ArticleResponse):
    content_md: str = ""
    lsi_keywords: list[str] | None = None
    schema_json: dict[str, Any] | None = None
    utm_links: dict[str, Any] | None = None
    internal_links: list[str] | None = None


class ArticleListResponse(BaseModel):
    articles: list[ArticleResponse]
    total: int
