"""ابزارهای حسابداری — پارس مبالغ (اعداد فارسی/ویرگول) و ردیف‌های اکسل."""
import re

from core.jalali import parse_jalali, to_en_digits


def parse_amount(value):
    """مبلغ را از متن (فارسی/لاتین، با ویرگول/فاصله/ریال) به عدد صحیح مثبت تبدیل می‌کند."""
    if value is None or value == '':
        return 0
    s = to_en_digits(str(value))
    s = re.sub(r'[^\d.\-]', '', s)  # فقط رقم، نقطه، منفی
    if s in ('', '-', '.', '-.'):
        return 0
    try:
        return int(round(float(s)))
    except ValueError:
        return 0


def parse_excel_date(value):
    """تاریخِ سلول اکسل را به date میلادی تبدیل می‌کند.
    ورودی نمونه: «۱۴۰۵/۰۴/۲۴ | ۱۱:۵۹» یا «1405/04/24» یا datetime.
    برمی‌گرداند (date, time_str)."""
    import datetime as _dt
    if isinstance(value, (_dt.datetime, _dt.date)):
        d = value.date() if isinstance(value, _dt.datetime) else value
        t = value.strftime('%H:%M') if isinstance(value, _dt.datetime) else ''
        return d, t
    s = to_en_digits(str(value)).strip()
    time_str = ''
    # جداسازی ساعت (بعد از | یا فاصله)
    m = re.search(r'(\d{1,2}:\d{2})', s)
    if m:
        time_str = m.group(1)
    m = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', s)
    if not m:
        return None, time_str
    y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        # سال > 1900 = میلادی، وگرنه شمسی
        if y >= 1900:
            return _dt.date(y, mo, dd), time_str
        return parse_jalali(f'{y}/{mo}/{dd}'), time_str
    except (ValueError, TypeError):
        return None, time_str
