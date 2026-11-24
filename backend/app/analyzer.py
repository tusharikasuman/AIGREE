"""Core pipeline: chunk -> find checklist items with the LLM -> verify quotes -> score in code."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from . import config
from .checklist import BY_ID
from .chunker import chunk_text, normalize
from .prompts import merge_prompt, system_prompt
from .providers import AnalysisError, Provider, make_provider
from .schemas import (
    ANALYSIS_JSON_SCHEMA,
    MERGE_JSON_SCHEMA,
    AnalysisResult,
    ChunkAnalysis,
    Finding,
    MergeResult,
    OtherConcern,
)
from .scoring import score

log = logging.getLogger("aigree.analyzer")

T = TypeVar("T", bound=BaseModel)
Q = TypeVar("Q", Finding, OtherConcern)

__all__ = ["Analyzer", "AnalysisError"]


# ---------------------------------------------------------------------------
# Quote verification: original_text must actually appear in the document.
# ---------------------------------------------------------------------------

_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "–": "-", "—": "-", " ": " "})


def _canon(s: str) -> str:
    """Loose form used only for matching: unify quotes/dashes, collapse whitespace, casefold."""
    return re.sub(r"\s+", " ", s.translate(_QUOTE_MAP)).strip().casefold()


def verify_quotes(items: list[Q], source: str) -> list[Q]:
    """No quote, no points: drop anything whose quote isn't really in the document."""
    canon_source = _canon(source)
    kept = []
    for c in items:
        if _canon(c.original_text) in canon_source:
            kept.append(c)
        else:
            log.warning("Dropping clause whose quote isn't in the source: %.80r", c.original_text)
    return kept


def dedupe_others(items: list[OtherConcern], findings: list[Finding]) -> list[OtherConcern]:
    """Drop 'other' concerns that repeat each other or quote a clause already on the checklist."""
    taken = [_canon(f.original_text) for f in findings]
    result: list[OtherConcern] = []
    for o in sorted(items, key=lambda o: (o.severity != "high", -len(o.original_text))):
        key = _canon(o.original_text)
        if any(key in k or k in key for k in taken):
            continue
        taken.append(key)
        result.append(o)
    return result


# ---------------------------------------------------------------------------
# Input sanity checks
# ---------------------------------------------------------------------------

NOT_TERMS_MESSAGE = (
    "This doesn't look like a Terms & Conditions or Privacy Policy document, so it can't be scored. "
    "Paste the full terms text, or use a link to the terms page."
)

_WORD = re.compile(r"[^\W\d_]+")


def looks_like_prose(text: str) -> bool:
    """Cheap check that catches keyboard-mash before spending an AI call on it.

    Real terms are made of ordinary-length words; random typing is mostly very long runs of
    letters. Language-neutral on purpose, so non-English terms still pass.
    """
    words = _WORD.findall(text)
    if not words:
        return False
    letters = sum(len(w) for w in words)
    normal = sum(len(w) for w in words if len(w) <= 20)
    return len(words) >= 30 and normal / letters >= 0.8


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

    async def _analyze_chunk(self, chunk: str, index: int, total: int) -> ChunkAnalysis:
        if total == 1:
            content = f"<document>\n{chunk}\n</document>\n\nAnalyze the terms above."
        else:
            content = (
                f'<document part="{index + 1}" of="{total}">\n{chunk}\n</document>\n\n'
                f"This is part {index + 1} of {total} of a longer document. Report only what this part says."
            )
        result = await self._call_validated(system_prompt(), content, ANALYSIS_JSON_SCHEMA, ChunkAnalysis)
        result.findings = verify_quotes(result.findings, chunk)
        result.other_concerns = verify_quotes(result.other_concerns, chunk)
        return result

    async def _merge(self, parts: list[ChunkAnalysis]) -> MergeResult:
        payload = [
            {"part": i + 1, "summary": p.summary,
             "found": [BY_ID[f.check_id].label for f in p.findings] + [o.label for o in p.other_concerns]}
            for i, p in enumerate(parts)
        ]
        content = (
            f"Here are the summaries of all {len(parts)} parts of the document:\n\n"
            f"<part_summaries>\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n</part_summaries>\n\n"
            "Write the summary for the whole document."
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
        if not looks_like_prose(text):
            raise AnalysisError(NOT_TERMS_MESSAGE, status_code=422)

        chunks = chunk_text(text, config.CHUNK_CHARS, config.CHUNK_OVERLAP_CHARS)
        log.info("Analyzing %d chars in %d chunk(s)", len(text), len(chunks))
        parts = await asyncio.gather(
            *(self._analyze_chunk(c, i, len(chunks)) for i, c in enumerate(chunks))
        )

        # Never turn "this isn't terms" into a score. In long documents, ignore parts that
        # aren't terms (e.g. page navigation) and score the rest.
        parts = [p for p in parts if p.is_terms_document]
        if not parts:
            raise AnalysisError(NOT_TERMS_MESSAGE, status_code=422)

        summary = parts[0].summary if len(parts) == 1 else (await self._merge(parts)).summary
        findings = [f for p in parts for f in p.findings]
        others = dedupe_others([o for p in parts for o in p.other_concerns], findings)
        return score(summary, findings, others)


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
