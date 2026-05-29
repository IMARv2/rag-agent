import sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import List, Optional
from indexer.indexer import index_all, sync_index, search_docs
from indexer.watcher import start_watcher
from db.chroma import get_collection
from agent.agent import chat
from config import settings
import httpx

_index_running = False
_watcher = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _watcher
    _watcher = start_watcher()
    yield
    if _watcher:
        _watcher.stop()
        _watcher.join()

app = FastAPI(title="RAG Agent", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=604800)
app.mount("/static", StaticFiles(directory="static"), name="static")

def is_logged_in(request: Request) -> bool:
    return request.session.get("logged_in") is True

@app.get("/login")
def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return FileResponse("static/login.html")

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.auth_user and password == settings.auth_pass:
        request.session["logged_in"] = True
        return RedirectResponse("/", status_code=302)
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    model: Optional[str] = None

@app.get("/")
def root(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("static/index.html")

@app.get("/api/status")
def status(request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    col = get_collection()
    return {"status": "ok", "doc_count": col.count(), "index_running": _index_running}

@app.get("/api/models")
def get_models(request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        chat_models = [m for m in models if "embed" not in m and "nomic" not in m]
        return {"models": chat_models, "default": settings.chat_model}
    except Exception:
        return {"models": [settings.chat_model], "default": settings.chat_model}

@app.post("/api/index")
def trigger_index(request: Request, background_tasks: BackgroundTasks):
    if not is_logged_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    global _index_running
    if _index_running:
        return JSONResponse({"status": "already running"}, status_code=409)
    def _run():
        global _index_running
        _index_running = True
        try:
            sync_index()
            index_all()
        finally:
            _index_running = False
    background_tasks.add_task(_run)
    return {"status": "indexing started"}

@app.post("/api/search")
def search(req: SearchRequest, request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    results = search_docs(req.query, req.top_k)
    return {"query": req.query, "results": results}

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, request: Request):
    if not is_logged_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    result = chat(req.message, req.history, model=req.model)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
