"""ویوهای core — مدیریت تعطیلات + آپلود عکس ادیتور."""
import os
import uuid

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from .models import Holiday

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
