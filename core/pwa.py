"""PWA — مانیفست + سرویس‌ورکر (سرو از ریشه تا اسکوپش کلِ اپ باشد).

نگه‌داشتِ ساده: کشِ فایل‌های استاتیک (cache-first) + ناوبری network-first با fallbackِ کش.
دادهٔ کاربر کش نمی‌شود (زنده است) — فقط پوسته/استاتیک برای نصب‌پذیری و بارِ سریع‌تر.
"""
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static

CACHE_VERSION = 'seopanel-v2'  # با هر تغییرِ مهمِ استاتیک بالا ببر تا کشِ سرویس‌ورکر پاک شود


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
    css = static('css/style.css')
    vaz = static('vendor/vazirmatn/vazirmatn.css')
    appjs = static('js/app.js')
    ico = static('img/icon-192.png')
    js = f"""
const CACHE = '{CACHE_VERSION}';
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
  if (url.pathname.startsWith('/static/')) {{           // استاتیک: cache-first
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {{
      const cp = res.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return res;
    }})));
    return;
  }}
  if (req.mode === 'navigate') {{                        // صفحات: network-first
    e.respondWith(fetch(req).catch(() => caches.match(req)));
  }}
}});
"""
    resp = HttpResponse(js, content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache'
    return resp
