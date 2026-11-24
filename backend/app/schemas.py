"""Pydantic models: API request/response and the strict shape the AI must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from .checklist import CHECK_IDS

Severity = Literal["low", "medium", "high"]
Tier = Literal["serious", "notable", "standard", "good", "other"]

# Fixed category list keeps the UI consistent.
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


def _check_summary(v: str) -> str:
    words = len(v.split())
    if words > SUMMARY_MAX_WORDS:
        raise ValueError(f"summary has {words} words; must be under {SUMMARY_MAX_WORDS}")
    return v


# ---- What the AI returns for each chunk -----------------------------------


class Finding(BaseModel):
    """A checklist item the AI found in the document."""

    check_id: str
    original_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    what_you_can_do: str = ""

    @field_validator("check_id")
    @classmethod
    def known_check(cls, v: str) -> str:
        if v not in CHECK_IDS:
            raise ValueError(f"unknown check_id '{v}'")
        return v


class OtherConcern(BaseModel):
    """Something worth flagging that isn't on the checklist."""

    category: Category
    severity: Literal["medium", "high"]
    label: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    what_you_can_do: str = ""


class ChunkAnalysis(BaseModel):
    is_terms_document: bool
    summary: str = Field(min_length=1)
    findings: list[Finding]
    other_concerns: list[OtherConcern]

    _summary_len = field_validator("summary")(_check_summary)


class MergeResult(BaseModel):
    """For long documents: one summary written from the per-part summaries."""

    summary: str = Field(min_length=1)

    _summary_len = field_validator("summary")(_check_summary)


# ---- API -------------------------------------------------------------------


class SubScores(BaseModel):
    data_privacy: int = Field(ge=0, le=100)
    financial_risk: int = Field(ge=0, le=100)
    user_rights: int = Field(ge=0, le=100)
    exit_clauses: int = Field(ge=0, le=100)


class FlaggedClause(BaseModel):
    check_id: str  # checklist id, or "other"
    label: str
    category: Category
    tier: Tier
    severity: Severity
    points: int  # effect on the trust score: negative = penalty, positive = good sign
    original_text: str
    explanation: str
    what_you_can_do: str


class AnalysisResult(BaseModel):
    summary: str
    trust_score: int = Field(ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "E"]
    grade_label: str
    sub_scores: SubScores
    score_notes: list[str]  # plain-language explanation of how the score was reached
    flagged_clauses: list[FlaggedClause]


class AnalyzeRequest(BaseModel):
    text: str | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "AnalyzeRequest":
        has_text = bool(self.text and self.text.strip())
        if has_text == bool(self.url):
            raise ValueError("Provide exactly one of 'text' or 'url'.")
        return self


# ---- JSON Schemas sent to the AI's structured-output mode -------------------
# Hand-written to stay within the structured-output subset.

_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "check_id": {"type": "string", "enum": CHECK_IDS},
        "original_text": {"type": "string"},
        "explanation": {"type": "string"},
        "what_you_can_do": {"type": "string"},
    },
    "required": ["check_id", "original_text", "explanation", "what_you_can_do"],
    "additionalProperties": False,
}

_OTHER_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "severity": {"type": "string", "enum": ["medium", "high"]},
        "label": {"type": "string"},
        "original_text": {"type": "string"},
        "explanation": {"type": "string"},
        "what_you_can_do": {"type": "string"},
    },
    "required": ["category", "severity", "label", "original_text", "explanation", "what_you_can_do"],
    "additionalProperties": False,
}

ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_terms_document": {"type": "boolean"},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": _FINDING_SCHEMA},
        "other_concerns": {"type": "array", "items": _OTHER_SCHEMA},
    },
    "required": ["is_terms_document", "summary", "findings", "other_concerns"],
    "additionalProperties": False,
}

MERGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}
