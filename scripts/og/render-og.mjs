// 공유 미리보기 카드(1200×630) 생성: og-card.html 을 오행별로 렌더링해 assets/og_<오행>.jpg 로 저장
//
// 사용법 (Chrome 설치 필요):
//   cd scripts/og
//   npm install --no-save puppeteer-core
//   node render-og.mjs            # CHROME_PATH 환경변수로 Chrome 경로 지정 가능
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(here, '../../assets');
const chromePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const elements = ['wood', 'fire', 'earth', 'metal', 'water'];

const browser = await puppeteer.launch({ executablePath: chromePath, headless: true, args: ['--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });

for (const slug of elements) {
  const url = `${pathToFileURL(path.join(here, 'og-card.html')).href}?el=${slug}`;
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.evaluate(async () => {
    await document.fonts.ready;
    const img = document.getElementById('dog');
    if (!img.complete) await new Promise((resolve) => { img.onload = resolve; img.onerror = resolve; });
  });
  const file = path.join(outDir, `og_${slug}.jpg`);
  await page.screenshot({ path: file, type: 'jpeg', quality: 88 });
  console.log('saved', path.relative(path.resolve(here, '../..'), file));
}

await browser.close();
