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
TASKS = [
    {'key': 'priority', 'label': 'اولویت', 'display': 'badge'},
    {'key': 'estimate_minutes', 'label': 'تخمین (ساعت)', 'display': 'time'},
    {'key': 'word_count', 'label': 'تعداد کلمه', 'display': 'number'},
    {'key': 'published_url', 'label': 'لینک انتشار', 'display': 'link_icon', 'default': True},
]

PROJECTS = [
    {'key': 'planned', 'label': 'برنامه', 'display': 'number', 'default': True},
    {'key': 'done', 'label': 'انجام', 'display': 'number', 'default': True},
    {'key': 'remaining', 'label': 'باقی', 'display': 'number', 'default': True},
    {'key': 'overdue', 'label': 'عقب', 'display': 'number', 'default': True},
    {'key': 'minutes', 'label': 'جمع ساعت', 'display': 'time', 'default': True},
    {'key': 'words', 'label': 'جمع کلمه', 'display': 'number'},
    {'key': 'progress', 'label': 'پیشرفت', 'display': 'progress', 'default': True},
    {'key': 'last_report', 'label': 'آخرین گزارش', 'display': 'date', 'default': True},
    {'key': 'last_activity', 'label': 'آخرین فعالیت', 'display': 'timeago'},
    # هنوز به finance وصل نیست؛ همیشه «—» نشان می‌دهد تا آن گام بعدی انجام شود
    {'key': 'last_payment', 'label': 'آخرین پرداخت', 'display': 'date', 'default': True},
    {'key': 'state', 'label': 'وضعیت', 'display': 'badge', 'default': True},
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
}


def custom_field_columns():
    """ستون‌های داینامیکِ فیلدِ سفارشیِ انواعِ فعالِ سازمانِ جاری (فقط برای تسک‌ها)."""
    from tasks.models import TaskTypeDef
    out = []
    for td in TaskTypeDef.objects.filter(is_active=True).prefetch_related('fields'):
        for f in td.fields.all():
            out.append({
                'key': f'cf:{td.id}:{f.key}',
                'label': f'{td.name} — {f.label}',
                'display': _FIELD_KIND_TO_DISPLAY.get(f.kind, 'text'),
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
    """ستون‌های اضافیِ جدولِ تسک‌ها با قاعدهٔ «عمومی همیشه، سفارشیِ نوع فقط وقتی همان
    نوع فیلتر شده». وگرنه اگر کاربر همهٔ فیلدهای سفارشیِ همهٔ انواع را در تنظیمات فعال کند،
    جدول از ده‌ها ستونِ بی‌ربط شلوغ می‌شود (باگِ گزارش‌شده). `active_type_def_id` = نوعِ
    فیلترشدهٔ جاری (یا None). منبعِ واحد — لیستِ تسک‌ها، لودِ تنبل و بردِ سئو از همین می‌خوانند."""
    cols = get_columns(ColumnConfig.TASKS, ColumnConfig.PAGE)
    tid = str(active_type_def_id) if active_type_def_id else ''
    return [c for c in cols if (not c['key'].startswith('cf:')) or c['key'].split(':')[1] == tid]


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
