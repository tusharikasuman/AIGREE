# AIGREE browser extension (Phase 2)

Manifest V3 extension (React + TypeScript, built with [WXT](https://wxt.dev)).

**Cookie banners:** when a page shows a cookie popup, the toolbar icon gets an orange `!` badge. Open the popup and pick:

- **Necessary only**: rejects everything except the strictly necessary cookies that a site is allowed to set without consent. (Necessary cookies can't be refused, so this is the same as "Reject all".)
- **Accept all**

You can remember the choice per site, or set a default ("Automatically choose Necessary only") for every site. Banner detection and clicking use DuckDuckGo's [autoconsent](https://github.com/duckduckgo/autoconsent) rules (MPL-2.0), which cover over a thousand cookie-banner providers.

## Develop

```powershell
cd extension
npm install
npm run dev        # opens a Chrome window with the extension loaded and reloads on save
npm run build      # production build in .output/chrome-mv3
npm run zip        # .zip for the Chrome Web Store
```

## Load the build in your own Chrome / Edge

1. `npm run build`
2. Go to `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**
3. Click **Load unpacked** and pick `extension/.output/chrome-mv3`

## Layout

```
entrypoints/
  content.ts      # runs autoconsent in every page/frame; applies remembered/default choices
  background.ts   # tracks banner status per tab (badge), runs autoconsent's built-in page snippets
  popup/          # React popup: buttons, per-site memory, default setting
utils/settings.ts # stored settings + per-tab status types
```
