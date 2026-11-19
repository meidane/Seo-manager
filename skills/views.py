"""صفحهٔ «اسکیل‌ها» (مدیرِ دوستونه) + API. دیدن: همهٔ اعضا (اسکیلِ پروژه فقط برای پروژه‌های قابلِ‌دیدن)؛
ویرایش: پرمیشنِ `manage_skills`. هر ذخیره یک `SkillVersion` (source=web) می‌سازد.

ایندکس: index · api_save · api_detail (نسخه‌ها/حذف) · api_restore · api_duplicate · api_files (آپلود) · api_file (حذف/توضیح)
· api_detect (آزمایشِ تشخیص = همان چیزی که هوش مصنوعی می‌گیرد) · api_starters · public_file (لینکِ توکنی، بدونِ ورود)
"""
import json
import mimetypes

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.access import has_perm, require_perm
from core.templatetags.seo_extras import jalali, timeago
from projects.access import accessible_project_ids

from .mcp import ToolError, file_row, restore_version, save_file_bytes
from .models import Skill, SkillFile, SkillVersion

PERM = 'manage_skills'


def _visible(request):
    qs = Skill.objects.filter(deleted_at__isnull=True).select_related('project', 'updated_by').prefetch_related('task_types', 'files')
    return qs.filter(Q(project__isnull=True) | Q(project_id__in=accessible_project_ids(request)))


def _who(u):
    return (u.get_full_name() or u.username) if u else ''


def _frow(f):
    r = file_row(f)
    return {'id': r[0], 'name': r[1], 'kind': r[2], 'size': r[3], 'note': f.note, 'url': r[5]}


def _row(s):
    return {'id': s.id, 'scope': s.scope, 'project': s.project_id, 'project_name': s.project.name if s.project_id else '',
            'title': s.title, 'summary': s.summary, 'body': s.body, 'order': s.order, 'active': s.active,
            'apply': s.apply, 'category': s.category, 'tags': s.tags, 'types': [t.id for t in s.task_types.all()],
            'files': [_frow(f) for f in s.files.all() if not f.deleted_at],
            'by': _who(s.updated_by), 'ago': timeago(s.updated_at)}


def _one(pk):
    return _row(Skill.objects.select_related('project', 'updated_by').prefetch_related('task_types', 'files').get(pk=pk))


@login_required
def index(request):
    from projects.models import Project
    from tasks.models import TaskTypeDef

    from .starters import STARTERS
    projects = Project.objects.filter(id__in=accessible_project_ids(request), personal_owner__isnull=True).order_by('status', 'name')
    existing = set(Skill.objects.filter(deleted_at__isnull=True).values_list('title', flat=True))
    return render(request, 'skills/index.html', {
        'page_title': 'اسکیل‌ها', 'skills': [_row(s) for s in _visible(request)],
        'projects': projects, 'types': list(TaskTypeDef.objects.filter(is_active=True).order_by('order').values('id', 'name')),
        'starters': [{'key': x['key'], 'title': x['title'], 'summary': x['summary'], 'have': x['title'] in existing} for x in STARTERS],
        'can_edit': has_perm(request, PERM), 'sel_project': request.GET.get('project', ''),
        'mcp_ok': has_perm(request, 'manage_api_tokens'),
    })


def _body(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return {}


@login_required
@require_http_methods(['POST'])
def api_save(request):
    require_perm(request, PERM)
    d = _body(request)
    s = get_object_or_404(_visible(request), pk=d['id']) if d.get('id') else Skill()
    scope = d.get('scope') or Skill.GENERAL
    if scope not in dict(Skill.SCOPES):
        return JsonResponse({'detail': 'سطحِ نامعتبر'}, status=400)
    title = (d.get('title') or '').strip()[:200]
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    pid = d.get('project') or None
    if scope == Skill.PROJECT and (not pid or int(pid) not in accessible_project_ids(request)):
        return JsonResponse({'detail': 'پروژه را انتخاب کن'}, status=400)
    s.scope, s.project_id, s.title = scope, (int(pid) if scope == Skill.PROJECT else None), title
    s.summary = (d.get('summary') or '').strip()[:300]
    s.body = d.get('body') or ''
    s.apply = d.get('apply') if d.get('apply') in dict(Skill.APPLY) else Skill.AUTO
    s.category = (d.get('category') or '').strip()[:60]
    s.tags = (d.get('tags') or '').strip()[:400]
    s.order = int(d.get('order') or 0)
    s.active = d.get('active', True) is not False
    s.save(actor=request.user, source='web')
    if 'types' in d:
        s.task_types.set([int(t) for t in d.get('types') or []])
    return JsonResponse({'skill': _one(s.pk)})


@login_required
@require_http_methods(['GET', 'DELETE'])
def api_detail(request, pk):
    """GET = نسخه‌ها؛ DELETE = حذف (نرم)."""
    s = get_object_or_404(_visible(request), pk=pk)
    if request.method == 'DELETE':
        require_perm(request, PERM)
        s.deleted_at = timezone.now()
        s.save(actor=request.user)
        return JsonResponse({'ok': True})
    return JsonResponse({'versions': [
        {'id': v.id, 'title': v.title, 'summary': v.summary, 'body': v.body, 'by': _who(v.user), 'source': v.source,
         'note': v.note, 'date': jalali(v.created_at), 'time': timezone.localtime(v.created_at).strftime('%H:%M')}
        for v in s.versions.select_related('user')[:50]]})


@login_required
@require_http_methods(['POST'])
def api_restore(request, pk, vid):
    require_perm(request, PERM)
    s = get_object_or_404(_visible(request), pk=pk)
    restore_version(s, get_object_or_404(SkillVersion, pk=vid, skill=s), request.user)
    return JsonResponse({'skill': _one(s.pk)})


@login_required
@require_http_methods(['POST'])
def api_duplicate(request, pk):
    """کپی (مثلاً پروفایلِ یک پروژه برای پروژهٔ دیگر) — فایل‌ها هم کپی می‌شوند. body: {project?}."""
    require_perm(request, PERM)
    src = get_object_or_404(_visible(request), pk=pk)
    d = _body(request)
    new = Skill(scope=src.scope, project_id=src.project_id, title=f'{src.title} (کپی)', summary=src.summary, body=src.body,
                apply=src.apply, category=src.category, tags=src.tags, order=src.order)
    if d.get('project') and int(d['project']) in accessible_project_ids(request):
        new.scope, new.project_id, new.title = Skill.PROJECT, int(d['project']), src.title
    new.save(actor=request.user, source='web', note=f'کپی از #{src.pk}')
    new.task_types.set(src.task_types.all())
    for f in src.files.filter(deleted_at__isnull=True):
        with f.file.open('rb') as fh:
            save_file_bytes(new, f.name, fh.read(), request.user, f.note)
    return JsonResponse({'skill': _one(new.pk)})


@login_required
@require_http_methods(['POST'])
def api_files(request, pk):
    """آپلودِ یک یا چند فایل (multipart `file`)؛ هم‌نام → جایگزینیِ محتوا (لینک ثابت)."""
    require_perm(request, PERM)
    s = get_object_or_404(_visible(request), pk=pk)
    ups = request.FILES.getlist('file')
    if not ups:
        return JsonResponse({'detail': 'فایلی انتخاب نشده'}, status=400)
    try:
        for up in ups:
            save_file_bytes(s, up.name, up.read(), request.user)
    except ToolError as e:
        return JsonResponse({'detail': str(e)}, status=400)
    s.save(update_fields=['updated_at'])
    return JsonResponse({'skill': _one(s.pk)})


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def api_file(request, fid):
    require_perm(request, PERM)
    f = get_object_or_404(SkillFile, pk=fid, deleted_at__isnull=True)
    get_object_or_404(_visible(request), pk=f.skill_id)
    if request.method == 'DELETE':
        f.deleted_at = timezone.now()
        f.save(update_fields=['deleted_at'])
    else:
        f.note = (_body(request).get('note') or '').strip()[:300]
        f.save(update_fields=['note'])
    return JsonResponse({'skill': _one(f.skill_id)})


@login_required
@require_http_methods(['POST'])
def api_detect(request):
    """«آزمایشِ تشخیص»: همان `skills_start`ِ MCP — کدام پروژه/نوع و کدام اسکیل‌ها بار می‌شوند."""
    from .text import detect, select
    d = _body(request)
    org = request.organization
    det = detect(org, project=d.get('project'), type=d.get('type'), text=d.get('text') or '')
    load, avail = select(org, det['project'], det['type'], det['text'])
    from projects.models import Project
    from tasks.models import TaskTypeDef
    p = Project.objects.filter(pk=det['project']).first() if det['project'] else None
    t = TaskTypeDef.objects.filter(pk=det['type']).first() if det['type'] else None
    return JsonResponse({'project': p.name if p else '', 'type': t.name if t else '', 'how': det['how'],
                         'load': [{'id': s.id, 'title': s.title, 'why': why, 'chars': len(s.body)} for s, why in load],
                         'available': [{'id': s.id, 'title': s.title, 'why': why} for s, why in avail]})


@login_required
@require_http_methods(['POST'])
def api_starters(request):
    """ساختِ اسکیل‌های آماده (keys) یا «پروفایلِ پروژه» برای یک پروژه ({project})."""
    from tasks.models import TaskTypeDef

    from .starters import PROJECT_PROFILE, STARTERS
    require_perm(request, PERM)
    d = _body(request)
    made = []
    if d.get('project'):
        pid = int(d['project'])
        if pid not in accessible_project_ids(request):
            return JsonResponse({'detail': 'پروژه در دسترس نیست'}, status=403)
        x = PROJECT_PROFILE
        s = Skill(scope=Skill.PROJECT, project_id=pid, title=x['title'], summary=x['summary'], body=x['body'],
                  apply=x['apply'], category=x['category'])
        s.save(actor=request.user, source='web', note='قالبِ آماده')
        made.append(s.pk)
    for x in STARTERS:
        if x['key'] not in (d.get('keys') or []) or Skill.objects.filter(title=x['title'], deleted_at__isnull=True).exists():
            continue
        s = Skill(scope=x['scope'], title=x['title'], summary=x['summary'], body=x['body'], apply=x['apply'],
                  category=x.get('category', ''), tags=x.get('tags', ''))
        s.save(actor=request.user, source='web', note='اسکیلِ آماده')
        if x['key'] == 'article':
            s.task_types.set(TaskTypeDef.objects.filter(name__in=['انتشار', 'آپدیت']))
        elif x['key'] == 'reportage':
            s.task_types.set(TaskTypeDef.objects.filter(name='رپورتاژ'))
        made.append(s.pk)
    return JsonResponse({'skills': [_one(pk) for pk in made]})


def public_file(request, token, name=''):
    """لینکِ ضمیمه بدونِ ورود (توکنِ تصادفی) — برای خواندنِ هوش مصنوعی یا آپلودِ عکسِ نمونه به وردپرس."""
    f = SkillFile.all_objects.filter(token=token, deleted_at__isnull=True).first()
    if not f or not f.file:
        raise Http404
    try:
        fh = f.file.open('rb')
    except FileNotFoundError as e:
        raise Http404 from e
    ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
    if f.kind == 'text':
        ctype = 'text/plain; charset=utf-8'   # کد/HTML اجرا نشود، فقط نمایش
    inline = f.kind in ('image', 'text') or ctype == 'application/pdf'
    return FileResponse(fh, content_type=ctype, as_attachment=not inline, filename=f.name)
