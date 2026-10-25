// همگام‌سازی با پنلِ SEO Manager (اپِ `connector`ِ جنگو) — دستی، موقعِ باز شدن، هر چند دقیقه، و بعد از هر تغییر.
// اصل: هرگز برنامه را مختل نکند؛ خطا فقط در وضعیت/لاگ ثبت می‌شود و برنامه با دادهٔ محلی ادامه می‌دهد.
// داده: ادغامِ سه‌طرفه‌ی ساده — هر سایت با `updated_at`ِ جدیدتر برنده؛ حذف با نشانهٔ `deleted`؛
// تنظیماتِ مشترک با `settings_updated_at`. فایل‌ها (`files/`): مقایسهٔ sha1 با آخرین وضعیتِ همگام‌شده.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, statSync, unlinkSync, renameSync } from 'node:fs';
import { join, dirname, relative, sep } from 'node:path';
import { hostname } from 'node:os';
import { HOME, DIRS, rawConfig, replaceConfig, readLocal, writeLocal } from './config.mjs';
import { log } from './log.mjs';

const SHARED_SETTINGS = ['hl', 'gl', 'maxChars', 'insecure']; // بقیه (مسیرِ مرورگر/پراکسی/نمایش) مالِ همین کامپیوتر است
const MAX_FILE = 20 * 1024 * 1024;
const LOCK = join(HOME, '.sync.lock');

export function syncSettings() {
  const l = readLocal().sync || {};
  return { url: (l.url || '').trim().replace(/\/+$/, ''), token: (l.token || '').trim(), interval: Math.max(1, +l.interval || 5), enabled: l.enabled !== false };
}
export function saveSyncSettings(patch) {
  const cur = readLocal().sync || {};
  writeLocal({ sync: { ...cur, ...patch } });
  return syncSettings();
}
export function syncStatus() { return readLocal().sync_status || null; }
const setStatus = st => writeLocal({ sync_status: { ...st, at: Date.now() } });

// ───────── HTTP ─────────
async function api(cfg, path, { method = 'GET', json, form, raw, timeout = 20000 } = {}) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeout);
  try {
    const headers = { Authorization: `Token ${cfg.token}`, Accept: 'application/json' };
    let body;
    if (json) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
    if (form) body = form;
    const r = await fetch(`${cfg.url}/connector/api/${path}`, { method, headers, body, signal: ctl.signal, redirect: 'manual' });
    if (raw && r.ok) return Buffer.from(await r.arrayBuffer());
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { throw new Error(r.status === 404 || r.status >= 300 && r.status < 400 ? 'آدرسِ پنل اشتباه است یا همگام‌سازی روی پنل نصب نیست' : `پاسخِ نامعتبر از پنل (${r.status})`); }
    if (r.status === 401) throw new Error('توکن نامعتبر است (از تنظیمات ← توکن‌های API در پنل یک توکنِ تازه بساز)');
    if (!r.ok && r.status !== 409) throw new Error(data.detail || `خطای پنل (${r.status})`);
    return { status: r.status, ...data };
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('پنل جواب نداد (timeout)');
    if (e.message === 'fetch failed' || e.cause) {
      const code = e.cause?.code || e.cause?.errors?.[0]?.code || 'شبکه';
      throw new Error(`پنل در دسترس نیست (${code}) — اینترنت/آدرس را چک کن؛ برنامه با دادهٔ همین کامپیوتر ادامه می‌دهد`);
    }
    throw e;
  } finally { clearTimeout(t); }
}

// ───────── ادغامِ داده ─────────
function stable(v) {
  if (Array.isArray(v)) return `[${v.map(stable).join(',')}]`;
  if (v && typeof v === 'object') return `{${Object.keys(v).sort().filter(k => v[k] !== undefined).map(k => `${JSON.stringify(k)}:${stable(v[k])}`).join(',')}}`;
  return JSON.stringify(v ?? null);
}
const shared = d => ({
  settings: Object.fromEntries(SHARED_SETTINGS.map(k => [k, d.settings?.[k]])),
  settings_updated_at: d.settings_updated_at || 0, sites: d.sites || [], deleted: d.deleted || [],
});

export function merge(L, R) {
  const tomb = new Map();
  for (const t of [...(L.deleted || []), ...(R.deleted || [])]) if (t?.id) tomb.set(t.id, Math.max(tomb.get(t.id) || 0, t.at || 0));
  const byId = new Map((L.sites || []).map(s => [s.id, s]));
  const order = (L.sites || []).map(s => s.id);
  for (const s of R.sites || []) {
    const l = byId.get(s.id);
    if (!l) order.push(s.id);
    if (!l || (s.updated_at || 0) > (l.updated_at || 0)) byId.set(s.id, s);
  }
  const sites = order.map(id => byId.get(id)).filter(s => !(tomb.get(s.id) >= (s.updated_at || 0)));
  const remoteSettingsNewer = (R.settings_updated_at || 0) > (L.settings_updated_at || 0);
  return {
    settings: remoteSettingsNewer ? { ...L.settings, ...Object.fromEntries(SHARED_SETTINGS.filter(k => R.settings?.[k] !== undefined).map(k => [k, R.settings[k]])) } : L.settings,
    settings_updated_at: Math.max(L.settings_updated_at || 0, R.settings_updated_at || 0),
    sites, deleted: [...tomb].map(([id, at]) => ({ id, at })),
  };
}

// ───────── فایل‌ها ─────────
function localFiles(cache) {
  const out = {};
  const walk = d => {
    if (!existsSync(d)) return;
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (e.name.startsWith('.') || e.name.startsWith('~$') || e.name.endsWith('.tmp')) continue;
      const p = join(d, e.name);
      if (e.isDirectory()) { walk(p); continue; }
      const st = statSync(p);
      if (st.size > MAX_FILE) continue;
      const rel = relative(HOME, p).split(sep).join('/');
      const c = cache[rel];
      const sha1 = c && c.size === st.size && c.mtime === st.mtimeMs ? c.sha1 : createHash('sha1').update(readFileSync(p)).digest('hex');
      out[rel] = { sha1, size: st.size, mtime: st.mtimeMs };
    }
  };
  walk(DIRS.files);
  return out;
}

async function syncFiles(cfg, remoteList, stats) {
  const local = readLocal();
  const base = local.base_files || {};
  const lf = localFiles(local.file_cache || {});
  const rf = Object.fromEntries((remoteList || []).filter(f => f.path.startsWith('files/')).map(f => [f.path, f]));
  const next = {};
  const abs = rel => join(HOME, ...rel.split('/'));
  const upload = async rel => {
    const form = new FormData();
    form.append('path', rel);
    form.append('file', new Blob([readFileSync(abs(rel))]), rel.split('/').pop());
    await api(cfg, 'file/', { method: 'POST', form, timeout: 120000 });
    stats.up++;
  };
  const download = async rel => {
    const buf = await api(cfg, `file/?path=${encodeURIComponent(rel)}`, { raw: true, timeout: 120000 });
    const p = abs(rel);
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p + '.tmp', buf); renameSync(p + '.tmp', p);
    stats.down++;
  };
  for (const rel of new Set([...Object.keys(lf), ...Object.keys(rf)])) {
    const l = lf[rel]?.sha1, r = rf[rel]?.sha1, b = base[rel];
    try {
      if (l === r) { if (l) next[rel] = l; continue; }
      if (l && !r) {
        if (b && b === l) { unlinkSync(abs(rel)); stats.del++; } // روی پنل حذف شده بود
        else { await upload(rel); next[rel] = l; }
      } else if (!l && r) {
        if (b && b === r) { await api(cfg, 'file/delete/', { method: 'POST', json: { path: rel } }); stats.del++; } // اینجا حذف شده بود
        else { await download(rel); next[rel] = r; }
      } else if (b === r || (b !== l && lf[rel].mtime > (rf[rel].updated_at || 0))) { await upload(rel); next[rel] = l; }
      else { await download(rel); next[rel] = r; }
    } catch (e) {
      stats.errors.push(`${rel}: ${e.message}`);
      if (b) next[rel] = b;
    }
  }
  const cache = {};
  for (const [rel, f] of Object.entries(localFiles(local.file_cache || {}))) cache[rel] = { sha1: f.sha1, size: f.size, mtime: f.mtime };
  writeLocal({ base_files: next, file_cache: cache });
}

// ───────── اجرا ─────────
let running = null;

/** همگام‌سازی؛ هرگز throw نمی‌کند — نتیجه را برمی‌گرداند و در وضعیت ثبت می‌کند. */
export function syncNow(reason = 'manual') {
  if (running) return running;
  running = (async () => {
    const cfg = syncSettings();
    if (!cfg.url || !cfg.token) return { ok: false, skipped: true, message: 'همگام‌سازی تنظیم نشده' };
    if (!cfg.enabled && reason !== 'manual') return { ok: false, skipped: true, message: 'همگام‌سازی خاموش است' };
    // قفل بینِ پنل و سرورِ MCP (هر دو ممکن است هم‌زمان باز باشند)
    try {
      if (existsSync(LOCK) && Date.now() - statSync(LOCK).mtimeMs < 3 * 60e3) return { ok: true, skipped: true, message: 'همگام‌سازیِ دیگری در جریان است' };
      writeFileSync(LOCK, String(process.pid));
    } catch { /* اگر قفل نشد هم ادامه */ }
    const stats = { up: 0, down: 0, del: 0, errors: [] };
    const t0 = Date.now();
    try {
      let pushed = false, pulled = false, version = 0, remote;
      for (let attempt = 0; attempt < 3; attempt++) {
        remote = await api(cfg, 'state/');
        const local = rawConfig();
        const merged = merge(local, remote.data || {});
        if (stable(shared(merged)) !== stable(shared(local))) { replaceConfig({ ...local, ...merged }); pulled = true; }
        version = remote.version;
        if (remote.version > 0 && stable(shared(merged)) === stable(shared(remote.data || {}))) break;
        const r = await api(cfg, 'state/', { method: 'POST', json: { base_version: remote.version, data: shared(merged), client: hostname() } });
        if (r.status === 409) continue; // کسِ دیگری زودتر نوشت → دوباره بخوان و ادغام کن
        version = r.version; pushed = true;
        break;
      }
      await syncFiles(cfg, remote.files, stats);
      const parts = [pulled && 'دریافت', pushed && 'ارسال', stats.up && `${stats.up} فایل ↑`, stats.down && `${stats.down} فایل ↓`, stats.del && `${stats.del} حذف`].filter(Boolean);
      const res = { ok: !stats.errors.length, version, reason, message: parts.length ? parts.join('، ') : 'به‌روز است',
        errors: stats.errors.slice(0, 5), ms: Date.now() - t0 };
      writeLocal({ base_version: version });
      setStatus(res);
      log(res.ok ? 'info' : 'warn', `sync(${reason}) v${version}: ${res.message}${stats.errors.length ? ' | ' + stats.errors.join(' | ') : ''}`);
      return res;
    } catch (e) {
      const res = { ok: false, reason, message: e.message };
      setStatus(res);
      log('warn', `sync(${reason}) failed: ${e.message}`);
      return res;
    } finally {
      try { unlinkSync(LOCK); } catch { /* نبود */ }
    }
  })().finally(() => { running = null; });
  return running;
}

/** همگام‌سازیِ خودکار: یک بار حالا (با تأخیر) + هر N دقیقه. هر دقیقه تنظیمات دوباره خوانده می‌شود. */
export function startAutoSync({ delay = 2000 } = {}) {
  let last = 0;
  const tick = () => {
    const cfg = syncSettings();
    if (!cfg.url || !cfg.token || !cfg.enabled) return;
    if (Date.now() - last < cfg.interval * 60e3) return;
    last = Date.now();
    syncNow('auto');
  };
  setTimeout(() => { last = Date.now(); syncNow('start'); }, delay).unref?.();
  setInterval(tick, 60e3).unref?.();
}

let debounce = null;
/** بعد از تغییرِ محلی، چند ثانیه صبر و بعد ارسال. */
export function syncSoon(ms = 8000) {
  clearTimeout(debounce);
  debounce = setTimeout(() => syncNow('change'), ms);
  debounce.unref?.();
}
