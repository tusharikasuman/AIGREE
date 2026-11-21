import type { AnalysisResult } from "@/lib/api";
import ClauseList from "./ClauseList";
import ScoreRing from "./ScoreRing";
import SubScores from "./SubScores";

export default function Results({ result }: { result: AnalysisResult }) {
  return (
    <section aria-label="Analysis results" className="space-y-6">
      <div className="grid gap-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-[auto_1fr]">
        <div className="flex justify-center md:border-r md:border-slate-200 md:pr-8">
          <ScoreRing score={result.trust_score} />
        </div>
        <div className="space-y-5">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">In plain words</h2>
            <p className="mt-1 leading-relaxed text-slate-800">{result.summary}</p>
          </div>
          <SubScores scores={result.sub_scores} />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Flagged clauses</h2>
        <ClauseList clauses={result.flagged_clauses} />
      </div>

      <p className="text-center text-xs text-slate-500">
        AI-generated analysis for information only. It is not legal advice.
      </p>
    </section>
  );
}
