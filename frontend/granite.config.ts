import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "daengsaju",
  brand: {
    displayName: "댕사주",
    primaryColor: "#8B5CF6",
    icon: "https://web-production-285b5.up.railway.app/appsintoss-logo.png",
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
});
