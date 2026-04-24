from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import TaskStatus
from src.config.settings import settings
from src.dashboard.deps import get_approval_manager, get_db, get_task_manager
from src.core.approval_manager import ApprovalManager
from src.core.task_manager import TaskManager
from src.models.article import Article
from src.models.keyword import Keyword, KeywordCluster
from src.models.kpi import DailyKPI
from src.models.task import Task
from src.schemas.article import ArticleDetail, ArticleListResponse, ArticleResponse
from src.schemas.keyword import ClusterListResponse, ClusterResponse, KeywordListResponse, KeywordResponse
from src.schemas.kpi import KPISummary
from src.schemas.task import ApprovalAction, ApprovalResponse, TaskCreate, TaskListResponse, TaskResponse

app = FastAPI(title="SEO Agents Dashboard", version="0.3.0")


# --- HTML Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"><title>SEO Agents — spioniro.ru</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;max-width:960px;margin:0 auto;padding:24px;background:#f0f2f5;color:#1a1a2e}
h1{color:#2E5090;margin-bottom:8px}h2{margin-bottom:12px;font-size:18px}
.sub{color:#666;margin-bottom:24px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.card{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card.full{grid-column:1/-1}
.badge{display:inline-block;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600}
.badge.g{background:#d4edda;color:#155724}.badge.y{background:#fff3cd;color:#856404}.badge.gr{background:#e2e3e5;color:#383d41}
table{width:100%;border-collapse:collapse;margin-top:12px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}
th{font-weight:600;color:#555}
.kpi{font-size:28px;font-weight:700;color:#2E5090}.kpi-l{font-size:13px;color:#888}
.kpi-g{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px}
.api a{display:block;padding:5px 0;color:#2E5090;text-decoration:none;font-size:14px}
.api a:hover{text-decoration:underline}
.btn{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}
.btn-ok{background:#28a745;color:#fff}.btn-no{background:#dc3545;color:#fff;margin-left:6px}
.prog{height:6px;background:#e9ecef;border-radius:3px;margin-top:4px}
.prog-bar{height:100%;border-radius:3px;background:#2E5090;transition:width .3s}
</style>
</head>
<body>
<h1>SEO Agents Dashboard</h1>
<p class="sub">spioniro.ru v1.0 — все 7 агентов активны</p>
<div class="card full">
<h2>KPI</h2>
<div class="kpi-g">
<div><div class="kpi" id="v">-</div><div class="kpi-l">Посетители / мес</div><div class="prog"><div class="prog-bar" id="vp" style="width:0"></div></div></div>
<div><div class="kpi" id="r">-</div><div class="kpi-l">Регистрации / мес</div><div class="prog"><div class="prog-bar" id="rp" style="width:0"></div></div></div>
<div><div class="kpi" id="k">-</div><div class="kpi-l">Ключей ТОП-10</div></div>
<div><div class="kpi" id="a">-</div><div class="kpi-l">AI-цитирований</div></div>
</div></div>
<div class="grid">
<div class="card"><h2>Агенты</h2><table>
<tr><td>Orchestrator</td><td><span class="badge g">Active</span></td></tr>
<tr><td>SEO Audit</td><td><span class="badge g">Active</span></td></tr>
<tr><td>Content Engine</td><td><span class="badge g">Active</span></td></tr>
<tr><td>Technical SEO</td><td><span class="badge g">Active</span></td></tr>
<tr><td>Analytics</td><td><span class="badge g">Active</span></td></tr>
<tr><td>Link Building</td><td><span class="badge g">Active</span></td></tr>
<tr><td>AI Visibility</td><td><span class="badge g">Active</span></td></tr>
</table></div>
<div class="card"><h2>API</h2><div class="api">
<a href="/api/health">/api/health</a><a href="/api/kpi">/api/kpi</a>
<a href="/api/tasks">/api/tasks</a><a href="/api/approvals">/api/approvals</a>
<a href="/api/articles">/api/articles</a><a href="/api/keywords">/api/keywords</a>
<a href="/api/clusters">/api/clusters</a><a href="/docs">/docs Swagger</a>
</div></div></div>
<div class="card full"><h2>Очередь одобрений</h2><div id="aq"><em>Загрузка...</em></div></div>
<div class="card full"><h2>Последние статьи</h2><div id="al"><em>Загрузка...</em></div></div>
<script>
fetch('/api/kpi').then(r=>r.json()).then(d=>{
document.getElementById('v').textContent=d.current_month_visitors.toLocaleString();
document.getElementById('r').textContent=d.current_month_registrations;
document.getElementById('k').textContent=d.keywords_top10;
document.getElementById('a').textContent=d.ai_citations;
document.getElementById('vp').style.width=Math.min(d.visitors_progress,100)+'%';
document.getElementById('rp').style.width=Math.min(d.registrations_progress,100)+'%';
}).catch(()=>{});
fetch('/api/approvals').then(r=>r.json()).then(d=>{
const el=document.getElementById('aq');
if(!d.count){el.innerHTML='<p>Нет задач на одобрение</p>';return;}
let h='<table><tr><th>ID</th><th>Тип</th><th>Агент</th><th>Действие</th></tr>';
d.pending.forEach(t=>{h+=`<tr><td>${t.id}</td><td>${t.task_type}</td><td>${t.agent_type}</td><td><button class="btn btn-ok" onclick="act(${t.id},'approve')">OK</button><button class="btn btn-no" onclick="act(${t.id},'reject')">X</button></td></tr>`;});
el.innerHTML=h+'</table>';
}).catch(()=>{document.getElementById('aq').innerHTML='<p>API недоступен</p>';});
fetch('/api/articles?limit=5').then(r=>r.json()).then(d=>{
const el=document.getElementById('al');
if(!d.total){el.innerHTML='<p>Нет статей</p>';return;}
let h='<table><tr><th>ID</th><th>Заголовок</th><th>Тип</th><th>Слов</th><th>GEO</th><th>Статус</th></tr>';
d.articles.forEach(a=>{h+=`<tr><td>${a.id}</td><td>${a.title}</td><td>${a.content_type}</td><td>${a.word_count}</td><td>${a.geo_score}</td><td><span class="badge ${a.status==='published'?'g':'y'}">${a.status}</span></td></tr>`;});
el.innerHTML=h+'</table>';
}).catch(()=>{});
function act(id,action){
fetch(`/api/approvals/${id}/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({feedback:action==='reject'?prompt('Причина отклонения:'):''})})
.then(()=>location.reload());
}
</script>
</body></html>"""


# --- API Endpoints ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "phase": "production", "version": "1.0.0", "agents_active": 7}


@app.get("/api/kpi", response_model=KPISummary)
async def kpi_summary(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            func.coalesce(func.sum(DailyKPI.total_visitors), 0).label("visitors"),
            func.coalesce(func.sum(DailyKPI.registrations), 0).label("regs"),
            func.coalesce(func.max(DailyKPI.keywords_top10), 0).label("top10"),
            func.coalesce(func.max(DailyKPI.ai_citations_count), 0).label("ai"),
            func.coalesce(func.avg(DailyKPI.bounce_rate), 0).label("bounce"),
        ).where(DailyKPI.date >= month_start)
    )
    row = result.one()
    visitors = int(row.visitors)
    regs = int(row.regs)
    return KPISummary(
        current_month_visitors=visitors,
        current_month_registrations=regs,
        goal_visitors=settings.goal_monthly_visitors,
        goal_registrations=settings.goal_monthly_registrations,
        visitors_progress=round(visitors / settings.goal_monthly_visitors * 100, 1) if settings.goal_monthly_visitors else 0,
        registrations_progress=round(regs / settings.goal_monthly_registrations * 100, 1) if settings.goal_monthly_registrations else 0,
        keywords_top10=int(row.top10),
        ai_citations=int(row.ai),
        avg_bounce_rate=round(float(row.bounce), 2),
    )


@app.get("/api/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).order_by(Task.created_at.desc()).limit(limit).offset(offset)
    if status:
        query = query.where(Task.status == status)
    if agent_type:
        query = query.where(Task.agent_type == agent_type)
    result = await db.execute(query)
    tasks = result.scalars().all()

    count_result = await db.execute(select(func.count(Task.id)))
    total = count_result.scalar() or 0

    return TaskListResponse(
        tasks=[TaskResponse(
            id=t.id, task_type=t.task_type, agent_type=t.agent_type,
            priority=t.priority, status=t.status, data=t.data or {},
            result=t.result, error=t.error, retry_count=t.retry_count,
            created_by=t.created_by, created_at=t.created_at,
            updated_at=t.updated_at, completed_at=t.completed_at,
        ) for t in tasks],
        total=total,
    )


@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    tm: TaskManager = Depends(get_task_manager),
):
    task_id = await tm.create_task(
        task_type=body.task_type,
        agent_type=body.agent_type,
        priority=body.priority,
        data=body.data,
    )
    task = await tm.get_task(task_id)
    return TaskResponse(**task)


@app.get("/api/approvals", response_model=ApprovalResponse)
async def list_approvals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task)
        .where(Task.status == TaskStatus.NEEDS_APPROVAL)
        .order_by(Task.created_at)
    )
    tasks = result.scalars().all()
    return ApprovalResponse(
        pending=[TaskResponse(
            id=t.id, task_type=t.task_type, agent_type=t.agent_type,
            priority=t.priority, status=t.status, data=t.data or {},
            result=t.result, error=t.error, retry_count=t.retry_count,
            created_by=t.created_by, created_at=t.created_at,
            updated_at=t.updated_at, completed_at=t.completed_at,
        ) for t in tasks],
        count=len(tasks),
    )


@app.post("/api/approvals/{task_id}/approve")
async def approve_task(
    task_id: int,
    am: ApprovalManager = Depends(get_approval_manager),
):
    try:
        await am.approve(task_id)
        return {"status": "approved", "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/approvals/{task_id}/reject")
async def reject_task(
    task_id: int,
    body: ApprovalAction,
    am: ApprovalManager = Depends(get_approval_manager),
):
    try:
        await am.reject(task_id, feedback=body.feedback)
        return {"status": "rejected", "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/articles", response_model=ArticleListResponse)
async def list_articles(
    status: str | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Article).order_by(Article.created_at.desc()).limit(limit)
    if status:
        query = query.where(Article.status == status)
    result = await db.execute(query)
    articles = result.scalars().all()

    count_result = await db.execute(select(func.count(Article.id)))
    total = count_result.scalar() or 0

    return ArticleListResponse(
        articles=[ArticleResponse(
            id=a.id, title=a.title, slug=a.slug, h1=a.h1,
            meta_title=a.meta_title, meta_description=a.meta_description,
            word_count=a.word_count, content_type=a.content_type,
            marker_keyword=a.marker_keyword, geo_score=a.geo_score,
            platform=a.platform, status=a.status,
            published_url=a.published_url, created_at=a.created_at,
            published_at=a.published_at,
        ) for a in articles],
        total=total,
    )


@app.get("/api/articles/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetail(
        id=article.id, title=article.title, slug=article.slug, h1=article.h1,
        meta_title=article.meta_title, meta_description=article.meta_description,
        content_md=article.content_md, word_count=article.word_count,
        content_type=article.content_type, marker_keyword=article.marker_keyword,
        lsi_keywords=article.lsi_keywords, geo_score=article.geo_score,
        platform=article.platform, status=article.status,
        schema_json=article.schema_json, utm_links=article.utm_links,
        internal_links=article.internal_links,
        published_url=article.published_url, created_at=article.created_at,
        published_at=article.published_at,
    )


@app.get("/api/keywords", response_model=KeywordListResponse)
async def list_keywords(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Keyword).order_by(Keyword.frequency.desc()).limit(limit)
    )
    kws = result.scalars().all()
    count_result = await db.execute(select(func.count(Keyword.id)))
    total = count_result.scalar() or 0

    return KeywordListResponse(
        keywords=[KeywordResponse(
            id=k.id, query=k.query, frequency=k.frequency,
            intent=k.intent, source=k.source, cluster_id=k.cluster_id,
            created_at=k.created_at,
        ) for k in kws],
        total=total,
    )


@app.get("/api/clusters", response_model=ClusterListResponse)
async def list_clusters(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KeywordCluster).order_by(KeywordCluster.total_frequency.desc()).limit(limit)
    )
    clusters = result.scalars().all()
    count_result = await db.execute(select(func.count(KeywordCluster.id)))
    total = count_result.scalar() or 0

    return ClusterListResponse(
        clusters=[ClusterResponse(
            id=c.id, name=c.name, marker_keyword=c.marker_keyword,
            total_frequency=c.total_frequency, intent_type=c.intent_type,
            geo_score=c.geo_score, content_type=c.content_type,
            article_id=c.article_id, lsi_keywords=c.lsi_keywords,
            created_at=c.created_at,
        ) for c in clusters],
        total=total,
    )
