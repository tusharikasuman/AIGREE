/** T&C analysis: types shared with the backend, score bands, and the per-site cache. */

export const API_URL = "http://localhost:8000";

export type Severity = "low" | "medium" | "high";

export type FlaggedClause = {
  category: string;
  severity: Severity;
  original_text: string;
  explanation: string;
};

export type AnalysisResult = {
  summary: string;
  trust_score: number;
  sub_scores: { data_privacy: number; financial_risk: number; user_rights: number; exit_clauses: number };
  flagged_clauses: FlaggedClause[];
};

export type SiteAnalysis =
  | { status: "loading"; url?: string; at: number }
  | { status: "done"; url: string; at: number; result: AnalysisResult }
  | { status: "error"; url?: string; at: number; error: string };

export const analysisKey = (siteKey: string) => `analysis-${siteKey}`;

/** Same bands as the web app (frontend/lib/colors.ts). Higher = better for the user. */
export type Band = "good" | "fair" | "poor";

export function scoreBand(score: number): Band {
  if (score >= 70) return "good";
  if (score >= 40) return "fair";
  return "poor";
}

export const BAND_LABEL: Record<Band, string> = {
  good: "Fair to users",
  fair: "Some concerns",
  poor: "High risk",
};

export const SUB_SCORE_LABEL: Record<keyof AnalysisResult["sub_scores"], string> = {
  data_privacy: "Data privacy",
  financial_risk: "Money",
  user_rights: "Your rights",
  exit_clauses: "Leaving",
};

/** Links the content script found on the page. */
export type TermsLinks = { terms?: string; privacy?: string; self?: string };
