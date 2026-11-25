import { useEffect, useState } from "react";
import {
  DEFAULT_API_URL,
  getSettings,
  saveSettings,
  siteKey,
  tabStatusKey,
  type CookieChoice,
  type DefaultChoice,
  type Settings,
  type TabStatus,
} from "@/utils/settings";
import TermsCard from "./TermsCard";

const CHOICE_LABEL: Record<CookieChoice, string> = {
  optOut: "Necessary only",
  optIn: "Accept all",
};

export default function App() {
  const [tab, setTab] = useState<{ id: number; host: string } | null>(null);
  const [status, setStatus] = useState<TabStatus>({ state: "none" });
  const [settings, setSettings] = useState<Settings | null>(null);
  const [remember, setRemember] = useState(false);

  useEffect(() => {
    (async () => {
      const [active] = await browser.tabs.query({ active: true, currentWindow: true });
      const host = active?.url?.startsWith("http") ? new URL(active.url).hostname : "";
      if (active?.id !== undefined) setTab({ id: active.id, host });
      setSettings(await getSettings());
    })();
  }, []);

  // Follow the banner status live while the popup is open.
  useEffect(() => {
    if (!tab) return;
    const key = tabStatusKey(tab.id);
    browser.storage.session.get(key).then((r) => setStatus((r[key] as TabStatus) ?? { state: "none" }));
    const onChange = (changes: Record<string, { newValue?: unknown }>, area: string) => {
      if (area === "session" && changes[key]) setStatus((changes[key].newValue as TabStatus) ?? { state: "none" });
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, [tab]);

  async function apply(choice: CookieChoice) {
    if (!tab || !settings) return;
    setStatus((s) => ({ ...s, state: "working", choice }));
    await browser.tabs
      .sendMessage(tab.id, { type: choice }, { frameId: status.frameId ?? 0 })
      .catch(() => setStatus((s) => ({ ...s, state: "failed" })));
    if (remember && tab.host) {
      const next = { ...settings, siteChoices: { ...settings.siteChoices, [siteKey(tab.host)]: choice } };
      setSettings(next);
      await saveSettings(next);
    }
  }

  async function setDefault(defaultChoice: DefaultChoice) {
    if (!settings) return;
    const next = { ...settings, defaultChoice };
    setSettings(next);
    await saveSettings(next);
  }

  async function forgetSite() {
    if (!tab || !settings) return;
    const { [siteKey(tab.host)]: _removed, ...rest } = settings.siteChoices;
    const next = { ...settings, siteChoices: rest };
    setSettings(next);
    await saveSettings(next);
  }

  if (!settings) return null;
  const remembered = tab?.host ? settings.siteChoices[siteKey(tab.host)] : undefined;
  const canAct = status.state === "found" || status.state === "failed";

  return (
    <main>
      <header>
        <h1>AIGREE</h1>
        <span className="host">{tab?.host || "This page"}</span>
      </header>

      <section className="card">
        <h2>Cookie banner</h2>
        <p className={`status ${status.state}`}>{statusText(status)}</p>

        <div className="buttons">
          <button className="primary" disabled={!canAct} onClick={() => apply("optOut")}>
            Necessary only
          </button>
          <button disabled={!canAct} onClick={() => apply("optIn")}>
            Accept all
          </button>
        </div>
        <label className="check">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          Remember my choice for this site
        </label>

        {remembered && (
          <p className="remembered">
            Always <b>{CHOICE_LABEL[remembered]}</b> here.{" "}
            <button className="link" onClick={forgetSite}>
              Forget
            </button>
          </p>
        )}
      </section>

      {tab?.host && <TermsCard tabId={tab.id} site={siteKey(tab.host)} />}

      <section className="card">
        <h2>On every other site</h2>
        {(["ask", "optOut", "optIn"] as DefaultChoice[]).map((c) => (
          <label key={c} className="radio">
            <input type="radio" name="default" checked={settings.defaultChoice === c} onChange={() => setDefault(c)} />
            {c === "ask" ? "Ask me (show the buttons)" : `Automatically choose ${CHOICE_LABEL[c]}`}
          </label>
        ))}
        <p className="hint">Takes effect when a page loads.</p>
      </section>

      <ServerSetting
        value={settings.apiUrl}
        onSave={async (apiUrl) => {
          const next = { ...settings, apiUrl };
          setSettings(next);
          await saveSettings(next);
        }}
      />
    </main>
  );
}

/** Where the terms are sent for analysis. Defaults to a backend running on this computer. */
function ServerSetting({ value, onSave }: { value: string; onSave: (url: string) => Promise<void> }) {
  const [draft, setDraft] = useState(value);
  const [msg, setMsg] = useState("");

  async function save() {
    const url = draft.trim().replace(/\/+$/, "");
    if (!/^https?:\/\/[^\s/]+/.test(url)) return setMsg("Enter a full address, e.g. http://localhost:8000");
    await onSave(url);
    setDraft(url);
    try {
      const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
      setMsg(r.ok ? "Saved. The server is reachable." : `Saved, but the server answered ${r.status}.`);
    } catch {
      setMsg("Saved, but the server can't be reached right now.");
    }
  }

  return (
    <details className="card server">
      <summary>AIGREE server</summary>
      <p className="hint">Terms are sent here to be analysed.</p>
      <div className="server-row">
        <input
          type="url"
          value={draft}
          spellCheck={false}
          aria-label="AIGREE server address"
          onChange={(e) => (setDraft(e.target.value), setMsg(""))}
          onKeyDown={(e) => e.key === "Enter" && save()}
        />
        <button onClick={save} disabled={draft.trim() === value}>
          Save
        </button>
      </div>
      {msg && <p className="hint">{msg}</p>}
      {value !== DEFAULT_API_URL && (
        <button className="link" onClick={() => (setDraft(DEFAULT_API_URL), onSave(DEFAULT_API_URL), setMsg(""))}>
          Use this computer ({DEFAULT_API_URL})
        </button>
      )}
    </details>
  );
}

function statusText(s: TabStatus): string {
  const who = s.cmp ? ` (${s.cmp})` : "";
  switch (s.state) {
    case "found":
      return `Cookie banner found${who}. Pick an option below.`;
    case "working":
      return "Answering the banner…";
    case "done":
      return `Done: ${s.choice ? CHOICE_LABEL[s.choice] : "answered"}${who}.`;
    case "failed":
      return `Couldn't answer this banner automatically${who}. Try again, or use the site's own buttons.`;
    default:
      return "No cookie banner detected on this page (yet).";
  }
}
