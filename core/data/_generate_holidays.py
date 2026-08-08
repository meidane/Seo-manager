"""تولید فایل‌های JSON تعطیلات رسمی ایران برای سال‌های شمسی هدف.

- تعطیلات خورشیدی ثابت: هر سال تاریخ یکسان.
- تعطیلات قمری (هجری): با hijridate (تقویم ام‌القری) به میلادی و سپس به شمسی
  تبدیل می‌شوند. ممکن است ±۱ روز با تقویم رسمی رصدیِ ایران تفاوت کند.
"""
import json
import jdatetime
from datetime import date
from hijridate import Hijri, Gregorian

TARGET_YEARS = [1405, 1406, 1407, 1408]

# تقویم رسمیِ رصدیِ ایران معمولاً ۱ روز بعد از ام‌القری (عربستان) است؛ با دو نقطه‌ی
# کالیبراسیون (عاشورا و عید فطر ۱۴۰۴) این اختلاف +۱ روز تأیید شد.
IRAN_OFFSET_DAYS = 1

# ── تعطیلات خورشیدی ثابت (ماه/روز شمسی) ──
SOLAR = [
    (1, 1, 'نوروز'), (1, 2, 'نوروز'), (1, 3, 'نوروز'), (1, 4, 'نوروز'),
    (1, 12, 'روز جمهوری اسلامی ایران'),
    (1, 13, 'روز طبیعت (سیزده‌بدر)'),
    (3, 14, 'رحلت امام خمینی'),
    (3, 15, 'قیام ۱۵ خرداد'),
    (11, 22, 'پیروزی انقلاب اسلامی'),
    (12, 29, 'روز ملی شدن صنعت نفت'),
]

# ── تعطیلات قمری رسمیِ روزِ‌تعطیل (ماه هجری، روز، عنوان) ──
# فقط روزهای «تعطیل رسمی»؛ مناسبت‌های غیرتعطیل (مثل ۱۳ رجب) نمی‌آیند.
LUNAR = [
    (1, 9, 'تاسوعای حسینی'),
    (1, 10, 'عاشورای حسینی'),
    (2, 20, 'اربعین حسینی'),
    (2, 28, 'رحلت پیامبر و شهادت امام حسن مجتبی'),
    (2, 30, 'شهادت امام رضا'),          # آخر صفر؛ اگر ۲۹روزه بود به ۲۹ می‌افتد
    (3, 8, 'شهادت امام حسن عسکری'),
    (3, 17, 'میلاد پیامبر و امام جعفر صادق'),
    (6, 3, 'شهادت حضرت فاطمه زهرا'),
    (7, 27, 'مبعث پیامبر'),
    (8, 15, 'ولادت امام مهدی (نیمه شعبان)'),
    (9, 21, 'شهادت امام علی'),
    (10, 1, 'عید سعید فطر'),
    (10, 25, 'شهادت امام جعفر صادق'),
    (12, 10, 'عید سعید قربان'),
    (12, 18, 'عید سعید غدیر خم'),
]


def hijri_to_greg(hy, hm, hd):
    """هجری قمری → date میلادی؛ روز نامعتبر (مثل ۳۰ در ماه ۲۹روزه) → None."""
    try:
        g = Hijri(hy, hm, hd).to_gregorian()
        return date(g.year, g.month, g.day)
    except (ValueError, OverflowError):
        return None


def jalali_year_of(g: date) -> tuple[int, int, int]:
    j = jdatetime.date.fromgregorian(date=g)
    return j.year, j.month, j.day


def build_year(jyear: int):
    entries = []
    # خورشیدی ثابت
    for m, d, title in SOLAR:
        entries.append({'jm': m, 'jd': d, 'title': title,
                        'kind': 'official', 'is_off': True})

    # قمری: محدوده‌ی هجریِ پوشاننده‌ی سال شمسی را جست‌وجو کن
    # سال شمسی Y تقریباً از هجری (Y-622+? ) ... ساده: چند سال هجری کاندید را امتحان کن
    # اول و آخر سال شمسی به میلادی:
    g_start = jdatetime.date(jyear, 1, 1).togregorian()
    from datetime import timedelta
    g_end = jdatetime.date(jyear + 1, 1, 1).togregorian() - timedelta(days=1)
    h_start = Gregorian(g_start.year, g_start.month, g_start.day).to_hijri()
    h_end = Gregorian(g_end.year, g_end.month, g_end.day).to_hijri()
    hy_candidates = range(h_start.year - 1, h_end.year + 2)

    from datetime import timedelta as _td
    for hm, hd, title in LUNAR:
        for hy in hy_candidates:
            g = hijri_to_greg(hy, hm, hd)
            if g is None and hd == 30:            # ماه ۲۹روزه → آخر ماه = ۲۹
                g = hijri_to_greg(hy, hm, 29)
            if g is None:
                continue
            g = g + _td(days=IRAN_OFFSET_DAYS)    # تصحیح رصدی ایران
            jy, jm, jd = jalali_year_of(g)
            if jy == jyear:
                entries.append({'jm': jm, 'jd': jd, 'title': title,
                                'kind': 'religious', 'is_off': True})

    # مرتب‌سازی بر اساس ماه/روز شمسی؛ اگر دو مناسبت روی یک روز افتادند، عنوان‌ها را
    # با « / » ادغام کن (مثلاً عاشورا که در ۱۴۰۷ با قیام ۱۵ خرداد یکی می‌شود).
    entries.sort(key=lambda e: (e['jm'], e['jd']))
    by_key = {}
    order = []
    for e in entries:
        key = (e['jm'], e['jd'])
        if key not in by_key:
            by_key[key] = {'date': f"{jyear}/{e['jm']:02d}/{e['jd']:02d}",
                           'title': e['title'], 'kind': e['kind'], 'is_off': e['is_off']}
            order.append(key)
        elif e['title'] not in by_key[key]['title']:
            by_key[key]['title'] += ' / ' + e['title']
    return [by_key[k] for k in order]


import os
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
for y in TARGET_YEARS:
    data = build_year(y)
    path = os.path.join(OUT_DIR, f'holidays_{y}.json')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('[\n')
        fh.write(',\n'.join(
            '  ' + json.dumps(e, ensure_ascii=False) for e in data))
        fh.write('\n]\n')
    print(f"{path}  ({len(data)} مورد)")
    for e in data:
        print('  ', e['date'], e['title'])
