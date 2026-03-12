"""Configuration for the Resume Ranking System."""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# ── Google OAuth2 ───────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# ── Security ────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ── Database ────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "resumerank.db")

# ── Model Settings ──────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-20250514"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Pipeline Settings ───────────────────────────────────────
TOP_N_SHORTLIST = 30
MAX_RESUMES = 200

# ── Scoring Weights ─────────────────────────────────────────
SCORING_WEIGHTS = {
    "skills_match": 0.40,
    "experience_relevance": 0.25,
    "education_fit": 0.15,
    "achievements": 0.10,
    "communication_quality": 0.10,
}

# ── File Settings ───────────────────────────────────────────
UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE_MB = 10
