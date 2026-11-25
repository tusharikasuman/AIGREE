import AutoConsent from "@duckduckgo/autoconsent";
import genericRules from "@/utils/rules/generic.json";
import { choiceFor, getSettings } from "@/utils/settings";
import type { TermsLinks } from "@/utils/analysis";

export default defineContentScript({
  matches: ["<all_urls>"],
  runAt: "document_start",
  allFrames: true,
  matchOriginAsFallback: true,
  async main() {
    // Rules for any site are bundled here; rules for this specific site come from the background worker.
    const [settings, siteRules] = await Promise.all([
      getSettings(),
      browser.runtime.sendMessage({ type: "aigree-siteRules", url: location.href }).catch(() => []),
    ]);
    const auto = choiceFor(settings, location.hostname);
    const rules = { autoconsent: [...(genericRules as any[]), ...((siteRules as any[]) ?? [])] };

    const consent = new AutoConsent(
      (msg) => browser.runtime.sendMessage(msg),
      {
        enabled: true,
        autoAction: auto, // null = detect the banner and wait for the user's click in the popup
        enablePrehide: auto !== null, // only hide the banner up front when we'll answer it ourselves
        enableCosmeticRules: true,
        detectRetries: 20,
        isMainWorld: false,
        logs: { lifecycle: false, rulesteps: false, detectionsteps: false, evals: false, errors: true, messages: false, waits: false },
      },
      rules as any,
    );

    browser.runtime.onMessage.addListener((message: any, _sender, sendResponse) => {
      if (message?.type === "aigree-findTerms") {
        if (window === window.top) sendResponse(findTermsLinks());
        return;
      }
      // optIn / optOut from the popup, evalResp from the background worker
      consent.receiveMessageCallback(message);
    });
  },
});

const TERMS = /\b(terms|conditions|terms of (service|use)|user agreement|tos)\b/i;
const TERMS_HREF = /terms|conditions|\btos\b|user-?agreement|legal/i;
const PRIVACY = /privacy/i;

/** Find the page's Terms and Privacy links (usually in the footer). */
function findTermsLinks(): TermsLinks {
  let terms: { url: string; score: number } | undefined;
  let privacy: string | undefined;

  for (const a of Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"))) {
    if (!/^https?:/.test(a.href)) continue;
    const text = (a.textContent || a.getAttribute("aria-label") || "").trim();
    if (text.length > 60) continue; // a sentence that happens to mention "terms", not a link label
    const score = (TERMS.test(text) ? 2 : 0) + (TERMS_HREF.test(a.href) ? 1 : 0) - (PRIVACY.test(text) ? 2 : 0);
    if (score >= 2 && (!terms || score > terms.score)) terms = { url: a.href, score };
    if (!privacy && PRIVACY.test(text)) privacy = a.href;
  }

  // Already on a terms/privacy page? Then analyse this page itself.
  const here = `${location.pathname} ${document.title}`;
  const self = TERMS_HREF.test(here) || PRIVACY.test(here) ? location.href : undefined;

  return { terms: terms?.url, privacy, self };
}
