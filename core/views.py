"""ویوهای core — مدیریت تعطیلات، آپلود عکس ادیتور، سفارشی‌سازی ستون‌ها."""
import json
import os
import uuid

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, TemplateView

from accounts.access import require_perm

from .columns import get_catalog, resolve_state
from .models import ColumnConfig, Holiday

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


@login_required
@require_http_methods(['POST'])
def editor_upload(request):
    """آپلود عکس داخل ادیتور غنی (TinyMCE) — برمی‌گرداند {location: url}."""
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'detail': 'فایلی ارسال نشد'}, status=400)
    if f.size > 20 * 1024 * 1024:
        return JsonResponse({'detail': 'حجم فایل بیش از ۲۰ مگابایت است'}, status=400)
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in IMAGE_EXTS:
        return JsonResponse({'detail': 'فقط فایل تصویری مجاز است'}, status=400)
    name = f'editor/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}'
    saved = default_storage.save(name, f)
    return JsonResponse({'location': default_storage.url(saved)})


class HolidayListView(LoginRequiredMixin, ListView):
    """صفحه‌ی مدیریت تعطیلات `/settings/holidays/`.

    فعلاً فقط فهرست را نمایش می‌دهد؛ افزودن/حذف دستی در گام‌های بعد کامل می‌شود.
    """

    model = Holiday
    template_name = 'settings/holidays.html'
    context_object_name = 'holidays'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_holidays')
        return super().dispatch(request, *args, **kwargs)


# ── سفارشی‌سازیِ ستون‌ها `/settings/columns/` ───────────────────────────────
# بخش‌های قابل‌تنظیم: پروژه‌ها(صفحه/داشبورد)، همکاران(صفحه/داشبورد).
# تسک‌ها دیگر اینجا نیست — ستون‌های اضافیِ جدولِ تسک از فیلدهای سفارشیِ نوعِ انتخاب‌شده
# می‌آیند (`core.columns.visible_task_columns`)، نه از یک کاتالوگِ ثابت.
COLUMN_SECTIONS = [
    (ColumnConfig.PROJECTS, ColumnConfig.PAGE, 'وضعیت پروژه‌ها — صفحه‌ی پروژه‌ها'),
    (ColumnConfig.PROJECTS, ColumnConfig.DASHBOARD, 'وضعیت پروژه‌ها — داشبورد'),
    (ColumnConfig.COLLEAGUES, ColumnConfig.PAGE, 'عملکرد همکاران — صفحه‌ی همکاران'),
    (ColumnConfig.COLLEAGUES, ColumnConfig.DASHBOARD, 'عملکرد همکاران — داشبورد'),
]


class ColumnsSettingsView(LoginRequiredMixin, TemplateView):
    """تنظیمِ ستون‌های قابل‌نمایش/ترتیبشان برای هر جدول+محل — per سازمان."""

    template_name = 'settings/columns.html'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_columns')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sections = []
        for table, scope, title in COLUMN_SECTIONS:
            catalog, saved, configured = resolve_state(table, scope)
            by_key = {c['key']: c for c in catalog}
            # ترتیب: کلیدهای فعال (ذخیره‌شده یا پیش‌فرض) اول، بعد بقیه‌ی کاتالوگ (غیرفعال)
            ordered = [by_key[k] for k in saved if k in by_key]
            ordered += [c for c in catalog if c['key'] not in saved]
            items = [{'key': c['key'], 'label': c['label'], 'checked': c['key'] in saved} for c in ordered]
            sections.append({'table': table, 'scope': scope, 'title': title, 'items': items, 'configured': configured})
        ctx['sections'] = sections
        ctx['page_title'] = 'سفارشی‌سازی ستون‌ها'
        return ctx


@login_required
@require_http_methods(['POST'])
def columns_save(request):
    """ذخیره‌ی ترتیب/انتخابِ ستون‌های یک (table, scope). بدنه: {table, scope, keys:[...]}."""
    require_perm(request, 'manage_columns')
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'بدنه نامعتبر'}, status=400)
    table, scope, keys = data.get('table'), data.get('scope'), data.get('keys')
    if table not in dict(ColumnConfig.TABLE_CHOICES) or scope not in dict(ColumnConfig.SCOPE_CHOICES):
        return JsonResponse({'detail': 'جدول/محلِ نامعتبر'}, status=400)
    if not isinstance(keys, list):
        return JsonResponse({'detail': 'فهرستِ ستون‌ها لازم است'}, status=400)
    valid_keys = {c['key'] for c in get_catalog(table)}
    keys = [k for k in keys if k in valid_keys]
    ColumnConfig.objects.update_or_create(table=table, scope=scope, defaults={'keys': keys})
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def columns_reset(request):
    """حذفِ تنظیمِ ذخیره‌شده = برگشت به پیش‌فرضِ کاتالوگ (نه «خالی»). بدنه: {table, scope}."""
    require_perm(request, 'manage_columns')
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'بدنه نامعتبر'}, status=400)
    ColumnConfig.objects.filter(table=data.get('table'), scope=data.get('scope')).delete()
    return JsonResponse({'ok': True})


# ── ماه‌های گزارش `/settings/report-months/` (منبعِ واحدِ ماه‌های گزارش) ────────
class ReportMonthsView(LoginRequiredMixin, TemplateView):
    """تعریفِ ماه‌های گزارش (سطحِ سازمان) — «مرداد ۱۴۰۵». مودالِ تسک و بردِ سئو از همین می‌خوانند."""
    template_name = 'settings/report_months.html'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_task_types')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from tasks.models import ReportPeriod, Task
        from core.jalali import today_jalali
        ctx = super().get_context_data(**kwargs)
        ctx['periods'] = ReportPeriod.objects.all()
        ctx['months'] = Task.REPORT_MONTH_CHOICES
        ctx['cur_year'] = today_jalali().year
        return ctx


@login_required
@require_http_methods(['POST'])
def report_month_add(request):
    from tasks.models import ReportPeriod
    require_perm(request, 'manage_task_types')
    d = json.loads(request.body or '{}')
    try:
        year, month = int(d.get('year')), int(d.get('month'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'سال و ماه لازم است'}, status=400)
    if not (1 <= month <= 12) or not (1300 <= year <= 1500):
        return JsonResponse({'detail': 'مقدارِ سال/ماه نامعتبر است'}, status=400)
    p, created = ReportPeriod.objects.get_or_create(year=year, month=month)
    return JsonResponse({'ok': True, 'id': p.id, 'label': p.label, 'value': p.value, 'created': created})


@login_required
@require_http_methods(['DELETE'])
def report_month_delete(request, pk):
    from tasks.models import ReportPeriod
    require_perm(request, 'manage_task_types')
    ReportPeriod.objects.filter(pk=pk).delete()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def report_month_reorder(request):
    """ترتیبِ نمایشِ ماه‌های گزارش (کدام اولِ دراپ‌داون) — فهرستِ id به ترتیبِ جدید."""
    from tasks.models import ReportPeriod
    require_perm(request, 'manage_task_types')
    ids = json.loads(request.body or '{}').get('ids') or []
    objs = {p.id: p for p in ReportPeriod.objects.filter(id__in=ids)}
    for i, pid in enumerate(ids):
        p = objs.get(int(pid))
        if p and p.order != i:
            p.order = i
            p.save(update_fields=['order'])
    return JsonResponse({'ok': True})
