import { useEffect, useState } from "react";
import {
  analysisKey,
  BAND_LABEL,
  scoreBand,
  SUB_SCORE_LABEL,
  type AnalysisResult,
  type SiteAnalysis,
} from "@/utils/analysis";

/** Trust score for the current site's Terms, cached per site. */
export default function TermsCard({ tabId, site }: { tabId: number; site: string }) {
  const [analysis, setAnalysis] = useState<SiteAnalysis | null>(null);
  const key = analysisKey(site);

  useEffect(() => {
    browser.storage.local.get(key).then((r) => setAnalysis((r[key] as SiteAnalysis) ?? null));
    const onChange = (changes: Record<string, { newValue?: unknown }>, area: string) => {
      if (area === "local" && changes[key]) setAnalysis((changes[key].newValue as SiteAnalysis) ?? null);
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, [key]);

  const check = () => browser.runtime.sendMessage({ type: "aigree-analyze", tabId, site });
  const loading = analysis?.status === "loading";

  return (
    <section className="card">
      <h2>Terms & trust score</h2>

      {analysis?.status === "done" && <Score result={analysis.result} url={analysis.url} />}
      {analysis?.status === "error" && <p className="status failed">{analysis.error}</p>}
      {loading && <p className="status">Reading the terms… this takes about 10–30 seconds. You can close this popup.</p>}
      {!analysis && <p className="status">Find out what you're agreeing to on this site.</p>}

      <button className={analysis?.status === "done" ? "" : "primary"} disabled={loading} onClick={check}>
        {analysis?.status === "done" ? "Check again" : loading ? "Checking…" : "Check this site's terms"}
      </button>
    </section>
  );
}

function Score({ result, url }: { result: AnalysisResult; url: string }) {
  const band = scoreBand(result.trust_score);
  const top = result.flagged_clauses.filter((c) => c.severity !== "low").slice(0, 3);

  return (
    <div className="score">
      <div className="score-head">
        <span className={`score-num ${band}`}>{result.trust_score}</span>
        <div>
          <div className={`band ${band}`}>{BAND_LABEL[band]}</div>
          <a className="source" href={url} target="_blank" rel="noreferrer">
            {new URL(url).pathname || url}
          </a>
        </div>
      </div>

      <div className="subs">
        {(Object.keys(SUB_SCORE_LABEL) as (keyof AnalysisResult["sub_scores"])[]).map((k) => {
          const v = result.sub_scores[k];
          return (
            <div key={k} className="sub">
              <span>{SUB_SCORE_LABEL[k]}</span>
              <span className="bar">
                <span className={scoreBand(v)} style={{ width: `${v}%` }} />
              </span>
              <span className="sub-num">{v}</span>
            </div>
          );
        })}
      </div>

      {top.length > 0 && (
        <ul className="clauses">
          {top.map((c, i) => (
            <li key={i} className={c.severity}>
              <b>{c.category}</b> {c.explanation}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
