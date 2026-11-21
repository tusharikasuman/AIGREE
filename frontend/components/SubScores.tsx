import type { SubScores as SubScoresT } from "@/lib/api";
import { bandStyles, scoreBand } from "@/lib/colors";

const LABELS: { key: keyof SubScoresT; label: string; hint: string }[] = [
  { key: "data_privacy", label: "Data privacy", hint: "How well your personal data is protected" },
  { key: "financial_risk", label: "Financial safety", hint: "Higher = lower risk to your money" },
  { key: "user_rights", label: "User rights", hint: "Your freedoms and legal options" },
  { key: "exit_clauses", label: "Ease of leaving", hint: "How easy it is to cancel and leave" },
];

export default function SubScores({ scores }: { scores: SubScoresT }) {
  return (
    <ul className="space-y-4">
      {LABELS.map(({ key, label, hint }) => {
        const value = scores[key];
        const band = scoreBand(value);
        return (
          <li key={key}>
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium text-slate-800">{label}</span>
              <span className={`text-sm font-semibold tabular-nums ${bandStyles[band].text}`}>{value}</span>
            </div>
            <div
              className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-slate-200"
              role="meter"
              aria-label={label}
              aria-valuenow={value}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className={`h-full rounded-full ${bandStyles[band].bar} transition-[width] duration-700`}
                style={{ width: `${value}%` }}
              />
            </div>
            <p className="mt-0.5 text-xs text-slate-500">{hint}</p>
          </li>
        );
      })}
    </ul>
  );
}
