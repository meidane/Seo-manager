"""کلاینتِ خواندنِ داده‌ی حضورغیاب از پروژه‌ی worktracker (مجزا).

seo-manager با نام‌کاربریِ worktrackerِ هر همکار (`Colleague.worktracker_username`)
داده‌ی حضورش را از APIِ آن پروژه می‌خواند. سرور-به-سرور، توکنِ ثابت.

تنظیمات (env، در `config/settings.py` خوانده می‌شوند):
    WORKTRACKER_BASE_URL   مثل https://team.lomin.co
    WORKTRACKER_API_TOKEN  همان توکنِ سرویسِ سمتِ worktracker

اگر تنظیم نشده یا در دسترس نبود، توابع «خالی/None» برمی‌گردانند (بدونِ خطا) تا UI فقط
بخشِ حضورغیاب را نشان ندهد، نه اینکه صفحه بشکند.
"""
from django.conf import settings

TIMEOUT = 5


def is_configured():
    return bool(getattr(settings, 'WORKTRACKER_BASE_URL', '') and
                getattr(settings, 'WORKTRACKER_API_TOKEN', ''))


def _get(path):
    if not is_configured():
        return None
    import requests
    base = settings.WORKTRACKER_BASE_URL.rstrip('/')
    try:
        r = requests.get(base + path, timeout=TIMEOUT,
                         headers={'Authorization': f'Token {settings.WORKTRACKER_API_TOKEN}'})
        if r.status_code == 200:
            return r.json()
    except Exception:  # noqa: BLE001 — شبکه/تایم‌اوت: بی‌صدا رد شو
        return None
    return None


def today_all():
    """{username: {online, start, end, sum_minutes, sum_words, records, app_records,…}}
    برای همه‌ی کاربرانِ worktracker (لیستِ همکاران/سایدبار). با کشِ ۶۰ثانیه‌ای — چون در
    سایدبار روی هر ریکوئست خوانده می‌شود، نباید هر بار به API بزند."""
    from django.core.cache import cache
    cached = cache.get('wt_today_all')
    if cached is not None:
        return cached
    d = _get('/api/attendance/today/')
    users = (d or {}).get('users', []) if d else []
    result = {u.get('username'): u for u in users}
    cache.set('wt_today_all', result, 60)
    return result


def user_detail(username, days=5):
    """جزئیاتِ چند روزِ اخیرِ یک کاربر (تبِ حضورِ همکار)."""
    if not username:
        return None
    return _get(f'/api/attendance/user/{username}/?days={days}')
