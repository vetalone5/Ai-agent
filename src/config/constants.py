from enum import StrEnum


class AgentType(StrEnum):
    ORCHESTRATOR = "orchestrator"
    SEO_AUDIT = "seo_audit"
    CONTENT_ENGINE = "content_engine"
    LINK_BUILDING = "link_building"
    TECHNICAL_SEO = "technical_seo"
    ANALYTICS = "analytics"
    AI_VISIBILITY = "ai_visibility"


class TaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_APPROVAL = "needs_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    RETRY = "retry"
    ERROR = "error"


class TaskPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContentType(StrEnum):
    GUIDE = "guide"
    REVIEW = "review"
    RATING = "rating"
    COMPARISON = "comparison"
    FAQ = "faq"
    TRENDS = "trends"
    CASE_STUDY = "case_study"
    CHECKLIST = "checklist"
    RESOURCE_LIST = "resource_list"
    CALCULATOR = "calculator"
    MYTHS = "myths"
    GLOSSARY = "glossary"


class GeoScore(StrEnum):
    STAR_1 = "1"
    STAR_2 = "2"
    STAR_3 = "3"
    STAR_4 = "4"
    STAR_5 = "5"


class Platform(StrEnum):
    BLOG = "blog"
    VC_RU = "vcru"
    DZEN = "dzen"
    HABR = "habr"
    TELEGRAM = "telegram"
    YANDEX_KYU = "yandex_kyu"


class SearchEngine(StrEnum):
    YANDEX = "yandex"
    GOOGLE = "google"


ANTIDETECT_FORBIDDEN_PHRASES = [
    "В заключение",
    "Подводя итоги",
    "Резюмируя",
    "Несомненно",
    "Безусловно",
    "Очевидно",
    "Стоит отметить",
    "Важно отметить",
    "Следует обратить внимание",
    "В современном мире",
    "В наше время",
    "Невозможно переоценить значение",
    "Более того",
    "Кроме того",
    "Помимо всего прочего",
    "Как известно",
    "Как правило",
    "В целом",
    "Таким образом",
    "Следовательно",
    "Исходя из вышеизложенного",
    "Целью данной статьи является",
    "Давайте рассмотрим",
    "Специалисты рекомендуют",
    "Вопрос остается актуальным",
    "Прежде всего",
    "В первую очередь",
    "Это совершенно не случайно",
    "Актуальность данного вопроса очевидна",
]

GEO_SCORING = {
    ContentType.FAQ: 5,
    ContentType.GLOSSARY: 5,
    ContentType.GUIDE: 4,
    ContentType.COMPARISON: 4,
    ContentType.CALCULATOR: 4,
    ContentType.CHECKLIST: 3,
    ContentType.RATING: 3,
    ContentType.RESOURCE_LIST: 3,
    ContentType.REVIEW: 3,
    ContentType.MYTHS: 2,
    ContentType.CASE_STUDY: 2,
    ContentType.TRENDS: 2,
}
