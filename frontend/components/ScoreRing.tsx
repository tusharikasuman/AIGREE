import type { Grade } from "@/lib/api";
import { bandStyles, scoreBand } from "@/lib/colors";

export default function ScoreRing({ score, grade, label }: { score: number; grade: Grade; label: string }) {
  const band = scoreBand(score);
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score / 100);

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-36 w-36">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90" aria-hidden="true">
          <circle cx="60" cy="60" r={r} fill="none" strokeWidth="10" className="stroke-slate-200" />
          <circle
            cx="60"
            cy="60"
            r={r}
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${bandStyles[band].ring} transition-[stroke-dashoffset] duration-700`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-5xl font-bold leading-none ${bandStyles[band].text}`} aria-label={`Grade ${grade}`}>
            {grade}
          </span>
          <span className="mt-1 text-sm font-semibold tabular-nums text-slate-600">{score}/100</span>
        </div>
      </div>
      <p className="mt-2 text-sm font-semibold text-slate-700">Trust score</p>
      <p className={`text-sm font-medium ${bandStyles[band].text}`}>{label}</p>
    </div>
  );
}
