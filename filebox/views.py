"""صفحه و APIِ «فایل‌ها» — گیت: پرمیشنِ `shared_files`. لینکِ عمومی (`public`) بدونِ ورود سرو می‌شود."""
import json
import mimetypes
import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.access import require_perm
from core.templatetags.seo_extras import timeago

from .models import SharedFile

MAX_SIZE = 20 * 1024 * 1024  # سقفِ nginx: 25M


def _clean_name(name, fallback_ext=''):
    name = os.path.basename(str(name or '')).strip().replace('/', '-').replace('\\', '-')[:200]
    if fallback_ext and '.' not in name:
        name = f'{name}.{fallback_ext}'
    return name


def _size_h(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
    return ''


def _row(request, f):
    link = request.build_absolute_uri(reverse('filebox:public', args=[f.token]))
    by = (f.uploaded_by.get_full_name() or f.uploaded_by.username) if f.uploaded_by else ''
    return {'id': f.id, 'name': f.name, 'kind': f.kind, 'size': _size_h(f.size), 'link': link,
            'thumb': f.file.url if f.kind == 'image' else '', 'by': by, 'ago': timeago(f.updated_at)}


@login_required
def page(request):
    require_perm(request, 'shared_files')
    files = [_row(request, f) for f in SharedFile.objects.select_related('uploaded_by')]
    return render(request, 'filebox/index.html', {'files': files, 'page_title': 'فایل‌ها', 'max_mb': MAX_SIZE // (1024 * 1024)})


@login_required
@require_http_methods(['GET', 'POST'])
def api_list(request):
    """GET = فهرست؛ POST = آپلود (multipart `file`، `replace=1` برای جایگزینیِ هم‌نام → 409 اگر هم‌نام بود و replace نبود)."""
    require_perm(request, 'shared_files')
    if request.method == 'GET':
        return JsonResponse({'files': [_row(request, f) for f in SharedFile.objects.select_related('uploaded_by')]})
    up = request.FILES.get('file')
    if not up:
        return JsonResponse({'detail': 'فایلی انتخاب نشده'}, status=400)
    if up.size > MAX_SIZE:
        return JsonResponse({'detail': f'حداکثر حجم {MAX_SIZE // (1024 * 1024)} مگابایت است'}, status=413)
    name = _clean_name(up.name)
    existing = SharedFile.objects.filter(name=name).first()
    if existing and request.POST.get('replace') != '1':
        return JsonResponse({'conflict': True, 'name': name, 'detail': f'فایلی با نامِ «{name}» از قبل هست'}, status=409)
    f = existing or SharedFile(name=name)
    f.file = up  # فایلِ قدیمی را django-cleanup پاک می‌کند؛ توکن (لینک) همان می‌ماند
    f.size = up.size
    f.uploaded_by = request.user
    f.save()
    return JsonResponse({'ok': True, 'replaced': bool(existing), 'file': _row(request, f)})


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def api_detail(request, pk):
    require_perm(request, 'shared_files')
    f = get_object_or_404(SharedFile, pk=pk)
    if request.method == 'DELETE':
        f.delete()
        return JsonResponse({'ok': True})
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        body = {}
    name = _clean_name(body.get('name'), fallback_ext=f.ext)
    if not name or name.startswith('.'):
        return JsonResponse({'detail': 'نام معتبر نیست'}, status=400)
    other = SharedFile.objects.filter(name=name).exclude(pk=f.pk).first()
    if other and not body.get('replace'):
        return JsonResponse({'conflict': True, 'name': name, 'detail': f'فایلی با نامِ «{name}» از قبل هست'}, status=409)
    if other:
        other.delete()  # «جایگزین کن» → فایلِ هم‌نامِ قبلی حذف می‌شود
    f.name = name
    f.save(update_fields=['name', 'updated_at'])
    return JsonResponse({'ok': True, 'file': _row(request, f)})


def public(request, token):
    """لینکِ اشتراکی — بدونِ ورود. تصویر/PDF در مرورگر باز می‌شود، بقیه دانلود."""
    f = SharedFile.all_objects.filter(token=token).first()
    if not f or not f.file:
        raise Http404
    try:
        fh = f.file.open('rb')
    except FileNotFoundError as e:
        raise Http404 from e
    ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
    inline = ctype.startswith(('image/', 'video/', 'audio/')) or ctype in ('application/pdf', 'text/plain')
    resp = FileResponse(fh, content_type=ctype, as_attachment=not inline, filename=f.name)
    resp['Cache-Control'] = 'private, max-age=300'
    return resp
