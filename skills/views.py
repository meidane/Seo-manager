"""صفحهٔ «اسکیل‌ها» (سایدبار) + APIِ ساده. دیدن: همهٔ اعضا (اسکیلِ پروژه فقط برای پروژه‌های قابلِ‌دیدن)؛
ویرایش: پرمیشنِ `manage_skills`. هر ذخیره یک `SkillVersion` (source=web) می‌سازد."""
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.access import has_perm, require_perm
from core.templatetags.seo_extras import jalali, timeago
from projects.access import accessible_project_ids

from .mcp import restore_version
from .models import Skill, SkillVersion

PERM = 'manage_skills'


def _visible(request):
    qs = Skill.objects.filter(deleted_at__isnull=True).select_related('project', 'updated_by')
    ids = accessible_project_ids(request)
    from django.db.models import Q
    return qs.filter(Q(project__isnull=True) | Q(project_id__in=ids))


def _who(u):
    return (u.get_full_name() or u.username) if u else ''


def _row(s):
    return {'id': s.id, 'scope': s.scope, 'project': s.project_id, 'project_name': s.project.name if s.project_id else '',
            'title': s.title, 'summary': s.summary, 'body': s.body, 'order': s.order, 'active': s.active,
            'by': _who(s.updated_by), 'ago': timeago(s.updated_at)}


@login_required
def index(request):
    from projects.models import Project
    ids = accessible_project_ids(request)
    projects = Project.objects.filter(id__in=ids, personal_owner__isnull=True).order_by('status', 'name')
    return render(request, 'skills/index.html', {
        'page_title': 'اسکیل‌ها', 'skills': [_row(s) for s in _visible(request)],
        'projects': projects, 'can_edit': has_perm(request, PERM), 'sel_project': request.GET.get('project', ''),
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
    if scope == Skill.PROJECT:
        if not pid or int(pid) not in accessible_project_ids(request):
            return JsonResponse({'detail': 'پروژه را انتخاب کن'}, status=400)
    s.scope, s.project_id, s.title = scope, (int(pid) if scope == Skill.PROJECT else None), title
    s.summary = (d.get('summary') or '').strip()[:300]
    s.body = d.get('body') or ''
    s.order = int(d.get('order') or 0)
    s.active = d.get('active', True) is not False
    s.save(actor=request.user, source='web')
    return JsonResponse({'skill': _row(Skill.objects.select_related('project', 'updated_by').get(pk=s.pk))})


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
    v = get_object_or_404(SkillVersion, pk=vid, skill=s)
    if not s:
        raise PermissionDenied
    restore_version(s, v, request.user)
    return JsonResponse({'skill': _row(Skill.objects.select_related('project', 'updated_by').get(pk=s.pk))})
