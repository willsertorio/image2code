// Captures each scene from six angles into rubrics/captures/<id>/, for grading.
// Run from the repo root:  node rubrics/capture.js [id ...]
// Uses Playwright's Chromium with software WebGL, so frame rates here say nothing about a real GPU.
// THREE_DIR (optional): a local three.js package folder to serve CDN three.js requests from, for
// machines that can't reach the CDN; the scene's own pinned version must match.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname);
const ids = process.argv.slice(2).length ? process.argv.slice(2)
  : JSON.parse(fs.readFileSync(path.join(ROOT, 'rubrics.json'))).samples.map(s => s.id);
const W = 960, H = 600, SETTLE = +(process.env.SETTLE || 20000);

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const id of ids) {
    const file = path.join(ROOT, 'samples', id, 'model.html');
    if (!fs.existsSync(file)) { console.log(`${id}: no model.html, skipped`); continue; }
    const out = path.join(ROOT, 'captures', id);
    fs.rmSync(out, { recursive: true, force: true });
    fs.mkdirSync(out, { recursive: true });
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    const log = [];
    page.on('pageerror', e => log.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') log.push('console error: ' + m.text()); });
    page.on('requestfailed', r => log.push('request failed: ' + r.url() + ' ' + r.failure().errorText));
    if (process.env.THREE_DIR) {
      await page.route(/\/three@[^/]+\//, r => {
        const rel = r.request().url().replace(/^.*three@[^/]+\//, '').split('?')[0];
        r.fulfill({ path: path.join(process.env.THREE_DIR, rel), contentType: 'application/javascript' });
      });
    }
    await page.goto('file://' + file);
    await page.waitForTimeout(SETTLE);
    const shot = name => page.screenshot({ path: path.join(out, name + '.jpg'), type: 'jpeg', quality: 85 });
    const drag = async (dx, dy) => {
      await page.mouse.move(W / 2, H / 2); await page.mouse.down();
      for (let i = 1; i <= 12; i++) { await page.mouse.move(W / 2 + dx * i / 12, H / 2 + dy * i / 12); await page.waitForTimeout(60); }
      await page.mouse.up(); await page.waitForTimeout(SETTLE);
    };
    await shot('01_default_view');
    await drag(H / 4, 0); await shot('02_orbit_left');            // about a quarter turn each way
    await drag(-H / 2, 0); await shot('03_orbit_right');
    await drag(H / 4, H * 0.45); await shot('04_from_above');
    await drag(0, -H * 0.8); await shot('05_low_angle');
    await page.mouse.move(W / 2, H / 2);
    for (let i = 0; i < 30; i++) { await page.mouse.wheel(0, 400); await page.waitForTimeout(40); }
    await page.waitForTimeout(SETTLE); await shot('06_zoomed_out');
    fs.writeFileSync(path.join(out, 'console.txt'), log.join('\n') + (log.length ? '\n' : 'no errors\n'));
    console.log(`${id}: 6 captures, ${log.length ? log.length + ' console/page errors' : 'no errors'}`);
    await page.close();
  }
  await browser.close();
})();
