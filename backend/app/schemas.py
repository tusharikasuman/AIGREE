"""Pydantic models: API request/response and the strict shape Claude must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

Severity = Literal["low", "medium", "high"]

# Fixed category list keeps the UI consistent. Edit together with prompts/system_prompt.md.
Category = Literal[
    "Data Privacy",
    "Financial",
    "User Rights",
    "Exit & Termination",
    "Liability",
    "Dispute Resolution",
    "Content & IP",
    "Changes to Terms",
    "Other",
]
CATEGORIES: list[str] = list(Category.__args__)  # type: ignore[attr-defined]

SUMMARY_MAX_WORDS = 150


class SubScores(BaseModel):
    data_privacy: int = Field(ge=0, le=100)
    financial_risk: int = Field(ge=0, le=100)
    user_rights: int = Field(ge=0, le=100)
    exit_clauses: int = Field(ge=0, le=100)


class FlaggedClause(BaseModel):
    category: Category
    severity: Severity
    original_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


def _check_summary(v: str) -> str:
    words = len(v.split())
    if words > SUMMARY_MAX_WORDS:
        raise ValueError(f"summary has {words} words; must be under {SUMMARY_MAX_WORDS}")
    return v


class AnalysisResult(BaseModel):
    """The final API response, and also what Claude returns for each chunk."""

    summary: str = Field(min_length=1)
    trust_score: int = Field(ge=0, le=100)
    sub_scores: SubScores
    flagged_clauses: list[FlaggedClause]

    _summary_len = field_validator("summary")(_check_summary)


class MergeResult(BaseModel):
    """What the merge step returns: whole-document summary + scores (clauses merged in code)."""

    summary: str = Field(min_length=1)
    trust_score: int = Field(ge=0, le=100)
    sub_scores: SubScores

    _summary_len = field_validator("summary")(_check_summary)


class AnalyzeRequest(BaseModel):
    text: str | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "AnalyzeRequest":
        has_text = bool(self.text and self.text.strip())
        if has_text == bool(self.url):
            raise ValueError("Provide exactly one of 'text' or 'url'.")
        return self


# ---- JSON Schemas sent to Claude's structured-output mode -------------------
# Hand-written (not model_json_schema()) to stay within the structured-output
# subset. Numeric ranges and the word limit are enforced by Pydantic above.

_SUB_SCORES_SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "integer"} for k in SubScores.model_fields},
    "required": list(SubScores.model_fields),
    "additionalProperties": False,
}

_CLAUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "original_text": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["category", "severity", "original_text", "explanation"],
    "additionalProperties": False,
}

ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "trust_score": {"type": "integer"},
        "sub_scores": _SUB_SCORES_SCHEMA,
        "flagged_clauses": {"type": "array", "items": _CLAUSE_SCHEMA},
    },
    "required": ["summary", "trust_score", "sub_scores", "flagged_clauses"],
    "additionalProperties": False,
}

MERGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "trust_score": {"type": "integer"},
        "sub_scores": _SUB_SCORES_SCHEMA,
    },
    "required": ["summary", "trust_score", "sub_scores"],
    "additionalProperties": False,
}
