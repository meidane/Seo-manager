"""پردازنده‌های زمینه (context processors) سراسری."""
from .daterange import PRESET_LABELS


def date_range(request):
    """پیش‌تنظیم‌های بازه‌ی زمانی را در دسترس همه‌ی تمپلیت‌ها قرار می‌دهد.

    مقدار فعلیِ بازه توسط هر ویو (از طریق DateRangeMixin.range_context) به
    زمینه اضافه می‌شود؛ اینجا فقط فهرست پیش‌تنظیم‌ها برای نوار هدر می‌آید.
    """
    return {'range_presets': PRESET_LABELS}
