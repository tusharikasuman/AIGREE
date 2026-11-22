"""Core pipeline: chunk -> analyze each chunk with the LLM -> verify quotes -> merge."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from . import config
from .chunker import chunk_text, normalize
from .prompts import merge_prompt, system_prompt
from .providers import AnalysisError, Provider, make_provider
from .schemas import (
    ANALYSIS_JSON_SCHEMA,
    MERGE_JSON_SCHEMA,
    AnalysisResult,
    FlaggedClause,
    MergeResult,
)

log = logging.getLogger("aigree.analyzer")

T = TypeVar("T", bound=BaseModel)

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}

__all__ = ["Analyzer", "AnalysisError"]


# ---------------------------------------------------------------------------
# Quote verification: original_text must actually appear in the document.
# ---------------------------------------------------------------------------

_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "–": "-", "—": "-", " ": " "})


def _canon(s: str) -> str:
    """Loose form used only for matching: unify quotes/dashes, collapse whitespace, casefold."""
    return re.sub(r"\s+", " ", s.translate(_QUOTE_MAP)).strip().casefold()


def verify_clauses(clauses: list[FlaggedClause], source: str) -> list[FlaggedClause]:
    canon_source = _canon(source)
    kept = []
    for c in clauses:
        if _canon(c.original_text) in canon_source:
            kept.append(c)
        else:
            log.warning("Dropping clause whose quote isn't in the source: %.80r", c.original_text)
    return kept


def dedupe_clauses(clauses: list[FlaggedClause]) -> list[FlaggedClause]:
    """Remove duplicates (chunk overlap can flag the same clause twice), then sort by severity."""
    result: list[FlaggedClause] = []
    for c in sorted(clauses, key=lambda c: (-SEVERITY_RANK[c.severity], -len(c.original_text))):
        key = _canon(c.original_text)
        # Earlier items are more severe (or longer), so they win ties.
        if any(key in _canon(k.original_text) or _canon(k.original_text) in key for k in result):
            continue
        result.append(c)
    return result


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------


class Analyzer:
    def __init__(self, provider: Provider | None = None):
        self.provider = provider or make_provider()
        self._sem = asyncio.Semaphore(config.MAX_PARALLEL_CHUNKS)

    async def _call_validated(self, system: str, user_content: str, schema: dict, model_cls: type[T]) -> T:
        """Call the LLM, validate with Pydantic, and retry once with the error if it fails."""
        messages: list = [{"role": "user", "content": user_content}]
        last_error = ""
        for attempt in (1, 2):
            async with self._sem:
                resp = await self.provider.complete(system, messages, schema)

            if resp.stop == "refusal":
                raise AnalysisError("The AI declined to analyse this document.", status_code=422)

            raw = _strip_fences(resp.text)
            try:
                if resp.stop == "max_tokens":
                    raise ValueError("Output was cut off by the token limit; respond more concisely.")
                return model_cls.model_validate_json(raw)
            except ValueError as e:  # pydantic.ValidationError subclasses ValueError
                last_error = _short_error(e)
                log.warning("Attempt %d returned invalid output: %s", attempt, last_error)
                messages = messages + [
                    resp.assistant_message,
                    {
                        "role": "user",
                        "content": (
                            f"Your reply failed validation: {last_error}\n"
                            "Reply again with the complete, corrected JSON object only."
                        ),
                    },
                ]
        raise AnalysisError(f"The AI returned malformed output twice. Last error: {last_error}")

    async def _analyze_chunk(self, chunk: str, index: int, total: int) -> AnalysisResult:
        if total == 1:
            content = f"<document>\n{chunk}\n</document>\n\nAnalyze the terms above."
        else:
            content = (
                f'<document part="{index + 1}" of="{total}">\n{chunk}\n</document>\n\n'
                f"This is part {index + 1} of {total} of a longer document. Analyze only this part; "
                "base the scores only on what this part says."
            )
        result = await self._call_validated(system_prompt(), content, ANALYSIS_JSON_SCHEMA, AnalysisResult)
        result.flagged_clauses = verify_clauses(result.flagged_clauses, chunk)
        return result

    async def _merge(self, parts: list[AnalysisResult]) -> MergeResult:
        payload = [
            {"part": i + 1, **p.model_dump()} for i, p in enumerate(parts)
        ]
        content = (
            f"Here are the analyses of all {len(parts)} parts of the document:\n\n"
            f"<part_analyses>\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n</part_analyses>\n\n"
            "Produce the combined verdict for the whole document."
        )
        return await self._call_validated(merge_prompt(), content, MERGE_JSON_SCHEMA, MergeResult)

    async def analyze(self, text: str) -> AnalysisResult:
        text = normalize(text)
        if len(text) < config.MIN_INPUT_CHARS:
            raise AnalysisError(
                f"The text is too short to be a T&C document (minimum {config.MIN_INPUT_CHARS} characters).",
                status_code=400,
            )
        if len(text) > config.MAX_INPUT_CHARS:
            raise AnalysisError(
                f"The document is too long ({len(text):,} characters; limit {config.MAX_INPUT_CHARS:,}).",
                status_code=413,
            )

        chunks = chunk_text(text, config.CHUNK_CHARS, config.CHUNK_OVERLAP_CHARS)
        log.info("Analyzing %d chars in %d chunk(s)", len(text), len(chunks))
        parts = await asyncio.gather(
            *(self._analyze_chunk(c, i, len(chunks)) for i, c in enumerate(chunks))
        )

        if len(parts) == 1:
            result = parts[0]
            result.flagged_clauses = dedupe_clauses(result.flagged_clauses)
            return result

        merged = await self._merge(list(parts))
        return AnalysisResult(
            summary=merged.summary,
            trust_score=merged.trust_score,
            sub_scores=merged.sub_scores,
            flagged_clauses=dedupe_clauses([c for p in parts for c in p.flagged_clauses]),
        )


def _strip_fences(text: str) -> str:
    """Some models wrap JSON in ```json fences even when asked not to."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t


def _short_error(e: Exception) -> str:
    if isinstance(e, ValidationError):
        return "; ".join(
            f"{'.'.join(str(x) for x in err['loc']) or 'root'}: {err['msg']}" for err in e.errors()[:8]
        )
    return str(e)[:500]
