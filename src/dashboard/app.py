from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="SEO Agents Dashboard", version="0.2.0")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>SEO Agents — spioniro.ru</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: system-ui, -apple-system, sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #f0f2f5; color: #1a1a2e; }
            h1 { color: #2E5090; margin-bottom: 8px; }
            h2 { margin-bottom: 12px; font-size: 18px; }
            .subtitle { color: #666; margin-bottom: 24px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
            .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            .card.full { grid-column: 1 / -1; }
            .badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }
            .badge.green { background: #d4edda; color: #155724; }
            .badge.blue { background: #cce5ff; color: #004085; }
            .badge.yellow { background: #fff3cd; color: #856404; }
            .badge.gray { background: #e2e3e5; color: #383d41; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 14px; }
            th { font-weight: 600; color: #555; }
            .api-list a { display: block; padding: 6px 0; color: #2E5090; text-decoration: none; font-size: 14px; }
            .api-list a:hover { text-decoration: underline; }
            .kpi { font-size: 28px; font-weight: 700; color: #2E5090; }
            .kpi-label { font-size: 13px; color: #888; }
            .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }
        </style>
    </head>
    <body>
        <h1>SEO Agents Dashboard</h1>
        <p class="subtitle">spioniro.ru — система автономных SEO-агентов v0.2</p>

        <div class="card full">
            <h2>KPI</h2>
            <div class="kpi-grid">
                <div><div class="kpi" id="kpi-visitors">—</div><div class="kpi-label">Посетители / мес</div></div>
                <div><div class="kpi" id="kpi-regs">—</div><div class="kpi-label">Регистрации / мес</div></div>
                <div><div class="kpi" id="kpi-top10">—</div><div class="kpi-label">Ключей в ТОП-10</div></div>
                <div><div class="kpi" id="kpi-ai">—</div><div class="kpi-label">AI-цитирований</div></div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Агенты</h2>
                <table>
                    <tr><td>Orchestrator</td><td><span class="badge gray">Phase 2</span></td></tr>
                    <tr><td>SEO Audit</td><td><span class="badge green">Active</span></td></tr>
                    <tr><td>Content Engine</td><td><span class="badge green">Active</span></td></tr>
                    <tr><td>Technical SEO</td><td><span class="badge green">Active</span></td></tr>
                    <tr><td>Analytics</td><td><span class="badge green">Active</span></td></tr>
                    <tr><td>Link Building</td><td><span class="badge gray">Phase 3</span></td></tr>
                    <tr><td>AI Visibility</td><td><span class="badge gray">Phase 3</span></td></tr>
                </table>
            </div>
            <div class="card">
                <h2>API Endpoints</h2>
                <div class="api-list">
                    <a href="/api/health">/api/health</a>
                    <a href="/api/agents">/api/agents</a>
                    <a href="/api/tasks">/api/tasks</a>
                    <a href="/api/approvals">/api/approvals</a>
                    <a href="/api/articles">/api/articles</a>
                    <a href="/api/keywords">/api/keywords</a>
                    <a href="/docs">/docs — Swagger UI</a>
                </div>
            </div>
        </div>

        <div class="card full">
            <h2>Очередь одобрений</h2>
            <div id="approvals-list"><em>Загрузка...</em></div>
        </div>

        <script>
        fetch('/api/approvals').then(r=>r.json()).then(d=>{
            const el = document.getElementById('approvals-list');
            if(d.count===0) { el.innerHTML='<p>Нет задач на одобрение</p>'; return; }
            let html='<table><tr><th>ID</th><th>Тип</th><th>Агент</th><th>Создано</th></tr>';
            d.pending.forEach(t=>{
                html+=`<tr><td>${t.id}</td><td>${t.task_type}</td><td>${t.agent_type}</td><td>${t.created_at||''}</td></tr>`;
            });
            el.innerHTML=html+'</table>';
        }).catch(()=>{document.getElementById('approvals-list').innerHTML='<p>API недоступен</p>';});
        </script>
    </body>
    </html>
    """


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "phase": "mvp",
        "version": "0.2.0",
        "agents": {
            "analytics": "active",
            "seo_audit": "active",
            "content_engine": "active",
            "technical_seo": "active",
            "link_building": "phase_3",
            "ai_visibility": "phase_3",
            "orchestrator": "phase_2",
        },
    }


@app.get("/api/agents")
async def agents():
    return {
        "agents": [
            {"name": "Analytics & KPI", "type": "analytics", "status": "active",
             "capabilities": ["collect_positions", "collect_traffic", "analyze_behavioral", "collect_geo_metrics", "generate_weekly_report"]},
            {"name": "SEO Audit", "type": "seo_audit", "status": "active",
             "capabilities": ["full_crawl", "keyword_research", "competitor_analysis", "serp_analysis"]},
            {"name": "Content Engine", "type": "content_engine", "status": "active",
             "capabilities": ["write_article", "run_pipeline", "run_batch", "adapt_for_platform"]},
            {"name": "Technical SEO", "type": "technical_seo", "status": "active",
             "capabilities": ["generate_schema", "generate_sitemap", "check_cwv"]},
            {"name": "Link Building", "type": "link_building", "status": "phase_3"},
            {"name": "AI Visibility", "type": "ai_visibility", "status": "phase_3"},
            {"name": "Orchestrator", "type": "orchestrator", "status": "phase_2"},
        ]
    }


@app.get("/api/approvals")
async def approvals():
    return {"pending": [], "count": 0}


@app.get("/api/tasks")
async def tasks():
    return {"tasks": [], "total": 0}


@app.get("/api/articles")
async def articles():
    return {"articles": [], "total": 0}


@app.get("/api/keywords")
async def keywords():
    return {"keywords": [], "total": 0}


@app.post("/api/approvals/{task_id}/approve")
async def approve_task(task_id: int):
    return {"status": "approved", "task_id": task_id}


@app.post("/api/approvals/{task_id}/reject")
async def reject_task(task_id: int, feedback: str = ""):
    return {"status": "rejected", "task_id": task_id, "feedback": feedback}
