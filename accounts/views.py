"""ویوهای احراز هویت + مدیریت افراد و تیم‌ها (نسخه‌ی ساده‌ی چندشرکتی).

منبعِ سازمانِ جاری: `request.user.default_membership().organization`.
دسترسی‌ها با `Membership.can(perm)` بررسی می‌شوند (permissions.py).
"""
import json

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from .models import Membership, Team, TeamMembership, User
from .permissions import PERM_LABELS, ROLE_CHOICES


class LoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')


# ── کمکی ────────────────────────────────────────────────────────────────

def _current_org(request):
    m = request.user.default_membership()
    return m.organization if m else None


def _require(request, perm):
    """سازمانِ جاری را برمی‌گرداند یا اگر دسترسی نبود، 403."""
    m = request.user.default_membership()
    if not m or not m.can(perm):
        raise PermissionDenied('دسترسی کافی نداری')
    return m.organization


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _team_tree(org):
    """درختِ تیم‌ها (ریشه‌ها و زیرمجموعه‌هایشان) برای نمایش."""
    teams = list(org.teams.all())
    by_parent = {}
    for t in teams:
        by_parent.setdefault(t.parent_id, []).append(t)
    def node(t):
        return {'id': t.id, 'name': t.name,
                'children': [node(c) for c in by_parent.get(t.id, [])],
                'count': t.memberships.count()}
    return [node(t) for t in by_parent.get(None, [])]


# ── صفحه ────────────────────────────────────────────────────────────────

class PeopleView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/people.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = _require(self.request, 'manage_people')
        members = (Membership.objects.filter(organization=org)
                   .select_related('user').order_by('-joined_at'))
        # عضویت‌های تیمیِ هر کاربر در این سازمان
        tm = {}
        for x in TeamMembership.objects.filter(team__organization=org).select_related('team'):
            tm.setdefault(x.user_id, []).append(x.team)
        rows = []
        for m in members:
            rows.append({'m': m, 'teams': tm.get(m.user_id, [])})
        ctx.update({
            'org': org,
            'rows': rows,
            'teams_flat': list(org.teams.select_related('parent').all()),
            'team_tree': _team_tree(org),
            'roles': ROLE_CHOICES,
            'perm_labels': PERM_LABELS,
            'page_title': 'افراد و دسترسی‌ها',
        })
        return ctx


# ── API: تیم‌ها ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def team_create(request):
    org = _require(request, 'manage_org')
    d = _body(request)
    name = (d.get('name') or '').strip()
    if not name:
        return JsonResponse({'detail': 'نام تیم لازم است'}, status=400)
    parent = None
    if d.get('parent'):
        parent = get_object_or_404(Team, pk=d['parent'], organization=org)
    t = Team.objects.create(organization=org, name=name, parent=parent)
    return JsonResponse({'id': t.id, 'name': t.name}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def team_edit(request, pk):
    org = _require(request, 'manage_org')
    t = get_object_or_404(Team, pk=pk, organization=org)
    if request.method == 'DELETE':
        t.delete()  # زیرمجموعه‌ها و عضویت‌های تیمی هم CASCADE می‌شوند
        return JsonResponse({'ok': True})
    d = _body(request)
    if d.get('name'):
        t.name = d['name'].strip()
        t.save(update_fields=['name'])
    return JsonResponse({'ok': True})


# ── API: افراد ────────────────────────────────────────────────────────────

def _set_teams(user, org, team_ids):
    """عضویت‌های تیمیِ کاربر را در این سازمان با فهرست جدید هم‌گام کن."""
    valid = set(org.teams.filter(id__in=team_ids or []).values_list('id', flat=True))
    TeamMembership.objects.filter(user=user, team__organization=org).exclude(team_id__in=valid).delete()
    for tid in valid:
        TeamMembership.objects.get_or_create(user=user, team_id=tid)


@login_required
@require_http_methods(['POST'])
def person_create(request):
    org = _require(request, 'manage_people')
    d = _body(request)
    username = (d.get('username') or '').strip()
    password = d.get('password') or ''
    if not username or not password:
        return JsonResponse({'detail': 'نام‌کاربری و رمز لازم است'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'detail': 'این نام‌کاربری قبلاً ثبت شده'}, status=400)
    role = d.get('role') if d.get('role') in dict(ROLE_CHOICES) else 'member'
    u = User.objects.create_user(
        username=username, password=password,
        first_name=(d.get('first_name') or '').strip(),
        last_name=(d.get('last_name') or '').strip(),
        email=(d.get('email') or '').strip())
    Membership.objects.create(user=u, organization=org, role=role)
    _set_teams(u, org, d.get('teams'))
    return JsonResponse({'id': u.id}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def person_edit(request, pk):
    org = _require(request, 'manage_people')
    m = get_object_or_404(Membership, user_id=pk, organization=org)
    if request.method == 'DELETE':
        # فقط عضویتِ این سازمان حذف می‌شود؛ خودِ کاربر (شاید در سازمان دیگر) می‌ماند
        TeamMembership.objects.filter(user=m.user, team__organization=org).delete()
        m.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if d.get('role') in dict(ROLE_CHOICES):
        # نگذار آخرین مالک از مالکی خارج شود
        if m.role == 'owner' and d['role'] != 'owner' and \
           Membership.objects.filter(organization=org, role='owner').count() <= 1:
            return JsonResponse({'detail': 'حداقل یک مالک باید بماند'}, status=400)
        m.role = d['role']
    if 'is_active' in d:
        m.is_active = bool(d['is_active'])
    m.save(update_fields=['role', 'is_active'])
    for f in ('first_name', 'last_name', 'email'):
        if f in d:
            setattr(m.user, f, (d[f] or '').strip())
    m.user.save(update_fields=['first_name', 'last_name', 'email'])
    if 'teams' in d:
        _set_teams(m.user, org, d.get('teams'))
    return JsonResponse({'ok': True})
