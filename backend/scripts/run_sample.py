"""Run a real analysis from the command line (needs ANTHROPIC_API_KEY).

Usage (from backend/):
    python -m scripts.run_sample                       # analyzes samples/sample_tos.txt
    python -m scripts.run_sample path/to/terms.txt
    python -m scripts.run_sample https://example.com/terms
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from app.analyzer import Analyzer
from app.scraper import scrape_url

DEFAULT = Path(__file__).resolve().parent.parent / "samples" / "sample_tos.txt"


async def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT)
    text = await scrape_url(src) if src.startswith(("http://", "https://")) else Path(src).read_text(encoding="utf-8")
    start = time.perf_counter()
    result = await Analyzer().analyze(text)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    print(f"\n[{len(result.flagged_clauses)} clauses flagged in {time.perf_counter() - start:.1f}s]", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
