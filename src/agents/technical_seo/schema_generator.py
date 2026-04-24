"""JSON-LD schema.org markup generator by content type."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.config.constants import ContentType
from src.config.settings import settings

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """Generates JSON-LD structured data based on content type."""

    def generate(self, article: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate all applicable schema types for an article."""
        schemas = []
        content_type = article.get("content_type", "guide")

        schemas.append(self._article_schema(article))

        if content_type in (ContentType.FAQ, "faq"):
            schemas.append(self._faq_schema(article))
        elif content_type in (ContentType.GUIDE, ContentType.CHECKLIST, "guide", "checklist"):
            schemas.append(self._howto_schema(article))
        elif content_type in (ContentType.REVIEW, "review"):
            schemas.append(self._review_schema(article))
        elif content_type in (ContentType.RATING, ContentType.RESOURCE_LIST, "rating", "resource_list"):
            schemas.append(self._itemlist_schema(article))
        elif content_type in (ContentType.GLOSSARY, "glossary"):
            schemas.append(self._defined_term_schema(article))

        schemas.append(self._breadcrumb_schema(article))
        schemas.append(self._organization_schema())

        return schemas

    def to_script_tags(self, schemas: list[dict[str, Any]]) -> str:
        """Convert schemas to HTML script tags."""
        tags = []
        for schema in schemas:
            tag = f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'
            tags.append(tag)
        return "\n".join(tags)

    def _article_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": article.get("meta_title", article.get("title", "")),
            "description": article.get("meta_description", ""),
            "author": {
                "@type": "Organization",
                "name": settings.target_site_name,
                "url": settings.target_site_url,
            },
            "publisher": {
                "@type": "Organization",
                "name": settings.target_site_name,
                "url": settings.target_site_url,
            },
            "datePublished": article.get("published_at", now),
            "dateModified": article.get("updated_at", now),
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{settings.target_site_url}/blog/{article.get('slug', '')}",
            },
            "wordCount": article.get("word_count", 0),
            "inLanguage": "ru-RU",
        }

    def _faq_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        content = article.get("content_md", "")
        qa_pairs = self._extract_qa_pairs(content)
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a,
                    },
                }
                for q, a in qa_pairs
            ],
        }

    def _howto_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        content = article.get("content_md", "")
        steps = self._extract_steps(content)
        return {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": article.get("h1", article.get("title", "")),
            "description": article.get("meta_description", ""),
            "step": [
                {"@type": "HowToStep", "name": name, "text": text}
                for name, text in steps
            ],
        }

    def _review_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "Review",
            "itemReviewed": {
                "@type": "SoftwareApplication",
                "name": article.get("marker_keyword", ""),
            },
            "author": {
                "@type": "Organization",
                "name": settings.target_site_name,
            },
            "reviewBody": article.get("meta_description", ""),
        }

    def _itemlist_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        content = article.get("content_md", "")
        items = self._extract_h2_titles(content)
        return {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": article.get("h1", ""),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name}
                for i, name in enumerate(items)
            ],
        }

    def _defined_term_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        content = article.get("content_md", "")
        terms = self._extract_h2_titles(content)
        return {
            "@context": "https://schema.org",
            "@type": "DefinedTermSet",
            "name": article.get("h1", ""),
            "hasDefinedTerm": [
                {"@type": "DefinedTerm", "name": term}
                for term in terms
            ],
        }

    def _breadcrumb_schema(self, article: dict[str, Any]) -> dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Главная", "item": settings.target_site_url},
                {"@type": "ListItem", "position": 2, "name": "Блог", "item": f"{settings.target_site_url}/blog"},
                {"@type": "ListItem", "position": 3, "name": article.get("title", "")},
            ],
        }

    @staticmethod
    def _organization_schema() -> dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": settings.target_site_name,
            "url": settings.target_site_url,
            "sameAs": [],
        }

    @staticmethod
    def _extract_qa_pairs(content: str) -> list[tuple[str, str]]:
        pairs = []
        lines = content.split("\n")
        current_q = ""
        current_a_lines: list[str] = []
        for line in lines:
            if line.startswith("### ") and "?" in line:
                if current_q and current_a_lines:
                    pairs.append((current_q, " ".join(current_a_lines).strip()))
                current_q = line.lstrip("# ").strip()
                current_a_lines = []
            elif current_q and line.strip() and not line.startswith("#"):
                current_a_lines.append(line.strip())
        if current_q and current_a_lines:
            pairs.append((current_q, " ".join(current_a_lines).strip()))
        return pairs

    @staticmethod
    def _extract_steps(content: str) -> list[tuple[str, str]]:
        steps = []
        lines = content.split("\n")
        current_step = ""
        current_text_lines: list[str] = []
        for line in lines:
            if line.startswith("## "):
                if current_step and current_text_lines:
                    steps.append((current_step, " ".join(current_text_lines[:3]).strip()))
                current_step = line.lstrip("# ").strip()
                current_text_lines = []
            elif current_step and line.strip() and not line.startswith("#"):
                current_text_lines.append(line.strip())
        if current_step and current_text_lines:
            steps.append((current_step, " ".join(current_text_lines[:3]).strip()))
        return steps

    @staticmethod
    def _extract_h2_titles(content: str) -> list[str]:
        return [
            line.lstrip("# ").strip()
            for line in content.split("\n")
            if line.startswith("## ") and not line.startswith("### ")
        ]
