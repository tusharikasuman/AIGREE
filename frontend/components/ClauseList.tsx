"use client";

import { useState } from "react";
import type { FlaggedClause, Severity } from "@/lib/api";
import { severityStyles } from "@/lib/colors";

const ORDER: Severity[] = ["high", "medium", "low"];

export default function ClauseList({ clauses }: { clauses: FlaggedClause[] }) {
  const [filter, setFilter] = useState<Severity | "all">("all");

  if (clauses.length === 0) {
    return <p className="text-sm text-slate-600">No clauses were flagged in this document.</p>;
  }

  const counts = Object.fromEntries(ORDER.map((s) => [s, clauses.filter((c) => c.severity === s).length]));
  const shown = filter === "all" ? clauses : clauses.filter((c) => c.severity === filter);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by severity">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>
          All ({clauses.length})
        </FilterButton>
        {ORDER.map((s) => (
          <FilterButton key={s} active={filter === s} onClick={() => setFilter(s)} disabled={counts[s] === 0}>
            <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${severityStyles[s].badge.split(" ")[0]}`} />
            {severityStyles[s].label} ({counts[s]})
          </FilterButton>
        ))}
      </div>

      <ul className="space-y-3">
        {shown.map((c, i) => (
          <li key={i} className={`rounded-lg border border-l-4 p-4 ${severityStyles[c.severity].card}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${severityStyles[c.severity].badge}`}
              >
                {severityStyles[c.severity].label}
              </span>
              <span className="text-sm font-semibold text-slate-800">{c.category}</span>
            </div>
            <p className="mt-2 text-[15px] leading-relaxed text-slate-900">{c.explanation}</p>
            <blockquote className="mt-3 border-l-2 border-slate-300 pl-3 text-sm italic leading-relaxed text-slate-600">
              &ldquo;{c.original_text}&rdquo;
            </blockquote>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FilterButton({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={`inline-flex items-center rounded-full border px-3 py-1 text-sm transition disabled:cursor-not-allowed disabled:opacity-40 ${
        active ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
      }`}
    >
      {children}
    </button>
  );
}
