/** User choices, shared by the popup, background worker and content script. */

export type CookieChoice = "optOut" | "optIn"; // optOut = necessary cookies only
export type DefaultChoice = CookieChoice | "ask";

export type Settings = {
  defaultChoice: DefaultChoice;
  siteChoices: Record<string, CookieChoice>; // hostname -> remembered choice
};

const DEFAULTS: Settings = { defaultChoice: "ask", siteChoices: {} };
const KEY = "settings";

export async function getSettings(): Promise<Settings> {
  const stored = (await browser.storage.local.get(KEY))[KEY] as Partial<Settings> | undefined;
  return { ...DEFAULTS, ...stored, siteChoices: { ...stored?.siteChoices } };
}

export async function saveSettings(settings: Settings): Promise<void> {
  await browser.storage.local.set({ [KEY]: settings });
}

/** The choice to apply automatically on this site, or null to wait for the user. */
export function choiceFor(settings: Settings, hostname: string): CookieChoice | null {
  const site = settings.siteChoices[siteKey(hostname)];
  if (site) return site;
  return settings.defaultChoice === "ask" ? null : settings.defaultChoice;
}

/** "www.example.com" and "example.com" share one remembered choice. */
export function siteKey(hostname: string): string {
  return hostname.replace(/^www\./, "");
}

/** Per-tab status, written by the background worker and read by the popup. */
export type TabStatus = {
  state: "none" | "found" | "working" | "done" | "failed";
  cmp?: string; // name of the cookie-banner provider, e.g. "Onetrust"
  frameId?: number; // frame that holds the banner
  choice?: CookieChoice;
};

export const tabStatusKey = (tabId: number) => `tab-${tabId}`;
