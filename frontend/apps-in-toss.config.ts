import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "daengsaju",
  webView: {},
  navigationBar: {
    withBackButton: true,
    withHomeButton: true,
  },
  permissions: [],
  webBundleDir: "dist",
});
