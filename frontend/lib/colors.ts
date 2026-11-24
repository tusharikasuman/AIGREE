import type { Tier } from "./api";

/** Score bands: higher score = better for the user. */
export type Band = "good" | "fair" | "poor";

export function scoreBand(score: number): Band {
  if (score >= 70) return "good";
  if (score >= 40) return "fair";
  return "poor";
}


export const bandStyles: Record<Band, { text: string; bar: string; ring: string; soft: string }> = {
  good: { text: "text-emerald-700", bar: "bg-emerald-500", ring: "stroke-emerald-500", soft: "bg-emerald-50" },
  fair: { text: "text-amber-700", bar: "bg-amber-400", ring: "stroke-amber-400", soft: "bg-amber-50" },
  poor: { text: "text-red-700", bar: "bg-red-500", ring: "stroke-red-500", soft: "bg-red-50" },
};

export const tierStyles: Record<Tier, { card: string; badge: string; label: string }> = {
  serious: { card: "border-red-200 bg-red-50 border-l-red-500", badge: "bg-red-600 text-white", label: "Serious" },
  notable: { card: "border-amber-200 bg-amber-50 border-l-amber-400", badge: "bg-amber-400 text-amber-950", label: "Notable" },
  other: { card: "border-amber-200 bg-amber-50 border-l-amber-400", badge: "bg-amber-200 text-amber-950", label: "Other concern" },
  standard: { card: "border-slate-200 bg-slate-50 border-l-slate-400", badge: "bg-slate-500 text-white", label: "Standard" },
  good: { card: "border-emerald-200 bg-emerald-50 border-l-emerald-500", badge: "bg-emerald-600 text-white", label: "Good sign" },
};
