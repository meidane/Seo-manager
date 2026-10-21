// کلاینتِ WordPress REST (Application Password) + عملیاتِ سطح‌بالا برای تولیدِ محتوا.
// همهٔ درخواست‌ها از همین کامپیوتر می‌روند (هاست‌های ایرانی از سرورهای OpenAI در دسترس نیستند).
import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { join, basename, extname } from 'node:path';
import { DIRS, HOME, resolvePath, defaultFeatured } from './config.mjs';
import {
  norm, relevance, looseRegex, stripTags, htmlToText, htmlSections, wordCount,
  markdownToHtml, looksLikeHtml, hostOf, decodeEntities,
} from './text.mjs';

export const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
const states = new Map();
const state = site => {
  if (!states.has(site.url)) states.set(site.url, { restRoute: false, media: new Map() });
  return states.get(site.url);
};

// ───────────── درخواستِ پایه ─────────────
export async function wpFetch(site, path, { method = 'GET', query, body, headers = {}, timeout = 60000, auth = true } = {}) {
  if (!site.url) throw new Error(`آدرسِ سایتِ «${site.key}» در اکسل خالی است.`);
  const st = state(site);
  const build = () => {
    if (/^https?:\/\//i.test(path)) return new URL(path);
    let [p, qs] = String(path).replace(/^\/+/, '').replace(/^wp-json\/+/, '').split('?');
    const u = st.restRoute ? new URL(site.url + '/') : new URL(site.url + '/wp-json/' + p);
    if (st.restRoute) u.searchParams.set('rest_route', '/' + p);
    if (qs) for (const [k, v] of new URLSearchParams(qs)) u.searchParams.append(k, v);
    for (const [k, v] of Object.entries(query || {})) {
      if (v === undefined || v === null || v === '') continue;
      u.searchParams.set(k, Array.isArray(v) ? v.join(',') : String(v));
    }
    return u;
  };
  const h = { 'User-Agent': UA, Accept: 'application/json', ...headers };
  if (auth && site.user && site.password) h.Authorization = 'Basic ' + Buffer.from(`${site.user}:${site.password}`).toString('base64');
  let payload = body;
  if (body && !(body instanceof Buffer) && typeof body === 'object') { payload = JSON.stringify(body); h['Content-Type'] = 'application/json'; }

  for (let attempt = 0; attempt < 2; attempt++) {
    const url = build();
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeout);
    let res, text;
    try {
      res = await fetch(url, { method, headers: h, body: payload, signal: ctl.signal });
      text = await res.text();
    } catch (e) {
      throw new Error(`اتصال به ${url.host} ناموفق (${e.name === 'AbortError' ? 'timeout' : (e.cause?.code || e.message)}). سایت از همین کامپیوتر باز می‌شود؟`);
    } finally { clearTimeout(timer); }
    let data;
    try { data = text ? JSON.parse(text.replace(/^﻿/, '')) : null; } catch { data = undefined; }
    if (res.ok && data !== undefined) {
      return { data, status: res.status, total: +res.headers.get('x-wp-total') || undefined, pages: +res.headers.get('x-wp-totalpages') || undefined };
    }
    // بدونِ پیوندِ یکتا (permalink ساده) /wp-json/ کار نمی‌کند → ?rest_route=
    if (!st.restRoute && !/^https?:/i.test(path) && data === undefined && (res.status === 404 || res.ok)) { st.restRoute = true; continue; }
    if (res.ok) throw new Error(`پاسخِ JSON نبود (${res.status}): ${text.slice(0, 200)}`);
    const msg = data ? `${data.code || ''} ${decodeEntities(data.message || '')}`.trim() : stripTags(text).slice(0, 200);
    const hint = res.status === 401 ? ' ← نام کاربری/«رمز برنامه» (Application Password) را در اکسل چک کن؛ اگر درست است، هاست هدرِ Authorization را حذف می‌کند.'
      : res.status === 403 ? ' ← این کاربر دسترسیِ کافی ندارد یا فایروال/امنیتِ سایت درخواست را بسته.'
        : res.status === 404 ? ' ← مسیر وجود ندارد (افزونه/نوعِ محتوا فعال نیست؟).' : '';
    const err = new Error(`WordPress ${res.status}: ${msg}${hint}`);
    err.status = res.status; err.data = data;
    throw err;
  }
}

export async function wpAll(site, path, query = {}, max = 3000) {
  const first = await wpFetch(site, path, { query: { ...query, per_page: 100, page: 1 } });
  let items = Array.isArray(first.data) ? first.data : [];
  const pages = Math.min(first.pages || 1, Math.ceil(max / 100));
  for (let p = 2; p <= pages; p += 4) {
    const batch = await Promise.all([p, p + 1, p + 2, p + 3].filter(n => n <= pages)
      .map(n => wpFetch(site, path, { query: { ...query, per_page: 100, page: n } }).then(r => r.data).catch(() => [])));
    for (const b of batch) items = items.concat(b);
  }
  return items.slice(0, max);
}

// ───────────── کشف (انواعِ محتوا/طبقه‌بندی/افزونه‌ها) ─────────────
async function discover(site) {
  const st = state(site);
  if (st.types) return st;
  const [types, taxes, root] = await Promise.all([
    wpFetch(site, 'wp/v2/types').then(r => r.data).catch(() => ({})),
    wpFetch(site, 'wp/v2/taxonomies').then(r => r.data).catch(() => ({})),
    wpFetch(site, '', { query: { _fields: 'name,namespaces' } }).then(r => r.data).catch(() => ({})),
  ]);
  st.types = {};
  for (const [k, v] of Object.entries(types || {})) if (v?.rest_base) st.types[k] = v.rest_base;
  st.taxes = {};
  for (const [k, v] of Object.entries(taxes || {})) if (v?.rest_base) st.taxes[k] = v.rest_base;
  st.namespaces = root?.namespaces || [];
  st.siteName = root?.name;
  st.woo = st.namespaces.includes('wc/v3');
  st.seo = st.namespaces.some(n => n.startsWith('rankmath')) ? 'rankmath' : st.namespaces.some(n => n.startsWith('yoast')) ? 'yoast' : '';
  return st;
}

const TYPE_ALIAS = { posts: 'post', pages: 'page', products: 'product', article: 'post', مقاله: 'post', برگه: 'page', صفحه: 'page', محصول: 'product' };
const TAX_ALIAS = { category: 'category', categories: 'category', دسته: 'category', tag: 'post_tag', tags: 'post_tag', product_cat: 'product_cat',
  'product-category': 'product_cat', product_category: 'product_cat', 'دسته محصول': 'product_cat', 'دسته‌بندی محصول': 'product_cat', product_tag: 'product_tag' };

async function postBase(site, type = 'post') {
  const st = await discover(site);
  const t = TYPE_ALIAS[type] || type;
  if (st.types[t]) return { kind: t, base: 'wp/v2/' + st.types[t] };
  const byBase = Object.entries(st.types).find(([, b]) => b === type);
  if (byBase) return { kind: byBase[0], base: 'wp/v2/' + type };
  if (t === 'product' && st.woo) return { kind: 'product', base: 'wc/v3/products', wc: true };
  if (t === 'post' || t === 'page') return { kind: t, base: `wp/v2/${t}s` };
  throw new Error(`نوعِ محتوای «${type}» در REST این سایت نیست. موجود: ${Object.keys(st.types).join(', ')}`);
}

async function taxBase(site, taxonomy = 'category') {
  const st = await discover(site);
  const t = TAX_ALIAS[taxonomy] || TAX_ALIAS[norm(taxonomy)] || taxonomy;
  if (st.taxes[t]) return { tax: t, base: 'wp/v2/' + st.taxes[t] };
  if (t === 'product_cat' && st.woo) return { tax: t, base: 'wc/v3/products/categories', wc: true };
  if (t === 'product_tag' && st.woo) return { tax: t, base: 'wc/v3/products/tags', wc: true };
  if (t === 'category') return { tax: t, base: 'wp/v2/categories' };
  throw new Error(`طبقه‌بندیِ «${taxonomy}» در REST این سایت نیست. موجود: ${Object.keys(st.taxes).join(', ')}`);
}

const isTaxonomy = t => !!(TAX_ALIAS[t] || TAX_ALIAS[norm(t)]) || /cat|tag|tax/i.test(t);

// ───────────── بک‌آپِ محلی پیش از هر ویرایشِ چیزِ موجود ─────────────
export function backup(site, kind, id, data) {
  const dir = join(DIRS.backups, site.key.replace(/[^\p{L}\p{N}._-]+/gu, '_'));
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const file = join(dir, `${kind}-${id}-${new Date().toISOString().replace(/[:.]/g, '-')}.json`);
  writeFileSync(file, JSON.stringify(data, null, 1), 'utf8');
  return file;
}

// ───────────── بررسیِ اتصال ─────────────
export async function wpCheck(site) {
  if (!site.user || !site.password) throw new Error(`برای «${site.key}» نام کاربری یا «رمز برنامه» در اکسل خالی است.`);
  const me = await wpFetch(site, 'wp/v2/users/me', { query: { context: 'edit', _fields: 'id,name,slug,roles,capabilities' } });
  const st = await discover(site);
  const caps = me.data.capabilities || {};
  const count = async base => (await wpFetch(site, base, { query: { per_page: 1, _fields: 'id' } }).catch(() => ({}))).total;
  const counts = {};
  for (const t of ['post', 'page', 'product']) if (st.types[t]) counts[t] = await count('wp/v2/' + st.types[t]);
  if (!st.types.product && st.woo) counts.product = await count('wc/v3/products');
  for (const t of ['category', 'product_cat']) if (st.taxes[t]) counts[t] = await count('wp/v2/' + st.taxes[t]);
  return {
    ok: true, site: site.key, site_name: st.siteName, user: me.data.name, roles: me.data.roles,
    can: Object.fromEntries(['edit_posts', 'publish_posts', 'edit_pages', 'upload_files', 'manage_categories', 'edit_products', 'manage_product_terms']
      .map(c => [c, !!caps[c]])),
    seo_plugin: site.seo === 'auto' ? (st.seo || 'نامشخص') : site.seo, seo_detected: st.seo || 'none',
    woocommerce: st.woo, rest_mode: st.restRoute ? '?rest_route=' : '/wp-json/',
    post_types: Object.keys(st.types), taxonomies: Object.keys(st.taxes), counts,
  };
}

// ───────────── جست‌وجو و خواندن ─────────────
export async function wpFind(site, { query, kind = 'any', limit = 10 }) {
  const kinds = kind === 'any' ? ['post', 'term'] : [kind];
  const out = [];
  for (const type of kinds) {
    const r = await wpFetch(site, 'wp/v2/search', { query: { search: query, type, per_page: Math.min(limit, 100), _fields: 'id,title,url,type,subtype' } }).catch(e => ({ data: [], err: e.message }));
    for (const x of r.data || []) out.push({ id: x.id, type: x.subtype, title: decodeEntities(x.title), url: x.url });
  }
  return out;
}

export async function wpGet(site, { type = 'post', id, format = 'outline', max_chars = 20000 }) {
  if (isTaxonomy(type)) {
    const { base, tax, wc } = await taxBase(site, type);
    const t = (await wpFetch(site, `${base}/${id}`, { query: wc ? {} : { context: 'edit' } })).data;
    return { id: t.id, taxonomy: tax, name: decodeEntities(t.name), slug: t.slug, link: t.link || t.permalink, parent: t.parent, count: t.count,
      description: fmt(t.description || '', format, max_chars), description_words: wordCount(stripTags(t.description || '')) };
  }
  const { base, kind, wc } = await postBase(site, type);
  let p;
  try { p = (await wpFetch(site, `${base}/${id}`, { query: wc ? {} : { context: 'edit' } })).data; }
  catch (e) { if (e.status === 401 || e.status === 403) p = (await wpFetch(site, `${base}/${id}`)).data; else throw e; }
  if (wc) {
    return { id: p.id, type: 'product', name: p.name, status: p.status, slug: p.slug, link: p.permalink, price: p.price, sku: p.sku,
      categories: (p.categories || []).map(c => ({ id: c.id, name: c.name })), images: (p.images || []).map(i => i.src).slice(0, 5),
      short_description: fmt(p.short_description, 'text', 2000), description: fmt(p.description, format, max_chars) };
  }
  const html = p.content?.raw ?? p.content?.rendered ?? '';
  const meta = {};
  for (const [k, v] of Object.entries(p.meta || {})) if (/rank_math_(title|description|focus_keyword)|_yoast_wpseo_(title|metadesc|focuskw)/.test(k) && v) meta[k] = v;
  return {
    id: p.id, type: kind, title: decodeEntities(p.title?.raw ?? p.title?.rendered ?? ''), status: p.status, slug: p.slug, link: p.link,
    modified: p.modified, categories: p.categories, tags: p.tags, featured_media: p.featured_media,
    excerpt: stripTags(p.excerpt?.raw ?? p.excerpt?.rendered ?? '').slice(0, 400),
    words: wordCount(stripTags(html)), seo_meta: Object.keys(meta).length ? meta : undefined,
    content: fmt(html, format, max_chars),
  };
}

function fmt(html, format, max) {
  if (format === 'html') return html.length > max ? html.slice(0, max) + '…' : html;
  if (format === 'text') { const t = htmlToText(html); return t.length > max ? t.slice(0, max) + '…' : t; }
  if (format === 'none') return undefined;
  return htmlSections(html, { level: format === 'sections' ? 'sections' : 'outline', maxChars: max });
}

// ───────────── فهرستِ سایت (برای لینکِ داخلی؛ فقط در حافظه، ۳۰ دقیقه) ─────────────
export async function inventory(site, { refresh = false, kinds } = {}) {
  const st = await discover(site);
  if (!refresh && st.inv && Date.now() - st.invAt < 30 * 60e3) return filterKinds(st.inv, kinds);
  const jobs = [];
  for (const t of ['post', 'page', 'product']) {
    if (st.types[t]) jobs.push(wpAll(site, 'wp/v2/' + st.types[t], { _fields: 'id,link,title,slug', status: 'publish' }, 5000)
      .then(rows => rows.map(r => ({ id: r.id, k: t, t: decodeEntities(r.title?.rendered || ''), u: r.link, s: r.slug }))).catch(() => []));
  }
  if (!st.types.product && st.woo) jobs.push(wpAll(site, 'wc/v3/products', { _fields: 'id,permalink,name,slug', status: 'publish' }, 5000)
    .then(rows => rows.map(r => ({ id: r.id, k: 'product', t: decodeEntities(r.name), u: r.permalink, s: r.slug }))).catch(() => []));
  for (const t of ['category', 'product_cat', 'post_tag', 'product_tag']) {
    if (st.taxes[t]) jobs.push(wpAll(site, 'wp/v2/' + st.taxes[t], { _fields: 'id,link,name,slug,count', hide_empty: t.endsWith('tag') ? true : undefined }, 3000)
      .then(rows => rows.map(r => ({ id: r.id, k: t, t: decodeEntities(r.name), u: r.link, s: r.slug, n: r.count }))).catch(() => []));
  }
  st.inv = (await Promise.all(jobs)).flat();
  st.invAt = Date.now();
  return filterKinds(st.inv, kinds);
}
const filterKinds = (inv, kinds) => (kinds?.length ? inv.filter(x => kinds.includes(x.k)) : inv);

export async function internalLinks(site, { keywords, limit = 6, kinds, exclude_urls = [], refresh = false }) {
  const inv = await inventory(site, { refresh, kinds });
  const ex = new Set(exclude_urls.map(u => u.replace(/\/+$/, '')));
  const out = [];
  for (const kw of keywords) {
    const scored = [];
    for (const x of inv) {
      if (ex.has((x.u || '').replace(/\/+$/, ''))) continue;
      const sc = relevance(kw, x.t, x.s);
      if (sc >= 0.6) scored.push({ ...x, sc });
    }
    scored.sort((a, b) => b.sc - a.sc || (b.n || 0) - (a.n || 0));
    out.push({ keyword: kw, links: scored.slice(0, limit).map(({ id, k, t, u, sc }) => ({ id, k, t, u, sc })) });
  }
  const byKind = inv.reduce((a, x) => ((a[x.k] = (a[x.k] || 0) + 1), a), {});
  return { inventory: byKind, results: out };
}

// ───────────── لینکِ ورودی از مطالبِ قدیمی به مطلبِ جدید ─────────────
function allowedAt(raw, idx) {
  const before = raw.slice(0, idx);
  if (before.lastIndexOf('<') > before.lastIndexOf('>')) return false;
  const cnt = re => (before.match(re) || []).length;
  if (cnt(/<a[\s>]/gi) > cnt(/<\/a>/gi)) return false;
  if (cnt(/<h[1-6][\s>]/gi) > cnt(/<\/h[1-6]>/gi)) return false;
  if (cnt(/<(script|style|figcaption|button)[\s>]/gi) > cnt(/<\/(script|style|figcaption|button)>/gi)) return false;
  return true;
}

export async function linkOpportunities(site, { target_url, keywords, limit = 10, types = ['post', 'page'] }) {
  const seen = new Set(), out = [];
  const target = (target_url || '').replace(/\/+$/, '');
  for (const kw of keywords) {
    const re = looseRegex(kw, 'i');
    for (const t of types) {
      let base;
      try { ({ base } = await postBase(site, t)); } catch { continue; }
      if (base.startsWith('wc/')) continue;
      const r = await wpFetch(site, base, { query: { search: kw, per_page: 20, status: 'publish', _fields: 'id,title,link,content' } }).catch(() => ({ data: [] }));
      for (const p of r.data || []) {
        const key = t + p.id;
        if (seen.has(key) || (p.link || '').replace(/\/+$/, '') === target) continue;
        const html = p.content?.rendered || '';
        if (target && html.includes(target)) continue;
        const g = new RegExp(re.source, 'gi');
        let m, ok = false;
        while ((m = g.exec(html))) if (allowedAt(html, m.index)) { ok = true; break; }
        if (!ok) continue;
        const text = stripTags(html), tm = text.match(re);
        seen.add(key);
        out.push({ id: p.id, type: t, title: decodeEntities(p.title?.rendered || ''), url: p.link, anchor: kw,
          snippet: tm ? '…' + text.slice(Math.max(0, tm.index - 70), tm.index + tm[0].length + 70) + '…' : '' });
        if (out.length >= limit) return out;
      }
    }
  }
  return out;
}

export async function addLink(site, { type = 'post', id, anchor, url, occurrence = 1, dry_run = true }) {
  const { base, wc } = await postBase(site, type);
  if (wc) throw new Error('برای محصول از wp_save_post/wp_api استفاده کن.');
  const p = (await wpFetch(site, `${base}/${id}`, { query: { context: 'edit' } })).data;
  const raw = p.content?.raw ?? '';
  if (raw.includes(url)) return { skipped: true, reason: 'این مطلب از قبل به همین آدرس لینک دارد.', id };
  const g = looseRegex(anchor, 'gi');
  let m, n = 0, hit = null;
  while ((m = g.exec(raw))) if (allowedAt(raw, m.index) && ++n === occurrence) { hit = m; break; }
  if (!hit) return { skipped: true, reason: `عبارتِ «${anchor}» (خارج از لینک/تیتر) در متنِ خامِ مطلب پیدا نشد.`, id };
  const link = `<a href="${url}">${hit[0]}</a>`;
  const next = raw.slice(0, hit.index) + link + raw.slice(hit.index + hit[0].length);
  const ctx = s => stripTags(s.slice(Math.max(0, hit.index - 160), hit.index + link.length + 160));
  const preview = { id, title: decodeEntities(p.title?.raw || ''), before: ctx(raw), after_html: next.slice(Math.max(0, hit.index - 80), hit.index + link.length + 80) };
  if (dry_run) return { dry_run: true, ...preview, note: 'برای اعمال، همین را با dry_run=false بفرست (بعد از تأییدِ کاربر).' };
  const bk = backup(site, base.split('/').pop(), id, { id, content_raw: raw, title: p.title?.raw, modified: p.modified });
  await wpFetch(site, `${base}/${id}`, { method: 'POST', body: { content: next } });
  return { done: true, ...preview, backup: bk };
}

// ───────────── رسانه ─────────────
// کشِ ماندگارِ آپلود (فایلِ محلیِ تغییرنکرده دوباره آپلود نشود — مخصوصاً عکسِ شاخصِ پیش‌فرض)
const CACHE_FILE = join(HOME, '.media-cache.json');
let diskCache = null;
const dcLoad = () => { if (!diskCache) { try { diskCache = JSON.parse(readFileSync(CACHE_FILE, 'utf8')); } catch { diskCache = {}; } } return diskCache; };
const dcSave = () => { try { writeFileSync(CACHE_FILE, JSON.stringify(diskCache)); } catch { /* مهم نیست */ } };
const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif',
  '.avif': 'image/avif', '.svg': 'image/svg+xml', '.pdf': 'application/pdf', '.mp4': 'video/mp4' };

export async function uploadMedia(site, { source, alt, title, caption, filename }) {
  const st = state(site);
  if (!source) throw new Error('source (مسیرِ فایل یا آدرس) لازم است.');
  let buf, name, mime, cacheKey = source;
  if (/^https?:\/\//i.test(source)) {
    if (st.media.has(source)) return st.media.get(source);
    const r = await fetch(source, { headers: { 'User-Agent': UA } });
    if (!r.ok) throw new Error(`دانلودِ تصویر ناموفق (${r.status}): ${source}`);
    buf = Buffer.from(await r.arrayBuffer());
    mime = (r.headers.get('content-type') || '').split(';')[0];
    name = basename(new URL(source).pathname) || 'image';
  } else {
    let p = resolvePath(source);
    if (!existsSync(p) && existsSync(join(DIRS.images, source))) p = join(DIRS.images, source);
    if (!existsSync(p)) throw new Error(`فایل پیدا نشد: ${p} (عکس‌ها را در ${DIRS.images} بگذار)`);
    const fst = statSync(p);
    cacheKey = `${p}:${fst.size}:${fst.mtimeMs}`;
    if (st.media.has(cacheKey)) return st.media.get(cacheKey);
    const hit = dcLoad()[site.url + '|' + cacheKey];
    if (hit) {
      const ok = await wpFetch(site, `wp/v2/media/${hit.id}`, { query: { _fields: 'id,source_url' } }).then(() => true).catch(() => false);
      if (ok) { const o = { ...hit, reused: true }; st.media.set(cacheKey, o); return o; }
    }
    buf = readFileSync(p); name = basename(p);
  }
  name = filename || name;
  let ext = extname(name).toLowerCase();
  if (!MIME[ext]) { ext = Object.entries(MIME).find(([, m]) => m === mime)?.[0] || '.jpg'; name += ext; }
  mime = MIME[ext];
  const ascii = name.replace(/[^\w.-]+/g, '-').replace(/^-+/, '') || `image-${Date.now()}${ext}`;
  const safeAscii = /^[-.]*\./.test(ascii) ? `image-${Date.now()}${ext}` : ascii;
  const r = await wpFetch(site, 'wp/v2/media', {
    method: 'POST', body: buf, timeout: 180000,
    headers: { 'Content-Type': mime, 'Content-Disposition': `attachment; filename="${safeAscii}"; filename*=UTF-8''${encodeURIComponent(name)}` },
  });
  const media = r.data;
  const upd = {};
  if (alt) upd.alt_text = alt;
  if (title) upd.title = title;
  if (caption) upd.caption = caption;
  if (Object.keys(upd).length) await wpFetch(site, `wp/v2/media/${media.id}`, { method: 'POST', body: upd }).catch(() => {});
  const out = { id: media.id, url: media.source_url, alt: alt || '' };
  st.media.set(cacheKey, out);
  if (!/^https?:/i.test(source)) { dcLoad()[site.url + '|' + cacheKey] = { id: out.id, url: out.url }; dcSave(); }
  return out;
}

const isLocalSrc = src => !/^(https?:|data:|\/\/)/i.test(src) || /^file:/i.test(src);

/** Markdown→HTML (در صورتِ نیاز) + آپلودِ خودکارِ عکس‌های محلی داخلِ متن و جایگزینیِ آدرس. */
export async function prepareContent(site, content, { format = 'auto', upload_remote_images = false } = {}) {
  if (content === undefined || content === null) return { html: undefined, uploaded: [], warnings: [] };
  let html = format === 'html' || (format === 'auto' && looksLikeHtml(content)) ? String(content) : markdownToHtml(content);
  // عنوانِ نوشته خودش H1 است → H1ِ اولِ متن حذف، بقیهٔ H1ها H2 می‌شوند
  html = html.replace(/^\s*<h1\b[^>]*>[\s\S]*?<\/h1>\s*/i, '').replace(/<(\/?)h1\b/gi, '<$1h2');
  const uploaded = [], warnings = [];
  const imgRe = /<img\b[^>]*>/gi;
  const tags = html.match(imgRe) || [];
  for (const tag of [...new Set(tags)]) {
    const src = decodeEntities((tag.match(/\bsrc=["']([^"']+)["']/i) || [])[1] || '');
    if (!src) continue;
    const local = isLocalSrc(src);
    if (!local && !upload_remote_images) continue;
    if (!local && hostOf(src) === hostOf(site.url)) continue;
    const alt = decodeEntities((tag.match(/\balt=["']([^"']*)["']/i) || [])[1] || '');
    try {
      const m = await uploadMedia(site, { source: src, alt });
      uploaded.push(m);
      let nt = tag.replace(src, m.url).replace(/\bsrc=["'][^"']+["']/i, `src="${m.url}"`);
      nt = /\bclass=/i.test(nt) ? nt.replace(/\bclass=["']([^"']*)["']/i, `class="$1 wp-image-${m.id}"`) : nt.replace(/<img\b/i, `<img class="wp-image-${m.id}"`);
      html = html.split(tag).join(nt);
    } catch (e) { warnings.push(`عکسِ ${src}: ${e.message}`); }
  }
  return { html, uploaded, warnings };
}

// ───────────── طبقه‌بندی‌ها (نام → id) ─────────────
async function resolveTerms(site, taxonomy, list, warnings) {
  if (!list?.length) return undefined;
  const { base, wc } = await taxBase(site, taxonomy);
  const ids = [];
  for (const v of list) {
    if (/^\d+$/.test(String(v))) { ids.push(+v); continue; }
    const r = await wpFetch(site, base, { query: { search: v, per_page: 20 } }).catch(() => ({ data: [] }));
    const hit = (r.data || []).find(t => norm(decodeEntities(t.name)) === norm(v));
    if (hit) { ids.push(hit.id); continue; }
    try { ids.push((await wpFetch(site, base, { method: 'POST', body: { name: v } })).data.id); warnings.push(`«${v}» در ${taxonomy} ساخته شد.`); }
    catch (e) { warnings.push(`«${v}» پیدا/ساخته نشد: ${e.message}`); }
  }
  return wc ? ids.map(id => ({ id })) : ids;
}

// ───────────── سئو (Rank Math / Yoast) ─────────────
const SEO_KEYS = {
  rankmath: { title: 'rank_math_title', description: 'rank_math_description', focus_keyword: 'rank_math_focus_keyword' },
  yoast: { title: '_yoast_wpseo_title', description: '_yoast_wpseo_metadesc', focus_keyword: '_yoast_wpseo_focuskw' },
};

export async function setSeo(site, objectType, id, seo, restPath) {
  if (!seo || !['title', 'description', 'focus_keyword'].some(k => seo[k])) return undefined;
  const st = await discover(site);
  const plugin = site.seo && site.seo !== 'auto' ? (site.seo.includes('yoast') ? 'yoast' : 'rankmath') : (st.seo || 'rankmath');
  const keys = SEO_KEYS[plugin];
  const meta = {};
  for (const [k, mk] of Object.entries(keys)) if (seo[k]) meta[mk] = seo[k];
  const tried = [];
  if (plugin === 'rankmath') {
    try {
      await wpFetch(site, 'rankmath/v1/updateMeta', { method: 'POST', body: { objectType, objectID: id, meta } });
      return { ok: true, plugin, via: 'rankmath/v1/updateMeta', meta };
    } catch (e) { tried.push('rankmath/v1/updateMeta → ' + e.message); }
  }
  if (restPath && !restPath.startsWith('wc/')) {
    try {
      const r = await wpFetch(site, `${restPath}/${id}`, { method: 'POST', body: { meta }, query: { context: 'edit', _fields: 'meta' } });
      const saved = r.data?.meta || {};
      if (Object.keys(meta).every(k => saved[k] === meta[k])) return { ok: true, plugin, via: 'meta', meta };
      tried.push('meta → فیلدها در REST ثبت نشده‌اند (show_in_rest)');
    } catch (e) { tried.push('meta → ' + e.message); }
  }
  return { ok: false, plugin, meta, tried, note: 'سئو خودکار ثبت نشد؛ این مقادیر را دستی در پیشخوان وارد کن (یا مسیرِ دیگری را با wp_api امتحان کن).' };
}

// ───────────── ذخیرهٔ نوشته/برگه/محصول ─────────────
export async function savePost(site, a) {
  const { base, kind, wc } = await postBase(site, a.type || 'post');
  const warnings = [];
  const prep = await prepareContent(site, a.content, { format: a.content_format, upload_remote_images: a.upload_remote_images });
  warnings.push(...prep.warnings);
  const ex = a.excerpt !== undefined ? await prepareContent(site, a.excerpt, { format: a.content_format }) : null;
  let featured;
  if ((a.featured_image === undefined || a.featured_image === '') && !a.id && kind === 'post') {
    const df = defaultFeatured(site, a.prompt);
    if (df) { a.featured_image = df.path; warnings.push(`تصویرِ شاخصِ پیش‌فرض گذاشته شد: ${df.path}`); }
  }
  if (a.featured_image === 'none') a.featured_image = undefined;
  if (a.featured_image !== undefined && a.featured_image !== '') {
    if (/^\d+$/.test(String(a.featured_image))) featured = { id: +a.featured_image };
    else {
      try { featured = await uploadMedia(site, { source: a.featured_image, alt: a.featured_alt || a.title }); }
      catch (e) { warnings.push('تصویرِ شاخص: ' + e.message); }
    }
  }
  let old = null;
  if (a.id) {
    old = (await wpFetch(site, `${base}/${a.id}`, { query: wc ? {} : { context: 'edit' } })).data;
    backup(site, kind, a.id, old);
  }
  let body;
  if (wc) {
    body = { name: a.title, description: prep.html, short_description: ex?.html, slug: a.slug,
      status: a.status || (a.id ? undefined : 'draft'),
      categories: await resolveTerms(site, 'product_cat', a.categories, warnings),
      tags: await resolveTerms(site, 'product_tag', a.tags, warnings) };
    if (featured) body.images = [{ id: featured.id }, ...((old?.images || []).slice(1).map(i => ({ id: i.id })))];
  } else {
    body = { title: a.title, content: prep.html, excerpt: ex ? stripTags(ex.html) : undefined, slug: a.slug,
      status: a.status || (a.id ? undefined : 'draft'), featured_media: featured?.id,
      categories: kind === 'post' ? await resolveTerms(site, 'category', a.categories, warnings) : undefined,
      tags: kind === 'post' ? await resolveTerms(site, 'post_tag', a.tags, warnings) : undefined,
      parent: a.parent, date: a.date };
  }
  Object.assign(body, a.fields || {});
  for (const k of Object.keys(body)) if (body[k] === undefined) delete body[k];
  const r = (await wpFetch(site, a.id ? `${base}/${a.id}` : base, { method: a.id ? 'PUT' : 'POST', body })).data;
  const id = r.id;
  const seo = await setSeo(site, 'post', id, a.seo, base);
  const link = r.link || r.permalink;
  return {
    id, type: kind, status: r.status, link,
    preview: r.status === 'publish' ? link : `${site.url}/?p=${id}&preview=true`,
    edit: `${site.url}/wp-admin/post.php?post=${id}&action=edit`,
    title: decodeEntities(r.title?.raw ?? r.title?.rendered ?? r.name ?? ''),
    words: wordCount(stripTags(prep.html || '')), featured: featured || undefined,
    uploaded_images: prep.uploaded.length ? prep.uploaded : undefined,
    seo, warnings: warnings.length ? warnings : undefined,
  };
}

// ───────────── ذخیرهٔ دسته‌بندی (متنِ توضیحِ دستهٔ محصول/نوشته) ─────────────
export async function saveTerm(site, a) {
  const { base, tax, wc } = await taxBase(site, a.taxonomy || 'product_cat');
  const warnings = [];
  const prep = await prepareContent(site, a.description, { format: a.description_format, upload_remote_images: a.upload_remote_images });
  warnings.push(...prep.warnings);
  if (a.id) {
    const old = (await wpFetch(site, `${base}/${a.id}`, { query: wc ? {} : { context: 'edit' } })).data;
    backup(site, tax, a.id, old);
  }
  const body = { name: a.name, slug: a.slug, parent: a.parent, description: prep.html, ...(a.fields || {}) };
  for (const k of Object.keys(body)) if (body[k] === undefined) delete body[k];
  const r = (await wpFetch(site, a.id ? `${base}/${a.id}` : base, { method: a.id ? 'PUT' : 'POST', body })).data;
  const seo = await setSeo(site, 'term', r.id, a.seo, wc ? null : base);
  return { id: r.id, taxonomy: tax, name: decodeEntities(r.name), link: r.link || r.permalink, words: wordCount(stripTags(prep.html || '')),
    edit: `${site.url}/wp-admin/term.php?taxonomy=${tax}&tag_ID=${r.id}`, uploaded_images: prep.uploaded.length ? prep.uploaded : undefined,
    seo, warnings: warnings.length ? warnings : undefined };
}
