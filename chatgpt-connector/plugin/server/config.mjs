// تنظیماتِ برنامه: %USERPROFILE%\ChatGPT-WP\config.json — فقط از طریقِ پنل ویرایش می‌شود (منبعِ واحد).
// هر سایت: اتصال + پرامپت‌های خودش (عمومی/اختصاصی با مراحل) + فایل‌ها (پوشه‌بندیِ خودکار) + رقبا.
// با تغییرِ فایل (mtime) دوباره خوانده می‌شود — نیازی به ری‌استارتِ ChatGPT نیست.
import { readFileSync, writeFileSync, renameSync, statSync, existsSync, mkdirSync, readdirSync, copyFileSync } from 'node:fs';
import { join, isAbsolute, extname, basename, relative, sep } from 'node:path';
import { homedir } from 'node:os';
import { norm, hostOf } from './text.mjs';
import { DEFAULT_PROMPTS, DEFAULT_COMPETITORS, DEFAULT_SETTINGS, STEP_KEYS } from './defaults.mjs';

export const HOME = process.env.CWP_HOME || join(homedir(), 'ChatGPT-WP');
export const CONFIG = join(HOME, 'config.json');
/** تنظیماتِ فقط همین کامپیوتر (آدرس/توکنِ همگام‌سازی + وضعیت) — همگام نمی‌شود. */
export const LOCAL = join(HOME, 'local.json');
export const DIRS = {
  images: join(HOME, 'images'),
  files: join(HOME, 'files'),
  backups: join(HOME, 'backups'),
  profile: join(HOME, '.browser-profile'),
};

export const newId = () => Math.random().toString(36).slice(2, 10);
const key = s => norm(s).replace(/\s+/g, '');
/** نامِ امن برای پوشه (فارسی مجاز؛ نویسه‌های ممنوعِ ویندوز حذف). */
export const safeName = s => String(s || '').replace(/[<>:"/\\|?*\x00-\x1f]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/[. ]+$/, '') || 'بی‌نام';

export function ensureHome() {
  for (const d of [HOME, DIRS.images, DIRS.files, DIRS.backups]) if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

export function normUrl(u) {
  u = String(u || '').trim();
  if (!u) return '';
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  return u.replace(/\/+$/, '');
}

// ───────────── خواندن/نوشتن ─────────────
let cache = null;

function normalizeSite(s) {
  const prompts = (s.prompts || []).map(p => ({
    id: p.id || newId(), kind: p.kind === 'general' ? 'general' : 'specific', title: String(p.title || '').trim(),
    use: String(p.use || '').trim(), body: String(p.body || ''),
    steps: p.kind === 'general' ? undefined
      : Object.fromEntries([...STEP_KEYS.map(k => [k, !!p.steps?.[k]]), ['competitors_n', +p.steps?.competitors_n || 5]]),
  }));
  return {
    id: s.id || newId(), key: safeName(s.key || hostOf(normUrl(s.url)) || 'site'), url: normUrl(s.url), user: String(s.user || '').trim(),
    password: String(s.password || '').trim().replace(/\s+/g, ' '), seo: s.seo || 'rankmath', notes: s.notes || '', active: s.active !== false,
    prompts,
    files: (s.files || []).filter(f => f && f.path).map(f => ({ path: f.path, prompt: f.prompt || '', role: f.role || '', description: f.description || '' })),
    competitors: (s.competitors || []).map(c => ({ domain: hostOf(normUrl(c.domain)) || String(c.domain || '').trim(),
      kind: c.kind === 'ignore' ? 'ignore' : 'competitor', notes: c.notes || '' })).filter(c => c.domain),
    updated_at: +s.updated_at || 0,
  };
}

function normalize(data) {
  const settings = { ...DEFAULT_SETTINGS, ...(data.settings || {}) };
  settings.maxChars = parseInt(settings.maxChars, 10) || 20000;
  settings.browser = /edge/i.test(settings.browser) ? 'msedge' : 'chrome';
  settings.headed = !!settings.headed; settings.insecure = !!settings.insecure;
  const cutoff = Date.now() - 90 * 864e5; // نشانهٔ حذفِ قدیمی‌تر از ۹۰ روز لازم نیست
  return { version: 2, settings, settings_updated_at: +data.settings_updated_at || 0, sites: (data.sites || []).map(normalizeSite),
    deleted: (data.deleted || []).filter(t => t && t.id && t.at > cutoff) };
}

function load() {
  ensureHome();
  if (!existsSync(CONFIG)) writeConfig(normalize({}));
  const mtime = statSync(CONFIG).mtimeMs;
  if (cache && cache.mtime === mtime) return cache;
  let raw;
  try { raw = JSON.parse(readFileSync(CONFIG, 'utf8').replace(/^﻿/, '')); }
  catch (e) {
    if (cache) return cache;
    // فایلِ خراب (مثلاً قطعِ برق وسطِ ذخیره) → نسخهٔ پشتیبانِ قبلی
    try { raw = JSON.parse(readFileSync(CONFIG + '.bak', 'utf8')); } catch { throw new Error(`config.json خراب است: ${e.message}`); }
  }
  const data = normalize(raw);
  if (data.settings.insecure) process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
  if (!data.settings.browserPath && process.env.CWP_BROWSER_PATH) data.settings.browserPath = process.env.CWP_BROWSER_PATH;
  for (const s of data.sites) { const d = siteDir(s); if (!existsSync(d)) mkdirSync(d, { recursive: true }); }
  cache = { ...data, all: data.sites, sites: data.sites.filter(s => s.active), mtime };
  return cache;
}

function writeConfig(data, { silent = false } = {}) {
  ensureHome();
  const tmp = CONFIG + '.tmp';
  writeFileSync(tmp, JSON.stringify(data, null, 1), 'utf8');
  if (existsSync(CONFIG)) { try { copyFileSync(CONFIG, CONFIG + '.bak'); } catch { /* مهم نیست */ } }
  renameSync(tmp, CONFIG);
  cache = null;
  if (!silent) for (const fn of listeners) { try { fn(); } catch { /* شنونده نباید ذخیره را خراب کند */ } }
}

const listeners = new Set();
/** خبر از هر ذخیره (برای همگام‌سازیِ خودکار بعد از تغییر). */
export const onConfigChange = fn => listeners.add(fn);

const strip = s => { const { updated_at, ...rest } = s; void updated_at; return JSON.stringify(rest); };
/** زمانِ تغییرِ هر سایت/تنظیمات + نشانهٔ حذف — پایهٔ ادغام در همگام‌سازی (sync.mjs). */
function stamp(before, after) {
  const now = Date.now();
  const old = new Map(before.sites.map(s => [s.id, s]));
  for (const s of after.sites) {
    const o = old.get(s.id);
    if (!o || strip(normalizeSite(o)) !== strip(normalizeSite(s))) s.updated_at = now;
  }
  const ids = new Set(after.sites.map(s => s.id));
  after.deleted = [...(after.deleted || []), ...before.sites.filter(s => !ids.has(s.id)).map(s => ({ id: s.id, at: now }))];
  if (JSON.stringify(before.settings) !== JSON.stringify(after.settings)) after.settings_updated_at = now;
}

/** داده‌ی خام برای پنل (همه‌ی سایت‌ها، حتی غیرفعال). */
export function rawConfig() {
  const c = load();
  return { version: 2, settings: c.settings, settings_updated_at: c.settings_updated_at, sites: c.all, deleted: c.deleted };
}
/** تغییر و ذخیره (از پنل): fn روی کپیِ داده اجرا می‌شود؛ زمانِ تغییر خودکار ثبت می‌شود. */
export function updateConfig(fn) {
  const before = rawConfig();
  const data = structuredClone(before);
  const out = fn(data);
  stamp(before, data);
  writeConfig(normalize(data));
  return out;
}
/** جایگزینیِ کامل (فقط همگام‌سازی، بدونِ ثبتِ زمانِ تغییرِ جدید). */
export function replaceConfig(data) { writeConfig(normalize(data), { silent: true }); }
/** زمانِ آخرین تغییرِ config.json (پنل با آن می‌فهمد همگام‌سازی چیزی آورده). */
export function configMtime() { try { return statSync(CONFIG).mtimeMs; } catch { return 0; } }

// ───────────── تنظیماتِ محلیِ همین کامپیوتر ─────────────
export function readLocal() {
  try { return JSON.parse(readFileSync(LOCAL, 'utf8')); } catch { return {}; }
}
export function writeLocal(patch) {
  ensureHome();
  const next = { ...readLocal(), ...patch };
  const tmp = LOCAL + '.tmp';
  writeFileSync(tmp, JSON.stringify(next, null, 1), 'utf8');
  renameSync(tmp, LOCAL);
  return next;
}
export function config() { return load(); }

export function newSite(fields = {}) {
  return normalizeSite({
    ...fields,
    prompts: fields.prompts || DEFAULT_PROMPTS.map(p => ({ ...structuredClone(p), id: newId() })),
    competitors: fields.competitors || structuredClone(DEFAULT_COMPETITORS),
  });
}

export function getSite(name) {
  const cfg = load();
  if (!name) {
    if (cfg.sites.length === 1) return cfg.sites[0];
    throw new Error(`سایت را مشخص کن (site). موجود: ${cfg.sites.map(s => s.key).join('، ') || '— (در پنلِ ChatGPT-WP سایت اضافه کن)'}`);
  }
  const k = key(name), h = hostOf(normUrl(name));
  const s = cfg.sites.find(s => key(s.key) === k || s.id === name) || cfg.sites.find(s => hostOf(s.url) === h)
    || cfg.sites.find(s => key(s.key).includes(k) || k.includes(key(s.key)));
  if (!s) throw new Error(`سایتِ «${name}» تعریف نشده. موجود: ${cfg.sites.map(s => s.key).join('، ') || '—'} (پنلِ ChatGPT-WP)`);
  return s;
}

// ───────────── فایل‌ها (پوشه‌بندیِ خودکار) ─────────────
// files\<سایت>\*                → برای همهٔ کارهای سایت
// files\<سایت>\<عنوان پرامپت>\*  → فقط همان پرامپت
export const ROLES = { default_featured: 'تصویر شاخص پیش‌فرض', featured: 'تصویر شاخص', inline: 'داخل متن', logo: 'لوگو', reference: 'مرجع', other: 'سایر' };
export const IMG_EXT = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif']);
export function roleOf(text, file = '') {
  if (text && ROLES[text]) return text;
  const t = key(text || basename(file, extname(file)));
  if (/پیشفرض|پیش‌فرض|default/.test(t)) return 'default_featured';
  if (/شاخص|featured|cover|کاور/.test(t)) return 'featured';
  if (/لوگو|logo|واترمارک|watermark/.test(t)) return 'logo';
  if (/مرجع|نمونه|reference|sample|راهنما|guide/.test(t)) return 'reference';
  if (/داخلمتن|داخل|inline|body/.test(t)) return 'inline';
  if (text) return 'other';
  return IMG_EXT.has(extname(file).toLowerCase()) ? 'inline' : 'reference';
}

export const siteDir = site => join(DIRS.files, safeName(site.key));
export const promptDir = (site, prompt) => (prompt ? join(siteDir(site), safeName(prompt.title)) : siteDir(site));
export const absPath = p => (isAbsolute(p) || /^[a-z]:[\\/]/i.test(p) ? p : join(HOME, p));
export const relPath = p => { const r = relative(HOME, p); return r.startsWith('..') || isAbsolute(r) ? p : r.split(sep).join('/'); };

const listFiles = dir => readdirSync(dir, { withFileTypes: true }).filter(e => e.isFile() && !e.name.startsWith('.') && !e.name.startsWith('~$')).map(e => e.name);
/** b.txt کنارِ b.jpg «توضیح» است، نه فایلِ جدا. */
const isSidecar = (names, n) => n.endsWith('.txt') && names.some(o => o !== n && basename(o, extname(o)) === basename(n, '.txt'));

/** همهٔ فایل‌های سایت: پوشه + متادیتای ذخیره‌شده (نقش/توضیح/پرامپت). */
export function siteFiles(site, promptId = null, { all = false } = {}) {
  const meta = new Map(site.files.map(f => [absPath(f.path), f]));
  const out = [], seen = new Set();
  const push = (p, folderPrompt) => {
    const m = meta.get(p);
    let description = m?.description || '';
    if (!description && !p.endsWith('.txt')) {
      const txt = p.slice(0, -extname(p).length) + '.txt';
      if (existsSync(txt)) description = readFileSync(txt, 'utf8').replace(/^﻿/, '').trim().slice(0, 500);
    }
    seen.add(p);
    out.push({ path: p, rel: relPath(p), name: basename(p), prompt: m ? m.prompt : folderPrompt,
      role: m?.role || roleOf('', basename(p)), description, missing: existsSync(p) ? undefined : true });
  };
  const root = siteDir(site);
  if (existsSync(root)) {
    const rootNames = listFiles(root);
    for (const n of rootNames) if (!isSidecar(rootNames, n)) push(join(root, n), '');
    for (const d of readdirSync(root, { withFileTypes: true }).filter(e => e.isDirectory() && !e.name.startsWith('.'))) {
      const pr = site.prompts.find(x => safeName(x.title) === d.name);
      const dir = join(root, d.name), names = listFiles(dir);
      for (const n of names) if (!isSidecar(names, n)) push(join(dir, n), pr ? pr.id : '');
    }
  }
  for (const [p] of meta) if (!seen.has(p)) push(p, '');
  return all ? out : out.filter(f => !f.prompt || f.prompt === promptId);
}

export function findPrompt(site, title) {
  const k = key(title);
  const sp = site.prompts.filter(p => p.kind === 'specific');
  return sp.find(p => key(p.title) === k || p.id === title) || sp.find(p => key(p.title).includes(k) || (p.use && key(p.use).includes(k)));
}

export function defaultFeatured(site, promptTitle) {
  const pid = promptTitle ? findPrompt(site, promptTitle)?.id : null;
  const list = siteFiles(site, pid).filter(f => f.role === 'default_featured' && !f.missing);
  return (pid && list.find(f => f.prompt === pid)) || list.find(f => !f.prompt) || null;
}

/** پیدا کردنِ فایلِ محلی از روی نام یا مسیر: مسیرِ کامل → پوشهٔ ChatGPT-WP → images → فایل‌های سایت. */
export function findLocal(name, site) {
  let p = String(name || '').trim().replace(/^"|"$/g, '');
  if (/^file:\/\//i.test(p)) p = decodeURIComponent(p.replace(/^file:\/\/\/?/i, ''));
  if (isAbsolute(p) || /^[a-z]:[\\/]/i.test(p)) return p;
  const cands = [join(HOME, p), join(DIRS.images, p)];
  if (site) cands.push(join(DIRS.images, safeName(site.key), p), join(siteDir(site), p));
  for (const c of cands) if (existsSync(c)) return c;
  if (site) { const f = siteFiles(site, null, { all: true }).find(f => f.name === basename(p) && !f.missing); if (f) return f.path; }
  return cands[0];
}
export const resolvePath = p => findLocal(p, null);

// ───────────── بریف برای ChatGPT ─────────────
const STEP_LABEL = { competitors: 'بررسیِ رقبا (competitor_research / page_outline)', serp: 'نتایجِ گوگل + سؤالاتِ مرتبط (serp)',
  suggest: 'گوگل ساجست (google_suggest)', internal_links: 'لینکِ داخلی (wp_internal_links)', images: 'عکس (فایل‌های سایت / پوشهٔ images / wp_upload_media)' };

export function siteBrief(site, promptTitle) {
  const fileRow = f => ({ path: f.path, missing: f.missing, role: ROLES[f.role] || f.role, description: f.description || undefined,
    for_prompt: f.prompt ? site.prompts.find(p => p.id === f.prompt)?.title : undefined });
  const brief = {
    site: site.key, url: site.url, seo_plugin: site.seo, has_credentials: !!(site.user && site.password),
    general_prompts: site.prompts.filter(p => p.kind === 'general' && p.body.trim()).map(p => p.body), notes: site.notes || undefined,
    competitors: site.competitors.filter(c => c.kind === 'competitor').map(c => c.domain),
    ignore_domains: site.competitors.filter(c => c.kind === 'ignore').map(c => c.domain),
    images_folder: DIRS.images,
  };
  if (promptTitle) {
    const p = findPrompt(site, promptTitle);
    if (!p) throw new Error(`پرامپتِ اختصاصیِ «${promptTitle}» برای ${site.key} نیست. موجود: ${site.prompts.filter(x => x.kind === 'specific').map(x => x.title).join('، ') || '—'}`);
    brief.prompt = { title: p.title, use: p.use, body: p.body };
    brief.steps = {
      do: STEP_KEYS.filter(k => p.steps[k]).map(k => STEP_LABEL[k]),
      competitors_n: p.steps.competitors ? p.steps.competitors_n : undefined,
      rule: 'فقط همین مراحل (و هرچه صریحاً در متنِ پرامپت یا پیامِ کاربر خواسته شده) را انجام بده؛ بقیهٔ بررسی‌ها لازم نیست.',
    };
    brief.files = siteFiles(site, p.id).map(fileRow);
  } else {
    brief.prompts = site.prompts.filter(p => p.kind === 'specific').map(p => ({ title: p.title, use: p.use, steps: STEP_KEYS.filter(k => p.steps[k]) }));
    brief.files = siteFiles(site).map(fileRow);
    brief.hint = 'پرامپتِ اختصاصیِ مناسبِ کار را با همین ابزار و پارامترِ prompt بگیر (متن + مراحلِ لازم + فایل‌هایش).';
  }
  const df = defaultFeatured(site, promptTitle);
  if (df) brief.default_featured_image = df.path;
  return brief;
}
