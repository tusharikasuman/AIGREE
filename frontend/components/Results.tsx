import type { AnalysisResult } from "@/lib/api";
import ClauseList from "./ClauseList";
import ScoreRing from "./ScoreRing";
import SubScores from "./SubScores";

export default function Results({ result }: { result: AnalysisResult }) {
  return (
    <section aria-label="Analysis results" className="space-y-6">
      <div className="grid gap-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-3 md:border-r md:border-slate-200 md:pr-8">
          <ScoreRing score={result.trust_score} grade={result.grade} label={result.grade_label} />
          <ul className="max-w-[14rem] space-y-1 text-center text-xs text-slate-500">
            {result.score_notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
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
        <h2 className="text-lg font-semibold">What we found</h2>
        <p className="mb-4 text-sm text-slate-500">
          Every score starts at 100. Each item below shows how many points it changed the score by.
        </p>
        <ClauseList clauses={result.flagged_clauses} />
      </div>

      <p className="text-center text-xs text-slate-500">
        AI-generated analysis for information only. It is not legal advice.
      </p>
    </section>
  );
}
