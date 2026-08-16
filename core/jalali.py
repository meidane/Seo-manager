"""ابزار تاریخ شمسی — تبدیل بین میلادی و شمسی، فقط برای لایه‌ی نمایش/ورودی.

هیچ تاریخی در دیتابیس شمسی نیست؛ این توابع صرفاً برای نمایش و پارس ورودی
کاربر به کار می‌روند.
"""
from datetime import date

import jdatetime

# نام روزهای هفته به فارسی (شنبه = ۰ در تقویم شمسی)
WEEKDAY_NAMES = ['شنبه', 'یک‌شنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
MONTH_NAMES = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

# ارقام فارسی برای نمایش
_FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
_EN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def to_fa_digits(value) -> str:
    """تبدیل ارقام لاتین به فارسی برای نمایش."""
    return str(value).translate(_FA_DIGITS)


def to_en_digits(value) -> str:
    """تبدیل ارقام فارسی به لاتین برای پردازش ورودی."""
    return str(value).translate(_EN_DIGITS)


def g2j(gregorian: date) -> jdatetime.date:
    """میلادی → شمسی."""
    return jdatetime.date.fromgregorian(date=gregorian)


def j2g(year: int, month: int, day: int) -> date:
    """شمسی → میلادی."""
    return jdatetime.date(year, month, day).togregorian()


def format_jalali(gregorian, fmt: str = '%Y/%m/%d', fa_digits: bool = False) -> str:
    """قالب‌بندی یک تاریخ میلادی به رشته‌ی شمسی."""
    if gregorian is None:
        return ''
    if hasattr(gregorian, 'date') and not isinstance(gregorian, date):
        gregorian = gregorian.date()
    jd = g2j(gregorian)
    out = jd.strftime(fmt)
    return to_fa_digits(out) if fa_digits else out


def jalali_long(gregorian, fa_digits: bool = False) -> str:
    """قالب طولانی: «۱۵ مرداد ۱۴۰۵»."""
    if gregorian is None:
        return ''
    if hasattr(gregorian, 'date') and not isinstance(gregorian, date):
        gregorian = gregorian.date()
    jd = g2j(gregorian)
    out = f'{jd.day} {MONTH_NAMES[jd.month - 1]} {jd.year}'
    return to_fa_digits(out) if fa_digits else out


def parse_jalali(value: str) -> date:
    """پارس رشته‌ی شمسی «۱۴۰۵/۰۵/۱۵» یا «1405-05-15» به تاریخ میلادی."""
    value = to_en_digits(value.strip()).replace('-', '/')
    year, month, day = (int(p) for p in value.split('/'))
    return j2g(year, month, day)


def today_jalali() -> jdatetime.date:
    """امروز به شمسی."""
    return jdatetime.date.today()
