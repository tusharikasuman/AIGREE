"use client";

import { useRef, useState } from "react";
import Results from "@/components/Results";
import { analyze, type AnalysisResult } from "@/lib/api";

type Mode = "text" | "url";

export default function Home() {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const input = mode === "text" ? text.trim() : url.trim();
  const canSubmit = !loading && input.length > 0;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    if (mode === "url" && !/^https?:\/\//i.test(input)) {
      setError("Enter a full URL starting with http:// or https://");
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyze(mode === "text" ? { text: input } : { url: input }, controller.signal);
      setResult(data);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      if (abortRef.current === controller) setLoading(false);
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:py-14">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">AIGREE</h1>
        <p className="mt-2 text-slate-600">Know what you&rsquo;re agreeing to. Paste Terms &amp; Conditions or a link.</p>
      </header>

      <form onSubmit={onSubmit} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 inline-flex rounded-lg bg-slate-100 p-1" role="tablist" aria-label="Input type">
          {(["text", "url"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
                mode === m ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {m === "text" ? "Paste text" : "From URL"}
            </button>
          ))}
        </div>

        {mode === "text" ? (
          <div>
            <label htmlFor="tc-text" className="sr-only">
              Terms and conditions text
            </label>
            <textarea
              id="tc-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the full Terms & Conditions here…"
              rows={10}
              disabled={loading}
              className="w-full resize-y rounded-lg border border-slate-300 p-3 text-sm leading-relaxed focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 disabled:bg-slate-50"
            />
            <p className="mt-1 text-right text-xs text-slate-500">{text.length.toLocaleString()} characters</p>
          </div>
        ) : (
          <div>
            <label htmlFor="tc-url" className="sr-only">
              Terms and conditions URL
            </label>
            <input
              id="tc-url"
              type="url"
              inputMode="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/terms"
              disabled={loading}
              className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 disabled:bg-slate-50"
            />
            <p className="mt-1 text-xs text-slate-500">Works best on plain pages. If a site blocks it, paste the text instead.</p>
          </div>
        )}

        <div className="mt-4 flex items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loading && (
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                aria-hidden="true"
              />
            )}
            {loading ? "Analyzing…" : "Analyze"}
          </button>
          {loading && (
            <button type="button" onClick={cancel} className="text-sm text-slate-600 underline hover:text-slate-900">
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="mt-8" aria-live="polite">
        {loading && <LoadingCard />}
        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <p className="font-semibold">Couldn&rsquo;t analyze that.</p>
            <p className="mt-1">{error}</p>
          </div>
        )}
        {result && <Results result={result} />}
      </div>
    </main>
  );
}

function LoadingCard() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-700">Reading the fine print… with a local model this can take a few minutes.</p>
      <div className="mt-4 animate-pulse space-y-3">
        <div className="h-24 rounded-lg bg-slate-100" />
        <div className="h-3 w-3/4 rounded bg-slate-100" />
        <div className="h-3 w-1/2 rounded bg-slate-100" />
        <div className="h-16 rounded-lg bg-slate-100" />
      </div>
    </div>
  );
}
