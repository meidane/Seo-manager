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

from .columns import get_catalog
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


# ── سفارشی‌سازیِ ستون‌ها `/settings/columns/` ───────────────────────────────
# پنج بخشِ قابل‌تنظیم: تسک‌ها(صفحه)، پروژه‌ها(صفحه/داشبورد)، همکاران(صفحه/داشبورد).
COLUMN_SECTIONS = [
    (ColumnConfig.TASKS, ColumnConfig.PAGE, 'تسک‌ها — ستون‌های اضافی (صفحه‌ی تسک‌ها)'),
    (ColumnConfig.PROJECTS, ColumnConfig.PAGE, 'وضعیت پروژه‌ها — صفحه‌ی پروژه‌ها'),
    (ColumnConfig.PROJECTS, ColumnConfig.DASHBOARD, 'وضعیت پروژه‌ها — داشبورد'),
    (ColumnConfig.COLLEAGUES, ColumnConfig.PAGE, 'عملکرد همکاران — صفحه‌ی همکاران'),
    (ColumnConfig.COLLEAGUES, ColumnConfig.DASHBOARD, 'عملکرد همکاران — داشبورد'),
]


class ColumnsSettingsView(LoginRequiredMixin, TemplateView):
    """تنظیمِ ستون‌های قابل‌نمایش/ترتیبشان برای هر جدول+محل — per سازمان."""

    template_name = 'settings/columns.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cfgs = {(c.table, c.scope): c.keys for c in ColumnConfig.objects.all()}
        sections = []
        for table, scope, title in COLUMN_SECTIONS:
            catalog = get_catalog(table)
            by_key = {c['key']: c for c in catalog}
            saved = cfgs.get((table, scope)) or []
            # ترتیب: کلیدهای ذخیره‌شده (فعال) اول، بعد بقیه‌ی کاتالوگ (غیرفعال)
            ordered = [by_key[k] for k in saved if k in by_key]
            ordered += [c for c in catalog if c['key'] not in saved]
            items = [{'key': c['key'], 'label': c['label'], 'checked': c['key'] in saved} for c in ordered]
            sections.append({'table': table, 'scope': scope, 'title': title, 'items': items})
        ctx['sections'] = sections
        ctx['page_title'] = 'سفارشی‌سازی ستون‌ها'
        return ctx


@login_required
@require_http_methods(['POST'])
def columns_save(request):
    """ذخیره‌ی ترتیب/انتخابِ ستون‌های یک (table, scope). بدنه: {table, scope, keys:[...]}."""
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
