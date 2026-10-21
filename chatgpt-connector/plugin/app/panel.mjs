// پنلِ محلیِ ChatGPT-WP (همان «نرم‌افزار»): http://127.0.0.1:47800
// همهٔ مدیریت از اینجاست: سایت‌ها (اتصال)، پرامپت‌های هر سایت، آپلود/پوشه‌بندیِ فایل‌ها، رقبا، تنظیمات،
// تستِ اتصال/گوگل، مرورگرِ ابزار، به‌روزرسانی با zip. داده: ChatGPT-WP\config.json (server/config.mjs).
import { createServer } from 'node:http';
import { readFileSync, existsSync, mkdirSync, writeFileSync, rmSync, renameSync, unlinkSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, extname, basename, resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { install, installedVersion, marketplaceOk, DEST, VERSION } from './install.mjs';
import {
  rawConfig, updateConfig, newSite, getSite, HOME, DIRS, ensureHome, siteFiles, siteDir, promptDir,
  safeName, relPath, absPath, ROLES, IMG_EXT,
} from '../server/config.mjs';
import { STEP_KEYS, STEP_LABELS, DEFAULT_PROMPTS } from '../server/defaults.mjs';
import { wpCheck } from '../server/wp.mjs';
import { googleSuggest, browserContext } from '../server/research.mjs';
import { unzipAll } from '../server/files.mjs';

const PORT = +(process.env.CWP_PANEL_PORT || 47800);
const HERE = dirname(fileURLToPath(import.meta.url));
const URL_ = `http://127.0.0.1:${PORT}/`;

function openPath(p) {
  // explorer هم پوشه، هم فایل (با برنامهٔ پیش‌فرض) و هم آدرسِ وب را باز می‌کند
  if (process.platform === 'win32') spawn('explorer.exe', [p], { detached: true, stdio: 'ignore' }).on('error', () => {}).unref();
  else spawn(process.platform === 'darwin' ? 'open' : 'xdg-open', [p], { detached: true, stdio: 'ignore' }).on('error', () => {}).unref();
}

function state() {
  ensureHome();
  const cfg = rawConfig();
  return {
    version: VERSION, node: process.versions.node, home: HOME,
    plugin: { installed: installedVersion(), path: DEST, marketplace: marketplaceOk() },
    settings: cfg.settings, roles: ROLES, steps: STEP_KEYS, step_labels: STEP_LABELS,
    sites: cfg.sites.map(s => ({ ...s, files: siteFiles(s, null, { all: true }).map(f => ({ ...f, image: IMG_EXT.has(extname(f.name).toLowerCase()) })) })),
  };
}

const findIdx = (data, id) => {
  const i = data.sites.findIndex(s => s.id === id);
  if (i < 0) throw new Error('سایت پیدا نشد');
  return i;
};
const uniquePath = p => {
  if (!existsSync(p)) return p;
  const ext = extname(p), stem = p.slice(0, -ext.length || undefined);
  for (let n = 2; ; n++) if (!existsSync(`${stem}-${n}${ext}`)) return `${stem}-${n}${ext}`;
};
const moveFile = (from, to) => {
  if (from === to || !existsSync(from)) return from;
  mkdirSync(dirname(to), { recursive: true });
  to = uniquePath(to);
  renameSync(from, to);
  const sf = from.slice(0, -extname(from).length) + '.txt', st = to.slice(0, -extname(to).length) + '.txt';
  if (!from.endsWith('.txt') && existsSync(sf)) try { renameSync(sf, st); } catch { /* مهم نیست */ }
  return to;
};
const swapPrefix = (files, a, b) => files.map(f => ({ ...f, path: f.path.startsWith(relPath(a) + '/') ? relPath(b) + f.path.slice(relPath(a).length) : f.path }));

/** ذخیرهٔ سایت (+ تغییرِ نامِ پوشه‌ها وقتی نامِ سایت یا عنوانِ پرامپت عوض شد). */
function saveSite(input) {
  return updateConfig(data => {
    if (!input.id) {
      const src = input.copy_from ? data.sites.find(s => s.id === input.copy_from) : null;
      const s = newSite({ ...input, prompts: src ? src.prompts.map(p => ({ ...p, id: undefined })) : input.prompts,
        competitors: src ? src.competitors : input.competitors });
      if (data.sites.some(x => x.key === s.key)) throw new Error(`سایتی با نامِ «${s.key}» از قبل هست.`);
      data.sites.push(s);
      return s.id;
    }
    const i = findIdx(data, input.id), old = data.sites[i];
    const next = { ...old, ...input, files: old.files };
    next.key = safeName(next.key);
    if (data.sites.some(x => x.id !== old.id && x.key === next.key)) throw new Error(`سایتی با نامِ «${next.key}» از قبل هست.`);
    if (next.key !== old.key) { // نامِ سایت عوض شد → پوشه هم
      const a = siteDir(old), b = siteDir(next);
      if (existsSync(a) && !existsSync(b)) { renameSync(a, b); next.files = swapPrefix(next.files, a, b); }
      const ai = join(DIRS.images, old.key), bi = join(DIRS.images, next.key);
      if (existsSync(ai) && !existsSync(bi)) renameSync(ai, bi);
    }
    if (input.prompts) { // عنوانِ پرامپت عوض شد → پوشه‌اش هم؛ پرامپتِ حذف‌شده → فایل‌هایش «همهٔ کارها»
      for (const p of input.prompts) {
        const o = old.prompts.find(x => x.id === p.id);
        if (o && safeName(o.title) !== safeName(p.title)) {
          const a = promptDir(next, o), b = promptDir(next, p);
          if (existsSync(a) && !existsSync(b)) { renameSync(a, b); next.files = swapPrefix(next.files, a, b); }
        }
      }
      const ids = new Set(input.prompts.map(p => p.id).filter(Boolean));
      next.files = next.files.map(f => (f.prompt && !ids.has(f.prompt) ? { ...f, prompt: '' } : f));
    }
    data.sites[i] = next;
    return next.id;
  });
}

function upload(q, buf) {
  if (!buf?.length) throw new Error('فایلی نرسید');
  if (buf.length > 50 * 1024 * 1024) throw new Error('حداکثر ۵۰ مگابایت');
  return updateConfig(data => {
    const s = data.sites[findIdx(data, q.get('site'))];
    const pr = s.prompts.find(p => p.id === q.get('prompt')) || null;
    const dir = promptDir(s, pr);
    mkdirSync(dir, { recursive: true });
    const p = uniquePath(join(dir, safeName(basename(q.get('name') || 'file'))));
    writeFileSync(p, buf);
    s.files.push({ path: relPath(p), prompt: pr ? pr.id : '', role: ROLES[q.get('role')] ? q.get('role') : '', description: q.get('description') || '' });
    return relPath(p);
  });
}

/** ویرایشِ فایل: نقش/توضیح/پرامپت (تغییرِ پرامپت = جابه‌جاییِ فایل به پوشهٔ همان پرامپت). */
function saveFile(b) {
  return updateConfig(data => {
    const s = data.sites[findIdx(data, b.site)];
    let p = absPath(b.path);
    let meta = s.files.find(f => absPath(f.path) === p);
    if (!meta) { meta = { path: relPath(p), prompt: '', role: '', description: '' }; s.files.push(meta); }
    if (b.prompt !== undefined && (b.prompt || '') !== (meta.prompt || '') && p.startsWith(siteDir(s))) {
      const pr = s.prompts.find(x => x.id === b.prompt) || null;
      p = moveFile(p, join(promptDir(s, pr), basename(p)));
      meta.path = relPath(p);
    }
    if (b.prompt !== undefined) meta.prompt = b.prompt || '';
    if (b.role !== undefined) meta.role = ROLES[b.role] ? b.role : '';
    if (b.description !== undefined) meta.description = String(b.description);
    return meta.path;
  });
}

function deleteFile(b) {
  return updateConfig(data => {
    const s = data.sites[findIdx(data, b.site)];
    const p = absPath(b.path);
    if (p.startsWith(resolve(HOME)) && existsSync(p)) {
      unlinkSync(p);
      const txt = p.slice(0, -extname(p).length) + '.txt';
      if (!p.endsWith('.txt') && existsSync(txt)) unlinkSync(txt);
    }
    s.files = s.files.filter(f => absPath(f.path) !== p);
    return true;
  });
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
  'GET /api/state': () => state(),
  'POST /api/site/save': b => { const id = saveSite(b.site || {}); return { id, state: state() }; },
  'POST /api/site/delete': b => { updateConfig(d => { d.sites = d.sites.filter(s => s.id !== b.id); }); return state(); },
  'POST /api/site/add-samples': b => {
    updateConfig(d => { d.sites[findIdx(d, b.id)].prompts.push(...DEFAULT_PROMPTS.map(p => structuredClone(p))); });
    return state();
  },
  'POST /api/settings/save': b => { updateConfig(d => { d.settings = { ...d.settings, ...(b.settings || {}) }; }); return state(); },
  'POST /api/upload': (b, q) => { const path = upload(q, b); return { path, state: state() }; },
  'POST /api/file/save': b => { saveFile(b); return state(); },
  'POST /api/file/delete': b => { deleteFile(b); return state(); },
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
    const map = { home: HOME, images: DIRS.images, files: DIRS.files, backups: DIRS.backups };
    let p = map[b.what];
    if (b.what === 'site') { const s = rawConfig().sites.find(x => x.id === b.site); if (s) { p = siteDir(s); mkdirSync(p, { recursive: true }); } }
    if (b.what === 'file' && b.path) p = absPath(b.path);
    if (!p) throw new Error('مسیرِ نامعتبر');
    openPath(p);
    return { ok: true, path: p };
  },
  'POST /api/update': b => {
    const r = updateFromZip(b);
    setTimeout(() => restart(), 400); // پنل با کدِ جدید دوباره بالا بیاید
    return { ...r, restarting: true };
  },
};

async function readBody(req) {
  const chunks = []; for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks);
  if (/octet-stream|zip/.test(req.headers['content-type'] || '')) return raw;
  try { return JSON.parse(raw.toString() || '{}'); } catch { return {}; }
}

const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.avif': 'image/avif' };

function restart() {
  server.close(); server.closeAllConnections?.();
  spawn(process.execPath, [join(DEST, 'app', 'panel.mjs')], { detached: true, stdio: 'ignore', env: { ...process.env, CWP_NO_OPEN: '1', CWP_RESTART: '1' } }).unref();
  setTimeout(() => process.exit(0), 300);
}

const server = createServer(async (req, res) => {
  const u = new URL(req.url, URL_);
  const key = `${req.method} ${u.pathname}`;
  if (key === 'GET /' || key === 'GET /index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    return res.end(readFileSync(join(HERE, 'panel.html')));
  }
  if (key === 'GET /api/thumb') { // پیش‌نمایشِ عکس‌های داخلِ پوشهٔ ChatGPT-WP
    const p = absPath(u.searchParams.get('p') || '');
    if (!p.startsWith(resolve(HOME)) || !MIME[extname(p).toLowerCase()] || !existsSync(p) || statSync(p).size > 15e6) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': MIME[extname(p).toLowerCase()], 'Cache-Control': 'max-age=60' });
    return res.end(readFileSync(p));
  }
  const fn = routes[key];
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (!fn) { res.writeHead(404); return res.end('{}'); }
  // فقط خودِ پنل (همین مبدأ) بتواند اکشن بزند
  if (req.method === 'POST' && req.headers.origin && req.headers.origin !== URL_.slice(0, -1)) { res.writeHead(403); return res.end('{}'); }
  try { res.end(JSON.stringify(await fn(await readBody(req), u.searchParams))); }
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
