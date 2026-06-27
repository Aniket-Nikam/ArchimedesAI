import os
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- API Keys ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- LLM Fallback Models ---
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "compound-beta",
    "compound-beta-mini",
]

# --- Database ---
DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "archimedes.db")

# --- Security ---
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
BCRYPT_ROUNDS = 12

# --- Validation Constants ---
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 8
