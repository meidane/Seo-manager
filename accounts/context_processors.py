"""سازمان و دسترسی‌های کاربر جاری را در دسترسِ همه‌ی تمپلیت‌ها می‌گذارد.

منبع: `request.organization` / `request.membership` که میدل‌ورِ CurrentOrgMiddleware
ست می‌کند (سازگار با سوییچرِ سازمان). همچنین فهرست سازمان‌های کاربر برای سوییچر.

در تمپلیت:  {{ current_org.name }} · {% if 'manage_people' in org_perms %}…{% endif %}
"""


def org(request):
    user = getattr(request, 'user', None)
    organization = getattr(request, 'organization', None)
    membership = getattr(request, 'membership', None)
    if not user or not user.is_authenticated or organization is None:
        return {}
    my_orgs = [m.organization for m in
               user.memberships.filter(is_active=True).select_related('organization')]
    return {
        'current_org': organization,
        'current_membership': membership,
        'org_perms': (membership.perms if membership else set()),
        'my_orgs': my_orgs,
    }
