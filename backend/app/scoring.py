"""Turn checklist findings into the trust score, sub-scores and grade. No AI involved."""

from __future__ import annotations

from .checklist import (
    A_MIN_SCORE,
    BY_ID,
    OTHER_POINTS,
    OTHER_TOTAL_CAP,
    SERIOUS_CAPS,
    SEVERITY,
    SUB_SCORE_MULTIPLIER,
    grade_for,
)
from .schemas import AnalysisResult, Finding, FlaggedClause, OtherConcern, SubScores

# Areas for "other" concerns, by category (sub-scores only; they always count overall).
_OTHER_AREA = {
    "Data Privacy": "data_privacy",
    "Financial": "financial_risk",
    "User Rights": "user_rights",
    "Liability": "user_rights",
    "Dispute Resolution": "user_rights",
    "Changes to Terms": "user_rights",
    "Content & IP": "user_rights",
    "Exit & Termination": "exit_clauses",
}


def _n(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def score(summary: str, findings: list[Finding], others: list[OtherConcern]) -> AnalysisResult:
    """`findings` must already be quote-verified; each checklist item counts once."""
    clauses: list[FlaggedClause] = []
    area_points = {a: 0 for a in SubScores.model_fields}

    seen: set[str] = set()
    for f in findings:
        if f.check_id in seen:
            continue
        seen.add(f.check_id)
        check = BY_ID[f.check_id]
        if check.area:
            area_points[check.area] += check.points
        clauses.append(FlaggedClause(
            check_id=check.id, label=check.label, category=check.category, tier=check.tier,
            severity=SEVERITY[check.tier], points=check.points, original_text=f.original_text,
            explanation=f.explanation, what_you_can_do=f.what_you_can_do.strip() or check.tip,
        ))

    # Concerns outside the checklist: small penalties, capped in total.
    other_budget = OTHER_TOTAL_CAP
    for o in others:
        points = max(OTHER_POINTS[o.severity], other_budget)
        other_budget -= points
        area = _OTHER_AREA.get(o.category)
        if area:
            area_points[area] += points
        clauses.append(FlaggedClause(
            check_id="other", label=o.label, category=o.category, tier="other", severity=o.severity,
            points=points, original_text=o.original_text, explanation=o.explanation,
            what_you_can_do=o.what_you_can_do.strip(),
        ))

    penalties = sum(c.points for c in clauses if c.points < 0)
    bonuses = sum(c.points for c in clauses if c.points > 0)
    total = _clamp(100 + penalties + bonuses)

    red_flags = sum(1 for c in clauses if c.points < 0)
    good = sum(1 for c in clauses if c.points > 0)
    if red_flags:
        notes = [f"Starts at 100. {_n(red_flags, 'issue')} cost {-penalties} points"
                 + (f"; {_n(good, 'good sign')} add{'s' if good == 1 else ''} {bonuses}." if good else ".")]
    else:
        notes = ["Starts at 100. No issues from the checklist were found"
                 + (f"; {_n(good, 'good sign')} add{'s' if good == 1 else ''} {bonuses}." if good else ".")]

    serious = sum(1 for c in clauses if c.tier == "serious")
    for minimum, cap in SERIOUS_CAPS:
        if serious >= minimum:
            if total > cap:
                total = cap
                notes.append(f"Limited to {cap} because of {_n(serious, 'serious red flag')}.")
            break

    # Saying nothing bad isn't the same as being good: an A needs real commitments to the user.
    if total >= A_MIN_SCORE and good == 0:
        total = A_MIN_SCORE - 1
        notes.append(f"Limited to {total}: an A needs at least one good sign, such as a promise not to sell your data.")
    if red_flags == 0:
        notes.append("No red flags were found, but that isn't a guarantee. The check can miss things, "
                     "so read anything important yourself.")

    sub_scores = SubScores(**{a: _clamp(100 + SUB_SCORE_MULTIPLIER * p) for a, p in area_points.items()})
    letter, label = grade_for(total)
    clauses.sort(key=lambda c: c.points)  # worst first, good signs last

    return AnalysisResult(
        summary=summary, trust_score=total, grade=letter, grade_label=label,
        sub_scores=sub_scores, score_notes=notes, flagged_clauses=clauses,
    )
