"""صفحهٔ تنظیماتِ سرچ کنسول (`/settings/gsc/`) + APIِ کارتِ تسک و تبِ تحلیلِ پروژه.
ایندکس: page · save · test · sync_now (نخِ پس‌زمینه) · site_update · task_api · project_api"""
import json
import threading

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from accounts.access import require_perm
from projects.access import accessible_project_ids

from . import analysis
from .client import GSCError
from .models import GSCAccount, GSCCredential, GSCPageDay, GSCSite
from .sync import refresh_sites, sync_account

PERM = 'manage_api_tokens'


def _acc(org):
    return GSCAccount.objects.get_or_create(organization=org)[0]


def _site_row(s):
    return {'id': s.id, 'url': s.site_url, 'project': s.project_id, 'active': s.active, 'permission': s.permission,
            'credential': s.credential_id, 'synced_until': s.synced_until.isoformat() if s.synced_until else '', 'error': s.last_error}


@login_required
def page(request):
    from projects.models import Project
    org = require_perm(request, PERM)
    acc = _acc(org)
    sites = list(GSCSite.objects.filter(organization=org).select_related('project'))
    counts = {}
    for s in sites:
        counts[s.id] = GSCPageDay.objects.filter(site=s).values('page_key').distinct().count() if s.synced_until else 0
    return render(request, 'gsc/settings.html', {
        'page_title': 'سرچ کنسول', 'acc': acc,
        'sites': [{**_site_row(s), 'pages': counts[s.id]} for s in sites],
        'projects': Project.objects.filter(personal_owner__isnull=True).order_by('status', 'name'),
        'creds': GSCCredential.objects.filter(organization=org),
        'has_key': bool(acc.credentials_enc) or GSCCredential.objects.filter(organization=org).exists(),
    })


def _body(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return {}


@login_required
@require_http_methods(['POST'])
def save(request):
    org = require_perm(request, PERM)
    acc = _acc(org)
    d = _body(request)
    if d.get('json'):
        cred, err = _parse_key(d['json'])
        if err:
            return JsonResponse({'detail': err}, status=400)
        acc.credentials = cred
    if 'proxy' in d:
        acc.proxy = (d.get('proxy') or '').strip()
    if 'relay_url' in d:
        acc.relay_url = (d.get('relay_url') or '').strip().rstrip('/')
    if 'relay_key' in d and d.get('relay_key') != '••••':
        acc.relay_key = (d.get('relay_key') or '').strip()
    if d.get('days_back'):
        acc.days_back = max(7, min(int(d['days_back']), 480))
    acc.save()
    return JsonResponse({'ok': True, 'email': acc.client_email})


@login_required
@require_http_methods(['POST'])
def test(request):
    org = require_perm(request, PERM)
    acc = _acc(org)
    try:
        sites = refresh_sites(acc)
    except GSCError as e:
        acc.last_error = str(e)
        acc.save(update_fields=['last_error'])
        return JsonResponse({'detail': str(e)}, status=400)
    acc.last_error = ''
    acc.save(update_fields=['last_error'])
    return JsonResponse({'sites': [_site_row(s) for s in sites]})


@login_required
@require_http_methods(['POST'])
def sync_now(request):
    org = require_perm(request, PERM)
    acc = _acc(org)
    if acc.syncing:
        return JsonResponse({'detail': 'همگام‌سازی در حالِ اجراست'}, status=409)
    if not acc.credentials_enc and not GSCCredential.objects.filter(organization=org).exists():
        return JsonResponse({'detail': 'اول کلید را ثبت کن'}, status=400)

    def run():
        close_old_connections()
        try:
            sync_account(acc, log=lambda m: None)
        finally:
            close_old_connections()
    threading.Thread(target=run, daemon=True).start()
    return JsonResponse({'ok': True})


@login_required
def status(request):
    org = require_perm(request, PERM)
    acc = _acc(org)
    return JsonResponse({'syncing': acc.syncing, 'error': acc.last_error,
                         'sites': [_site_row(s) for s in GSCSite.objects.filter(organization=org)]})


@login_required
@require_http_methods(['POST'])
def site_update(request, pk):
    org = require_perm(request, PERM)
    s = get_object_or_404(GSCSite, pk=pk, organization=org)
    d = _body(request)
    if 'project' in d:
        s.project_id = int(d['project']) if d.get('project') else None
    if 'active' in d:
        s.active = bool(d['active'])
    if 'credential' in d:
        s.credential = get_object_or_404(GSCCredential, pk=d['credential'], organization=org) if d.get('credential') else None
    s.save()
    return JsonResponse({'site': _site_row(s)})


def _parse_key(raw):
    try:
        cred = json.loads(raw or '')
    except ValueError:
        return None, 'فایلِ JSON معتبر نیست'
    if cred.get('type') != 'service_account' or not cred.get('private_key'):
        return None, 'این فایل کلیدِ Service Account نیست (type=service_account)'
    return cred, ''


@login_required
@require_http_methods(['POST'])
def cred_add(request):
    """کلیدِ اضافه برای سایت‌های پرداده (body: {name, json})."""
    org = require_perm(request, PERM)
    d = _body(request)
    cred, err = _parse_key(d.get('json'))
    if err:
        return JsonResponse({'detail': err}, status=400)
    c = GSCCredential(organization=org, name=(d.get('name') or cred.get('client_email', ''))[:80])
    c.credentials = cred
    c.save()
    return JsonResponse({'id': c.id, 'email': c.client_email})


@login_required
@require_http_methods(['POST'])
def cred_delete(request, pk):
    org = require_perm(request, PERM)
    get_object_or_404(GSCCredential, pk=pk, organization=org).delete()   # سایت‌هایش به کلیدِ اصلی برمی‌گردند (SET_NULL)
    return JsonResponse({'ok': True})


@login_required
def task_api(request, pk):
    """کارتِ زیرِ تسک: کلماتِ ۳ ماهِ صفحهٔ تسک + نمودار + قبل/بعد (اگر انجام شده)."""
    from tasks.api import _task_visible_ok
    from tasks.models import Task
    t = get_object_or_404(Task.objects.select_related('type_def').prefetch_related('type_def__fields'), pk=pk)
    if not _task_visible_ok(request, t):
        raise PermissionDenied
    return JsonResponse({'pages': analysis.task_card(t)})


@login_required
def project_api(request, pk):
    from projects.models import Project
    if pk not in accessible_project_ids(request):
        raise PermissionDenied
    p = get_object_or_404(Project, pk=pk)
    return JsonResponse({'data': analysis.project_analysis(p),
                         'connected': GSCSite.objects.filter(project=p).exists()})
