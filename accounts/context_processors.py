"""سازمان و دسترسی‌های کاربر جاری را در دسترسِ همه‌ی تمپلیت‌ها می‌گذارد.

منبع: `request.organization` / `request.membership` که میدل‌ورِ CurrentOrgMiddleware
ست می‌کند (سازگار با سوییچرِ سازمان). همچنین فهرست سازمان‌های کاربر برای سوییچر.

در تمپلیت:  {{ current_org.name }} · {% if 'manage_people' in org_perms %}…{% endif %}
"""


def org(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    from .models import Invite
    pending_invites = list(
        Invite.objects.filter(user=user, status=Invite.PENDING).select_related('organization'))

    organization = getattr(request, 'organization', None)
    if organization is None:
        return {'pending_invites': pending_invites}

    membership = getattr(request, 'membership', None)
    my_orgs = [m.organization for m in
               user.memberships.filter(is_active=True).select_related('organization')]
    perms = membership.perms if membership else set()
    if '*' in perms:  # مالک: '*' یعنی همه، ولی چک‌های تمپلیت رشته‌ی دقیق می‌خواهند
        from .permissions import PERMS
        perms = set(PERMS)
    from .permissions import SETTINGS_PERMS
    return {
        'current_org': organization,
        'current_membership': membership,
        'org_perms': perms,
        'my_orgs': my_orgs,
        'pending_invites': pending_invites,
        'has_settings_access': any(p in perms for p in SETTINGS_PERMS),
    }
