"""ابزارهای MCPِ پنل (تعریف + اجرا). هر ابزار `site` می‌گیرد؛ پنل با دسترسیِ ذخیره‌شدهٔ همان سایت درخواست می‌دهد.
بدونِ محدودیت به خواستِ کاربر: `wp_api` هر مسیر/متدِ REST، و `site_tools`/`site_call` همهٔ ابزارهای Novamira
(اجرای PHP، خواندن/نوشتنِ فایل و قالب، المنتور از طریقِ PHP/متا و…).
"""
import html as htmlmod
import json
import re

from . import wp
from .models import MCPSite

S = lambda t, d, **x: {'type': t, 'description': d, **x}  # noqa: E731
SITE = S('string', 'نامِ کوتاهِ سایت یا دامنه (از ابزارِ sites). اگر فقط یک سایت باشد اختیاری است.')


def obj(props, req=()):
    return {'type': 'object', 'properties': props, 'required': list(req)}


SEO = obj({'title': S('string', 'عنوانِ سئو'), 'description': S('string', 'توضیحِ متا'), 'focus_keyword': S('string', 'کلمهٔ کلیدیِ کانونی')})

TOOLS = [
    {'name': 'sites', 'description': 'فهرستِ سایت‌های تعریف‌شده در پنل (نام، آدرس، وضعیتِ اتصال). اولِ کار صدا بزن.',
     'inputSchema': obj({})},
    {'name': 'wp_check', 'description': 'تستِ اتصال به سایت: REST (کاربر/نقش، انواعِ محتوا، ووکامرس، افزونهٔ سئو) + MCPِ Novamira (تعدادِ ابزارها).',
     'inputSchema': obj({'site': SITE})},
    {'name': 'wp_api', 'description': 'درخواستِ آزاد به REST API سایت — هر مسیر و متد، بدونِ محدودیت (مثلاً wp/v2/posts، wc/v3/products، '
     'wp/v2/pages/12 با body={"meta":{...}} برای دادهٔ المنتور _elementor_data، wp/v2/plugins، wp/v2/themes، wp/v2/settings). '
     'برای کم‌مصرف ماندن از query._fields و per_page استفاده کن.',
     'inputSchema': obj({'site': SITE, 'path': S('string', 'مسیر بعد از /wp-json/ (مثلاً wp/v2/posts) یا آدرسِ کامل'),
                         'method': S('string', 'GET | POST | PUT | PATCH | DELETE'), 'query': S('object', 'پارامترهای کوئری'),
                         'body': S('object', 'بدنهٔ JSON'), 'headers': S('object', 'هدرهای اضافه')}, ['path'])},
    {'name': 'site_tools', 'description': 'فهرستِ ابزارهای MCPِ خودِ سایت (افزونهٔ Novamira: اجرای PHP، خواندن/نوشتن/ویرایش/حذفِ فایل، '
     'فهرستِ پوشه، WP-CLI و…). قبل از site_call صدا بزن تا نام و ورودیِ دقیقِ هر ابزار را ببینی.',
     'inputSchema': obj({'site': SITE})},
    {'name': 'site_call', 'description': 'اجرای یک ابزارِ MCPِ سایت (Novamira) — بدونِ محدودیت: اجرای کدِ PHP، ویرایشِ فایل‌های قالب/افزونه، '
     'مدیریتِ المنتور، کوئریِ دیتابیس و… . نام و arguments را دقیقاً مطابقِ خروجیِ site_tools بفرست.',
     'inputSchema': obj({'site': SITE, 'tool': S('string', 'نامِ ابزار از site_tools'), 'arguments': S('object', 'ورودی‌های ابزار')}, ['tool'])},
    {'name': 'wp_find', 'description': 'جست‌وجو در سایت (نوشته/برگه/محصول یا دسته‌ها) → id, type, title, url.',
     'inputSchema': obj({'site': SITE, 'query': S('string', 'عبارت'), 'kind': S('string', 'any | post | term'),
                         'limit': S('integer', 'پیش‌فرض ۱۰')}, ['query'])},
    {'name': 'wp_get', 'description': 'خواندنِ یک نوشته/برگه/محصول یا دسته. format: text (پیش‌فرض) | html | none.',
     'inputSchema': obj({'site': SITE, 'type': S('string', 'post | page | product | category | product_cat | …'),
                         'id': S('integer', 'شناسه'), 'format': S('string', 'text | html | none'),
                         'max_chars': S('integer', 'سقفِ طول (پیش‌فرض ۲۰۰۰۰)')}, ['type', 'id'])},
    {'name': 'wp_save_post', 'description': 'ساخت/ویرایشِ نوشته، برگه یا محصول (پیش‌فرض پیش‌نویس). content: Markdown یا HTML. '
     'categories/tags با id یا نام (نامِ ناموجود ساخته می‌شود). featured_image: id رسانه یا URL. نسخهٔ قبلی در لاگِ پنل ذخیره می‌شود.',
     'inputSchema': obj({'site': SITE, 'type': S('string', 'post (پیش‌فرض) | page | product'), 'id': S('integer', 'برای ویرایش'),
                         'title': S('string', 'عنوان'), 'content': S('string', 'متن (Markdown یا HTML)'),
                         'content_format': S('string', 'auto | markdown | html'), 'excerpt': S('string', 'خلاصه'),
                         'status': S('string', 'draft (پیش‌فرض) | pending | publish | private | future'), 'slug': S('string', 'نامک'),
                         'categories': S('array', 'id یا نام', items={'type': 'string'}), 'tags': S('array', 'id یا نام', items={'type': 'string'}),
                         'featured_image': S('string', 'id رسانه یا URL'), 'featured_alt': S('string', 'alt'),
                         'seo': SEO, 'parent': S('integer', 'والد'), 'date': S('string', 'تاریخِ ISO'),
                         'fields': S('object', 'هر فیلدِ RESTِ دیگر (meta، regular_price و…)')})},
    {'name': 'wp_save_term', 'description': 'ساخت/ویرایشِ دسته/برچسب (پیش‌فرض دستهٔ محصول product_cat) — مثلاً متنِ توضیحاتِ دسته.',
     'inputSchema': obj({'site': SITE, 'taxonomy': S('string', 'product_cat (پیش‌فرض) | category | post_tag | …'),
                         'id': S('integer', 'برای ویرایش'), 'name': S('string', 'نام'), 'slug': S('string', 'نامک'),
                         'parent': S('integer', 'والد'), 'description': S('string', 'توضیحات (Markdown یا HTML)'),
                         'description_format': S('string', 'auto | markdown | html'), 'seo': SEO, 'fields': S('object', 'فیلدهای دیگر')})},
    {'name': 'wp_upload_media', 'description': 'آپلودِ عکس/فایل به کتابخانهٔ رسانه از URL یا base64 → id و آدرس.',
     'inputSchema': obj({'site': SITE, 'source': S('string', 'آدرسِ http فایل'), 'data_base64': S('string', 'محتوای base64 (به‌جای source)'),
                         'filename': S('string', 'نامِ فایل'), 'alt': S('string', 'alt'), 'title': S('string', 'عنوان')})},
    {'name': 'wp_internal_links', 'description': 'پیشنهادِ لینکِ داخلی: برای هر عبارت، مطالب/برگه‌ها/محصولات/دسته‌های مرتبطِ منتشرشده.',
     'inputSchema': obj({'site': SITE, 'keywords': S('array', 'عبارت‌ها', items={'type': 'string'}),
                         'limit': S('integer', 'برای هر عبارت (پیش‌فرض ۵)')}, ['keywords'])},
]

INSTRUCTIONS = ('پنلِ seo-manager واسطِ اتصال به سایت‌های وردپرسی است؛ همهٔ درخواست‌ها از سرورِ پنل به سایت می‌روند. '
                'شروع: sites. برای محتوا wp_* ، برای هر کارِ دیگری در REST از wp_api، و برای PHP/فایل/قالب/المنتور از '
                'site_tools → site_call (افزونهٔ Novamira) استفاده کن.')


class ToolError(Exception):
    pass


def get_site(org, name):
    qs = MCPSite.objects.filter(organization=org)
    active = list(qs.filter(active=True))
    if not name:
        if len(active) == 1:
            return active[0]
        raise ToolError('سایت را مشخص کن (site). موجود: ' + ('، '.join(s.key for s in active) or '— (در پنل سایت اضافه کن)'))
    n = str(name).strip().lower()
    host = re.sub(r'^(https?://)?(www\.)?', '', n).split('/')[0]
    for s in qs:
        sh = re.sub(r'^(https?://)?(www\.)?', '', s.url.lower()).split('/')[0]
        if s.key.lower() == n or sh == host or sh.split('.')[0] == host.split('.')[0]:
            if not s.active:
                raise ToolError(f'سایتِ «{s.key}» در پنل غیرفعال است.')
            return s
    for s in active:
        if n in s.key.lower() or n in s.url.lower():
            return s
    raise ToolError(f'سایتِ «{name}» تعریف نشده. موجود: ' + '، '.join(f'{s.key} ({s.url})' for s in active))


def _fmt(h, fmt, mx):
    if fmt == 'none':
        return None
    out = h if fmt == 'html' else wp.html_to_text(h)
    return out if len(out) <= mx else out[:mx] + '…'


def run(org, name, a, log):
    """اجرای یک ابزار. `log` = دیکشنری‌ای که site/summary/backup را برای MCPLog پر می‌کند."""
    if name == 'sites':
        return [{'site': s.key, 'url': s.url, 'active': s.active, 'has_credentials': bool(s.wp_user and s.password_enc),
                 'notes': s.notes or None} for s in MCPSite.objects.filter(organization=org)]
    site = get_site(org, a.get('site'))
    log['site'] = site.key

    if name == 'wp_check':
        return check(site)

    if name == 'wp_api':
        method = (a.get('method') or 'GET').upper()
        log['summary'] = f"{method} {a.get('path')}"[:300]
        r = wp.request(site, a['path'], method, query=a.get('query'), body=a.get('body'), headers=a.get('headers'), raw=True)
        data = r['data']
        if isinstance(data, list):
            for x in data:
                if isinstance(x, dict):
                    x.pop('_links', None)
        elif isinstance(data, dict):
            data.pop('_links', None)
        return {'status': r['status'], 'total': r['total'], 'pages': r['pages'], 'data': data}

    if name == 'site_tools':
        res = wp.mcp(site, 'tools/list') or {}
        return [{'name': t.get('name'), 'description': (t.get('description') or '')[:600], 'inputSchema': t.get('inputSchema')}
                for t in res.get('tools', [])]

    if name == 'site_call':
        log['summary'] = str(a.get('tool'))[:300]
        res = wp.mcp(site, 'tools/call', {'name': a['tool'], 'arguments': a.get('arguments') or {}}) or {}
        return {'_mcp': res}  # محتوای MCPِ سایت عیناً برگردانده می‌شود

    if name == 'wp_find':
        kinds = ['post', 'term'] if (a.get('kind') or 'any') == 'any' else [a['kind']]
        out = []
        for k in kinds:
            try:
                rows = wp.request(site, 'wp/v2/search', query={'search': a['query'], 'type': k, 'per_page': min(int(a.get('limit') or 10), 100),
                                                               '_fields': 'id,title,url,type,subtype'})['data'] or []
            except wp.WPError:
                rows = []
            out += [{'id': x['id'], 'type': x.get('subtype'), 'title': htmlmod.unescape(x.get('title') or ''), 'url': x.get('url')} for x in rows]
        return out

    if name == 'wp_get':
        t, fmt, mx = a.get('type') or 'post', a.get('format') or 'text', int(a.get('max_chars') or 20000)
        if wp.is_taxonomy(t):
            tax, base, wc = wp.tax_base(site, t)
            x = wp.request(site, f"{base}/{a['id']}", query={} if wc else {'context': 'edit'})['data']
            return {'id': x['id'], 'taxonomy': tax, 'name': htmlmod.unescape(x.get('name', '')), 'slug': x.get('slug'),
                    'link': x.get('link') or x.get('permalink'), 'parent': x.get('parent'), 'count': x.get('count'),
                    'description': _fmt(x.get('description') or '', fmt, mx)}
        kind, base, wc = wp.post_base(site, t)
        try:
            p = wp.request(site, f"{base}/{a['id']}", query={} if wc else {'context': 'edit'})['data']
        except wp.WPError as e:
            if e.status not in (401, 403):
                raise
            p = wp.request(site, f"{base}/{a['id']}")['data']
        if wc:
            return {'id': p['id'], 'type': 'product', 'name': p.get('name'), 'status': p.get('status'), 'link': p.get('permalink'),
                    'price': p.get('price'), 'sku': p.get('sku'), 'categories': [{'id': c['id'], 'name': c['name']} for c in p.get('categories', [])],
                    'short_description': _fmt(p.get('short_description') or '', 'text', 2000), 'description': _fmt(p.get('description') or '', fmt, mx)}
        h = (p.get('content') or {}).get('raw') or (p.get('content') or {}).get('rendered') or ''
        meta = {k: v for k, v in (p.get('meta') or {}).items()
                if v and re.search(r'rank_math_(title|description|focus_keyword)|_yoast_wpseo_(title|metadesc|focuskw)', k)}
        return {'id': p['id'], 'type': kind, 'title': htmlmod.unescape((p.get('title') or {}).get('raw') or (p.get('title') or {}).get('rendered') or ''),
                'status': p.get('status'), 'slug': p.get('slug'), 'link': p.get('link'), 'modified': p.get('modified'),
                'categories': p.get('categories'), 'tags': p.get('tags'), 'featured_media': p.get('featured_media'),
                'template': p.get('template') or None, 'words': wp.word_count(wp.html_to_text(h)), 'seo_meta': meta or None,
                'content': _fmt(h, fmt, mx)}

    if name == 'wp_save_post':
        return save_post(site, a, log)

    if name == 'wp_save_term':
        tax, base, wc = wp.tax_base(site, a.get('taxonomy') or 'product_cat')
        if a.get('id'):
            log['backup'] = wp.request(site, f"{base}/{a['id']}", query={} if wc else {'context': 'edit'})['data']
        body = {'name': a.get('name'), 'slug': a.get('slug'), 'parent': a.get('parent'),
                'description': wp.prepare_html(a.get('description'), a.get('description_format') or 'auto'), **(a.get('fields') or {})}
        body = {k: v for k, v in body.items() if v is not None}
        r = wp.request(site, f"{base}/{a['id']}" if a.get('id') else base, 'PUT' if a.get('id') else 'POST', body=body)['data']
        log['summary'] = f"{tax} #{r['id']}"
        seo = wp.set_seo(site, 'term', r['id'], a.get('seo'), None if wc else base)
        return {'id': r['id'], 'taxonomy': tax, 'name': htmlmod.unescape(r.get('name', '')), 'link': r.get('link') or r.get('permalink'),
                'edit': f"{site.url.rstrip('/')}/wp-admin/term.php?taxonomy={tax}&tag_ID={r['id']}", 'seo': seo}

    if name == 'wp_upload_media':
        log['summary'] = (a.get('filename') or a.get('source') or '')[:300]
        return wp.upload_media(site, a.get('source'), a.get('data_base64'), a.get('filename'), a.get('alt') or '', a.get('title') or '')

    if name == 'wp_internal_links':
        out = []
        for kw in a.get('keywords') or []:
            links = []
            for k in ('post', 'term'):
                try:
                    rows = wp.request(site, 'wp/v2/search', query={'search': kw, 'type': k, 'per_page': int(a.get('limit') or 5),
                                                                   '_fields': 'id,title,url,subtype'})['data'] or []
                except wp.WPError:
                    rows = []
                links += [{'id': x['id'], 'k': x.get('subtype'), 't': htmlmod.unescape(x.get('title') or ''), 'u': x.get('url')} for x in rows]
            out.append({'keyword': kw, 'links': links[:int(a.get('limit') or 5) * 2]})
        return out

    raise ToolError(f'ابزارِ ناشناخته: {name}')


def check(site):
    out = {'site': site.key, 'url': site.url}
    if not (site.wp_user and site.password):
        out['rest'] = {'ok': False, 'error': 'نامِ کاربری یا رمزِ برنامه خالی است.'}
    else:
        try:
            try:
                me = wp.request(site, 'wp/v2/users/me', query={'context': 'edit', '_fields': 'id,name,roles'})['data']
            except wp.WPError as e:
                if e.status == 401:
                    raise
                wp.request(site, 'wp/v2/posts', query={'context': 'edit', 'per_page': 1, '_fields': 'id'})
                me = {'name': site.wp_user, 'roles': ['?']}
            st = wp.discover(site)
            out['rest'] = {'ok': True, 'user': me.get('name'), 'roles': me.get('roles'), 'site_name': st['name'],
                           'woocommerce': st['woo'], 'seo_plugin': st['seo'] or 'none', 'post_types': list(st['types'])}
        except wp.WPError as e:
            out['rest'] = {'ok': False, 'error': str(e)}
    try:
        tools = (wp.mcp(site, 'tools/list') or {}).get('tools', [])
        out['novamira'] = {'ok': True, 'path': site.mcp_path, 'tools': len(tools), 'names': [t.get('name') for t in tools][:30]}
    except wp.WPError as e:
        out['novamira'] = {'ok': False, 'error': str(e)[:400]}
    out['ok'] = out['rest'].get('ok', False)
    return out


def save_post(site, a, log):
    kind, base, wc = wp.post_base(site, a.get('type') or 'post')
    warnings = []
    content = wp.prepare_html(a.get('content'), a.get('content_format') or 'auto')
    featured = None
    fi = a.get('featured_image')
    if fi not in (None, '', 'none'):
        if re.fullmatch(r'\d+', str(fi)):
            featured = {'id': int(fi)}
        else:
            try:
                featured = wp.upload_media(site, fi, alt=a.get('featured_alt') or a.get('title') or '')
            except wp.WPError as e:
                warnings.append(f'تصویرِ شاخص: {e}')
    old = None
    if a.get('id'):
        old = wp.request(site, f"{base}/{a['id']}", query={} if wc else {'context': 'edit'})['data']
        log['backup'] = old
    status = a.get('status') or (None if a.get('id') else 'draft')
    if wc:
        body = {'name': a.get('title'), 'description': content, 'short_description': wp.prepare_html(a.get('excerpt')),
                'slug': a.get('slug'), 'status': status,
                'categories': wp.resolve_terms(site, 'product_cat', a.get('categories'), warnings),
                'tags': wp.resolve_terms(site, 'product_tag', a.get('tags'), warnings)}
        if featured:
            body['images'] = [{'id': featured['id']}] + [{'id': i['id']} for i in (old or {}).get('images', [])[1:]]
    else:
        body = {'title': a.get('title'), 'content': content, 'excerpt': wp.html_to_text(wp.prepare_html(a.get('excerpt')) or '') or None,
                'slug': a.get('slug'), 'status': status, 'featured_media': featured and featured['id'],
                'categories': wp.resolve_terms(site, 'category', a.get('categories'), warnings) if kind == 'post' else None,
                'tags': wp.resolve_terms(site, 'post_tag', a.get('tags'), warnings) if kind == 'post' else None,
                'parent': a.get('parent'), 'date': a.get('date')}
    body.update(a.get('fields') or {})
    body = {k: v for k, v in body.items() if v is not None}
    r = wp.request(site, f"{base}/{a['id']}" if a.get('id') else base, 'PUT' if a.get('id') else 'POST', body=body)['data']
    log['summary'] = f"{kind} #{r['id']} {'ویرایش' if a.get('id') else 'جدید'}"
    seo = wp.set_seo(site, 'post', r['id'], a.get('seo'), base)
    link = r.get('link') or r.get('permalink')
    root = site.url.rstrip('/')
    return {'id': r['id'], 'type': kind, 'status': r.get('status'), 'link': link,
            'preview': link if r.get('status') == 'publish' else f"{root}/?p={r['id']}&preview=true",
            'edit': f"{root}/wp-admin/post.php?post={r['id']}&action=edit",
            'words': wp.word_count(wp.html_to_text(content or '')), 'featured': featured, 'seo': seo, 'warnings': warnings or None}


def to_content(out, max_chars=60000):
    """خروجیِ ابزار → محتوای MCP. خروجیِ site_call (MCPِ سایت) عیناً پاس داده می‌شود."""
    if isinstance(out, dict) and '_mcp' in out:
        res = out['_mcp']
        if isinstance(res, dict) and 'content' in res:
            return res
        return {'content': [{'type': 'text', 'text': json.dumps(res, ensure_ascii=False)[:max_chars]}]}
    text = json.dumps(out, ensure_ascii=False, default=str, separators=(',', ':'))
    if len(text) > max_chars:
        text = text[:max_chars] + f'… [بریده شد؛ کلِ خروجی {len(text)} نویسه — با _fields/per_page/max_chars کمترش کن]'
    return {'content': [{'type': 'text', 'text': text}]}
