"""نرمال‌سازیِ نشانی تا لینکِ تسک با صفحهٔ گوگل جور شود: میزبانِ کوچک بدونِ www، مسیرِ decode‌شده بدونِ اسلشِ آخر،
بدونِ پروتکل/کوئری/فرگمنت. `host_of` دامنهٔ property یا پروژه."""
from urllib.parse import unquote, urlsplit


def host_of(v):
    v = str(v or '').strip()
    if v.startswith('sc-domain:'):
        v = v.split(':', 1)[1]
    if '://' not in v:
        v = 'http://' + v
    h = (urlsplit(v).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def page_key(url):
    url = str(url or '').strip()
    if not url:
        return ''
    if '://' not in url:
        url = 'http://' + url
    p = urlsplit(url)
    path = unquote(p.path or '/').rstrip('/') or '/'
    return (host_of(url) + path).lower()[:700]
