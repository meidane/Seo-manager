"""ثبتِ تاریخچهٔ تسک (ساخت/ویرایش/حذف/بازیابی) + محاسبهٔ تفاوتِ نسخهٔ قبلی.

منبعِ واحدِ ثبتِ تاریخچه — از `api.py` صدا زده می‌شود. `snapshot()` قبل از تغییر گرفته
می‌شود، بعد از ذخیره `diff()` تغییرات را می‌سازد و `record()` یک `TaskHistory` می‌نویسد.
"""
from core.jalali import format_jalali

from .models import TaskHistory

# فیلدهای قابل‌ردیابی: نامِ فیلد → برچسبِ فارسی
TRACKED = {
    'title': 'عنوان', 'status': 'وضعیت', 'project_id': 'پروژه', 'assignee_id': 'مسئول',
    'planned_date': 'تاریخ برنامه', 'done_date': 'تاریخ انجام', 'priority': 'اولویت',
    'needs_review': 'نیاز به بازبینی', 'estimate_minutes': 'تخمین زمان (دقیقه)',
    'type_def_id': 'نوع', 'description': 'توضیحات',
}


def snapshot(task):
    return {f: getattr(task, f) for f in TRACKED}


def _disp(field, value):
    """نمایشِ خواناى مقدارِ یک فیلد (FK/choice/date/bool)."""
    if value in (None, ''):
        return '—'
    if field == 'status':
        from .models import Task
        return dict(Task.STATUS_CHOICES).get(value, value)
    if field == 'priority':
        from .models import Task
        return dict(Task.PRIORITY_CHOICES).get(value, value)
    if field in ('planned_date', 'done_date'):
        try:
            return format_jalali(value)
        except Exception:  # noqa: BLE001
            return str(value)
    if field == 'needs_review':
        return 'بله' if value else 'خیر'
    if field == 'project_id':
        from projects.models import Project
        p = Project.all_objects.filter(id=value).first()
        return p.name if p else str(value)
    if field == 'assignee_id':
        from colleagues.models import Colleague
        c = Colleague.all_objects.filter(id=value).first()
        return c.full_name if c else str(value)
    if field == 'type_def_id':
        from .models import TaskTypeDef
        t = TaskTypeDef.all_objects.filter(id=value).first()
        return t.name if t else str(value)
    if field == 'description':
        import re
        txt = re.sub('<[^>]+>', '', str(value)).strip()
        return (txt[:60] + '…') if len(txt) > 60 else (txt or '—')
    return str(value)


def diff(task, before):
    """{برچسب: [قدیم, جدید]} برای فیلدهای تغییرکرده."""
    changes = {}
    for field, label in TRACKED.items():
        old, new = before.get(field), getattr(task, field)
        if old != new:
            changes[label] = [_disp(field, old), _disp(field, new)]
    return changes


def record(task, action, user, changes=None):
    u = user if getattr(user, 'is_authenticated', False) else None
    TaskHistory.objects.create(task=task, action=action, user=u, changes=changes or {})
