/** T&C analysis: types shared with the backend, score bands, and the per-site cache. */

export type Severity = "low" | "medium" | "high";

export type Tier = "serious" | "notable" | "standard" | "good" | "other";

export type FlaggedClause = {
  check_id: string;
  label: string;
  category: string;
  tier: Tier;
  severity: Severity;
  points: number; // negative = penalty, positive = good sign
  original_text: string;
  explanation: string;
  what_you_can_do: string;
};

export type AnalysisResult = {
  summary: string;
  trust_score: number;
  grade: "A" | "B" | "C" | "D" | "E";
  grade_label: string;
  sub_scores: { data_privacy: number; financial_risk: number; user_rights: number; exit_clauses: number };
  score_notes: string[];
  flagged_clauses: FlaggedClause[];
};

export type SiteAnalysis =
  | { status: "loading"; url?: string; at: number }
  | { status: "done"; url: string; at: number; result: AnalysisResult }
  | { status: "error"; url?: string; at: number; error: string };

// v2: checklist scoring. Results cached by older versions are ignored.
export const analysisKey = (siteKey: string) => `analysis-v2-${siteKey}`;

/** Same bands as the web app (frontend/lib/colors.ts). Higher = better for the user. */
export type Band = "good" | "fair" | "poor";

export function scoreBand(score: number): Band {
  if (score >= 70) return "good";
  if (score >= 40) return "fair";
  return "poor";
}


export const SUB_SCORE_LABEL: Record<keyof AnalysisResult["sub_scores"], string> = {
  data_privacy: "Data privacy",
  financial_risk: "Money",
  user_rights: "Your rights",
  exit_clauses: "Leaving",
};

/** Links the content script found on the page. */
export type TermsLinks = { terms?: string; privacy?: string; self?: string };
