import { evalSnippets } from "@duckduckgo/autoconsent";
import type { ContentScriptMessage } from "@duckduckgo/autoconsent";
import { tabStatusKey, type TabStatus } from "@/utils/settings";

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

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((msg: ContentScriptMessage, sender) => {
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
