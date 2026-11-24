// video_v2.html（大株主の動き）を1コマずつ絵にする（相場環境の render_v3.js の写し・2026-11-23）（画面なしの Chrome）
//   静止画：node render.js stills <出す先フォルダ> <秒,秒,...>
//   動画　：node render.js video <出力.mp4>（音なし・30コマ/秒・1920x1080）
const { chromium } = require('C:/Users/vioma/.claude/_mcp/node_modules/playwright-core');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const FF = 'C:/Users/vioma/OneDrive/デスクトップ/Claudcode/王ディオ/_ffmpeg/ffmpeg.exe';
const URL0 = 'http://127.0.0.1:47632/video_v2.html';
(async () => {
  const [mode, out, list] = process.argv.slice(2);
  const b = await chromium.launch({ channel: 'chrome', headless: true });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(URL0 + '?v=' + Date.now());
  await p.waitForFunction(() => window.READY === true, null, { timeout: 30000 });
  const total = await p.evaluate(() => window.TL.total);
  if (mode === 'stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const s of list.split(',')) {
      const t = parseFloat(s);
      await p.evaluate(t => window.render(t), t);
      await p.screenshot({ path: path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`) });
    }
    console.log('静止画', list.split(',').length, '枚', 'エラー', errs);
  } else {
    if (fs.existsSync(out)) { console.error('もうあるので書かない:', out); process.exit(1); }
    const fps = 30, n = Math.ceil(total * fps);
    const ff = spawn(FF, ['-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let f = 0; f < n; f++) {
      await p.evaluate(t => window.render(t), f / fps);
      const buf = await p.screenshot({ type: 'jpeg', quality: 94 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 300 === 0) console.log(`${f}/${n} コマ  ${((Date.now() - t0) / 1000).toFixed(0)}秒`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('動画', out, n, 'コマ', ((Date.now() - t0) / 1000).toFixed(0), '秒', 'エラー', errs);
  }
  await b.close();
})();
