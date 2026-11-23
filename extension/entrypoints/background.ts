import { evalSnippets } from "@duckduckgo/autoconsent";
import type { ContentScriptMessage } from "@duckduckgo/autoconsent";
import { tabStatusKey, type TabStatus } from "@/utils/settings";
import { API_URL, analysisKey, type AnalysisResult, type SiteAnalysis, type TermsLinks } from "@/utils/analysis";

type AigreeMessage = { type: "aigree-analyze"; tabId: number; site: string };

async function setStatus(tabId: number, patch: Partial<TabStatus>) {
  const key = tabStatusKey(tabId);
  const current = ((await browser.storage.session.get(key))[key] as TabStatus | undefined) ?? { state: "none" };
  const next = { ...current, ...patch };
  await browser.storage.session.set({ [key]: next });
  const badge = { found: "!", working: "…", done: "✓", failed: "×", none: "" }[next.state];
  const color = { found: "#d97706", working: "#6b7280", done: "#16a34a", failed: "#dc2626", none: "#000000" }[next.state];
  await browser.action.setBadgeText({ tabId, text: badge });
  await browser.action.setBadgeBackgroundColor({ tabId, color });
}

/** Find the site's Terms (or Privacy) page, send it to the AIGREE backend, cache the result per site. */
async function analyzeSite(tabId: number, site: string) {
  const key = analysisKey(site);
  const save = (value: SiteAnalysis) => browser.storage.local.set({ [key]: value });
  await save({ status: "loading", at: Date.now() });

  let links: TermsLinks = {};
  try {
    links = await browser.tabs.sendMessage(tabId, { type: "aigree-findTerms" }, { frameId: 0 });
  } catch {
    return save({ status: "error", at: Date.now(), error: "Reload the page and try again." });
  }
  const url = links?.self ?? links?.terms ?? links?.privacy;
  if (!url) {
    return save({
      status: "error",
      at: Date.now(),
      error: "Couldn't find a Terms or Privacy link on this page. Open the site's Terms page and try again.",
    });
  }
  await save({ status: "loading", url, at: Date.now() });

  try {
    const res = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(body.detail) ? body.detail.map((d: any) => d.msg).join(" ") : body.detail;
      return save({ status: "error", url, at: Date.now(), error: detail || `The AIGREE server returned ${res.status}.` });
    }
    await save({ status: "done", url, at: Date.now(), result: body as AnalysisResult });
  } catch {
    await save({ status: "error", url, at: Date.now(), error: `Can't reach the AIGREE server at ${API_URL}. Is it running?` });
  }
}

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((msg: ContentScriptMessage | AigreeMessage, sender) => {
    // From the popup (no sender tab)
    if (msg.type === "aigree-analyze") {
      analyzeSite(msg.tabId, msg.site);
      return;
    }

    const tabId = sender.tab?.id;
    const frameId = sender.frameId ?? 0;
    if (tabId === undefined) return;

    switch (msg.type) {
      case "eval": {
        // Some banners can only be answered through the page's own JS API (e.g. Didomi.setUserDisagreeToAll()).
        // Only the library's fixed, bundled snippets are run; arbitrary code strings are never evaluated.
        const fn = msg.snippetId ? (evalSnippets as Record<string, () => unknown>)[msg.snippetId] : undefined;
        const reply = (result: unknown) =>
          browser.tabs.sendMessage(tabId, { type: "evalResp", id: msg.id, result }, { frameId });
        if (!fn) {
          reply(false);
          break;
        }
        browser.scripting
          .executeScript({ target: { tabId, frameIds: [frameId] }, world: "MAIN", func: fn })
          .then(([r]) => reply(r?.result))
          .catch(() => reply(false));
        break;
      }
      case "popupFound":
        setStatus(tabId, { state: "found", cmp: msg.cmp, frameId });
        break;
      case "optOutResult":
      case "optInResult":
        setStatus(tabId, {
          state: msg.result ? "done" : "failed",
          cmp: msg.cmp,
          frameId,
          choice: msg.type === "optOutResult" ? "optOut" : "optIn",
        });
        break;
    }
  });

  // A new page in the tab starts with a clean slate.
  browser.webNavigation?.onCommitted.addListener((d) => {
    if (d.frameId === 0) setStatus(d.tabId, { state: "none", cmp: undefined, frameId: undefined, choice: undefined });
  });
  browser.tabs.onRemoved.addListener((tabId) => browser.storage.session.remove(tabStatusKey(tabId)));
});
