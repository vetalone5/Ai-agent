from datetime import datetime

from pydantic import BaseModel


class KeywordResponse(BaseModel):
    id: int
    query: str
    frequency: int = 0
    intent: str = "informational"
    source: str = ""
    cluster_id: int | None = None
    created_at: datetime | None = None


class ClusterResponse(BaseModel):
    id: int
    name: str
    marker_keyword: str
    total_frequency: int = 0
    intent_type: str = "informational"
    geo_score: int = 1
    content_type: str | None = None
    article_id: int | None = None
    lsi_keywords: list[str] | None = None
    created_at: datetime | None = None


class KeywordListResponse(BaseModel):
    keywords: list[KeywordResponse]
    total: int


class ClusterListResponse(BaseModel):
    clusters: list[ClusterResponse]
    total: int
