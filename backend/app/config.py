"""Settings, read from environment variables (or backend/.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

PROMPTS_DIR = BACKEND_DIR / "prompts"

# ---- Which AI to use: ollama | openai | claude ------------------------------
PROVIDER = os.getenv("AIGREE_PROVIDER", "ollama").strip().lower()

_DEFAULTS = {
    #           model                 base URL                    timeout(s) parallel chunk chars
    "ollama": ("qwen2.5:3b",        os.getenv("AIGREE_OLLAMA_URL", "http://localhost:11434"), 1200, 1, 12000),
    "openai": ("gpt-4o-mini",       "",                         300,       4,       30000),
    "claude": ("claude-opus-5-5",   "",                         600,       4,       30000),
}
_d = _DEFAULTS.get(PROVIDER, _DEFAULTS["ollama"])

MODEL = os.getenv("AIGREE_MODEL", _d[0])
# For "openai": leave empty for OpenAI itself, or point at a compatible API, e.g.
#   Alibaba Qwen:  https://dashscope-intl.aliyuncs.com/compatible-mode/v1
#   OpenRouter:    https://openrouter.ai/api/v1
BASE_URL = os.getenv("AIGREE_BASE_URL", _d[1])
API_KEY = (
    os.getenv("AIGREE_API_KEY")
    or (os.getenv("OPENAI_API_KEY") if PROVIDER == "openai" else None)
    or (os.getenv("ANTHROPIC_API_KEY") if PROVIDER == "claude" else None)
    or ""
)
TIMEOUT_SECONDS = int(os.getenv("AIGREE_TIMEOUT_SECONDS", str(_d[2])))

# "openai" provider: json_schema (strict, OpenAI/OpenRouter) or json_object (wider support, e.g. DashScope)
JSON_MODE = os.getenv("AIGREE_JSON_MODE", "json_schema").strip().lower()

# "ollama" provider
OLLAMA_NUM_CTX = int(os.getenv("AIGREE_OLLAMA_NUM_CTX", "8192"))
_think = os.getenv("AIGREE_OLLAMA_THINK", "").strip().lower()
OLLAMA_THINK = {"true": True, "false": False}.get(_think)  # None = model default

# "claude" provider
EFFORT = os.getenv("AIGREE_EFFORT", "medium")
MAX_OUTPUT_TOKENS = int(os.getenv("AIGREE_MAX_OUTPUT_TOKENS", "16000"))
USE_FALLBACKS = os.getenv("AIGREE_USE_FALLBACKS", "true").lower() == "true"

# ---- Chunking / limits ------------------------------------------------------
CHUNK_CHARS = int(os.getenv("AIGREE_CHUNK_CHARS", str(_d[4])))
CHUNK_OVERLAP_CHARS = int(os.getenv("AIGREE_CHUNK_OVERLAP_CHARS", "500"))
MAX_PARALLEL_CHUNKS = int(os.getenv("AIGREE_MAX_PARALLEL_CHUNKS", str(_d[3])))

MAX_INPUT_CHARS = int(os.getenv("AIGREE_MAX_INPUT_CHARS", "400000"))
MIN_INPUT_CHARS = 200

CORS_ORIGINS = [
    o.strip() for o in os.getenv("AIGREE_CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
