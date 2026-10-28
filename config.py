import os
import secrets
from dotenv import load_dotenv
from utils.secret_store import load_groq

# Load environment variables
load_dotenv()

# --- API Keys ---
GROQ_API_KEY = os.environ["GROQ_API_KEY"] if "GROQ_API_KEY" in os.environ else load_groq()

# --- LLM Fallback Models ---
FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

# --- Database ---
DATABASE_DIR = os.environ.get("ARCHIMEDES_DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
DATABASE_PATH = os.path.join(DATABASE_DIR, "archimedes.db")

# --- Security ---
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
BCRYPT_ROUNDS = 12

# --- Validation Constants ---
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 8

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "86400"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
RESEARCH_TIMEOUT_SECONDS = int(os.environ.get("RESEARCH_TIMEOUT_SECONDS", "180"))
MAX_CONCURRENT_RESEARCH = int(os.environ.get("MAX_CONCURRENT_RESEARCH", "2"))
ENABLE_GOOGLE_SCHOLAR = os.environ.get("ENABLE_GOOGLE_SCHOLAR", "0") == "1"
if os.environ.get("GROQ_MODELS"):
    FALLBACK_MODELS = [m.strip() for m in os.environ["GROQ_MODELS"].split(",") if m.strip()]
