import AutoConsent from "@duckduckgo/autoconsent";
import rules from "@duckduckgo/autoconsent/rules/rules.json";
import { choiceFor, getSettings } from "@/utils/settings";

export default defineContentScript({
  matches: ["<all_urls>"],
  runAt: "document_start",
  allFrames: true,
  matchOriginAsFallback: true,
  async main() {
    const settings = await getSettings();
    const auto = choiceFor(settings, location.hostname);

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

    // optIn / optOut from the popup, evalResp from the background worker
    browser.runtime.onMessage.addListener((message) => {
      consent.receiveMessageCallback(message);
    });
  },
});
