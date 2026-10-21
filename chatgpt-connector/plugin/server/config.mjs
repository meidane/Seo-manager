// خواندنِ تنظیمات از اکسلِ کاربر (%USERPROFILE%\ChatGPT-WP\sites.xlsx).
// هر بار که فایل عوض شود (mtime) دوباره خوانده می‌شود — نیازی به ری‌استارتِ ChatGPT نیست.
import { readFileSync, statSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, isAbsolute, resolve, extname, basename } from 'node:path';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';
import { norm, hostOf } from './text.mjs';

const require = createRequire(import.meta.url);
const XLSX = require('xlsx');

export const HOME = process.env.CWP_HOME || join(homedir(), 'ChatGPT-WP');
export const EXCEL = join(HOME, 'sites.xlsx');
export const DIRS = {
  images: join(HOME, 'images'),
  files: join(HOME, 'files'),
  backups: join(HOME, 'backups'),
  profile: join(HOME, '.browser-profile'),
};

export function ensureHome() {
  for (const d of [HOME, DIRS.images, DIRS.files, DIRS.backups]) if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

const key = s => norm(s).replace(/\s+/g, '');
const truthy = v => /^(بله|آره|اره|1|true|yes|y|فعال|✓|x)$/i.test(String(v ?? '').trim());
const falsy = v => /^(خیر|نه|0|false|no|n|غیرفعال)$/i.test(String(v ?? '').trim());

/** مقدارِ ستون با چند نامِ مستعار (تطبیقِ «شامل» روی سرتیترِ نرمال‌شده). */
function pick(row, aliases) {
  const keys = Object.keys(row);
  for (const a of aliases) {
    const ak = key(a);
    const k = keys.find(k => key(k) === ak) || keys.find(k => key(k).includes(ak));
    if (k !== undefined && String(row[k]).trim() !== '') return String(row[k]).trim();
  }
  return '';
}

function sheet(wb, aliases) {
  const name = wb.SheetNames.find(n => aliases.some(a => key(n).includes(key(a))));
  if (!name) return [];
  return XLSX.utils.sheet_to_json(wb.Sheets[name], { defval: '', raw: false });
}

export function normUrl(u) {
  u = String(u || '').trim();
  if (!u) return '';
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  return u.replace(/\/+$/, '');
}

export function resolvePath(p) {
  if (!p) return '';
  p = String(p).trim().replace(/^"|"$/g, '');
  if (/^file:\/\//i.test(p)) p = decodeURIComponent(p.replace(/^file:\/\/\/?/i, ''));
  if (isAbsolute(p) || /^[a-z]:[\\/]/i.test(p)) return p;
  for (const base of [HOME, DIRS.files, DIRS.images]) {
    const full = resolve(base, p);
    if (existsSync(full)) return full;
  }
  return resolve(HOME, p);
}

const SETTING_KEYS = {
  hl: ['زبان گوگل', 'language'],
  gl: ['کشور گوگل', 'country'],
  browser: ['مرورگر', 'browser'],
  headed: ['نمایش مرورگر', 'show browser', 'headed'],
  browserPath: ['مسیر مرورگر', 'browser path'],
  proxy: ['پراکسی', 'proxy'],
  insecure: ['خطای ssl', 'ssl'],
  maxChars: ['حداکثر طول', 'max chars'],
  imagesDir: ['پوشه عکس', 'images folder'],
};

let cache = null;

function load() {
  ensureHome();
  if (!existsSync(EXCEL)) {
    return { sites: [], prompts: [], files: [], competitors: [], settings: defaults(), mtime: 0,
      error: `فایل تنظیمات پیدا نشد: ${EXCEL} — یک بار INSTALL.cmd را اجرا کن.` };
  }
  const mtime = statSync(EXCEL).mtimeMs;
  if (cache && cache.mtime === mtime) return cache;
  let wb;
  try {
    wb = XLSX.read(readFileSync(EXCEL), { type: 'buffer' });
  } catch (e) {
    if (cache) return { ...cache, error: `اکسل الان خوانده نشد (${e.code || e.message}); نسخهٔ قبلی استفاده شد.` };
    throw new Error(`خواندنِ اکسل ناموفق: ${e.message}`);
  }

  const settings = defaults();
  for (const row of sheet(wb, ['تنظیمات', 'settings'])) {
    const vals = Object.values(row).map(v => String(v).trim());
    const label = key(vals[0] || ''), val = vals[1] ?? '';
    if (!label || val === '') continue;
    for (const [k, aliases] of Object.entries(SETTING_KEYS)) {
      if (aliases.some(a => label.includes(key(a)))) settings[k] = val;
    }
  }
  settings.headed = truthy(settings.headed);
  settings.insecure = truthy(settings.insecure);
  settings.maxChars = parseInt(settings.maxChars, 10) || 20000;
  settings.browser = /edge/i.test(settings.browser) ? 'msedge' : /chromium/i.test(settings.browser) ? 'chromium' : 'chrome';
  DIRS.images = settings.imagesDir ? resolvePath(settings.imagesDir) : join(HOME, 'images');
  if (settings.insecure) process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

  const sites = [];
  for (const row of sheet(wb, ['سایت', 'sites'])) {
    const name = pick(row, ['نام کوتاه', 'نام سایت', 'name', 'نام']);
    const url = normUrl(pick(row, ['آدرس سایت', 'آدرس', 'url', 'domain']));
    if (!name && !url) continue;
    if (falsy(pick(row, ['فعال', 'active']))) continue;
    sites.push({
      key: name || hostOf(url),
      url,
      user: pick(row, ['نام کاربری', 'username', 'user']),
      password: pick(row, ['رمز برنامه', 'application password', 'app password', 'رمز']).replace(/\s+/g, ' '),
      seo: (pick(row, ['افزونه سئو', 'seo']) || 'auto').toLowerCase().replace(/\s/g, ''),
      prompt: pick(row, ['پرامپت عمومی', 'general prompt', 'پرامپت']),
      notes: pick(row, ['توضیحات', 'یادداشت', 'notes']),
    });
  }

  for (const s of sites) { // پوشهٔ فایل‌های هر سایت خودکار ساخته شود
    const d = join(DIRS.files, s.key.replace(/[<>:"/\\|?*]+/g, '_'));
    try { if (!existsSync(d)) mkdirSync(d, { recursive: true }); } catch { /* مهم نیست */ }
  }

  const prompts = sheet(wb, ['پرامپت', 'prompts']).map(row => {
    const kind = /عموم|general/i.test(pick(row, ['نوع پرامپت', 'نوع', 'kind'])) ? 'general' : 'specific';
    const flag = aliases => truthy(pick(row, aliases));
    return {
      site: pick(row, ['سایت', 'site']) || 'همه',
      kind,
      title: pick(row, ['عنوان', 'title']) || (kind === 'general' ? 'عمومی' : ''),
      use: pick(row, ['کاربرد', 'use']),
      body: pick(row, ['متن پرامپت', 'متن', 'body', 'prompt']),
      // مراحلِ تحقیق فقط وقتی انجام می‌شوند که «بله» باشند (خالی = لازم نیست)
      steps: kind === 'general' ? undefined : {
        competitors: flag(['بررسی رقبا', 'رقبا', 'competitors']),
        competitors_n: parseInt(pick(row, ['تعداد رقبا']), 10) || undefined,
        serp: flag(['نتایج گوگل', 'سؤالات مرتبط', 'serp']),
        suggest: flag(['گوگل ساجست', 'ساجست', 'suggest']),
        internal_links: flag(['لینک داخلی', 'internal links']),
        images: flag(['عکس', 'تصویر', 'images']),
      },
    };
  }).filter(p => p.title || p.body);

  const files = sheet(wb, ['فایل', 'files']).map(row => ({
    site: pick(row, ['سایت', 'site']) || 'همه',
    prompt: pick(row, ['عنوان پرامپت', 'پرامپت', 'prompt']),
    path: resolvePath(pick(row, ['مسیر فایل', 'مسیر', 'path', 'file'])),
    role: roleOf(pick(row, ['کاربرد', 'role'])),
    description: pick(row, ['توضیح', 'description']),
    from: 'excel',
  })).filter(f => f.path);

  const competitors = sheet(wb, ['رقبا', 'رقیب', 'competitors']).map(row => ({
    site: pick(row, ['سایت', 'site']) || 'همه',
    domain: hostOf(normUrl(pick(row, ['دامنه', 'آدرس', 'domain', 'url']))),
    kind: /نادیده|ignore|حذف/i.test(pick(row, ['نوع', 'type', 'kind'])) ? 'ignore' : 'competitor',
    notes: pick(row, ['یادداشت', 'توضیح', 'notes']),
  })).filter(c => c.domain);

  cache = { sites, prompts, files, competitors, settings, mtime };
  return cache;
}

function defaults() {
  return { hl: 'fa', gl: 'ir', browser: 'chrome', headed: false, browserPath: process.env.CWP_BROWSER_PATH || '',
    proxy: '', insecure: false, maxChars: 20000, imagesDir: '' };
}

export function config() { return load(); }

const forSite = (list, site) => list.filter(x => {
  const s = key(x.site);
  return !s || s === key('همه') || s === 'all' || s === key(site.key) || hostOf(normUrl(x.site)) === hostOf(site.url);
});

export function getSite(name) {
  const cfg = load();
  if (cfg.error && !cfg.sites.length) throw new Error(cfg.error);
  if (!name) {
    if (cfg.sites.length === 1) return cfg.sites[0];
    throw new Error(`سایت را مشخص کن (site). موجود: ${cfg.sites.map(s => s.key).join('، ') || '—'}`);
  }
  const k = key(name), h = hostOf(normUrl(name));
  const s = cfg.sites.find(s => key(s.key) === k) || cfg.sites.find(s => hostOf(s.url) === h)
    || cfg.sites.find(s => key(s.key).includes(k) || k.includes(key(s.key)));
  if (!s) throw new Error(`سایتِ «${name}» در اکسل نیست. موجود: ${cfg.sites.map(s => s.key).join('، ') || '—'} (فایل: ${EXCEL})`);
  return s;
}

// ───────────── فایل‌ها: اکسل + پوشه‌بندی ─────────────
// files\<سایت>\*            → برای همهٔ کارهای آن سایت
// files\<سایت>\<عنوان پرامپت>\* → فقط برای همان پرامپت      (files\همه\ = همهٔ سایت‌ها)
// کاربرد از نامِ فایل: «پیشفرض/default» = تصویرِ شاخصِ پیش‌فرض، «شاخص/featured»، «لوگو/logo»،
// «مرجع/نمونه/reference»، «داخل متن/inline»؛ توضیح = فایلِ txt هم‌نام کنارش (مثلاً banner.jpg + banner.txt).
export const ROLES = { default_featured: 'تصویر شاخص پیش‌فرض', featured: 'تصویر شاخص', inline: 'داخل متن', logo: 'لوگو', reference: 'مرجع', other: 'سایر' };
const IMG_EXT = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif']);
export function roleOf(text, file = '') {
  const t = key(text || basename(file, extname(file)));
  if (/پیشفرض|پیش‌فرض|default/.test(t)) return 'default_featured';
  if (/شاخص|featured|cover|کاور/.test(t)) return 'featured';
  if (/لوگو|logo|واترمارک|watermark/.test(t)) return 'logo';
  if (/مرجع|نمونه|reference|sample|راهنما|guide/.test(t)) return 'reference';
  if (/داخلمتن|داخل|inline|body/.test(t)) return 'inline';
  if (text) return 'other';
  return IMG_EXT.has(extname(file).toLowerCase()) ? 'inline' : 'reference';
}

function folderFiles(site) {
  const out = [];
  if (!existsSync(DIRS.files)) return out;
  const siteDirs = readdirSync(DIRS.files, { withFileTypes: true }).filter(d => d.isDirectory())
    .filter(d => [key(site.key), key('همه'), 'all', key(hostOf(site.url))].includes(key(d.name)));
  const scan = (dir, prompt) => {
    const entries = readdirSync(dir, { withFileTypes: true });
    const names = new Set(entries.filter(e => e.isFile()).map(e => e.name));
    for (const e of entries) {
      if (e.name.startsWith('.') || e.name.startsWith('~$')) continue;
      const p = join(dir, e.name);
      if (e.isDirectory()) { if (!prompt) scan(p, e.name); continue; }
      const stem = basename(e.name, extname(e.name));
      if (extname(e.name).toLowerCase() === '.txt' && [...names].some(n => n !== e.name && basename(n, extname(n)) === stem)) continue;
      const txt = join(dir, stem + '.txt');
      const description = e.name.endsWith('.txt') || !existsSync(txt) ? '' : readFileSync(txt, 'utf8').replace(/^\uFEFF/, '').trim().slice(0, 500);
      out.push({ site: site.key, prompt: prompt || '', path: p, role: roleOf('', e.name), description, from: 'folder' });
    }
  };
  for (const d of siteDirs) scan(join(DIRS.files, d.name), '');
  return out;
}

export function siteFiles(site, promptTitle) {
  const all = [...forSite(load().files, site), ...folderFiles(site)];
  const pk = promptTitle ? key(promptTitle) : null;
  return all.filter(f => !f.prompt || (pk && key(f.prompt) === pk));
}

/** تصویرِ شاخصِ پیش‌فرض: اولویت با پرامپت، بعد سایت. */
export function defaultFeatured(site, promptTitle) {
  const list = siteFiles(site, promptTitle).filter(f => f.role === 'default_featured' && existsSync(f.path));
  return (promptTitle && list.find(f => f.prompt)) || list.find(f => !f.prompt) || null;
}

const STEP_LABEL = { competitors: 'بررسیِ رقبا (competitor_research / page_outline)', serp: 'نتایجِ گوگل + سؤالاتِ مرتبط (serp)',
  suggest: 'گوگل ساجست (google_suggest)', internal_links: 'لینکِ داخلی (wp_internal_links)', images: 'عکس (پوشهٔ images / wp_upload_media)' };

export function siteBrief(site, promptTitle) {
  const cfg = load();
  const prompts = forSite(cfg.prompts, site);
  const comps = forSite(cfg.competitors, site);
  const fileRow = f => ({ path: f.path, missing: existsSync(f.path) ? undefined : true, role: ROLES[f.role] || f.role, description: f.description || undefined, for_prompt: f.prompt || undefined });
  const general = prompts.filter(p => p.kind === 'general' && p.body).map(p => p.body);
  if (site.prompt) general.unshift(site.prompt);
  const specific = prompts.filter(p => p.kind !== 'general');
  const brief = {
    site: site.key, url: site.url, seo_plugin: site.seo, has_credentials: !!(site.user && site.password),
    general_prompts: general, notes: site.notes || undefined,
    competitors: comps.filter(c => c.kind === 'competitor').map(c => c.domain),
    ignore_domains: comps.filter(c => c.kind === 'ignore').map(c => c.domain),
    images_folder: DIRS.images,
    files_folder: join(DIRS.files, site.key),
  };
  if (promptTitle) {
    const k = key(promptTitle);
    const p = specific.find(p => key(p.title) === k) || specific.find(p => key(p.title).includes(k) || (p.use && key(p.use).includes(k)));
    if (!p) throw new Error(`پرامپتِ اختصاصیِ «${promptTitle}» پیدا نشد. موجود: ${specific.map(p => p.title).join('، ') || '—'}`);
    const on = Object.entries(p.steps).filter(([k2, v]) => v === true).map(([k2]) => STEP_LABEL[k2]);
    brief.prompt = { title: p.title, use: p.use, body: p.body };
    brief.steps = {
      do: on, competitors_n: p.steps.competitors ? (p.steps.competitors_n || 5) : undefined,
      rule: 'فقط همین مراحل (و هرچه صریحاً در متنِ پرامپت یا پیامِ کاربر خواسته شده) را انجام بده؛ بقیهٔ بررسی‌ها لازم نیست.',
    };
    brief.files = siteFiles(site, p.title).map(fileRow);
    const df = defaultFeatured(site, p.title);
    if (df) brief.default_featured_image = df.path;
  } else {
    brief.prompts = specific.map(p => ({ title: p.title, use: p.use, steps: Object.entries(p.steps).filter(([, v]) => v === true).map(([k2]) => k2) }));
    brief.files = siteFiles(site).map(fileRow);
    const df = defaultFeatured(site);
    if (df) brief.default_featured_image = df.path;
    brief.hint = 'پرامپتِ اختصاصیِ مناسبِ کار را با همین ابزار و پارامترِ prompt بگیر (متن + مراحلِ لازم + فایل‌هایش).';
  }
  return brief;
}
