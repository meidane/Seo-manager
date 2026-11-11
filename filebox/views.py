"""صفحه و APIِ «فایل‌ها» (+ پوشه‌ها) — گیت: پرمیشنِ `shared_files`. لینکِ عمومی بدونِ ورود سرو می‌شود:
`public_path` (مسیرِ ثابتِ `/f/<سازمان>/<پوشه>/<نام.پسوند>`) و `public` (لینکِ قدیمیِ توکنی)."""
import json
import mimetypes
import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import uri_to_iri
from django.views.decorators.http import require_http_methods

from accounts.access import require_perm
from core.templatetags.seo_extras import timeago

from .models import SharedFile, SharedFolder, org_key

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
    by = (f.uploaded_by.get_full_name() or f.uploaded_by.username) if f.uploaded_by else ''
    return {'id': f.id, 'name': f.name, 'kind': f.kind, 'size': _size_h(f.size), 'folder': f.folder_id,
            # نمایشِ خوانا (حروفِ فارسی باز، فاصله/کاراکترهای رزرو کدشده) — مرورگر خودش کد می‌کند
            'link': uri_to_iri(request.build_absolute_uri(f.public_path())),
            'thumb': f.file.url if f.kind == 'image' else '', 'by': by, 'ago': timeago(f.updated_at)}


def _frow(d):
    return {'id': d.id, 'name': d.name, 'parent': d.parent_id}


def _state(request):
    return {'files': [_row(request, f) for f in SharedFile.objects.select_related('uploaded_by', 'folder')],
            'folders': [_frow(d) for d in SharedFolder.objects.all()]}


def _folder_or_none(pk):
    return get_object_or_404(SharedFolder, pk=pk) if pk not in (None, '', 'null', 0, '0') else None


def _same_name(name, folder, exclude=None):
    qs = SharedFile.objects.filter(name=name, folder=folder)
    return qs.exclude(pk=exclude).first() if exclude else qs.first()


@login_required
def page(request):
    require_perm(request, 'shared_files')
    return render(request, 'filebox/index.html', {'state': _state(request), 'page_title': 'فایل‌ها',
                                                  'max_mb': MAX_SIZE // (1024 * 1024)})


@login_required
@require_http_methods(['GET', 'POST'])
def api_list(request):
    """GET = همه؛ POST = آپلود (multipart `file` + `folder`؛ `replace=1` برای جایگزینیِ هم‌نامِ همان پوشه → وگرنه 409)."""
    require_perm(request, 'shared_files')
    if request.method == 'GET':
        return JsonResponse(_state(request))
    up = request.FILES.get('file')
    if not up:
        return JsonResponse({'detail': 'فایلی انتخاب نشده'}, status=400)
    if up.size > MAX_SIZE:
        return JsonResponse({'detail': f'حداکثر حجم {MAX_SIZE // (1024 * 1024)} مگابایت است'}, status=413)
    folder = _folder_or_none(request.POST.get('folder'))
    name = _clean_name(up.name)
    existing = _same_name(name, folder)
    if existing and request.POST.get('replace') != '1':
        return JsonResponse({'conflict': True, 'name': name, 'detail': f'فایلی با نامِ «{name}» در این پوشه هست'}, status=409)
    f = existing or SharedFile(name=name, folder=folder)
    f.file = up  # فایلِ قدیمی را django-cleanup پاک می‌کند؛ لینک (مسیر) همان می‌ماند
    f.size = up.size
    f.uploaded_by = request.user
    f.save()
    return JsonResponse({'ok': True, 'replaced': bool(existing), 'file': _row(request, f)})


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def api_detail(request, pk):
    """PATCH `{name?, folder?, replace?}` = تغییرِ نام و/یا جابه‌جایی به پوشهٔ دیگر؛ DELETE = حذف."""
    require_perm(request, 'shared_files')
    f = get_object_or_404(SharedFile, pk=pk)
    if request.method == 'DELETE':
        f.delete()
        return JsonResponse({'ok': True})
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        body = {}
    name = _clean_name(body['name'], fallback_ext=f.ext) if 'name' in body else f.name
    if not name or name.startswith('.'):
        return JsonResponse({'detail': 'نام معتبر نیست'}, status=400)
    folder = _folder_or_none(body.get('folder')) if 'folder' in body else f.folder
    other = _same_name(name, folder, exclude=f.pk)
    if other and not body.get('replace'):
        return JsonResponse({'conflict': True, 'name': name, 'detail': f'فایلی با نامِ «{name}» در مقصد هست'}, status=409)
    if other:
        other.delete()  # «جایگزین کن» → فایلِ هم‌نامِ قبلی حذف می‌شود
    f.name, f.folder = name, folder
    f.save(update_fields=['name', 'folder', 'updated_at'])
    return JsonResponse({'ok': True, 'file': _row(request, f), 'removed': other.pk if other else None})


@login_required
@require_http_methods(['POST'])
def folder_create(request):
    require_perm(request, 'shared_files')
    body = json.loads(request.body or '{}')
    name = _clean_name(body.get('name'))[:120]
    parent = _folder_or_none(body.get('parent'))
    if not name:
        return JsonResponse({'detail': 'نامِ پوشه لازم است'}, status=400)
    if SharedFolder.objects.filter(name=name, parent=parent).exists():
        return JsonResponse({'detail': 'پوشه‌ای با این نام اینجا هست'}, status=400)
    return JsonResponse({'folder': _frow(SharedFolder.objects.create(name=name, parent=parent))})


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def folder_detail(request, pk):
    """PATCH `{name?, parent?}`؛ DELETE = حذفِ پوشه با همهٔ محتوایش."""
    require_perm(request, 'shared_files')
    d = get_object_or_404(SharedFolder, pk=pk)
    if request.method == 'DELETE':
        d.delete()
        return JsonResponse({'ok': True})
    body = json.loads(request.body or '{}')
    name = _clean_name(body['name'])[:120] if 'name' in body else d.name
    parent = _folder_or_none(body.get('parent')) if 'parent' in body else d.parent
    if not name:
        return JsonResponse({'detail': 'نامِ پوشه لازم است'}, status=400)
    if parent and (parent.pk == d.pk or d in parent.chain()):
        return JsonResponse({'detail': 'پوشه را نمی‌شود داخلِ خودش برد'}, status=400)
    if SharedFolder.objects.filter(name=name, parent=parent).exclude(pk=d.pk).exists():
        return JsonResponse({'detail': 'پوشه‌ای با این نام آنجا هست'}, status=400)
    d.name, d.parent = name, parent
    d.save()
    return JsonResponse({'folder': _frow(d), **_state(request)})


def _serve(f):
    if not f or not f.file:
        raise Http404
    try:
        fh = f.file.open('rb')
    except FileNotFoundError as e:
        raise Http404 from e
    ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
    inline = ctype.startswith(('image/', 'video/', 'audio/')) or ctype in ('application/pdf', 'text/plain')
    resp = FileResponse(fh, content_type=ctype, as_attachment=not inline, filename=f.name)
    resp['Cache-Control'] = 'public, max-age=300'
    return resp


def public(request, token):
    """لینکِ قدیمیِ توکنی (`/f/<token>/`) — برای لینک‌هایی که قبل از پوشه‌بندی پخش شده‌اند."""
    return _serve(SharedFile.all_objects.filter(token=token).first())


def public_path(request, org, path):
    """لینکِ ثابت: `/f/<سازمان>/<پوشه‌ها…>/<نام.پسوند>` — بدونِ ورود."""
    from accounts.models import Organization
    o = Organization.objects.filter(slug=org).first() or (Organization.objects.filter(pk=org).first() if org.isdigit() else None)
    if not o or org_key(o) != org:
        raise Http404
    parts = [p for p in path.split('/') if p]
    if not parts:
        raise Http404
    folder = None
    for name in parts[:-1]:
        folder = SharedFolder.all_objects.filter(organization=o, parent=folder, name=name).first()
        if not folder:
            raise Http404
    return _serve(SharedFile.all_objects.filter(organization=o, folder=folder, name=parts[-1]).first())
