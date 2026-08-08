"""بازه‌ی زمانی سراسری — کامپوننتی که در session ذخیره می‌شود و روی همه‌ی
صفحات آماری اثر می‌گذارد.

خواندن بازه از پارامترهای URL (`?range=30` یا `?from=...&to=...`)، ذخیره در
session و ارائه‌ی بازه‌ی قبلی برای مقایسه‌های ▲▼.
"""
from datetime import date, timedelta

from .jalali import format_jalali, parse_jalali

SESSION_KEY = 'date_range'

# پیش‌تنظیم‌های نسبی: کلید → تعداد روز
PRESETS = {
    'today': 0,
    'yesterday': 1,
    '7': 7,
    '30': 30,
    '60': 60,
    '90': 90,
    '365': 365,
}

PRESET_LABELS = {
    'today': 'امروز',
    'yesterday': 'دیروز',
    '7': '۷ روز',
    '30': '۳۰ روز',
    '60': '۶۰ روز',
    '90': '۹۰ روز',
    'this_month': 'این ماه',
    'last_month': 'ماه گذشته',
    '365': 'یک‌ساله',
    'custom': 'دلخواه',
}

DEFAULT_RANGE = 'this_month'


def _resolve_preset(key: str, ref: date) -> tuple[date, date]:
    """تبدیل کلید پیش‌تنظیم به بازه‌ی (شروع، پایان) میلادی."""
    if key == 'today':
        return ref, ref
    if key == 'yesterday':
        y = ref - timedelta(days=1)
        return y, y
    if key == 'this_month':
        from .jalali import g2j, j2g

        jt = g2j(ref)
        start = j2g(jt.year, jt.month, 1)
        return start, ref
    if key == 'last_month':
        from .jalali import g2j, j2g

        jt = g2j(ref)
        year, month = (jt.year, jt.month - 1) if jt.month > 1 else (jt.year - 1, 12)
        start = j2g(year, month, 1)
        # پایان ماه گذشته = یک روز قبل از اول ماه جاری
        this_start = j2g(jt.year, jt.month, 1)
        return start, this_start - timedelta(days=1)
    days = PRESETS.get(key, 30)
    return ref - timedelta(days=days), ref


class DateRangeMixin:
    """میکسین ویو برای مدیریت بازه‌ی زمانی سراسری."""

    #: کلید پیش‌تنظیم فعلی و بازه‌ی محاسبه‌شده، پس از فراخوانی get_range پر می‌شوند
    range_key = DEFAULT_RANGE
    range_start = None
    range_end = None

    def get_range(self, request) -> tuple[date, date]:
        """بازه‌ی فعال را از URL/session می‌خواند و در session ذخیره می‌کند."""
        today = date.today()
        params = request.GET

        # بازه‌ی دلخواه با from/to (شمسی)
        if params.get('from') and params.get('to'):
            try:
                start = parse_jalali(params['from'])
                end = parse_jalali(params['to'])
                self.range_key = 'custom'
                self._store(request, 'custom', start, end)
                self.range_start, self.range_end = start, end
                return start, end
            except (ValueError, TypeError):
                pass

        # پیش‌تنظیم از URL
        key = params.get('range')
        if key and (key in PRESETS or key in ('this_month', 'last_month')):
            start, end = _resolve_preset(key, today)
            self.range_key = key
            self._store(request, key, start, end)
            self.range_start, self.range_end = start, end
            return start, end

        # از session
        stored = request.session.get(SESSION_KEY)
        if stored:
            if stored['key'] == 'custom':
                start = date.fromisoformat(stored['start'])
                end = date.fromisoformat(stored['end'])
            else:
                start, end = _resolve_preset(stored['key'], today)
            self.range_key = stored['key']
            self.range_start, self.range_end = start, end
            return start, end

        # پیش‌فرض
        start, end = _resolve_preset(DEFAULT_RANGE, today)
        self.range_key = DEFAULT_RANGE
        self.range_start, self.range_end = start, end
        return start, end

    def get_previous_range(self) -> tuple[date, date]:
        """بازه‌ی قبلی هم‌طول برای مقایسه‌ی ▲▼."""
        if self.range_start is None or self.range_end is None:
            raise ValueError('ابتدا get_range را صدا بزن.')
        span = (self.range_end - self.range_start).days + 1
        prev_end = self.range_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        return prev_start, prev_end

    @staticmethod
    def _store(request, key, start, end):
        request.session[SESSION_KEY] = {
            'key': key,
            'start': start.isoformat(),
            'end': end.isoformat(),
        }

    def range_context(self) -> dict:
        """داده‌ی بازه برای تمپلیت (برچسب و متن نمایشی)."""
        span = (self.range_end - self.range_start).days + 1
        return {
            'range_key': self.range_key,
            'range_start': self.range_start,
            'range_end': self.range_end,
            'range_label': PRESET_LABELS.get(self.range_key, 'دلخواه'),
            'range_start_fa': format_jalali(self.range_start),
            'range_end_fa': format_jalali(self.range_end),
            'range_days': span,
        }
