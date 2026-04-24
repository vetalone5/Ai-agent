from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    h1: Mapped[str] = mapped_column(String(300), nullable=False)
    meta_title: Mapped[str] = mapped_column(String(70), nullable=False)
    meta_description: Mapped[str] = mapped_column(String(170), nullable=False)

    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marker_keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    lsi_keywords: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    geo_score: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="blog")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    schema_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    utm_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    internal_links: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)

    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_articles_status", "status"),
        Index("ix_articles_platform", "platform"),
        Index("ix_articles_cluster_id", "cluster_id"),
    )


class ArticleMetrics(Base, TimestampMixin):
    __tablename__ = "article_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    page_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_visitors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_time_on_page: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bounce_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scroll_depth: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    position_yandex: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_google: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ai_cited_yandex: Mapped[bool | None] = mapped_column(nullable=True)
    ai_cited_google: Mapped[bool | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_article_metrics_article_date", "article_id", "date"),
    )
