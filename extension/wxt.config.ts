import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "AIGREE",
    description: "One-click cookie choices and plain-language T&C checks.",
    permissions: ["storage", "scripting", "tabs", "webNavigation"],
    host_permissions: ["<all_urls>"],
  },
});
