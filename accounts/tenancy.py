"""زیرساختِ چندشرکتی (tenant) — اسکوپِ خودکارِ داده به سازمانِ جاری.

الگو: سازمانِ جاری در یک thread-local نگه داشته می‌شود؛ مدل‌های tenant از
`TenantManager` استفاده می‌کنند که هر کوئری را به همان سازمان فیلتر می‌کند. این‌طور
به‌جای فیلترِ دستی در ده‌ها ویو، اسکوپ به‌صورت پیش‌فرض و ضدِنشتی اعمال می‌شود.

- خواندن: `Model.objects` → فیلترشده به سازمانِ جاری (اگر ست شده باشد).
- خواندنِ بدون فیلتر (migration/مدیریت/ادمین): `Model.all_objects`.
- نوشتن: هر مدلِ tenant در `save()` اگر `organization` خالی بود از سازمانِ جاری پر می‌کند.
- مسیرهای `/admin/` و درخواست‌های بدون کاربر، سازمانِ جاری ست نمی‌شود (فیلتر خاموش).
"""
import threading

from django.db import models

_state = threading.local()


def set_current_org(org):
    _state.org = org


def get_current_org():
    return getattr(_state, 'org', None)


def clear_current_org():
    _state.org = None


class TenantManager(models.Manager):
    """منیجرِ پیش‌فرضِ مدل‌های tenant — فیلترِ خودکار به سازمانِ جاری."""

    def get_queryset(self):
        qs = super().get_queryset()
        org = get_current_org()
        if org is not None:
            return qs.filter(organization=org)
        return qs


def stamp_org(instance):
    """کمکی برای مدل‌هایی که TenantModel را به‌ارث نمی‌برند: استمپِ سازمانِ جاری."""
    if getattr(instance, 'organization_id', None) is None:
        org = get_current_org()
        if org is not None:
            instance.organization = org


def resolve_active(request):
    """(organization, membership) فعالِ کاربر را از session/عضویت‌ها برمی‌گرداند."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None, None
    mships = list(user.memberships.filter(is_active=True).select_related('organization'))
    if not mships:
        return None, None
    by_org = {m.organization_id: m for m in mships}
    aid = request.session.get('active_org_id')
    m = by_org.get(aid) or mships[0]
    if request.session.get('active_org_id') != m.organization_id:
        request.session['active_org_id'] = m.organization_id
    return m.organization, m


class CurrentOrgMiddleware:
    """سازمانِ جاری را روی request و thread-local ست می‌کند (بعد از Authentication)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_org(None)
        request.organization = None
        request.membership = None
        try:
            if not request.path.startswith('/admin/'):
                org, m = resolve_active(request)
                request.organization = org
                request.membership = m
                set_current_org(org)
            return self.get_response(request)
        finally:
            clear_current_org()
