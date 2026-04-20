import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "daengsaju",
  brand: {
    displayName: "댕사주",
    primaryColor: "#8B5CF6",
    // ⚠️ 토스 콘솔 > 앱 정보 > 업로드된 이미지를 우클릭 > 링크 복사 후 교체 필요
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
    type: "partner", // 비게임: 좌측에 로고+앱이름, 우측에 더보기/X 버튼
  },
});
