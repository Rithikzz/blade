import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-2")

AI_PRIMARY_PROVIDER = os.getenv("AI_PRIMARY_PROVIDER", "gemini")
AI_FALLBACK_PROVIDER = os.getenv("AI_FALLBACK_PROVIDER", "grok")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b-instruct-q4_K_M")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
