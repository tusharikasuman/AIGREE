"""Settings, read from environment variables (or backend/.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

PROMPTS_DIR = BACKEND_DIR / "prompts"

MODEL = os.getenv("AIGREE_MODEL", "claude-opus-5-5")
# low | medium | high | xhigh | max. Thinking depth vs. cost/latency.
EFFORT = os.getenv("AIGREE_EFFORT", "medium")
MAX_OUTPUT_TOKENS = int(os.getenv("AIGREE_MAX_OUTPUT_TOKENS", "16000"))

# If Claude declines a request, retry it automatically on a fallback model
# (server-side, same API call). Set to "false" to turn it off.
USE_FALLBACKS = os.getenv("AIGREE_USE_FALLBACKS", "true").lower() == "true"

# Chunking: ~30k chars is roughly 7-8k tokens per chunk.
CHUNK_CHARS = int(os.getenv("AIGREE_CHUNK_CHARS", "30000"))
CHUNK_OVERLAP_CHARS = int(os.getenv("AIGREE_CHUNK_OVERLAP_CHARS", "500"))
MAX_PARALLEL_CHUNKS = int(os.getenv("AIGREE_MAX_PARALLEL_CHUNKS", "4"))

# Hard cap on input size so a huge page can't run up a big bill.
MAX_INPUT_CHARS = int(os.getenv("AIGREE_MAX_INPUT_CHARS", "400000"))
MIN_INPUT_CHARS = 200

CORS_ORIGINS = [
    o.strip() for o in os.getenv("AIGREE_CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
