"use client";

import { useState } from "react";
import type { FlaggedClause, Tier } from "@/lib/api";
import { tierStyles } from "@/lib/colors";

const ORDER: Tier[] = ["serious", "notable", "other", "standard", "good"];

export default function ClauseList({ clauses }: { clauses: FlaggedClause[] }) {
  const [filter, setFilter] = useState<Tier | "all">("all");

  if (clauses.length === 0) {
    return <p className="text-sm text-slate-600">Nothing from the checklist was found in this document.</p>;
  }

  const counts = Object.fromEntries(ORDER.map((t) => [t, clauses.filter((c) => c.tier === t).length]));
  const shown = filter === "all" ? clauses : clauses.filter((c) => c.tier === filter);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by type">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>
          All ({clauses.length})
        </FilterButton>
        {ORDER.filter((t) => counts[t] > 0).map((t) => (
          <FilterButton key={t} active={filter === t} onClick={() => setFilter(t)}>
            <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${tierStyles[t].badge.split(" ")[0]}`} />
            {tierStyles[t].label} ({counts[t]})
          </FilterButton>
        ))}
      </div>

      <ul className="space-y-3">
        {shown.map((c, i) => (
          <li key={i} className={`rounded-lg border border-l-4 p-4 ${tierStyles[c.tier].card}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${tierStyles[c.tier].badge}`}
              >
                {tierStyles[c.tier].label}
              </span>
              <span className="text-[15px] font-semibold text-slate-900">{c.label}</span>
              <span className="ml-auto text-sm font-semibold tabular-nums text-slate-700">
                {c.points > 0 ? `+${c.points}` : c.points === 0 ? "±0" : `−${-c.points}`}
              </span>
            </div>
            <p className="mt-2 text-[15px] leading-relaxed text-slate-900">{c.explanation}</p>
            <blockquote className="mt-3 border-l-2 border-slate-300 pl-3 text-sm italic leading-relaxed text-slate-600">
              &ldquo;{c.original_text}&rdquo;
            </blockquote>
            {c.what_you_can_do && c.tier !== "good" && (
              <p className="mt-3 rounded-md bg-white/70 px-3 py-2 text-sm text-slate-800">
                <span className="font-semibold">What you can do: </span>
                {c.what_you_can_do}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`inline-flex items-center rounded-full border px-3 py-1 text-sm transition ${
        active ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
      }`}
    >
      {children}
    </button>
  );
}
