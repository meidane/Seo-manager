"""منطق تقویم شمسی — ساخت ماتریس ماه در پایتون (نه JS) تا یک‌جا بماند.

ستون‌ها از راست: شنبه … جمعه. jdatetime.weekday(): شنبه=۰ و جمعه=۶.
"""
from datetime import date

import jdatetime

from core.jalali import MONTH_NAMES, to_fa_digits

JALALI_MONTH_DAYS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]


def days_in_month(jyear: int, jmonth: int) -> int:
    if jmonth <= 6:
        return 31
    if jmonth <= 11:
        return 30
    # اسفند: ۲۹ یا ۳۰ (کبیسه)
    try:
        jdatetime.date(jyear, 12, 30)
        return 30
    except ValueError:
        return 29


def build_month(jyear: int, jmonth: int, tasks_by_date: dict, holiday_map: dict) -> list:
    """فهرست سلول‌های ماه (شامل چند روز از ماه قبل/بعد به‌صورت کم‌رنگ).

    tasks_by_date: {gregorian_date: [task_dict, ...]}
    holiday_map:   {gregorian_date: 'عنوان تعطیلی'}  (فقط تعطیلات is_off)
    """
    first = jdatetime.date(jyear, jmonth, 1)
    lead = first.weekday()  # تعداد خانه‌های خالی قبل از روز ۱ (شنبه=۰)
    dim = days_in_month(jyear, jmonth)
    today_g = date.today()

    cells = []

    # دنباله‌ی ماه قبل (کم‌رنگ)
    if lead:
        prev = first - jdatetime.timedelta(days=lead)
        for i in range(lead):
            d = prev + jdatetime.timedelta(days=i)
            cells.append(_cell(d, True, tasks_by_date, holiday_map, today_g))

    # روزهای ماه جاری
    for day in range(1, dim + 1):
        d = jdatetime.date(jyear, jmonth, day)
        cells.append(_cell(d, False, tasks_by_date, holiday_map, today_g))

    # دنباله‌ی ماه بعد تا کامل شدن هفته (مضرب ۷)
    while len(cells) % 7:
        d = jdatetime.date(jyear, jmonth, dim) + jdatetime.timedelta(days=(len(cells) - lead - dim + 1))
        cells.append(_cell(d, True, tasks_by_date, holiday_map, today_g))

    return cells


def _cell(jd, dim_flag, tasks_by_date, holiday_map, today_g):
    g = jd.togregorian()
    is_friday = jd.weekday() == 6
    holiday_title = holiday_map.get(g)
    return {
        'jday': jd.day,
        'jday_fa': to_fa_digits(jd.day),
        'jdate': jd.strftime('%Y/%m/%d'),  # شمسی لاتین، برای پرکردن فیلد تاریخ مودال
        'gdate': g.isoformat(),
        'dim': dim_flag,
        'is_today': g == today_g,
        'is_friday': is_friday,
        'is_holiday': is_friday or holiday_title is not None,
        'holiday_title': holiday_title or ('' if not is_friday else ''),
        'tasks': tasks_by_date.get(g, []),
    }


def month_title(jyear: int, jmonth: int) -> str:
    return f'{MONTH_NAMES[jmonth - 1]} {to_fa_digits(jyear)}'


def month_bounds_gregorian(jyear: int, jmonth: int):
    """بازه‌ی میلادی متناظر با کل ماه شمسی (برای کوئری تسک‌ها)."""
    start = jdatetime.date(jyear, jmonth, 1).togregorian()
    end = jdatetime.date(jyear, jmonth, days_in_month(jyear, jmonth)).togregorian()
    return start, end
