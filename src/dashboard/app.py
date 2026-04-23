from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="SEO Agents Dashboard", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>SEO Agents — spioniro.ru</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }
            h1 { color: #2E5090; }
            .card { background: white; border-radius: 8px; padding: 20px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .status { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 500; }
            .status.ok { background: #d4edda; color: #155724; }
            .status.warn { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <h1>SEO Agents Dashboard</h1>
        <p>spioniro.ru — система автономных SEO-агентов</p>

        <div class="card">
            <h2>Статус системы</h2>
            <p><span class="status ok">Работает</span> Фаза 1 — MVP</p>
        </div>

        <div class="card">
            <h2>Агенты</h2>
            <ul>
                <li>Orchestrator — координатор</li>
                <li>SEO Audit — аудит и анализ</li>
                <li>Content Engine — создание контента</li>
                <li>Link Building — ссылочная масса</li>
                <li>Technical SEO — техническое SEO</li>
                <li>Analytics &amp; KPI — аналитика</li>
                <li>AI Visibility — GEO-оптимизация</li>
            </ul>
        </div>

        <div class="card">
            <h2>API</h2>
            <ul>
                <li><a href="/api/health">/api/health</a> — проверка здоровья</li>
                <li><a href="/api/approvals">/api/approvals</a> — очередь одобрений</li>
            </ul>
        </div>
    </body>
    </html>
    """


@app.get("/api/health")
async def health():
    return {"status": "ok", "phase": "mvp", "version": "0.1.0"}


@app.get("/api/approvals")
async def approvals():
    return {"pending": [], "count": 0}
