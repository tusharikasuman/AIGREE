export type Severity = "low" | "medium" | "high";

/** serious / notable / standard = checklist red flags by weight; good = good sign; other = not on the checklist. */
export type Tier = "serious" | "notable" | "standard" | "good" | "other";

export type Grade = "A" | "B" | "C" | "D" | "E";

export interface FlaggedClause {
  check_id: string;
  label: string;
  category: string;
  tier: Tier;
  severity: Severity;
  points: number; // effect on the trust score: negative = penalty, positive = good sign
  original_text: string;
  explanation: string;
  what_you_can_do: string;
}

export interface SubScores {
  data_privacy: number;
  financial_risk: number;
  user_rights: number;
  exit_clauses: number;
}

export interface AnalysisResult {
  summary: string;
  trust_score: number;
  grade: Grade;
  grade_label: string;
  sub_scores: SubScores;
  score_notes: string[];
  flagged_clauses: FlaggedClause[];
}

export type AnalyzeInput = { text: string } | { url: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 20 * 60 * 1000; // local models on a CPU can take several minutes

export async function analyze(input: AnalyzeInput, signal?: AbortSignal): Promise<AnalysisResult> {
  const timeout = AbortSignal.timeout(TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: combined,
    });
  } catch (e) {
    if (timeout.aborted) throw new Error("The analysis took too long. Try a shorter document.");
    if (signal?.aborted) throw e;
    throw new Error(`Can't reach the analysis server at ${API_URL}. Is the backend running?`);
  }

  if (!res.ok) throw new Error(await errorMessage(res));
  return (await res.json()) as AnalysisResult;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{loc, msg, ...}]
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d: { msg?: string }) => d.msg?.replace(/^Value error, /, "")).join(" ");
    }
  } catch {
    /* fall through */
  }
  return `Request failed (${res.status} ${res.statusText}).`;
}
