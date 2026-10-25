"""API همگام‌سازیِ ChatGPT-WP — فقط با **توکنِ API** (`Authorization: Token xxx`، همان الگوی
`seo/api.py: token_required`). برنامهٔ دسکتاپ صدا می‌زند؛ سشن/کوکی ندارد.

GET  state/              → {version, updated_at, updated_by, data, files:[{path, sha1, size, updated_at}]}
POST state/              {base_version, data, client} → {version} | 409 {version, data} اگر کسِ دیگری زودتر پوش کرده
GET  file/?path=         → خودِ فایل
POST file/               multipart: path, sha1, file → {ok}
POST file/delete/        {path} → {ok}
"""
import hashlib
import json

from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.tenancy import get_current_org
from seo.api import token_required

from .models import SyncFile, SyncStore

MAX_FILE = 20 * 1024 * 1024  # nginx: client_max_body_size 25M


def _store(org):
    store, _ = SyncStore.objects.get_or_create(organization=org)
    return store


def _who(request, client=''):
    name = request.user.get_full_name() or request.user.username
    return f'{name} ({client})'[:150] if client else name[:150]


def _files(org):
    return [{'path': f.path, 'sha1': f.sha1, 'size': f.size, 'updated_at': int(f.updated_at.timestamp() * 1000)}
            for f in SyncFile.objects.filter(organization=org)]


def _state(store):
    return {'version': store.version, 'updated_at': store.updated_at.isoformat() if store.updated_at else None,
            'updated_by': store.updated_by, 'data': store.get_data(), 'files': _files(store.organization)}


def _token_org(request):
    """سازمانِ توکن — `token_required` قبلاً آن را در tenancy ست کرده."""
    return get_current_org()


def _clean_path(p):
    p = str(p or '').replace('\\', '/').strip('/')
    if not p or '..' in p.split('/') or len(p) > 500:
        return None
    return p


@csrf_exempt
@token_required
@require_http_methods(['GET', 'POST'])
def state(request):
    org = _token_org(request)
    store = _store(org)
    if request.method == 'GET':
        return JsonResponse(_state(store))
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'JSON نامعتبر'}, status=400)
    if not isinstance(body.get('data'), dict):
        return JsonResponse({'detail': 'data لازم است'}, status=400)
    # قفلِ خوش‌بینانه: فقط اگر برنامه آخرین نسخه را دیده باشد (به‌روزرسانیِ شرطی = اتمیک)
    try:
        base = int(body.get('base_version', -1))
    except (TypeError, ValueError):
        base = -1
    store.set_data(body['data'])
    now = timezone.now()
    who = _who(request, str(body.get('client', ''))[:60])
    n = SyncStore.objects.filter(pk=store.pk, version=base).update(
        data_enc=store.data_enc, version=base + 1, updated_at=now, updated_by=who)
    if not n:
        store.refresh_from_db()
        return JsonResponse({'detail': 'conflict', **_state(store)}, status=409)
    store.version = base + 1
    return JsonResponse({'version': store.version})


@csrf_exempt
@token_required
@require_http_methods(['GET', 'POST'])
def file(request):
    org = _token_org(request)
    if request.method == 'GET':
        p = _clean_path(request.GET.get('path'))
        f = SyncFile.objects.filter(organization=org, path=p).first() if p else None
        if not f or not f.file:
            return JsonResponse({'detail': 'پیدا نشد'}, status=404)
        return FileResponse(f.file.open('rb'), as_attachment=True, filename=p.split('/')[-1])
    p = _clean_path(request.POST.get('path'))
    up = request.FILES.get('file')
    if not p or not up:
        return JsonResponse({'detail': 'path و file لازم است'}, status=400)
    if up.size > MAX_FILE:
        return JsonResponse({'detail': 'حداکثر ۲۰ مگابایت'}, status=413)
    h = hashlib.sha1()
    for chunk in up.chunks():
        h.update(chunk)
    up.seek(0)
    obj = SyncFile.objects.filter(organization=org, path=p).first() or SyncFile(organization=org, path=p)
    obj.file = up  # فایلِ قبلی را django-cleanup پاک می‌کند
    obj.sha1, obj.size, obj.updated_by = h.hexdigest(), up.size, _who(request)
    obj.save()
    return JsonResponse({'ok': True, 'sha1': obj.sha1})


@csrf_exempt
@token_required
@require_http_methods(['POST'])
def file_delete(request):
    org = _token_org(request)
    try:
        p = _clean_path(json.loads(request.body or '{}').get('path'))
    except json.JSONDecodeError:
        p = None
    if p:
        for f in SyncFile.objects.filter(organization=org, path=p):
            f.delete()
    return JsonResponse({'ok': True})
