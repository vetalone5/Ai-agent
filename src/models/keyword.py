from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Keyword(Base, TimestampMixin):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intent: Mapped[str] = mapped_column(String(30), nullable=False, default="informational")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="wordstat")

    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_keywords_cluster_id", "cluster_id"),
        Index("ix_keywords_intent", "intent"),
    )


class KeywordCluster(Base, TimestampMixin):
    __tablename__ = "keyword_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    marker_keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    total_frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intent_type: Mapped[str] = mapped_column(String(30), nullable=False, default="informational")
    geo_score: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    article_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lsi_keywords: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_clusters_geo_score", "geo_score"),
    )


class Position(Base, TimestampMixin):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_id: Mapped[int] = mapped_column(Integer, nullable=False)
    search_engine: Mapped[str] = mapped_column(String(20), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_positions_keyword_engine", "keyword_id", "search_engine"),
    )
