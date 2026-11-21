export type Severity = "low" | "medium" | "high";

export interface FlaggedClause {
  category: string;
  severity: Severity;
  original_text: string;
  explanation: string;
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
  sub_scores: SubScores;
  flagged_clauses: FlaggedClause[];
}

export type AnalyzeInput = { text: string } | { url: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 5 * 60 * 1000; // long documents are analysed in several AI calls

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
