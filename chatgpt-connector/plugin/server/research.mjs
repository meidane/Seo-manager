// تحقیق: گوگل ساجست (HTTP)، نتایجِ گوگل/بینگ و سرفصلِ صفحاتِ رقبا (Playwright با Chrome/Edgeِ خودِ ویندوز).
// خروجی همیشه فشرده است (هیچ snapshot/HTMLِ کاملی به مدل داده نمی‌شود) تا توکن هدر نرود.
import { createRequire } from 'node:module';
import { existsSync, mkdirSync } from 'node:fs';
import { config, DIRS } from './config.mjs';
import { UA } from './wp.mjs';
import { norm, tokens, htmlToText, htmlSections, stripTags, decodeEntities, hostOf, wordCount } from './text.mjs';

const require = createRequire(import.meta.url);
let chromium = null;
function pw() {
  if (!chromium) chromium = require('playwright-core').chromium;
  return chromium;
}

// ───────────── مرورگر (یک نمونهٔ مشترک، بسته‌شدنِ خودکار پس از بیکاری) ─────────────
let ctx = null, ctxHeaded = false, idle = null, launching = null;
const IDLE_MS = 4 * 60e3;
function touch() {
  clearTimeout(idle);
  idle = setTimeout(() => closeBrowser().catch(() => {}), IDLE_MS);
  idle.unref?.();
}
export async function closeBrowser() {
  const c = ctx; ctx = null;
  if (c) await c.close().catch(() => {});
}

export async function browserContext({ headed } = {}) {
  const s = config().settings;
  const want = process.env.CWP_FORCE_HEADLESS ? false : (headed ?? s.headed); // FORCE فقط برای تستِ بی‌نمایشگر
  if (launching) await launching.catch(() => {});
  if (ctx && (!want || ctxHeaded)) { touch(); return ctx; }
  if (ctx) await closeBrowser();
  launching = (async () => {
    if (!existsSync(DIRS.profile)) mkdirSync(DIRS.profile, { recursive: true });
    const base = {
      headless: !want, viewport: { width: 1366, height: 900 }, locale: 'fa-IR', ignoreHTTPSErrors: true,
      args: ['--disable-blink-features=AutomationControlled', '--no-first-run', '--no-default-browser-check'],
      proxy: s.proxy ? { server: s.proxy } : undefined,
    };
    const tries = [];
    if (s.browserPath) tries.push({ executablePath: s.browserPath });
    if (process.env.CWP_BROWSER_PATH) tries.push({ executablePath: process.env.CWP_BROWSER_PATH });
    tries.push({ channel: s.browser === 'chromium' ? 'chrome' : s.browser }, { channel: s.browser === 'msedge' ? 'chrome' : 'msedge' });
    const errors = [];
    for (const t of tries) {
      try { return await pw().launchPersistentContext(DIRS.profile, { ...base, ...t }); }
      catch (e) { errors.push(`${t.channel || t.executablePath}: ${String(e.message).split('\n')[0]}`); }
    }
    // پروفایل در حالِ استفاده (مثلاً پنجرهٔ ورودِ دستیِ پنل باز است) → مرورگرِ موقت بدونِ پروفایل
    for (const t of tries) {
      try { const b = await pw().launch({ ...base, ...t }); const c = await b.newContext({ locale: 'fa-IR', viewport: base.viewport, ignoreHTTPSErrors: true }); c.on('close', () => b.close().catch(() => {})); return c; }
      catch { /* بعدی */ }
    }
    throw new Error('مرورگر اجرا نشد. Google Chrome یا Microsoft Edge نصب است؟ ' + errors.join(' | '));
  })();
  try {
    ctx = await launching;
    ctxHeaded = want;
    ctx.on('close', () => { if (ctx) ctx = null; });
  } finally { launching = null; }
  touch();
  return ctx;
}

async function newPage({ headed, block = true } = {}) {
  const c = await browserContext({ headed });
  const page = await c.newPage();
  if (block) await page.route('**/*', r => (['image', 'media', 'font'].includes(r.request().resourceType()) ? r.abort() : r.continue()));
  return page;
}

async function pool(items, n, fn) {
  const out = new Array(items.length);
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, async () => {
    while (i < items.length) { const k = i++; out[k] = await fn(items[k], k); }
  }));
  return out;
}

// ───────────── گوگل ساجست (بدونِ مرورگر) ─────────────
const FA_ALPHA = 'آ ا ب پ ت ث ج چ ح خ د ذ ر ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن و ه ی'.split(' ');
const QUESTION = ['چرا', 'چگونه', 'چطور', 'آیا', 'چیست', 'چه', 'کدام', 'بهترین', 'قیمت', 'خرید', 'مقایسه', 'انواع', 'مزایا', 'معایب', 'نحوه'];

async function suggestOnce(q, hl, gl) {
  const u = `https://suggestqueries.google.com/complete/search?client=firefox&hl=${hl}&gl=${gl}&ie=utf-8&oe=utf-8&q=${encodeURIComponent(q)}`;
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 10000);
  try {
    const r = await fetch(u, { headers: { 'User-Agent': UA }, signal: ctl.signal });
    const j = JSON.parse(await r.text());
    return Array.isArray(j?.[1]) ? j[1].map(String) : [];
  } finally { clearTimeout(t); }
}

export async function googleSuggest({ query, expand = 'basic', hl, gl }) {
  const s = config().settings;
  hl = hl || s.hl; gl = gl || s.gl;
  const qs = [query];
  if (expand === 'questions' || expand === 'all') for (const w of QUESTION) qs.push(`${w} ${query}`, `${query} ${w}`);
  if (expand === 'alphabet' || expand === 'all') for (const ch of FA_ALPHA) qs.push(`${query} ${ch}`);
  const seen = new Set(), out = [], errors = [];
  await pool(qs, 6, async q => {
    try { for (const x of await suggestOnce(q, hl, gl)) { const k = norm(x); if (!seen.has(k)) { seen.add(k); out.push(x); } } }
    catch (e) { errors.push(e.message); }
  });
  if (!out.length && errors.length) throw new Error('گوگل ساجست در دسترس نبود: ' + errors[0]);
  return { query, count: out.length, suggestions: out };
}

// ───────────── نتایجِ جست‌وجو ─────────────
function extractGoogle() {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const res = [], seen = new Set();
  for (const h3 of document.querySelectorAll('#search a h3, #rso a h3')) {
    const a = h3.closest('a'); const href = a && a.href;
    if (!href || !/^https?:/.test(href)) continue;
    let host = ''; try { host = new URL(href).hostname; } catch { continue; }
    if (/(^|\.)google\./.test(host) || seen.has(href)) continue;
    seen.add(href);
    const box = a.closest('div.g, div.MjjYud, div[data-hveid]') || a.parentElement;
    const sn = box && box.querySelector('.VwiC3b, [data-sncf], div[style*="-webkit-line-clamp"]');
    const title = clean(h3.textContent);
    const snip = sn ? clean(sn.textContent) : clean(box ? box.textContent : '').replace(title, '').slice(0, 240);
    res.push({ t: title, u: href, s: snip.slice(0, 240) });
  }
  const paa = [...new Set([...document.querySelectorAll('[data-q]')].map(e => clean(e.getAttribute('data-q'))).filter(Boolean))];
  const related = [...new Set([...document.querySelectorAll('#botstuff a[href*="/search?"], #bres a[href*="/search?"]')]
    .map(a => clean(a.textContent)).filter(t => t && t.length < 90))];
  const captcha = /\/sorry\//.test(location.href) || !!document.querySelector('form#captcha-form, #recaptcha, iframe[src*="recaptcha"]');
  return { res, paa, related, captcha };
}

function extractBing() {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const res = [...document.querySelectorAll('li.b_algo')].map(li => {
    const a = li.querySelector('h2 a');
    return a ? { t: clean(a.textContent), u: a.href, s: clean(li.querySelector('.b_caption p, p')?.textContent).slice(0, 240) } : null;
  }).filter(Boolean);
  const related = [...new Set([...document.querySelectorAll('.b_rs a, #brsv3 a')].map(a => clean(a.textContent)).filter(Boolean))];
  return { res, paa: [], related, captcha: false };
}

export async function serp({ query, n = 10, engine = 'google', hl, gl, headed }) {
  const s = config().settings;
  hl = hl || s.hl; gl = gl || s.gl;
  const page = await newPage({ headed });
  try {
    if (engine === 'bing') {
      await page.goto(`https://www.bing.com/search?q=${encodeURIComponent(query)}&setlang=${hl}&cc=${gl}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForSelector('li.b_algo', { timeout: 8000 }).catch(() => {});
      const r = await page.evaluate(extractBing);
      return { engine, query, results: r.res.slice(0, n), related: r.related };
    }
    await page.goto(`https://www.google.com/search?q=${encodeURIComponent(query)}&hl=${hl}&gl=${gl}&num=${Math.max(10, n)}&pws=0`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('#search, #rso, form#captcha-form', { timeout: 8000 }).catch(() => {});
    let r = await page.evaluate(extractGoogle);
    if (r.captcha) {
      await page.close().catch(() => {});
      if (!ctxHeaded) {
        // پنجرهٔ قابل‌دیدن باز می‌شود تا کاربر کپچا را حل کند؛ تا آن موقع از بینگ جواب می‌دهیم.
        const p2 = await newPage({ headed: true, block: false });
        await p2.goto(`https://www.google.com/search?q=${encodeURIComponent(query)}&hl=${hl}&gl=${gl}`, { waitUntil: 'domcontentloaded' }).catch(() => {});
      }
      const b = await serp({ query, n, engine: 'bing', hl, gl });
      return { ...b, note: 'گوگل کپچا داد؛ پنجرهٔ Chrome باز شد — کاربر یک بار کپچا را حل کند، بعد دوباره با engine=google بخواه. فعلاً نتایجِ بینگ:' };
    }
    if (!r.res.length) {
      await page.waitForTimeout(1500);
      r = await page.evaluate(extractGoogle);
    }
    return { engine, query, results: r.res.slice(0, n), people_also_ask: r.paa, related: r.related };
  } finally { if (!page.isClosed()) await page.close().catch(() => {}); }
}

// ───────────── سرفصلِ صفحه (H1–H6، مقدمه، متنِ بخش‌ها، FAQ، اسکیما، آمار) ─────────────
function extractOutline(opt) {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const words = s => (s ? s.split(/\s+/).filter(Boolean).length : 0);
  const meta = n => clean((document.querySelector(`meta[name="${n}"]`) || document.querySelector(`meta[property="${n}"]`) || {}).content || '');
  const NOISE = 'nav,header,footer,aside,form,[role=navigation],[role=banner],[role=contentinfo],[role=complementary],.widget,.widget-area,[class*="sidebar"],#sidebar,'
    + '#comments,.comments-area,.comment-list,.related,.related-posts,.yarpp-related,.jp-relatedposts,.post-navigation,.breadcrumb,.breadcrumbs,.rank-math-breadcrumb,'
    + '.menu,.share,.social,.author-box,[class*="site-header"],[class*="site-footer"],.elementor-location-header,.elementor-location-footer,.cookie,.popup,.modal';
  const BLOCK = 'p,li,blockquote,td,th,dd,dt,figcaption,pre';
  const noise = el => !!el.closest(NOISE);
  const linkHeavy = el => {
    const t = clean(el.textContent); if (!t) return true;
    let lt = 0; el.querySelectorAll('a').forEach(a => { lt += clean(a.textContent).length; });
    return lt / t.length > 0.8 && t.length < 140;
  };
  const all = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,' + BLOCK)];
  const items = [];
  for (const el of all) {
    const tag = el.tagName.toLowerCase();
    const isH = /^h[1-6]$/.test(tag);
    if (isH) {
      if (tag !== 'h1' && noise(el)) continue;
      const t = clean(el.textContent); if (!t) continue;
      items.push({ h: +tag[1], t });
    } else {
      if (noise(el) || el.querySelector(BLOCK) || el.closest('h1,h2,h3,h4,h5,h6') || linkHeavy(el)) continue;
      const t = clean(el.textContent); if (t.length < 2) continue;
      items.push({ b: 1, t, el });
    }
  }
  const firstH1 = items.findIndex(x => x.h === 1);
  const body = firstH1 > 0 ? items.slice(firstH1) : items;
  const sections = [];
  let cur = { l: 0, h: '(مقدمه)', parts: [] };
  for (const x of body) {
    if (x.h) { sections.push(cur); cur = { l: x.h, h: x.t, parts: [] }; } else cur.parts.push(x.t);
  }
  sections.push(cur);
  const h1 = items.filter(x => x.h === 1).map(x => x.t);
  const introSec = sections.find(s => s.l <= 1 && s.parts.length) || { parts: [] };
  const intro = introSec.parts.join(' ').slice(0, opt.introChars);
  let budget = opt.maxChars, totalWords = 0;
  const outline = [];
  for (const s of sections) {
    const text = s.parts.join(' ');
    const w = words(text); totalWords += w;
    if (s.l === 0 && !w) continue;
    if (s.l === 1 && !w) continue;
    const row = { l: s.l, h: s.h, w };
    if (opt.level !== 'outline' && budget > 0 && s.l > 1) {
      const lim = opt.level === 'full' ? budget : Math.min(opt.sectionChars, budget);
      row.t = text.length > lim ? text.slice(0, lim) + '…' : text;
      budget -= row.t.length;
    }
    outline.push(row);
  }
  // اسکیما + FAQ + تاریخ‌ها
  const types = new Set(), faq = [];
  let published = meta('article:published_time'), modified = meta('article:modified_time') || meta('og:updated_time');
  const walk = o => {
    if (!o || typeof o !== 'object') return;
    if (Array.isArray(o)) return o.forEach(walk);
    const ty = o['@type']; (Array.isArray(ty) ? ty : ty ? [ty] : []).forEach(t => types.add(t));
    if ((ty === 'FAQPage' || (Array.isArray(ty) && ty.includes('FAQPage'))) && o.mainEntity) [].concat(o.mainEntity).forEach(q => q && q.name && faq.push(clean(q.name)));
    if (o.datePublished && !published) published = o.datePublished;
    if (o.dateModified && !modified) modified = o.dateModified;
    for (const k in o) if (k !== '@context') walk(o[k]);
  };
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => { try { walk(JSON.parse(s.textContent)); } catch {} });
  if (!faq.length) outline.forEach(r => { if (r.l > 1 && /[?؟]\s*$/.test(r.h)) faq.push(r.h); });
  // آمارِ بخشِ محتوا
  const host = location.hostname.replace(/^www\./, '');
  let li = 0, le = 0;
  const contentEls = items.filter(x => x.el).map(x => x.el);
  contentEls.forEach(el => el.querySelectorAll('a[href]').forEach(a => {
    try { const h = new URL(a.href).hostname.replace(/^www\./, ''); if (h === host) li++; else le++; } catch {}
  }));
  const imgs = [...document.querySelectorAll('img')].filter(i => !noise(i) && !/^data:|\.svg/i.test(i.getAttribute('src') || i.getAttribute('data-src') || ''));
  const ids = [...document.querySelectorAll('table')].filter(t => !noise(t)).length;
  return {
    url: location.href, title: clean(document.title), description: meta('description'),
    canonical: (document.querySelector('link[rel=canonical]') || {}).href || '', robots: meta('robots') || undefined,
    lang: document.documentElement.lang || undefined, h1,
    stats: {
      words: totalWords, h2: outline.filter(r => r.l === 2).length, h3: outline.filter(r => r.l === 3).length,
      images: imgs.length, images_no_alt: imgs.filter(i => !clean(i.getAttribute('alt'))).length,
      tables: ids, lists: [...document.querySelectorAll('ul,ol')].filter(l => !noise(l) && !linkHeavy(l)).length,
      videos: [...document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="aparat"]')].length,
      internal_links: li, external_links: le,
    },
    published: published || undefined, modified: modified || undefined,
    schema: [...types].slice(0, 15), faq: faq.slice(0, 20),
    intro, outline,
  };
}

async function outlineOne(url, { level = 'outline', max_chars = 12000, section_chars = 300, timeout = 30000, headed } = {}) {
  const page = await newPage({ headed });
  const t0 = Date.now();
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
    await page.waitForLoadState('load', { timeout: 4000 }).catch(() => {});
    const r = await page.evaluate(extractOutline, { level, maxChars: max_chars, sectionChars: section_chars, introChars: level === 'outline' ? 450 : 900 });
    return { status: resp?.status(), ms: Date.now() - t0, ...r };
  } catch (e) {
    return { url, error: String(e.message).split('\n')[0] };
  } finally { await page.close().catch(() => {}); }
}

export async function pageOutline({ urls, url, level = 'outline', max_chars, section_chars, headed }) {
  const list = [...(urls || []), ...(url ? [url] : [])].filter(Boolean);
  if (!list.length) throw new Error('url یا urls لازم است.');
  const per = max_chars || (level === 'full' ? 15000 : 8000);
  const pages = await pool(list, 3, u => outlineOne(u, { level, max_chars: per, section_chars, headed }));
  return list.length === 1 ? pages[0] : { pages, common: commonTopics(pages) };
}

function commonTopics(pages, exclude = '') {
  const ok = pages.filter(p => p && p.outline);
  if (ok.length < 2) return undefined;
  const ex = new Set(tokens(exclude));
  const hCount = new Map(), tCount = new Map();
  for (const p of ok) {
    const hs = new Set(), ts = new Set();
    for (const r of p.outline) {
      if (r.l < 2 || r.l > 3) continue;
      hs.add(norm(r.h));
      for (const t of tokens(r.h)) if (!ex.has(t) && t.length > 2) ts.add(t);
    }
    for (const h of hs) hCount.set(h, (hCount.get(h) || 0) + 1);
    for (const t of ts) tCount.set(t, (tCount.get(t) || 0) + 1);
  }
  const top = (m, min) => [...m].filter(([, c]) => c >= min).sort((a, b) => b[1] - a[1]).slice(0, 30).map(([k, c]) => `${k} (${c})`);
  const words = ok.map(p => p.stats?.words || 0).filter(Boolean).sort((a, b) => a - b);
  return {
    competitors: ok.length,
    same_headings: top(hCount, 2),
    heading_terms: top(tCount, 2),
    words_median: words.length ? words[Math.floor(words.length / 2)] : undefined,
    words_max: words.length ? words[words.length - 1] : undefined,
  };
}

// ───────────── تحقیقِ رقبا (یک‌جا: نتایج + ساجست + سرفصلِ n رقیبِ اول) ─────────────
const DEFAULT_IGNORE = ['youtube.com', 'aparat.com', 'instagram.com', 'facebook.com', 'twitter.com', 'x.com', 'pinterest.com',
  'linkedin.com', 't.me', 'telegram.me', 'google.com', 'wikipedia.org', 'fa.wikipedia.org', 'namnak.com', 'ninisite.com'];

export async function competitorResearch({ keyword, site, n = 5, level = 'outline', engine = 'google', suggest = true, extra_urls = [], include_known = true }) {
  const deadline = Date.now() + 52000;
  const ignore = new Set([...DEFAULT_IGNORE, ...(site?.ignore || [])]);
  if (site?.url) ignore.add(hostOf(site.url));
  const [sr, sg] = await Promise.all([
    serp({ query: keyword, n: 15, engine }).catch(e => ({ error: String(e.message).split('\n')[0], results: [] })),
    suggest ? googleSuggest({ query: keyword, expand: 'questions' }).catch(e => ({ error: e.message })) : null,
  ]);
  const picked = [], hosts = new Set();
  for (const u of extra_urls) { picked.push(u); hosts.add(hostOf(u)); }
  for (const r of sr.results || []) {
    const h = hostOf(r.u);
    if (picked.length >= n + extra_urls.length) break;
    if (!h || hosts.has(h) || [...ignore].some(d => h === d || h.endsWith('.' + d))) continue;
    hosts.add(h); picked.push(r.u);
  }
  const remaining = Math.max(8000, deadline - Date.now());
  const pages = await pool(picked, 3, u => outlineOne(u, { level, max_chars: level === 'outline' ? 5000 : 7000, section_chars: 220, timeout: Math.min(28000, remaining) }));
  return {
    keyword, engine: sr.engine || engine, note: sr.note, serp_error: sr.error,
    serp: (sr.results || []).slice(0, 10).map(r => ({ t: r.t, u: r.u, s: r.s })),
    people_also_ask: sr.people_also_ask, related: sr.related,
    suggest: sg?.suggestions?.slice(0, 60), suggest_error: sg?.error,
    known_competitors: include_known ? site?.competitors : undefined,
    competitors: pages, common: commonTopics(pages, keyword),
  };
}

// ───────────── اسکریپتِ دلخواهِ Playwright (بدونِ محدودیت؛ به خواستِ کاربر) ─────────────
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
export async function browserRun({ url, script, headed, keep_open = false, screenshot = false, timeout = 45000, block_media = false }) {
  const page = await newPage({ headed, block: block_media });
  try {
    if (url) await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
    let result;
    if (script) {
      const fn = new AsyncFunction('page', 'context', 'helpers', script);
      result = await Promise.race([
        fn(page, page.context(), { htmlToText, htmlSections, stripTags, outline: o => page.evaluate(extractOutline, { level: 'outline', maxChars: 8000, sectionChars: 300, introChars: 450, ...o }) }),
        new Promise((_, rej) => setTimeout(() => rej(new Error('timeout اسکریپت')), timeout)),
      ]);
    } else if (url) {
      result = { url: page.url(), title: await page.title() };
    }
    const image = screenshot ? (await page.screenshot({ type: 'jpeg', quality: 60 })).toString('base64') : undefined;
    return { result, image, url: page.url() };
  } finally { if (!keep_open) await page.close().catch(() => {}); }
}

// ───────────── دریافتِ مستقیمِ یک آدرس (بدونِ مرورگر) ─────────────
export async function httpFetch({ url, method = 'GET', headers = {}, body, mode = 'text', max_chars = 20000, timeout = 30000 }) {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), timeout);
  let r, text;
  try {
    r = await fetch(url, { method, headers: { 'User-Agent': UA, ...headers }, body: body && typeof body === 'object' ? JSON.stringify(body) : body, signal: ctl.signal });
    text = await r.text();
  } finally { clearTimeout(t); }
  const head = { status: r.status, url: r.url, type: r.headers.get('content-type') };
  const cut = s => (s.length > max_chars ? s.slice(0, max_chars) + '…' : s);
  if (mode === 'raw') return { ...head, body: cut(text) };
  if (mode === 'sitemap') {
    const locs = [...text.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>(?:[\s\S]*?<lastmod>\s*([^<\s]+)\s*<\/lastmod>)?/gi)].map(m => (m[2] ? `${decodeEntities(m[1])} ${m[2].slice(0, 10)}` : decodeEntities(m[1])));
    return { ...head, index: /<sitemapindex/i.test(text), count: locs.length, urls: locs.slice(0, Math.floor(max_chars / 60)) };
  }
  if (mode === 'links') {
    const seen = new Set(), links = [];
    for (const m of text.matchAll(/<a\b[^>]*href=["']([^"'#]+)["'][^>]*>([\s\S]*?)<\/a>/gi)) {
      let u; try { u = new URL(decodeEntities(m[1]), r.url).href; } catch { continue; }
      if (seen.has(u)) continue; seen.add(u);
      links.push(`${u} | ${stripTags(m[2]).slice(0, 80)}`);
    }
    return { ...head, count: links.length, links: links.slice(0, Math.floor(max_chars / 80)) };
  }
  if (mode === 'outline') {
    const title = stripTags((text.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '');
    const desc = decodeEntities((text.match(/<meta[^>]+name=["']description["'][^>]*content=["']([^"']*)/i) || [])[1] || '');
    return { ...head, title, description: desc, words: wordCount(stripTags(text)), outline: htmlSections(text, { level: 'sections', maxChars: max_chars }) };
  }
  if (/json/.test(head.type || '')) return { ...head, body: cut(text) };
  return { ...head, text: cut(htmlToText(text)) };
}
