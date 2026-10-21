// وردپرسِ ساختگی برای تستِ محلیِ کانکتور (فقط توسعه). node dev/mock_wp.mjs [port]
// زیرمجموعه‌ای از REST: types/taxonomies/users/me/posts/pages/media/categories/product_cat/search/rankmath + یک صفحهٔ رقیب.
import { createServer } from 'node:http';

const PORT = +(process.argv[2] || 8766);
const AUTH = 'Basic ' + Buffer.from('admin:abcd efgh ijkl').toString('base64');
const H = `http://127.0.0.1:${PORT}`;
let nextId = 500;
const posts = [
  { id: 11, type: 'post', status: 'publish', slug: 'steel-304', title: 'ورق استیل ۳۰۴ چیست؟ مشخصات و کاربرد', content: '<p>ورق استیل 304 پرکاربردترین گرید است. برای <strong>لوله استیل</strong> هم استفاده می‌شود.</p><h2>کاربردها</h2><p>در صنایع غذایی لوله استیل زیاد است.</p>' },
  { id: 12, type: 'post', status: 'publish', slug: 'pipe-guide', title: 'راهنمای خرید لوله استيل', content: '<p>این راهنما برای خرید است. <a href="/x">لوله استیل</a> را ببینید. همچنین ورق استیل طلایی.</p>' },
  { id: 13, type: 'post', status: 'publish', slug: 'gold', title: 'ورق استیل طلایی', content: '<p>ورق رنگی.</p>' },
];
const pages = [{ id: 21, type: 'page', status: 'publish', slug: 'about', title: 'درباره ما', content: '<p>ما</p>' }];
const cats = [{ id: 3, name: 'آموزش', slug: 'learn', count: 3, taxonomy: 'category', description: '' }];
const pcats = [{ id: 31, name: 'لوله استیل', slug: 'steel-pipe', count: 40, taxonomy: 'product_cat', description: '<p>قدیمی</p>', parent: 0 },
  { id: 32, name: 'ورق استیل', slug: 'steel-sheet', count: 25, taxonomy: 'product_cat', description: '', parent: 0 }];
const media = [];
const rm = [];

const link = (base, p) => `${H}/${base}/${p.slug}/`;
const viewPost = (p, ctx) => ({ id: p.id, type: p.type, status: p.status, slug: p.slug, link: link(p.type, p), modified: '2026-01-01T00:00:00',
  title: ctx === 'edit' ? { raw: p.title, rendered: p.title } : { rendered: p.title },
  content: ctx === 'edit' ? { raw: p.content, rendered: p.content } : { rendered: p.content },
  excerpt: { rendered: p.excerpt || '' }, categories: p.categories || [], tags: [], featured_media: p.featured_media || 0, meta: p.meta || {}, _links: { self: [{}] } });
const viewTerm = t => ({ ...t, link: `${H}/${t.taxonomy}/${t.slug}/` });

function fields(obj, f) {
  if (!f) return obj;
  const keys = f.split(',');
  const pick = o => Object.fromEntries(keys.filter(k => k in o).map(k => [k, o[k]]));
  return Array.isArray(obj) ? obj.map(pick) : pick(obj);
}

function competitor(res) {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`<!doctype html><html lang="fa"><head><title>لوله استیل | رقیب</title><meta name="description" content="همه چیز درباره لوله استیل">
<link rel="canonical" href="${H}/competitor"><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Article","datePublished":"2025-05-01"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"قیمت لوله استیل چند است؟"}]}]}</script></head>
<body><header><nav><a href="/">خانه</a><h3>منو</h3></nav></header>
<main><article><h1>لوله استیل چیست؟</h1><p>لوله استیل یک محصول فولادی ضدزنگ است که در صنعت کاربرد فراوان دارد و مقدمه این مقاله است.</p>
<div class="toc"><ul><li><a href="#a">انواع</a></li><li><a href="#b">قیمت</a></li></ul></div>
<h2 id="a">انواع لوله استیل</h2><p>لوله درزدار و بدون درز دو نوع اصلی هستند.</p><ul><li>درزدار صنعتی</li><li>بدون درز</li></ul>
<h3>لوله ۳۰۴</h3><p>گرید ۳۰۴ رایج‌ترین است.</p><img src="/a.jpg" alt="لوله"><img src="/b.jpg">
<h2 id="b">قیمت لوله استیل</h2><p>قیمت به وزن بستگی دارد. <a href="https://other.com">منبع</a> <a href="/p">داخلی</a></p>
<table><tr><td>سایز</td><td>قیمت</td></tr></table></article></main>
<aside class="sidebar"><h2>مطالب پربازدید</h2><p>نویز سایدبار</p></aside><footer><h4>تماس</h4></footer></body></html>`);
}

createServer(async (req, res) => {
  const u = new URL(req.url, H);
  let path = u.pathname;
  if (u.searchParams.get('rest_route')) path = '/wp-json' + u.searchParams.get('rest_route');
  const chunks = []; for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks);
  const json = (code, data, headers = {}) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=UTF-8', ...headers }); res.end(JSON.stringify(data)); };
  if (path === '/competitor') return competitor(res);
  if (!path.startsWith('/wp-json')) { res.writeHead(404); return res.end('<html>not found</html>'); }
  const r = path.replace(/^\/wp-json\/?/, '').replace(/\/$/, '');
  const authed = req.headers.authorization === AUTH;
  const body = () => { try { return JSON.parse(raw.toString() || '{}'); } catch { return {}; } };
  const q = Object.fromEntries(u.searchParams);
  const f = q._fields;
  if (r === '') return json(200, fields({ name: 'سایت تست', namespaces: ['wp/v2', 'rankmath/v1', 'wc/v3'], routes: { huge: 1 } }, f));
  if (r === 'wp/v2/types') return json(200, { post: { rest_base: 'posts' }, page: { rest_base: 'pages' }, attachment: { rest_base: 'media' } });
  if (r === 'wp/v2/taxonomies') return json(200, { category: { rest_base: 'categories' }, post_tag: { rest_base: 'tags' }, product_cat: { rest_base: 'product_cat' } });
  if (r === 'wp/v2/users/me') return authed ? json(200, fields({ id: 1, name: 'مدیر', slug: 'admin', roles: ['administrator'], capabilities: { edit_posts: true, publish_posts: true, upload_files: true, manage_categories: true, manage_product_terms: true } }, f))
    : json(401, { code: 'rest_not_logged_in', message: 'شما وارد نشده‌اید.' });
  if (r === 'wp/v2/search') {
    const s = q.search || '';
    const items = q.type === 'term' ? [...cats, ...pcats].filter(t => t.name.includes(s)).map(t => ({ id: t.id, title: t.name, url: viewTerm(t).link, type: 'term', subtype: t.taxonomy }))
      : [...posts, ...pages].filter(p => p.title.includes(s) || p.content.includes(s)).map(p => ({ id: p.id, title: p.title, url: link(p.type, p), type: 'post', subtype: p.type }));
    return json(200, fields(items, f));
  }
  if (r === 'rankmath/v1/updateMeta') { if (!authed) return json(401, {}); rm.push(body()); return json(200, true); }
  let m;
  if ((m = r.match(/^wp\/v2\/(posts|pages)(?:\/(\d+))?$/))) {
    const list = m[1] === 'posts' ? posts : pages;
    if (!m[2] && req.method === 'GET') {
      let items = list.filter(p => !q.search || p.title.includes(q.search) || p.content.includes(q.search));
      const per = +q.per_page || 10, page = +q.page || 1;
      const total = items.length;
      items = items.slice((page - 1) * per, page * per).map(p => viewPost(p, q.context));
      return json(200, fields(items, f), { 'X-WP-Total': total, 'X-WP-TotalPages': Math.max(1, Math.ceil(total / per)) });
    }
    if (!authed && (req.method !== 'GET' || q.context === 'edit')) return json(401, { code: 'rest_forbidden_context', message: 'no' });
    if (!m[2] && req.method === 'POST') {
      const b = body();
      const p = { id: nextId++, type: m[1].slice(0, -1), status: b.status || 'draft', slug: b.slug || 'new-' + nextId, title: b.title || '', content: b.content || '', categories: b.categories, featured_media: b.featured_media };
      list.push(p);
      return json(201, viewPost(p, 'edit'));
    }
    const p = list.find(x => x.id === +m[2]);
    if (!p) return json(404, { code: 'rest_post_invalid_id', message: 'شناسهٔ نوشته نامعتبر است.' });
    if (req.method === 'GET') return json(200, fields(viewPost(p, q.context), f));
    const b = body();
    for (const k of ['title', 'content', 'status', 'slug', 'categories', 'featured_media']) if (b[k] !== undefined) p[k] = b[k];
    return json(200, fields(viewPost(p, 'edit'), f));
  }
  if ((m = r.match(/^wp\/v2\/(categories|product_cat|tags)(?:\/(\d+))?$/))) {
    const list = m[1] === 'product_cat' ? pcats : m[1] === 'categories' ? cats : [];
    if (!m[2] && req.method === 'GET') {
      const items = list.filter(t => !q.search || t.name.includes(q.search)).map(viewTerm);
      return json(200, fields(items, f), { 'X-WP-Total': items.length, 'X-WP-TotalPages': 1 });
    }
    if (!authed) return json(401, { code: 'rest_cannot_edit', message: 'no' });
    if (!m[2]) { const b = body(); const t = { id: nextId++, name: b.name, slug: 'n' + nextId, count: 0, taxonomy: m[1] === 'categories' ? 'category' : m[1], description: b.description || '' }; list.push(t); return json(201, viewTerm(t)); }
    const t = list.find(x => x.id === +m[2]);
    if (!t) return json(404, { code: 'rest_term_invalid', message: 'not found' });
    if (req.method !== 'GET') { const b = body(); for (const k of ['name', 'description', 'slug']) if (b[k] !== undefined) t[k] = b[k]; }
    return json(200, viewTerm(t));
  }
  if ((m = r.match(/^wp\/v2\/media(?:\/(\d+))?$/))) {
    if (!authed) return json(401, { code: 'rest_cannot_create', message: 'no' });
    if (!m[1]) {
      const md = { id: nextId++, source_url: `${H}/uploads/${decodeURIComponent((req.headers['content-disposition'] || '').match(/filename="([^"]+)"/)?.[1] || 'x')}`, size: raw.length, type: req.headers['content-type'] };
      media.push(md);
      return json(201, md);
    }
    const md = media.find(x => x.id === +m[1]);
    if (!md) return json(404, { code: 'rest_post_invalid_id', message: 'no' });
    if (req.method === 'POST') Object.assign(md, body());
    return json(200, fields(md, f));
  }
  if (r === '__state') return json(200, { posts, pcats, media, rm });
  return json(404, { code: 'rest_no_route', message: 'No route' });
}).listen(PORT, '127.0.0.1', () => console.error('mock wp on ' + PORT));
