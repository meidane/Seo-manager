// پنلِ کوچکِ محلی (همان «نرم‌افزارِ ویندوزی»): http://127.0.0.1:47800 در مرورگر.
// وضعیتِ نصب، سایت‌های اکسل + «تستِ اتصال»، باز کردنِ اکسل/پوشه‌ها، تستِ گوگل، مرورگرِ ابزار (حلِ کپچا/لاگین).
import { createServer } from 'node:http';
import { readFileSync, existsSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { install, installedVersion, marketplaceOk, DEST, VERSION } from './install.mjs';
import { config, getSite, EXCEL, HOME, DIRS, ensureHome } from '../server/config.mjs';
import { wpCheck } from '../server/wp.mjs';
import { googleSuggest, browserContext } from '../server/research.mjs';
import { unzipAll } from '../server/files.mjs';

const PORT = +(process.env.CWP_PANEL_PORT || 47800);
const HERE = dirname(fileURLToPath(import.meta.url));
const URL_ = `http://127.0.0.1:${PORT}/`;

function openPath(p) {
  // explorer هم پوشه، هم فایل (با برنامهٔ پیش‌فرض، مثلاً اکسل) و هم آدرسِ وب را باز می‌کند
  if (process.platform === 'win32') spawn('explorer.exe', [p], { detached: true, stdio: 'ignore' }).on('error', () => {}).unref();
  else spawn(process.platform === 'darwin' ? 'open' : 'xdg-open', [p], { detached: true, stdio: 'ignore' }).on('error', () => {}).unref();
}

function status() {
  ensureHome();
  let cfg, error;
  try { cfg = config(); error = cfg.error; } catch (e) { error = e.message; cfg = { sites: [], prompts: [], files: [] }; }
  return {
    version: VERSION, node: process.versions.node,
    plugin: { installed: installedVersion(), path: DEST, marketplace: marketplaceOk() },
    excel: EXCEL, excel_exists: existsSync(EXCEL), home: HOME, error,
    sites: cfg.sites.map(s => ({ key: s.key, url: s.url, user: s.user, has_password: !!s.password, seo: s.seo })),
    prompts: (cfg.prompts || []).map(p => ({ site: p.site, kind: p.kind, title: p.title })),
  };
}

async function rawBody(req) {
  const chunks = []; for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks);
}
async function body(req) {
  const raw = await rawBody(req);
  if (req.headers['content-type'] === 'application/zip') return raw;
  try { return JSON.parse(raw.toString() || '{}'); } catch { return {}; }
}

/** به‌روزرسانی با zipِ جدید (بدونِ Extractِ دستی): باز کردن در temp → همان install. */
function updateFromZip(buf) {
  if (!buf?.length) throw new Error('فایلی نرسید');
  const entries = unzipAll(buf);
  const pj = entries.find(e => /(^|\/)plugin\/plugin\.json$/.test(e.name));
  if (!pj) throw new Error('این zipِ برنامهٔ ChatGPT-WP نیست (plugin/plugin.json ندارد).');
  const prefix = pj.name.slice(0, -'plugin.json'.length);
  const dir = join(tmpdir(), 'cwp-update-' + Date.now());
  for (const e of entries) {
    if (!e.name.startsWith(prefix) || e.name.includes('..')) continue;
    const out = join(dir, e.name.slice(prefix.length));
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, e.data);
  }
  try { return install({ log: () => {}, src: dir }); }
  finally { try { rmSync(dir, { recursive: true, force: true }); } catch { /* مهم نیست */ } }
}

let toolPage = null;
const routes = {
  'GET /api/status': () => status(),
  'POST /api/install': () => install({ log: () => {} }),
  'POST /api/update': b => {
    const r = updateFromZip(b);
    setTimeout(() => restart(), 400); // پنل با کدِ جدید دوباره بالا بیاید
    return { ...r, restarting: true };
  },
  'POST /api/test': async b => wpCheck(getSite(b.site)),
  'POST /api/google': async () => {
    const r = await googleSuggest({ query: 'استیل', expand: 'basic' });
    return { ok: r.count > 0, count: r.count, sample: r.suggestions.slice(0, 5) };
  },
  'POST /api/browser': async () => {
    const ctx = await browserContext({ headed: true });
    if (toolPage && !toolPage.isClosed()) { await toolPage.bringToFront(); return { ok: true }; }
    toolPage = await ctx.newPage();
    await toolPage.goto('https://www.google.com/search?q=' + encodeURIComponent('استیل'), { waitUntil: 'domcontentloaded' }).catch(() => {});
    return { ok: true };
  },
  'POST /api/open': async b => {
    const map = { excel: EXCEL, home: HOME, images: DIRS.images, files: DIRS.files, backups: DIRS.backups };
    let p = map[b.what];
    if (b.what === 'site-files' && b.site) { p = join(DIRS.files, b.site); mkdirSync(p, { recursive: true }); }
    if (!p) throw new Error('مسیرِ نامعتبر');
    openPath(p);
    return { ok: true, path: p };
  },
};

function restart() {
  server.close(); server.closeAllConnections?.();
  spawn(process.execPath, [join(DEST, 'app', 'panel.mjs')], { detached: true, stdio: 'ignore', env: { ...process.env, CWP_NO_OPEN: '1', CWP_RESTART: '1' } }).unref();
  setTimeout(() => process.exit(0), 300);
}

const server = createServer(async (req, res) => {
  const key = `${req.method} ${req.url.split('?')[0]}`;
  if (key === 'GET /' || key === 'GET /index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    return res.end(readFileSync(join(HERE, 'panel.html')));
  }
  const fn = routes[key];
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (!fn) { res.writeHead(404); return res.end('{}'); }
  // فقط خودِ پنل (همین مبدأ) بتواند اکشن بزند
  if (req.method === 'POST' && req.headers.origin && req.headers.origin !== URL_.slice(0, -1)) { res.writeHead(403); return res.end('{}'); }
  try { res.end(JSON.stringify(await fn(await body(req)))); }
  catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: String(e.message).split('\n')[0] })); }
});

let retries = 0;
server.on('error', e => {
  if (e.code === 'EADDRINUSE' && process.env.CWP_RESTART && retries++ < 30) { setTimeout(() => server.listen(PORT, '127.0.0.1'), 300); return; }
  if (e.code === 'EADDRINUSE') { console.log('پنل از قبل باز است؛ در مرورگر باز می‌شود.'); openPath(URL_); setTimeout(() => process.exit(0), 500); }
  else { console.error(e); process.exit(1); }
});
server.listen(PORT, '127.0.0.1', () => {
  console.log(`ChatGPT-WP panel: ${URL_}`);
  console.log('تا وقتی با پنل کار داری این پنجره را نبند.');
  if (!process.env.CWP_NO_OPEN) openPath(URL_);
});
