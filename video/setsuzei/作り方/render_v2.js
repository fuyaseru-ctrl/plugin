// video_v2.html（v1 と絵は同じ・時間割だけ v2＝まとめの声を差し替え）（年末の節税売りの説明動画・2026-11-28 に新NISAの render_v2.js から写した）を1コマずつ絵にする（逆指値の render_v2.js の写し・2026-11-26）（画面なしの Chrome）
//   静止画：node render_v1.js stills <出す先フォルダ> <秒,秒,...>
//           ＝撮るたびに「字幕の帯と絵のかぶり」「画面の外へのはみ出し」も数えて出す（目で見るのが本番・これは見落とし防ぎ）
//   動画　：node render_v1.js video <出力.mp4>（音なし・30コマ/秒・1920x1080）
//   配り口＝range_server.py 47666（王ディオのフォルダ全体を配る・日本語の名前は % に直して渡す）
const { chromium } = require('C:/Users/vioma/.claude/_mcp/node_modules/playwright-core');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const FF = 'C:/Users/vioma/OneDrive/デスクトップ/Claudcode/王ディオ/_ffmpeg/ffmpeg.exe';
const URL0 = 'http://127.0.0.1:47666/video_v2.html';   // 作り方フォルダの中で py range_server.py 47666 .

// 見えている絵のうち、字幕の帯にかぶる物・画面の外へ出る物を数える（親の overflow:hidden で切れている所は数えない）
function layoutProblems() {
  const W = 1920, H = 1080;
  const sub = document.getElementById('sub');
  const span = sub && sub.querySelector('span');
  const subShown = sub && parseFloat(getComputedStyle(sub).opacity) > 0.05 && span && span.textContent.trim() !== '';
  const sr = subShown ? span.getBoundingClientRect() : null;
  const out = [];
  const visible = el => {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
    }
    return true;
  };
  const clipped = el => {
    let r = el.getBoundingClientRect();
    let x1 = r.left, y1 = r.top, x2 = r.right, y2 = r.bottom;
    for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.overflow !== 'visible' || cs.overflowX !== 'visible' || cs.overflowY !== 'visible' || cs.clipPath !== 'none') {
        const pr = e.getBoundingClientRect();
        x1 = Math.max(x1, pr.left); y1 = Math.max(y1, pr.top); x2 = Math.min(x2, pr.right); y2 = Math.min(y2, pr.bottom);
      }
    }
    return { x1, y1, x2, y2 };
  };
  for (const el of document.body.querySelectorAll('*')) {
    if (el === sub || (sub && sub.contains(el))) continue;
    if (['SCRIPT', 'STYLE'].includes(el.tagName)) continue;
    const r0 = el.getBoundingClientRect();
    if (r0.width < 2 || r0.height < 2) continue;
    // 字か絵を持つ物だけ（ただの入れ物の箱は、中身で数える）
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim() !== '');
    const cs = getComputedStyle(el);
    const painted = hasText || ['IMG', 'SVG', 'CANVAS'].includes(el.tagName.toUpperCase()) ||
      (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent') || cs.borderTopWidth !== '0px' || cs.boxShadow !== 'none';
    if (!painted || !visible(el)) continue;
    const c = clipped(el);
    if (c.x2 - c.x1 < 2 || c.y2 - c.y1 < 2) continue;
    const name = (el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '')) +
      (hasText ? '「' + el.textContent.trim().slice(0, 12) + '」' : '');
    if (c.x1 < -1 || c.y1 < -1 || c.x2 > W + 1 || c.y2 > H + 1) {
      if (!(el.id === 'stage' || el.id === 'bg' || cs.position === 'fixed' && r0.width >= W)) out.push('画面の外 ' + name + ` (${Math.round(c.x1)},${Math.round(c.y1)})-(${Math.round(c.x2)},${Math.round(c.y2)})`);
    }
    if (sr && c.x1 < sr.right && c.x2 > sr.left && c.y1 < sr.bottom && c.y2 > sr.top) {
      // 画面いっぱいの下地（背景）は数えない
      if (!(r0.width >= W - 2 && r0.height >= H - 2)) out.push('字幕にかぶる ' + name + ` 下の端 ${Math.round(c.y2)} / 帯の上の端 ${Math.round(sr.top)}`);
    }
  }
  return { sub: sr ? { top: Math.round(sr.top), bottom: Math.round(sr.bottom), left: Math.round(sr.left), right: Math.round(sr.right) } : null, out };
}

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
    const report = [];
    for (const s of list.split(',')) {
      const t = parseFloat(s);
      await p.evaluate(t => window.render(t), t);
      const lp = await p.evaluate(layoutProblems);
      report.push({ t, ...lp });
      await p.screenshot({ path: path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`) });
    }
    for (const r of report) console.log(r.t.toFixed(2), '字幕', r.sub ? `${r.sub.top}-${r.sub.bottom}` : 'なし', r.out.length ? r.out.join(' ／ ') : '問題なし');
    console.log('静止画', report.length, '枚', '全部の長さ', total, 'エラー', errs);
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
