"""موتورِ کاتالوگِ ستون‌های قابل‌سفارشی‌سازی — منبعِ واحدِ «چه ستون‌هایی، با چه
برچسب/حالتِ نمایشی، برای کدام جدول موجودند». تنظیمِ سازمان (`core.models.ColumnConfig`)
فقط فهرستِ کلیدهای انتخاب‌شده را نگه می‌دارد؛ برچسب/حالتِ نمایش همیشه از همین‌جا خوانده
می‌شود تا دوباره‌کاری/ناهم‌خوانی پیش نیاید (قانونِ طلایی #۷).

هر آیتمِ کاتالوگ: {key, label, display, default(اختیاری، برای پیش‌فرضِ بدون‌تنظیم)}
حالت‌های نمایش: text, number, time(دقیقه→ساعت), date, bool, badge, link_icon
برای جدولِ تسک‌ها، ستون‌های فیلدِ سفارشیِ هر نوعِ فعال هم داینامیک اضافه می‌شوند
(کلید `cf:<type_def_id>:<field_key>`) — همان چیزی که کاربر در «انواع تسک» ساخته.
"""
from .models import ColumnConfig

# پروژه/مسئول/تاریخ‌برنامه/وضعیت ستون‌های ثابتِ جدول تسک‌ها می‌مانند (ویرایشِ زنده دارند،
# `templates/tasks/list.html`) — اینجا فقط ستون‌های «اضافی»ِ اختیاری‌اند که بعد از آن‌ها می‌آیند.
# ستون‌های اضافیِ جدولِ تسک دیگر از یک کاتالوگِ ثابت نمی‌آیند — با انتخابِ نوعِ تسک،
# فیلدهای سفارشیِ همان نوع نمایش داده می‌شوند (`visible_task_columns` → `custom_field_columns`).
# پیش‌فرض (بدونِ انتخابِ نوع) فقط ستون‌های اصلیِ مشترک است، بدونِ ستونِ اضافی.
TASKS = []

PROJECTS = [
    {'key': 'planned', 'label': 'برنامه', 'display': 'number', 'default': True},
    {'key': 'done', 'label': 'انجام', 'display': 'number', 'default': True},
    {'key': 'remaining', 'label': 'باقی', 'display': 'number', 'default': True},
    {'key': 'overdue', 'label': 'عقب', 'display': 'number', 'default': True},
    {'key': 'est_minutes', 'label': 'ساعت تخمین', 'display': 'time', 'default': True},
    {'key': 'minutes', 'label': 'ساعت کارکرد', 'display': 'time'},
    {'key': 'words', 'label': 'جمع کلمه', 'display': 'number'},
    # نمودارِ کوچکِ روند ۱۴روزِ انجام‌شده‌ها (مثلِ اسپارک‌لاینِ صفحهٔ افراد؛ هاور = تعداد)
    {'key': 'spark', 'label': 'روند ۱۴ روز', 'display': 'spark', 'default': True},
    # یک ستونِ «وضعیت» به‌جای دو ستونِ گزارش/پرداخت (آخرین گزارش + آخرین پرداخت)
    {'key': 'status_col', 'label': 'وضعیت', 'display': 'status_col', 'default': True},
    {'key': 'progress', 'label': 'پیشرفت', 'display': 'progress'},
    {'key': 'last_report', 'label': 'آخرین گزارش', 'display': 'date'},
    {'key': 'last_activity', 'label': 'آخرین فعالیت', 'display': 'timeago'},
    {'key': 'last_payment', 'label': 'آخرین پرداخت', 'display': 'date'},
]

COLLEAGUES = [
    {'key': 'planned', 'label': 'برنامه‌ریزی', 'display': 'number', 'default': True},
    {'key': 'done', 'label': 'انجام‌شده', 'display': 'number', 'default': True},
    {'key': 'overdue', 'label': 'عقب‌افتاده', 'display': 'number', 'default': True},
    {'key': 'minutes', 'label': 'جمع ساعت', 'display': 'time', 'default': True},
    {'key': 'words', 'label': 'جمع کلمه', 'display': 'number'},
]

_BASE = {ColumnConfig.TASKS: TASKS, ColumnConfig.PROJECTS: PROJECTS, ColumnConfig.COLLEAGUES: COLLEAGUES}

_FIELD_KIND_TO_DISPLAY = {
    'text': 'text', 'textarea': 'text', 'number': 'number',
    'checkbox': 'bool', 'select': 'badge', 'url': 'link_icon', 'date': 'date',
    'tags': 'tags',
}


def custom_field_columns():
    """ستون‌های داینامیکِ فیلدِ سفارشیِ انواعِ فعالِ سازمانِ جاری (فقط برای تسک‌ها).
    فیلدِ «لینکِ صفحه» (`is_page_link`) ستون نمی‌شود — آیکنش کنارِ عنوانِ ردیف می‌آید."""
    from tasks.models import TaskTypeDef
    out = []
    for td in TaskTypeDef.objects.filter(is_active=True).prefetch_related('fields'):
        for f in td.fields.all():
            if f.is_page_link or f.is_word_source:   # لینکِ صفحه در عنوان؛ «تعداد کلمه» حذف
                continue
            out.append({
                'key': f'cf:{td.id}:{f.key}',
                'label': f.label,
                'display': _FIELD_KIND_TO_DISPLAY.get(f.kind, 'text'),
                # metaِ لازم برای ویرایشِ inline در جدول (وقتی نوع انتخاب شده):
                'kind': f.kind,                 # tags/select/checkbox/date/number/url/text
                'cf_key': f.key,                # کلیدِ داخلِ Task.custom (بدونِ cf:tid:)
                'options': f.options,           # برای select (با ویرگول جدا)
            })
    return out


def get_catalog(table):
    base = list(_BASE.get(table, []))
    if table == ColumnConfig.TASKS:
        base += custom_field_columns()
    return base


def resolve_state(table, scope):
    """(کاتالوگ, کلیدهای مؤثر, پیکربندی‌شده؟) — یک‌بار محاسبه، هم `get_columns`
    هم صفحهٔ تنظیمات از همین می‌خوانند تا هیچ‌وقت ناهم‌خوان نشوند.
    **بدونِ رکوردِ ColumnConfig** = پیش‌فرضِ کاتالوگ. **رکوردِ خالی (کاربر همه را
    برداشته و ذخیره کرده)** = واقعاً هیچ ستونی، نه بازگشت به پیش‌فرض."""
    catalog = get_catalog(table)
    cfg = ColumnConfig.objects.filter(table=table, scope=scope).first()
    if cfg is not None:
        return catalog, list(cfg.keys), True
    defaults = [c['key'] for c in catalog if c.get('default')] or [c['key'] for c in catalog[:6]]
    return catalog, defaults, False


def get_columns(table, scope):
    """فهرستِ ستون‌های فعالِ سازمانِ جاری برای یک جدول/محل — کلید+برچسب+حالتِ نمایش."""
    catalog, keys, _ = resolve_state(table, scope)
    by_key = {c['key']: c for c in catalog}
    return [by_key[k] for k in keys if k in by_key]


def visible_task_columns(active_type_def_id=None):
    """ستون‌های اضافیِ جدولِ تسک‌ها. بدونِ فیلترِ نوع → هیچ ستونِ اضافه‌ای. با انتخابِ
    یک نوع → **همهٔ** فیلدهای سفارشیِ همان نوع، بدونِ استثنا (شاملِ «لینکِ صفحه» و «تعداد
    کلمه» که در کاتالوگِ تنظیمات حذف می‌شوند ولی اینجا باید ویرایش‌پذیر باشند — خواستِ
    کاربر: «همهٔ فیلدها را نشان بده»). منبعِ واحد — لیست/لودِ تنبل/بردِ سئو از همین می‌خوانند."""
    if not active_type_def_id:
        return []
    from tasks.models import TaskTypeDef
    td = (TaskTypeDef.objects.filter(id=active_type_def_id)
          .prefetch_related('fields').first())
    if not td:
        return []
    return [{
        'key': f'cf:{td.id}:{f.key}',
        'label': f.label,
        'display': _FIELD_KIND_TO_DISPLAY.get(f.kind, 'text'),
        'kind': f.kind,
        'cf_key': f.key,
        'options': f.options,
    } for f in td.fields.all()]


def cell_value(obj, col):
    """مقدارِ خامِ یک ستون برای یک ردیف (Task/Project/Colleague)."""
    key = col['key']
    if key.startswith('cf:'):
        _, tid, fkey = key.split(':', 2)
        if str(getattr(obj, 'type_def_id', None)) != tid:
            return None
        return (getattr(obj, 'custom', None) or {}).get(fkey)
    if key == 'project':
        p = getattr(obj, 'project', None)
        return p.name if p else ''
    if key == 'assignee':
        a = getattr(obj, 'assignee', None)
        return a.full_name if a else ''
    return getattr(obj, key, None)
