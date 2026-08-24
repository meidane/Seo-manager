"""تمپلیت‌فیلترهای سراسری: jalali، money، timeago، fa_digits."""
from datetime import date, datetime

from django import template
from django.utils import timezone
from django.utils.html import escape, format_html

from core import jalali as j
from core.columns import cell_value

register = template.Library()


@register.filter(name='jalali')
def jalali(value, fmt='%Y/%m/%d'):
    """تاریخ میلادی → رشته‌ی شمسی با ارقام فارسی."""
    return j.format_jalali(value, fmt)


@register.filter(name='jalali_long')
def jalali_long(value):
    """قالب طولانی: «۱۵ مرداد ۱۴۰۵»."""
    return j.jalali_long(value)


@register.filter(name='reldate')
def reldate(value):
    """تاریخ نسبی: «امروز/دیروز/فردا/N روز قبل/N روز بعد» — همیشه نسبی، هر چقدر هم دور
    (مثلاً «۵۰۰ روز بعد»). تاریخِ اصلی در `title` (هاور) نمایش داده می‌شود، نه اینجا.
    منطقِ همسان با `App.relDate` در جاوااسکریپت (نمایشِ خواناترِ جدولِ تسک‌ها)."""
    if not value:
        return '—'
    if isinstance(value, datetime):
        value = value.date()
    diff = (value - date.today()).days
    if diff == 0:
        return 'امروز'
    if diff == 1:
        return 'فردا'
    if diff == -1:
        return 'دیروز'
    if diff > 0:
        return f'{diff} روز بعد'
    return f'{-diff} روز قبل'


@register.filter(name='fa_digits')
def fa_digits(value):
    """اعداد را لاتین نگه می‌دارد (طبق درخواست: نمایشِ همه‌ی اعداد انگلیسی).
    نامش تاریخی است؛ اگر ورودی فارسی بود هم به لاتین برمی‌گرداند."""
    return j.to_en_digits(value)


@register.filter(name='elided_pages')
def elided_pages(page_obj, on_each_side=2):
    """بازه‌ی صفحات با «…» (۱ ۲ ۳ … ۲۰) — منبعِ واحدِ شماره‌گذاریِ صفحه‌بندی.
    خروجی شامل اعداد و ثابتِ Paginator.ELLIPSIS ('…') است."""
    try:
        p = page_obj.paginator
        return p.get_elided_page_range(page_obj.number, on_each_side=on_each_side, on_ends=1)
    except Exception:  # noqa: BLE001
        return []


@register.filter(name='hours')
def hours(minutes):
    """دقیقه → ساعت (لاتین، مثلاً «2.5»). صفر/خالی → «0»."""
    try:
        m = int(minutes or 0)
    except (ValueError, TypeError):
        return '0'
    if not m:
        return '0'
    return f'{m / 60:.1f}'.rstrip('0').rstrip('.')


@register.filter(name='money')
def money(value):
    """قالب‌بندی مبلغ با جداکننده‌ی هزارگان و ارقامِ لاتین (طبق درخواست)."""
    if value is None or value == '':
        return '0'
    try:
        num = int(round(float(value)))
    except (ValueError, TypeError):
        return j.to_en_digits(value)
    return f'{num:,}'


@register.filter(name='dictkey')
def dictkey(d, key):
    """دسترسی به مقدار دیکشنری با کلید متغیر در تمپلیت: {{ mydict|dictkey:k }}."""
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter(name='split_options')
def split_options(value):
    """گزینه‌های یک فیلدِ select (رشته‌ی جداشده با ویرگولِ فارسی/انگلیسی) → لیستِ تمیز."""
    if not value:
        return []
    return [o.strip() for o in str(value).replace('،', ',').split(',') if o.strip()]


@register.filter(name='repfield')
def repfield(item, key):
    """مقدار نمایشی یک فیلد از ردیف گزارش با کلید متغیر."""
    return item.field_value(key)


_STATUS_BADGE = {'todo': ('mute', 'در انتظار'), 'doing': ('warn', 'در حال انجام'), 'done': ('ok', 'انجام شده')}
_PRIORITY_BADGE = {'low': ('mute', 'کم'), 'med': ('info', 'متوسط'), 'high': ('bad', 'زیاد')}


@register.simple_tag(name='column_cell')
def column_cell(obj, col):
    """رندرِ یک سلولِ جدولِ سفارشی‌سازی‌شده طبق `col['display']` (از core/columns.py).
    منبعِ واحدِ رندرِ ستون‌ها برای تسک/پروژه/همکار — همه‌جا از همین تگ استفاده کن."""
    value = cell_value(obj, col)
    display = col.get('display', 'text')

    if value in (None, ''):
        if display == 'link_icon':
            return format_html('<span class="lnk" style="opacity:.3">↗</span>')
        return format_html('<span class="zero">—</span>')

    if display == 'number':
        return fa_digits(value)
    if display == 'time':
        return hours(value)
    if display == 'date':
        return jalali(value) if hasattr(value, 'strftime') else escape(value)
    if display == 'timeago':
        return timeago(value)
    if display == 'bool':
        return format_html('✓') if value else format_html('<span class="zero">—</span>')
    if display == 'link_icon':
        return format_html('<a class="lnk" href="{}" target="_blank" rel="noopener">↗</a>', value)
    if display == 'progress':
        cls = 'ok' if value >= 100 else ('bad' if value < 40 else '')
        return format_html('<div class="bar {}"><i style="width:{}%"></i></div>', cls, value)
    if display == 'badge':
        key = col['key']
        if key == 'status':
            cls, label = _STATUS_BADGE.get(value, ('mute', value))
        elif key == 'priority':
            cls, label = _PRIORITY_BADGE.get(value, ('mute', value))
        elif key == 'state' and isinstance(value, (list, tuple)):
            cls, label = value
            return format_html('<span class="tag t-{}">● {}</span>', cls, label)
        else:
            cls, label = 'mute', value
        return format_html('<span class="tag t-{}">{}</span>', cls, label)
    return escape(value)


@register.filter(name='timeago')
def timeago(value):
    """فاصله‌ی زمانی نسبی به فارسی: «۳ روز پیش»."""
    if value is None:
        return ''
    now = timezone.now()
    if isinstance(value, datetime):
        moment = value if timezone.is_aware(value) else timezone.make_aware(value)
    elif isinstance(value, date):
        moment = timezone.make_aware(datetime(value.year, value.month, value.day))
    else:
        return ''

    delta = now - moment
    seconds = delta.total_seconds()

    if seconds < 0:
        return 'در آینده'
    if seconds < 60:
        return 'همین حالا'
    minutes = int(seconds // 60)
    if minutes < 60:
        return f'{minutes} دقیقه پیش'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} ساعت پیش'
    days = hours // 24
    if days == 1:
        return 'دیروز'
    if days < 30:
        return f'{days} روز پیش'
    months = days // 30
    if months < 12:
        return f'{months} ماه پیش'
    years = days // 365
    return f'{years} سال پیش'


@register.filter(name='min_hm')
def min_hm(value):
    """دقیقه → «HH:MM» با ارقامِ لاتین (برای ساعتِ کاریِ حضورغیاب)."""
    try:
        m = int(value or 0)
    except (ValueError, TypeError):
        return '00:00'
    return f'{m // 60:02d}:{m % 60:02d}'


@register.filter(name='sec_hm')
def sec_hm(value):
    """ثانیه → «HH:MM» با ارقامِ لاتین (زمانِ برنامه‌ها در حضورغیاب)."""
    try:
        m = int(value or 0) // 60
    except (ValueError, TypeError):
        return '00:00'
    return f'{m // 60:02d}:{m % 60:02d}'


@register.simple_tag(name='asset_v')
def asset_v():
    """نسخهٔ استاتیک (هشِ محتوای CSS/JS) — به‌عنوانِ `?v=` روی لینک‌های اصلی می‌آید تا با
    هر deploy، کشِ مرورگر و سرویس‌ورکر هر دو باطل شوند (رفعِ «کاربران آپدیت نمی‌بینند»)."""
    from core.pwa import _asset_version
    return _asset_version()
