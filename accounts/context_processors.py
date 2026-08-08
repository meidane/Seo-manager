"""سازمان و دسترسی‌های کاربر جاری را در دسترسِ همه‌ی تمپلیت‌ها می‌گذارد.

در تمپلیت:  {{ current_org.name }} · {% if 'manage_people' in org_perms %}…{% endif %}
"""


def org(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    m = user.default_membership()
    return {
        'current_org': m.organization if m else None,
        'current_membership': m,
        'org_perms': (m.perms if m else set()),
    }
