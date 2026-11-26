// Key rows on the built page, measured: the letter, the record of past elections, the question, the 2028 status and the
// record panel never overlap, at desktop, tablet and phone widths, at 150% and 200% zoom, light and dark, records closed and open.
//   node tests/browser_keys.js
const { chromium } = require('playwright'); const path = require('path');
const file = 'file://' + path.join(__dirname, '..', 'docs', 'index.html');
(async () => {
  const b = await chromium.launch(); const report = {};
  for (const [w, h, zoom, scheme] of [[1440, 900, 1, 'light'], [1280, 900, 1, 'dark'], [1024, 800, 1, 'light'], [820, 1100, 1, 'light'], [761, 1000, 1, 'light'], [760, 1000, 1, 'dark'], [600, 900, 1, 'light'], [390, 844, 1, 'dark'], [320, 700, 1, 'light'], [1280, 900, 2, 'light'], [1280, 900, 1.5, 'light']]) {
    const ctx = await b.newContext({ viewport: {width: Math.round(w / zoom), height: Math.round(h / zoom)}, deviceScaleFactor: zoom, colorScheme: scheme });
    const p = await ctx.newPage(); await p.goto(file); await p.waitForTimeout(1200); for (const open of [false, true]) { if (open) { await p.evaluate(() => document.querySelectorAll('.key .kd').forEach(d => d.open = true)); await p.waitForTimeout(800); }
    const measure = () => p.evaluate(() => {
      const box = e => e.getBoundingClientRect(), hit = (a, c) => a.width > 0 && c.width > 0 && a.left < c.right - 0.5 && c.left < a.right - 0.5 && a.top < c.bottom - 0.5 && c.top < a.bottom - 0.5;
      const keys = [...document.querySelectorAll('.key')], bad = [];
      let maxLines = 0, minStrip = 1e9;
      keys.forEach(k => {
        const id = k.querySelector('.id'), hist = k.querySelector('.hist'), strip = k.querySelector('.strip'), now = k.querySelector('.now'), q = k.querySelector('.q').parentElement, kd = k.querySelector('.kd summary');
        const B = {id: box(id), strip: box(strip), q: box(q), now: box(now), kd: box(kd), hist: box(hist)};
        const marks = [...strip.children].map(box); const sr = {left: Math.min(...marks.map(m => m.left)), right: Math.max(...marks.map(m => m.right)), top: Math.min(...marks.map(m => m.top)), bottom: Math.max(...marks.map(m => m.bottom))}; sr.width = sr.right - sr.left;
        const pairs = [['id', B.id, 'strip', sr], ['id', B.id, 'q', B.q], ['strip', sr, 'q', B.q], ['strip', sr, 'now', B.now], ['q', B.q, 'now', B.now], ['hist', B.hist, 'now', B.now], ['kd', B.kd, 'now', B.now], ['kd', B.kd, 'strip', sr]];
        pairs.forEach(([a, x, c, y]) => { if (hit(x, y)) bad.push(id.textContent + ': ' + a + '/' + c); });
        if (sr.right > box(k).right + 0.5 || sr.left < box(k).left - 0.5) bad.push(id.textContent + ': strip outside the row');
        if (sr.right > B.hist.right + 0.5) bad.push(id.textContent + ': strip wider than its column (' + Math.round(sr.width) + ' > ' + Math.round(B.hist.width) + ')');
        const tn = [...hist.childNodes].find(n => n.nodeType === 3); if (tn) { const rg = document.createRange(); rg.selectNodeContents(tn); const lines = new Set([...rg.getClientRects()].map(x => Math.round(x.top))).size; maxLines = Math.max(maxLines, lines); }
      });
      return { keys: keys.length, bad: bad.slice(0, 12), nbad: bad.length, maxFreqLines: maxLines, overflow: document.documentElement.scrollWidth - innerWidth };
    });
      report[`${w}x${zoom} ${scheme} ${open ? 'open' : 'closed'}`] = await measure(); }
    await ctx.close();
  }
  await b.close(); let bad = 0;
  for (const [k, v] of Object.entries(report)) { if (v.keys !== 52 || v.nbad || v.maxFreqLines > 1 || v.overflow > 0) { bad++; console.error('FAIL ' + k + ' ' + JSON.stringify(v)); } }
  if (bad) process.exit(1);
  console.log('ok (52 keys: no part overlaps another, the record reads on one line, no sideways scroll; ' + Object.keys(report).length + ' widths, zooms, themes and states)');
})();
