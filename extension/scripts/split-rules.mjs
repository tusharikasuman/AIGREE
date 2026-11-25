// Split autoconsent's rules.json so pages don't each load all ~1,400 rules.
//   generic.json : rules that can match any site. Bundled into the content script.
//   site.json    : rules for one specific site (runContext.urlPattern). Kept in the background
//                  worker, which sends a page only the ones matching its URL.
// Runs automatically on `npm install`, `npm run dev` and `npm run build`.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { autoconsent } = JSON.parse(readFileSync(require.resolve("@duckduckgo/autoconsent/rules/rules.json"), "utf8"));

const isSiteSpecific = (r) => Boolean(r.runContext?.urlPattern);
const generic = autoconsent.filter((r) => !isSiteSpecific(r));
const site = autoconsent.filter(isSiteSpecific);

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "utils", "rules");
mkdirSync(out, { recursive: true });
writeFileSync(join(out, "generic.json"), JSON.stringify(generic));
writeFileSync(join(out, "site.json"), JSON.stringify(site));
console.log(`autoconsent rules: ${generic.length} generic, ${site.length} site-specific`);
