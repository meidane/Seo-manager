"""PWA — مانیفست + سرویس‌ورکر (سرو از ریشه تا اسکوپش کلِ اپ باشد).

نگه‌داشتِ ساده: استاتیک با **stale-while-revalidate** (سریع از کش، ولی همیشه در پس‌زمینه
تازه می‌شود) + ناوبری network-first. دادهٔ کاربر کش نمی‌شود.

**چرا مهم است (باگِ کشِ کاربران که آپدیت‌ها را نمی‌دیدند):** نسخهٔ قبلی استاتیک را
cache-first با یک `CACHE_VERSION` ثابت نگه می‌داشت؛ یعنی وقتی مرورگرِ کاربر یک‌بار
`style.css`/`app.js` را کش می‌کرد، سرویس‌ورکر تا ابد همان نسخهٔ قدیمی را می‌داد و چون
نسخهٔ کش هیچ‌وقت عوض نمی‌شد، `activate` هم پاکش نمی‌کرد. حالا:
1. **نسخهٔ کش از محتوای واقعیِ استاتیک مشتق می‌شود** (`_asset_version` = هشِ بایت‌های
   style.css/app.js/tasks.js) — با هر تغییرِ CSS/JS خودکار عوض می‌شود، پس بایت‌های `sw.js`
   عوض می‌شوند، مرورگر سرویس‌ورکرِ جدید را نصب می‌کند و کشِ قدیمی در `activate` پاک می‌شود.
2. استاتیک stale-while-revalidate است، پس حتی اگر لحظه‌ای نسخهٔ قدیمی سرو شد، بارِ بعدی
   تازه است.
3. صفحه با فعال‌شدنِ سرویس‌ورکرِ جدید یک‌بار رفرش می‌شود (`controllerchange` در base.html)
   تا کاربر بدونِ پاک‌کردنِ دستیِ کش، آپدیت را ببیند.
"""
import functools
import hashlib
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static


@functools.lru_cache(maxsize=1)
def _asset_version():
    """هشِ کوتاه از محتوای فایل‌های استاتیکِ پرتغییر — با هر deploy که CSS/JS را عوض کند
    تغییر می‌کند (مستقل از DEBUG/هش‌دارشدنِ نامِ فایل). deploy پروسه را ری‌استارت می‌کند،
    پس lru_cache در تولید همیشه تازه محاسبه می‌شود."""
    h = hashlib.md5()
    for rel in ('css/style.css', 'js/app.js', 'js/tasks.js'):
        for base in settings.STATICFILES_DIRS:
            p = Path(base) / rel
            if p.exists():
                h.update(p.read_bytes())
                break
    return h.hexdigest()[:10] or 'dev'


def manifest(request):
    return JsonResponse({
        'name': 'پنل مدیریت سئو',
        'short_name': 'سئوپنل',
        'description': 'پلتفرم مدیریت پروژه‌های سئو، تسک‌ها، حسابداری و حضورغیاب',
        'lang': 'fa', 'dir': 'rtl',
        'start_url': '/', 'scope': '/',
        'display': 'standalone', 'orientation': 'portrait-primary',
        'background_color': '#070C18', 'theme_color': '#070C18',
        'icons': [
            {'src': static('img/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
            {'src': static('img/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    })


def service_worker(request):
    ver = _asset_version()
    cache = f'seopanel-{ver}'                 # با هر تغییرِ CSS/JS عوض می‌شود
    # css/app.js با همان `?v=` که base.html می‌فرستد تا precacheِ سرویس‌ورکر با درخواستِ
    # صفحه دقیقاً یکی شود (وگرنه کلیدِ کش فرق می‌کرد).
    css = f"{static('css/style.css')}?v={ver}"
    vaz = static('vendor/vazirmatn/vazirmatn.css')
    appjs = f"{static('js/app.js')}?v={ver}"
    ico = static('img/icon-192.png')
    js = f"""
const CACHE = '{cache}';
const ASSETS = ['{css}','{vaz}','{appjs}','{ico}'];
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(ks => Promise.all(
    ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/static/')) {{           // استاتیک: stale-while-revalidate
    e.respondWith(caches.open(CACHE).then(c => c.match(req).then(cached => {{
      const net = fetch(req).then(res => {{ if (res && res.ok) c.put(req, res.clone()); return res; }}).catch(() => cached);
      return cached || net;                              // کش فوری، در پس‌زمینه تازه می‌شود
    }})));
    return;
  }}
  if (req.mode === 'navigate') {{                        // صفحات: network-first (همیشه تازه)
    e.respondWith(fetch(req).catch(() => caches.match(req)));
  }}
}});
"""
    resp = HttpResponse(js, content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    # sw.js هرگز کش نشود تا مرورگر هر بار نسخهٔ جدید را ببیند (کلیدِ به‌روزرسانی)
    resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp
