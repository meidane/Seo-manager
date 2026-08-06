"""تمپلیت‌فیلترهای سراسری: jalali، money، timeago، fa_digits."""
from datetime import date, datetime

from django import template
from django.utils import timezone

from core import jalali as j

register = template.Library()


@register.filter(name='jalali')
def jalali(value, fmt='%Y/%m/%d'):
    """تاریخ میلادی → رشته‌ی شمسی با ارقام فارسی."""
    return j.format_jalali(value, fmt)


@register.filter(name='jalali_long')
def jalali_long(value):
    """قالب طولانی: «۱۵ مرداد ۱۴۰۵»."""
    return j.jalali_long(value)


@register.filter(name='fa_digits')
def fa_digits(value):
    """ارقام لاتین → فارسی."""
    return j.to_fa_digits(value)


@register.filter(name='money')
def money(value):
    """قالب‌بندی مبلغ با جداکننده‌ی هزارگان و ارقام فارسی."""
    if value is None or value == '':
        return '۰'
    try:
        num = int(round(float(value)))
    except (ValueError, TypeError):
        return j.to_fa_digits(value)
    return j.to_fa_digits(f'{num:,}')


@register.filter(name='dictkey')
def dictkey(d, key):
    """دسترسی به مقدار دیکشنری با کلید متغیر در تمپلیت: {{ mydict|dictkey:k }}."""
    try:
        return d.get(key)
    except AttributeError:
        return None


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
        return f'{j.to_fa_digits(minutes)} دقیقه پیش'
    hours = minutes // 60
    if hours < 24:
        return f'{j.to_fa_digits(hours)} ساعت پیش'
    days = hours // 24
    if days == 1:
        return 'دیروز'
    if days < 30:
        return f'{j.to_fa_digits(days)} روز پیش'
    months = days // 30
    if months < 12:
        return f'{j.to_fa_digits(months)} ماه پیش'
    years = days // 365
    return f'{j.to_fa_digits(years)} سال پیش'
