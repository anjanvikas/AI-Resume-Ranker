"""Resume Ranking System — FastAPI Application with Auth."""
import os
import uuid
import threading
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import MAX_RESUMES, UPLOAD_DIR, SECRET_KEY
from resume_parser import parse_uploads
from embedding_ranker import rank_by_embeddings
from llm_evaluator import evaluate_batch
from database import (
    init_db, save_api_key, get_api_key, has_api_key,
    update_theme, mark_tutorial_seen, get_user_by_id,
)
from auth import router as auth_router, require_auth, optional_auth

# ── App Setup ───────────────────────────────────────────────
app = FastAPI(title="Resume Ranker", version="2.0.0")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_router)

# In-memory job store (production → Redis)
jobs: dict = {}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Initialize DB on startup
@app.on_event("startup")
def startup():
    init_db()


# ── API Routes ──────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_resumes(
    request: Request,
    job_description: str = Form(...),
    files: list[UploadFile] = File(...),
    user: dict = Depends(require_auth),
):
    """Accept JD + resume files, start the ranking pipeline."""
    if not job_description.strip():
        raise HTTPException(400, "Job description cannot be empty.")
    if len(files) > MAX_RESUMES:
        raise HTTPException(400, f"Maximum {MAX_RESUMES} files allowed.")

    # Get user's API key
    api_key = get_api_key(user["id"])
    if not api_key:
        raise HTTPException(400, "Please set your Claude API key first.")

    # Read all files
    file_data = []
    for f in files:
        content = await f.read()
        file_data.append((f.filename, content))

    # Create job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "parsing",
        "progress": 0,
        "total": 0,
        "results": None,
        "all_resumes": None,
        "error": None,
        "user_id": user["id"],
    }

    # Run pipeline in background thread with user's API key
    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, job_description, file_data, api_key),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str, user: dict = Depends(require_auth)):
    """Poll for job progress."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/api/results/{job_id}")
async def get_results(job_id: str, user: dict = Depends(require_auth)):
    """Get final ranked results."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job["status"] != "complete":
        raise HTTPException(400, "Job not complete yet.")
    return {
        "results": job["results"],
        "all_resumes": job["all_resumes"],
    }


# ── User Settings Routes ───────────────────────────────────

@app.post("/api/save-key")
async def save_key(request: Request, user: dict = Depends(require_auth)):
    """Save user's Claude API key (encrypted)."""
    body = await request.json()
    api_key = body.get("api_key", "").strip()
    if not api_key:
        raise HTTPException(400, "API key cannot be empty.")
    if not api_key.startswith("sk-ant-"):
        raise HTTPException(400, "Invalid Claude API key format.")

    # Test the key with a quick ping
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
    except Exception as e:
        raise HTTPException(400, f"API key validation failed: {str(e)}")

    save_api_key(user["id"], api_key)
    return {"status": "saved"}


@app.get("/api/has-key")
async def check_key(user: dict = Depends(require_auth)):
    """Check if user has a saved API key."""
    return {"has_key": has_api_key(user["id"])}


@app.post("/api/theme")
async def set_theme(request: Request, user: dict = Depends(require_auth)):
    """Save user's theme preference."""
    body = await request.json()
    theme = body.get("theme", "light")
    if theme not in ("light", "dark"):
        raise HTTPException(400, "Theme must be 'light' or 'dark'.")
    update_theme(user["id"], theme)
    return {"theme": theme}


@app.post("/api/tutorial-seen")
async def tutorial_seen(user: dict = Depends(require_auth)):
    """Mark tutorial as seen."""
    mark_tutorial_seen(user["id"])
    return {"status": "ok"}


# ── Pipeline Runner ─────────────────────────────────────────

def _run_pipeline(job_id: str, jd: str, file_data: list, api_key: str):
    """Execute the full multi-stage ranking pipeline with user's API key."""
    job = jobs[job_id]

    try:
        job["status"] = "parsing"
        parsed = parse_uploads(file_data)
        if not parsed:
            job["status"] = "error"
            job["error"] = "No valid resumes could be extracted from uploaded files."
            return

        job["total"] = len(parsed)
        job["status"] = "embedding"

        shortlisted, all_ranked = rank_by_embeddings(jd, parsed)
        job["status"] = "evaluating"

        all_resumes_summary = []
        for r in all_ranked:
            all_resumes_summary.append({
                "filename": r["filename"],
                "embedding_score": r["embedding_score"],
            })
        job["all_resumes"] = all_resumes_summary

        def progress_cb(done, total):
            job["progress"] = done
            job["total_eval"] = total

        results = evaluate_batch(jd, shortlisted, api_key, progress_callback=progress_cb)

        job["results"] = results
        job["status"] = "complete"

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        import traceback
        traceback.print_exc()


# ── Serve Frontend ──────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/login")
async def serve_login(user: dict | None = Depends(optional_auth)):
    if user:
        return RedirectResponse(url="/")
    return FileResponse("static/login.html")


@app.get("/")
async def serve_index(user: dict | None = Depends(optional_auth)):
    if not user:
        return RedirectResponse(url="/login")
    return FileResponse("static/index.html")
