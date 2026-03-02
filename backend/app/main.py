from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Kanban Studio API")


@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kanban Studio</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:system-ui,sans-serif;background:#f7f8fb;color:#032147;
         display:flex;align-items:center;justify-content:center;min-height:100vh}
    .card{background:#fff;border-radius:24px;padding:48px 56px;
          box-shadow:0 18px 40px rgba(3,33,71,.12);text-align:center;max-width:480px}
    h1{font-size:2rem;margin-bottom:12px}
    p{color:#888;font-size:.95rem;line-height:1.6}
    .badge{display:inline-block;margin-top:20px;padding:8px 20px;border-radius:999px;
           background:#209dd7;color:#fff;font-size:.8rem;font-weight:600;letter-spacing:.05em}
  </style>
</head>
<body>
  <div class="card">
    <h1>Hello from Kanban Studio</h1>
    <p>The backend is running. The frontend will be wired in during Part 3.</p>
    <span class="badge">FastAPI + Docker</span>
  </div>
</body>
</html>"""


@app.get("/api/health")
async def health():
    return {"status": "ok"}
