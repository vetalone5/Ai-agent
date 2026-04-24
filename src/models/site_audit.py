from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class PageAudit(Base, TimestampMixin):
    __tablename__ = "page_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    h1: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_canonical: Mapped[bool | None] = mapped_column(nullable=True)
    has_schema: Mapped[bool | None] = mapped_column(nullable=True)
    internal_links_count: Mapped[int] = mapped_column(Integer, default=0)
    issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_page_audits_url", "url"),
    )


class AuditIssue(Base, TimestampMixin):
    __tablename__ = "audit_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_agent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_audit_issues_severity", "severity"),
        Index("ix_audit_issues_resolved", "resolved"),
    )


class Competitor(Base, TimestampMixin):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    blog_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    da_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
