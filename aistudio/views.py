"""API تبِ «AI»ی سینگلِ پروژه (JSON، بدونِ DRF).

گیتِ همه: پرمیشنِ سازمانیِ `project_ai` + دسترسی به همان پروژه (`accessible_project_ids`).
رمزها write-only: GET فقط `has_*` می‌دهد؛ PATCH با مقدارِ ناخالی ست می‌کند و با `clear` پاک.
"""
import json

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.access import require_perm
from core.jalali import format_jalali
from core.models import ActivityLog, Attachment
from projects.access import accessible_project_ids
from projects.models import Project

from .models import FILE_ROLE_KEYS, FILE_ROLES, AIPrompt, ProjectAI

MAX_FILE = 20 * 1024 * 1024


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _gate(request, project_id):
    """پرمیشن + دسترسی به پروژه؛ خودِ پروژه (اسکوپِ سازمان) را برمی‌گرداند."""
    require_perm(request, 'project_ai')
    ids = accessible_project_ids(request)
    if ids is not None and project_id not in ids:
        raise PermissionDenied('به این پروژه دسترسی نداری')
    return get_object_or_404(Project, pk=project_id)


def _config(project):
    cfg, _ = ProjectAI.objects.get_or_create(project=project)
    return cfg


def _file_json(a):
    return {'id': a.id, 'name': a.original_name or a.file.name.split('/')[-1], 'url': a.file.url,
            'is_image': a.is_image, 'size': a.size_h, 'role': a.role, 'description': a.description}


def _prompt_json(p):
    return {'id': p.id, 'title': p.title, 'task_type': p.task_type_id, 'body': p.body,
            'files': [_file_json(a) for a in p.files.all().order_by('uploaded_at')]}


def _config_json(cfg):
    return {
        'site_url': cfg.site_url, 'wp_username': cfg.wp_username,
        'has_wp_password': cfg.has_secret('wp_password'),
        'mcp_endpoint': cfg.mcp_endpoint, 'has_mcp_token': cfg.has_secret('mcp_token'),
        'general_prompt': cfg.general_prompt,
        'updated_fa': format_jalali(cfg.updated_at.date()) if cfg.pk and cfg.updated_at else '',
        'updated_by': (cfg.updated_by.get_full_name() or cfg.updated_by.username) if cfg.updated_by_id else '',
    }


@login_required
@require_http_methods(['GET', 'PATCH'])
def project_ai(request, pk):
    """GET: کلِ وضعیتِ تب (اتصال + پرامپتِ عمومی + پرامپت‌ها + گزینه‌ها). PATCH: اتصال/پرامپتِ عمومی."""
    project = _gate(request, pk)
    cfg = _config(project)
    if request.method == 'PATCH':
        d = _body(request)
        for f in ('site_url', 'wp_username', 'mcp_endpoint', 'general_prompt'):
            if f in d:
                setattr(cfg, f, (d[f] or '').strip() if f != 'general_prompt' else (d[f] or ''))
        changed = []
        for name in ProjectAI.SECRETS:
            if d.get(name):                       # مقدارِ جدید (خالی = بدونِ تغییر)
                cfg.set_secret(name, d[name].strip())
                changed.append(f'set:{name}')
        for name in d.get('clear') or []:
            if name in ProjectAI.SECRETS:
                cfg.set_secret(name, '')
                changed.append(f'clear:{name}')
        cfg.updated_by = request.user
        cfg.save()
        if changed:  # ردِّ ممیزی برای تغییرِ رمزها (بدونِ مقدار)
            ActivityLog.objects.create(actor=request.user, verb='ai_secret_change', content_object=cfg,
                                       changes={'project': project.name, 'secrets': changed})
    from tasks.models import TaskTypeDef
    return JsonResponse({
        'config': _config_json(cfg),
        'prompts': [_prompt_json(p) for p in project.ai_prompts.prefetch_related('files')],
        'task_types': [[t.id, t.name] for t in TaskTypeDef.objects.filter(is_active=True).order_by('order', 'id')],
        'roles': FILE_ROLES,
        'default_site_url': f'https://{project.domain}' if project.domain else '',
    })


@login_required
@require_http_methods(['POST'])
def project_ai_test(request, pk):
    """تستِ اتصالِ REST وردپرس **از سمتِ سرور** (users/me). رمز هرگز برنمی‌گردد.
    نتیجه این را هم نشان می‌دهد که سرورِ پنل اصلاً به سایت دسترسی دارد یا نه."""
    project = _gate(request, pk)
    cfg = _config(project)
    if not (cfg.site_url and cfg.wp_username and cfg.has_secret('wp_password')):
        return JsonResponse({'ok': False, 'message': 'اول آدرس سایت، نام کاربری و رمزِ برنامه را ذخیره کن.'})
    if not cfg.site_url.lower().startswith(('https://', 'http://')):
        return JsonResponse({'ok': False, 'message': 'آدرس سایت باید با https:// شروع شود.'})
    import requests
    url = cfg.site_url.rstrip('/') + '/wp-json/wp/v2/users/me?context=edit'
    try:
        r = requests.get(url, auth=(cfg.wp_username, cfg.get_secret('wp_password')),
                         timeout=12, allow_redirects=False)
    except requests.RequestException as e:
        return JsonResponse({'ok': False, 'message': f'سرورِ پنل به سایت دسترسی ندارد ({type(e).__name__}) — '
                                                     'اجرا باید از کامپیوترِ خودت (پلِ محلی) انجام شود.'})
    if r.status_code == 200:
        try:
            u = r.json()
        except ValueError:
            u = {}
        roles = '، '.join(u.get('roles') or [])
        return JsonResponse({'ok': True, 'message': f'اتصال برقرار است — کاربر: {u.get("name", "?")}' +
                                                    (f' ({roles})' if roles else '')})
    hints = {
        401: 'نام کاربری یا Application Password نادرست است، یا هاست هدرِ Authorization را حذف می‌کند.',
        403: 'سطحِ دسترسیِ این کاربرِ وردپرس کافی نیست.',
        404: 'REST API وردپرس در این آدرس پیدا نشد.',
    }
    msg = hints.get(r.status_code, 'پاسخِ غیرمنتظره.')
    if 300 <= r.status_code < 400:
        msg = 'سایت ریدایرکت می‌کند — آدرسِ نهایی (با/بدونِ www یا https) را وارد کن.'
    return JsonResponse({'ok': False, 'message': f'HTTP {r.status_code}: {msg}'})


@login_required
@require_http_methods(['POST'])
def prompt_create(request, pk):
    project = _gate(request, pk)
    d = _body(request)
    last = project.ai_prompts.order_by('-order').first()
    p = AIPrompt.objects.create(project=project, title=(d.get('title') or 'پرامپتِ جدید')[:120],
                                order=(last.order + 1) if last else 0)
    return JsonResponse(_prompt_json(p), status=201)


def _prompt_gate(request, prompt_id):
    p = get_object_or_404(AIPrompt.objects.select_related('project'), pk=prompt_id)
    _gate(request, p.project_id)
    return p


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def prompt_detail(request, pk):
    p = _prompt_gate(request, pk)
    if request.method == 'DELETE':
        p.delete()  # GenericRelation → فایل‌ها هم حذف (django-cleanup فایلِ دیسک را پاک می‌کند)
        return JsonResponse({'ok': True})
    d = _body(request)
    if 'title' in d:
        p.title = (d['title'] or '').strip()[:120] or 'بدونِ عنوان'
    if 'body' in d:
        p.body = d['body'] or ''
    if 'task_type' in d:
        from tasks.models import TaskTypeDef
        tid = d['task_type'] or None
        p.task_type = TaskTypeDef.objects.filter(pk=tid).first() if tid else None  # اسکوپِ سازمان
    p.save()
    return JsonResponse(_prompt_json(p))


@login_required
@require_http_methods(['POST'])
def prompt_files(request, pk):
    """آپلودِ یک یا چند فایل برای یک پرامپت (multipart، کلیدِ `file`)."""
    p = _prompt_gate(request, pk)
    ct = ContentType.objects.get_for_model(AIPrompt)
    role = request.POST.get('role', '')
    created, skipped = [], []
    for f in request.FILES.getlist('file'):
        if f.size > MAX_FILE:
            skipped.append(f.name)
            continue
        a = Attachment.objects.create(
            content_type=ct, object_id=p.id, file=f, original_name=f.name, size=f.size,
            mime=f.content_type or '', uploaded_by=request.user,
            role=role if role in FILE_ROLE_KEYS else '')
        created.append(_file_json(a))
    return JsonResponse({'files': created, 'skipped': skipped}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def prompt_file_detail(request, pk):
    """ویرایشِ توضیح/کاربرد یا حذفِ فایلِ پرامپت. فقط پیوست‌هایی که واقعاً مالِ یک AIPrompt‌اند
    (نه فایل‌های پروژه/تسک — وگرنه این اندپوینت دریچه‌ای به هر Attachment می‌شد)."""
    ct = ContentType.objects.get_for_model(AIPrompt)
    a = get_object_or_404(Attachment, pk=pk, content_type=ct)
    _prompt_gate(request, a.object_id)
    if request.method == 'DELETE':
        a.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    fields = []
    if 'description' in d:
        a.description = d['description'] or ''
        fields.append('description')
    if 'role' in d:
        a.role = d['role'] if d['role'] in FILE_ROLE_KEYS else ''
        fields.append('role')
    if fields:
        a.save(update_fields=fields)
    return JsonResponse(_file_json(a))
