"""ویوهای احراز هویت + مدیریت افراد و تیم‌ها (نسخه‌ی ساده‌ی چندشرکتی).

منبعِ سازمانِ جاری: `request.user.default_membership().organization`.
دسترسی‌ها با `Membership.can(perm)` بررسی می‌شوند (permissions.py).
"""
import json

from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from .models import Membership, Organization, Role, Team, TeamMembership, User, seed_roles
from .permissions import PERM_LABELS, PERMS


class LoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')


# ── کمکی ────────────────────────────────────────────────────────────────

def _require(request, perm):
    """سازمانِ جاری (از میدل‌ور) را برمی‌گرداند یا اگر دسترسی نبود، 403."""
    m = getattr(request, 'membership', None)
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
        role_objs = list(org.roles.all())
        ctx.update({
            'org': org,
            'rows': rows,
            'teams_flat': list(org.teams.select_related('parent').all()),
            'team_tree': _team_tree(org),
            'roles': [(r.key, r.name) for r in role_objs],
            'role_objs': role_objs,
            'all_perms': list(PERM_LABELS.items()),
            'perm_label_map': PERM_LABELS,
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
    role = d.get('role') if org.roles.filter(key=d.get('role')).exists() else 'member'
    u = User.objects.create_user(
        username=username, password=password,
        first_name=(d.get('first_name') or '').strip(),
        last_name=(d.get('last_name') or '').strip(),
        email=(d.get('email') or '').strip(),
        phone=(d.get('phone') or '').strip())
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
    if d.get('role') and org.roles.filter(key=d['role']).exists():
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


@login_required
@require_http_methods(['POST'])
def person_invite(request):
    """دعوتِ فردی که «قبلاً ثبت‌نام کرده» با شماره‌ی تماس، به سازمانِ جاری."""
    org = _require(request, 'manage_people')
    d = _body(request)
    phone = (d.get('phone') or '').strip()
    if not phone:
        return JsonResponse({'detail': 'شماره‌ی تماس لازم است'}, status=400)
    role = d.get('role') if org.roles.filter(key=d.get('role')).exists() else 'member'
    u = User.objects.filter(phone=phone).first()
    if not u:
        return JsonResponse({'detail': 'کاربری با این شماره ثبت‌نام نکرده است'}, status=400)
    if Membership.objects.filter(user=u, organization=org).exists():
        return JsonResponse({'detail': 'این فرد قبلاً عضو سازمان است'}, status=400)
    Membership.objects.create(user=u, organization=org, role=role)
    return JsonResponse({'ok': True}, status=201)


# ── API: نقش‌های سفارشی ───────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def role_create(request):
    org = _require(request, 'manage_org')
    d = _body(request)
    name = (d.get('name') or '').strip()
    if not name:
        return JsonResponse({'detail': 'نام نقش لازم است'}, status=400)
    perms = [p for p in (d.get('perms') or []) if p in PERMS]
    import re
    base = (re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_') or 'role')[:24]
    key, i = base, 1
    while org.roles.filter(key=key).exists():
        i += 1
        key = f'{base}{i}'
    r = Role.objects.create(organization=org, key=key, name=name, perms=perms, is_builtin=False)
    return JsonResponse({'id': r.id, 'key': r.key}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def role_edit(request, pk):
    org = _require(request, 'manage_org')
    r = get_object_or_404(Role, pk=pk, organization=org)
    if request.method == 'DELETE':
        if r.is_builtin:
            return JsonResponse({'detail': 'نقش پیش‌فرض حذف نمی‌شود'}, status=400)
        if Membership.objects.filter(organization=org, role=r.key).exists():
            return JsonResponse({'detail': 'این نقش به افرادی اختصاص دارد'}, status=400)
        r.delete()
        return JsonResponse({'ok': True})
    d = _body(request)
    if d.get('name'):
        r.name = d['name'].strip()
    if 'perms' in d and r.key != 'owner':  # مالک همیشه همه‌ی دسترسی‌ها
        r.perms = [p for p in d['perms'] if p in PERMS]
    r.save(update_fields=['name', 'perms'])
    return JsonResponse({'ok': True})


# ── سوییچرِ سازمان و ثبت‌نام ────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def switch_org(request):
    oid = _body(request).get('organization')
    if oid and request.user.memberships.filter(organization_id=oid, is_active=True).exists():
        request.session['active_org_id'] = int(oid)
        return JsonResponse({'ok': True})
    return JsonResponse({'detail': 'به این سازمان دسترسی نداری'}, status=403)


@require_http_methods(['GET', 'POST'])
def signup(request):
    """ثبت‌نامِ آزاد: کاربرِ مالک + سازمانِ جدید + نقش‌های پیش‌فرض."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    if request.method == 'GET':
        return render(request, 'registration/signup.html')

    p = request.POST
    org_name = (p.get('org_name') or '').strip()
    username = (p.get('username') or '').strip()
    password = p.get('password') or ''
    phone = (p.get('phone') or '').strip()
    full_name = (p.get('full_name') or '').strip()
    err = None
    if not (org_name and username and password):
        err = 'نام شرکت، نام‌کاربری و رمز الزامی است'
    elif User.objects.filter(username=username).exists():
        err = 'این نام‌کاربری قبلاً ثبت شده'
    elif len(password) < 6:
        err = 'رمز عبور حداقل ۶ کاراکتر باشد'
    if err:
        return render(request, 'registration/signup.html', {'error': err, 'form': p})

    first, _, last = full_name.partition(' ')
    with transaction.atomic():
        org = Organization.objects.create(name=org_name)
        seed_roles(org)
        user = User.objects.create_user(
            username=username, password=password, phone=phone,
            first_name=first, last_name=last)
        Membership.objects.create(user=user, organization=org, role='owner')
    login(request, user)
    request.session['active_org_id'] = org.id
    return redirect('dashboard:index')
