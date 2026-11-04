"""کلاینتِ وردپرس برای دروازهٔ MCP — همهٔ درخواست‌ها از سرورِ پنل به سایت می‌روند.

- `request`: REST وردپرس با Application Password (اگر `/wp-json/` بسته بود، یک بار با `?rest_route=`).
- `mcp`: کلاینتِ MCPِ سایت (Novamira، `/wp-json/mcp/novamira`) — initialize + session + پاسخِ JSON یا SSE.
- عملیاتِ سطح‌بالا (جستجو/خواندن/ذخیره/آپلود/سئو) نسخهٔ پایتونیِ `chatgpt-connector/plugin/server/wp.mjs` است.
"""
import base64
import html as htmlmod
import json
import re
from urllib.parse import urlparse

import requests
from django.core.cache import cache

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
TIMEOUT = 60


class WPError(Exception):
    def __init__(self, msg, status=None, data=None):
        super().__init__(msg)
        self.status, self.data = status, data


def _auth(site):
    if site.wp_user and site.password:
        return 'Basic ' + base64.b64encode(f'{site.wp_user}:{site.password}'.encode()).decode()
    return None


def _strip(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def _route_key(site):
    return f'mcpgate:restroute:{site.pk}'


def _build_url(site, path, rest_route):
    path = str(path or '')
    if re.match(r'^https?://', path, re.I):
        return path, {}
    p, _, qs = path.lstrip('/').removeprefix('wp-json/').lstrip('/').partition('?')
    extra = dict(x.split('=', 1) if '=' in x else (x, '') for x in qs.split('&') if x)
    base = site.url.rstrip('/')
    if rest_route:
        return base + '/', {'rest_route': '/' + p, **extra}
    return f'{base}/wp-json/{p}', extra


def request(site, path, method='GET', query=None, body=None, headers=None, timeout=TIMEOUT, raw=False):
    """یک درخواستِ REST. خروجی: {'data', 'status', 'total', 'pages'}. خطا → WPError با راهنمای فارسی."""
    if not site.url:
        raise WPError(f'آدرسِ سایتِ «{site.key}» خالی است.')
    h = {'User-Agent': UA, 'Accept': 'application/json', **(headers or {})}
    a = _auth(site)
    if a:
        h['Authorization'] = a
    data = body
    if body is not None and not isinstance(body, (bytes, bytearray, str)):
        data = json.dumps(body, ensure_ascii=False).encode()
        h['Content-Type'] = 'application/json; charset=utf-8'
    q = {k: (','.join(map(str, v)) if isinstance(v, (list, tuple)) else v)
         for k, v in (query or {}).items() if v not in (None, '')}
    use_route = bool(cache.get(_route_key(site)))
    tried_route, switched = use_route, False
    for _ in range(2):
        url, extra = _build_url(site, path, use_route)
        try:
            r = requests.request(method.upper(), url, params={**extra, **q}, data=data, headers=h, timeout=timeout)
        except requests.RequestException as e:
            raise WPError(f'اتصال از سرورِ پنل به {urlparse(url).netloc} ناموفق بود ({type(e).__name__}). سایت از سرورِ پنل باز می‌شود؟')
        text = r.text
        try:
            parsed = r.json() if text.strip() else None
            is_json = True
        except ValueError:
            parsed, is_json = None, False
        if r.ok and (is_json or raw):
            if switched:
                cache.set(_route_key(site), 1, 86400)
            return {'data': parsed if is_json else text, 'status': r.status_code,
                    'total': int(r.headers.get('x-wp-total') or 0) or None,
                    'pages': int(r.headers.get('x-wp-totalpages') or 0) or None}
        # پاسخِ HTML از /wp-json/ → فایروال یا پیوندِ یکتای ساده؛ یک بار با ?rest_route= امتحان کن
        if not is_json and not use_route and not tried_route and not re.match(r'^https?://', str(path)):
            use_route = tried_route = switched = True
            continue
        break
    if r.ok:
        raise WPError(f'پاسخِ JSON نبود ({r.status_code}): {_strip(text)[:200]}', r.status_code)
    server = r.headers.get('server', '')
    if is_json and isinstance(parsed, dict):
        msg = f"{parsed.get('code', '')} {htmlmod.unescape(str(parsed.get('message', '')))}".strip()
    else:
        msg = f'صفحهٔ «{_strip(text)[:80] or r.reason}»' + (f' از سرورِ {server}' if server else '')
    hint = ''
    if r.status_code == 401:
        hint = ' ← نامِ کاربری/رمزِ برنامه (Application Password) را چک کن؛ اگر درست است، هاست هدرِ Authorization را حذف می‌کند.'
    elif r.status_code == 403 and not is_json:
        hint = ' ← فایروالِ هاست یا افزونهٔ امنیتی بسته (احتمالاً IPِ سرورِ پنل را). در افزونهٔ امنیتی REST را باز کن یا IPِ پنل را مجاز کن.'
    elif r.status_code == 403:
        hint = ' ← این کاربر دسترسیِ کافی ندارد (نقشِ «مدیر» لازم است).'
    elif r.status_code == 404:
        hint = ' ← مسیر وجود ندارد (افزونه/نوعِ محتوا فعال نیست؟).'
    raise WPError(f'WordPress {r.status_code}: {msg}{hint}', r.status_code, parsed)


# ───────────── MCPِ سایت (Novamira) ─────────────
PROTO = '2025-06-18'


def _mcp_post(site, path, msg, sid=None, use_route=False):
    url, extra = _build_url(site, path, use_route)
    h = {'User-Agent': UA, 'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json',
         'MCP-Protocol-Version': PROTO}
    a = _auth(site)
    if a:
        h['Authorization'] = a
    if sid:
        h['Mcp-Session-Id'] = sid
    try:
        r = requests.post(url, params=extra, data=json.dumps(msg, ensure_ascii=False).encode(), headers=h, timeout=120)
    except requests.RequestException as e:
        raise WPError(f'اتصال به MCPِ سایت ناموفق ({type(e).__name__}).')
    return r


def _mcp_parse(r, want_id):
    ct = r.headers.get('content-type', '')
    if 'text/event-stream' in ct:
        found = None
        for line in r.text.splitlines():
            if line.startswith('data:'):
                try:
                    m = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if isinstance(m, dict) and m.get('id') == want_id:
                    found = m
        return found
    try:
        m = r.json()
    except ValueError:
        return None
    if isinstance(m, list):
        m = next((x for x in m if x.get('id') == want_id), None)
    return m


def _mcp_paths(site):
    first = (site.mcp_path or 'mcp/novamira').strip('/')
    return [first] + [p for p in ('mcp/novamira', 'mcp/mcp-adapter-default-server') if p != first]


def _mcp_session(site, fresh=False):
    """(path, use_route, sid) — کش ۲۰ دقیقه. اولین مسیری که initialize را جواب داد برنده است."""
    ck = f'mcpgate:mcpsess:{site.pk}'
    if not fresh and (hit := cache.get(ck)):
        return hit
    errors = []
    for path in _mcp_paths(site):
        for use_route in (False, True):
            r = _mcp_post(site, path, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': PROTO, 'capabilities': {}, 'clientInfo': {'name': 'seo-manager-mcpgate', 'version': '1.0'}}},
                use_route=use_route)
            m = _mcp_parse(r, 1) if r.ok else None
            if m and 'result' in m:
                sid = r.headers.get('mcp-session-id')
                _mcp_post(site, path, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, sid, use_route)
                if path != (site.mcp_path or '').strip('/'):
                    type(site).objects.filter(pk=site.pk).update(mcp_path=path)
                    site.mcp_path = path
                out = (path, use_route, sid)
                cache.set(ck, out, 1200)
                return out
            errors.append(f'{path}{" (rest_route)" if use_route else ""} → {r.status_code} {_strip(r.text)[:120]}')
            if r.status_code == 401:
                raise WPError('MCPِ سایت 401 داد ← رمزِ برنامه/نامِ کاربری را چک کن. ' + errors[-1], 401)
    raise WPError('MCPِ سایت پیدا نشد. افزونهٔ Novamira نصب و «AI abilities» در Novamira → Configuration روشن است؟ '
                  + ' | '.join(errors[:4]))


def mcp(site, method, params=None):
    """یک درخواستِ MCP به سایت (tools/list، tools/call و…). نتیجهٔ `result` را برمی‌گرداند."""
    for attempt in range(2):
        path, use_route, sid = _mcp_session(site, fresh=attempt > 0)
        r = _mcp_post(site, path, {'jsonrpc': '2.0', 'id': 2, 'method': method, 'params': params or {}}, sid, use_route)
        if r.status_code in (400, 404) and sid and attempt == 0:
            continue  # سشن منقضی شده
        m = _mcp_parse(r, 2)
        if m is None:
            raise WPError(f'پاسخِ نامعتبر از MCPِ سایت ({r.status_code}): {_strip(r.text)[:300]}', r.status_code)
        if 'error' in m:
            raise WPError(f"MCPِ سایت: {m['error'].get('message')}", r.status_code, m['error'])
        return m.get('result')
    raise WPError('سشنِ MCPِ سایت برقرار نشد.')


# ───────────── کشف ─────────────
def discover(site):
    ck = f'mcpgate:disc:{site.pk}'
    if hit := cache.get(ck):
        return hit

    def safe(path, query=None):
        try:
            return request(site, path, query=query)['data'] or {}
        except WPError:
            return {}
    types, taxes, root = safe('wp/v2/types'), safe('wp/v2/taxonomies'), safe('', {'_fields': 'name,namespaces'})
    ns = root.get('namespaces', []) if isinstance(root, dict) else []
    st = {
        'types': {k: v['rest_base'] for k, v in (types or {}).items() if isinstance(v, dict) and v.get('rest_base')},
        'taxes': {k: v['rest_base'] for k, v in (taxes or {}).items() if isinstance(v, dict) and v.get('rest_base')},
        'namespaces': ns, 'name': root.get('name') if isinstance(root, dict) else '',
        'woo': 'wc/v3' in ns,
        'seo': 'rankmath' if any(n.startswith('rankmath') for n in ns) else 'yoast' if any(n.startswith('yoast') for n in ns) else '',
        'novamira': any(n.startswith('mcp') or 'novamira' in n for n in ns),
    }
    cache.set(ck, st, 1800)
    return st


TYPE_ALIAS = {'posts': 'post', 'pages': 'page', 'products': 'product', 'article': 'post', 'مقاله': 'post', 'برگه': 'page',
              'صفحه': 'page', 'محصول': 'product'}
TAX_ALIAS = {'categories': 'category', 'دسته': 'category', 'tag': 'post_tag', 'tags': 'post_tag', 'product-category': 'product_cat',
             'product_category': 'product_cat', 'دسته محصول': 'product_cat', 'دسته‌بندی محصول': 'product_cat'}


def post_base(site, t='post'):
    st = discover(site)
    t = TYPE_ALIAS.get(t, t)
    if t in st['types']:
        return t, 'wp/v2/' + st['types'][t], False
    for k, b in st['types'].items():
        if b == t:
            return k, 'wp/v2/' + b, False
    if t == 'product' and st['woo']:
        return 'product', 'wc/v3/products', True
    if t in ('post', 'page'):
        return t, f'wp/v2/{t}s', False
    raise WPError(f"نوعِ محتوای «{t}» در REST این سایت نیست. موجود: {', '.join(st['types'])}")


def tax_base(site, t='category'):
    st = discover(site)
    t = TAX_ALIAS.get(t, t)
    if t in st['taxes']:
        return t, 'wp/v2/' + st['taxes'][t], False
    if t == 'product_cat' and st['woo']:
        return t, 'wc/v3/products/categories', True
    if t == 'product_tag' and st['woo']:
        return t, 'wc/v3/products/tags', True
    if t == 'category':
        return t, 'wp/v2/categories', False
    raise WPError(f"طبقه‌بندیِ «{t}» در REST این سایت نیست. موجود: {', '.join(st['taxes'])}")


def is_taxonomy(t):
    return t in TAX_ALIAS or TAX_ALIAS.get(t) or bool(re.search(r'cat|tag|tax', t or '', re.I)) or t in ('category', 'post_tag')


# ───────────── متن ─────────────
def html_to_text(h):
    h = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', h or '')
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|table|blockquote)>', '\n', h)
    h = re.sub(r'(?i)<h([1-6])[^>]*>', lambda m: '\n' + '#' * int(m.group(1)) + ' ', h)
    h = re.sub(r'(?i)<li[^>]*>', '- ', h)
    t = htmlmod.unescape(re.sub(r'<[^>]+>', '', h))
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', t)).strip()


def word_count(text):
    return len(re.findall(r'\S+', text or ''))


def looks_like_html(s):
    return bool(re.search(r'<(p|h[1-6]|ul|ol|div|table|img|a|strong|br|figure|section|span)\b', s or '', re.I))


def _inline(s):
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)', r'<img src="\2" alt="\1" />', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', s)


def markdown_to_html(md):
    lines, out, i = str(md or '').replace('\r\n', '\n').split('\n'), [], 0
    ul, ol = re.compile(r'^\s*[-*+]\s+'), re.compile(r'^\s*[0-9۰-۹]+[.)]\s+')
    sep = re.compile(r'^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$')
    cells = lambda l: [_inline(c.strip()) for c in l.strip().strip('|').split('|')]  # noqa: E731
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if m := re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line):
            n = len(m.group(1))
            out.append(f'<h{n}>{_inline(m.group(2))}</h{n}>')
            i += 1
            continue
        if line.lstrip().startswith('<'):
            buf = []
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i])
                i += 1
            out.append('\n'.join(buf))
            continue
        if line.strip().startswith('|') and i + 1 < len(lines) and sep.match(lines[i + 1]):
            head, i, rows = cells(line), i + 2, []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(cells(lines[i]))
                i += 1
            out.append('<table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in head) + '</tr></thead><tbody>'
                       + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>')
            continue
        if ul.match(line) or ol.match(line):
            tag, rx, items = ('ol', ol, []) if ol.match(line) else ('ul', ul, [])
            while i < len(lines) and rx.match(lines[i]):
                items.append(f'<li>{_inline(rx.sub("", lines[i], 1))}</li>')
                i += 1
            out.append(f'<{tag}>{"".join(items)}</{tag}>')
            continue
        if re.match(r'^\s*>\s?', line):
            buf = []
            while i < len(lines) and re.match(r'^\s*>\s?', lines[i]):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            out.append(f'<blockquote><p>{_inline(" ".join(buf))}</p></blockquote>')
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|\s*[-*+]\s|\s*[0-9۰-۹]+[.)]\s|\s*>|\s*<|\s*\|)', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if not buf:
            buf.append(lines[i].strip())
            i += 1
        out.append(f'<p>{_inline(" ".join(buf))}</p>')
    return '\n'.join(out)


def prepare_html(content, fmt='auto'):
    if content is None:
        return None
    h = str(content) if fmt == 'html' or (fmt == 'auto' and looks_like_html(content)) else markdown_to_html(content)
    h = re.sub(r'(?is)^\s*<h1\b[^>]*>.*?</h1>\s*', '', h)  # عنوان خودش H1 است
    return re.sub(r'(?i)<(/?)h1\b', r'<\1h2', h)


# ───────────── رسانه ─────────────
MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif',
        '.avif': 'image/avif', '.svg': 'image/svg+xml', '.pdf': 'application/pdf', '.mp4': 'video/mp4', '.zip': 'application/zip'}


def upload_media(site, source=None, data_base64=None, filename=None, alt='', title='', caption=''):
    if data_base64:
        buf = base64.b64decode(data_base64.split(',', 1)[-1])
        name = filename or 'file.jpg'
    elif source and re.match(r'^https?://', source, re.I):
        try:
            r = requests.get(source, headers={'User-Agent': UA}, timeout=60)
        except requests.RequestException as e:
            raise WPError(f'دانلودِ فایل ناموفق: {e}')
        if not r.ok:
            raise WPError(f'دانلودِ فایل ناموفق ({r.status_code}): {source}')
        buf = r.content
        name = filename or (urlparse(source).path.rsplit('/', 1)[-1] or 'image')
        if '.' not in name:
            ct = r.headers.get('content-type', '').split(';')[0]
            name += next((e for e, m in MIME.items() if m == ct), '.jpg')
    else:
        raise WPError('source (آدرسِ http) یا data_base64 لازم است.')
    ext = ('.' + name.rsplit('.', 1)[-1].lower()) if '.' in name else '.jpg'
    mime = MIME.get(ext, 'application/octet-stream')
    ascii_name = re.sub(r'[^\w.-]+', '-', name).strip('-') or f'file{ext}'
    from urllib.parse import quote
    r = request(site, 'wp/v2/media', 'POST', body=buf, timeout=180, headers={
        'Content-Type': mime, 'Content-Disposition': f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(name)}'})
    media = r['data']
    upd = {k: v for k, v in (('alt_text', alt), ('title', title), ('caption', caption)) if v}
    if upd:
        try:
            request(site, f"wp/v2/media/{media['id']}", 'POST', body=upd)
        except WPError:
            pass
    return {'id': media['id'], 'url': media.get('source_url'), 'alt': alt}


# ───────────── طبقه‌بندی و سئو ─────────────
def resolve_terms(site, taxonomy, values, warnings):
    if not values:
        return None
    _, base, wc = tax_base(site, taxonomy)
    ids = []
    for v in values:
        if re.fullmatch(r'\d+', str(v)):
            ids.append(int(v))
            continue
        try:
            found = request(site, base, query={'search': v, 'per_page': 20})['data'] or []
        except WPError:
            found = []
        hit = next((t for t in found if htmlmod.unescape(t.get('name', '')).strip() == str(v).strip()), None)
        if hit:
            ids.append(hit['id'])
            continue
        try:
            ids.append(request(site, base, 'POST', body={'name': v})['data']['id'])
            warnings.append(f'«{v}» در {taxonomy} ساخته شد.')
        except WPError as e:
            warnings.append(f'«{v}» پیدا/ساخته نشد: {e}')
    return [{'id': i} for i in ids] if wc else ids


SEO_KEYS = {
    'rankmath': {'title': 'rank_math_title', 'description': 'rank_math_description', 'focus_keyword': 'rank_math_focus_keyword'},
    'yoast': {'title': '_yoast_wpseo_title', 'description': '_yoast_wpseo_metadesc', 'focus_keyword': '_yoast_wpseo_focuskw'},
}


def set_seo(site, object_type, oid, seo, rest_path):
    if not seo or not any(seo.get(k) for k in ('title', 'description', 'focus_keyword')):
        return None
    plugin = discover(site)['seo'] or 'rankmath'
    meta = {mk: seo[k] for k, mk in SEO_KEYS[plugin].items() if seo.get(k)}
    tried = []
    if plugin == 'rankmath':
        try:
            request(site, 'rankmath/v1/updateMeta', 'POST', body={'objectType': object_type, 'objectID': oid, 'meta': meta})
            return {'ok': True, 'plugin': plugin, 'via': 'rankmath/v1/updateMeta', 'meta': meta}
        except WPError as e:
            tried.append(f'rankmath/v1/updateMeta → {e}')
    if rest_path and not rest_path.startswith('wc/'):
        try:
            saved = (request(site, f'{rest_path}/{oid}', 'POST', body={'meta': meta},
                             query={'context': 'edit', '_fields': 'meta'})['data'] or {}).get('meta') or {}
            if all(saved.get(k) == v for k, v in meta.items()):
                return {'ok': True, 'plugin': plugin, 'via': 'meta', 'meta': meta}
            tried.append('meta → فیلدها در REST ثبت نشده‌اند')
        except WPError as e:
            tried.append(f'meta → {e}')
    return {'ok': False, 'plugin': plugin, 'meta': meta, 'tried': tried,
            'note': 'سئو خودکار ثبت نشد؛ با wp_api یا site_call (Novamira/PHP) امتحان کن.'}
