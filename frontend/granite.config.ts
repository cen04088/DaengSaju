import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "daengsaju",
  brand: {
    displayName: "\uB315\uC0AC\uC8FC",
    primaryColor: "#8B5CF6",
    icon: "https://static.toss.im/appsintoss/35905/e34cfdc1-e7bb-46e7-9c3f-6d08a6834e49.png",
  },
  web: {
    host: "localhost",
    port: 5173,
    commands: {
      dev: "vite dev",
      build: "vite build",
    },
  },
  permissions: [],
  outdir: "dist",
  webViewProps: {
    type: "partner",
  },
});
