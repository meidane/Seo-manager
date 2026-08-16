"""دسترسیِ پروژه‌محور — «فقط مالکِ سازمان و کسی که `view_all_projects` دارد همه‌چیز را
می‌بیند»؛ بقیه باید عضوِ `Project.members` باشند. منبعِ واحد؛ همه‌جا (پروژه‌ها/تسک‌ها/
تقویم/داشبورد/همکاران) از همین یک تابع می‌خوانند.

`view_all_projects` («فعال‌سازیِ همه‌ی پروژه‌ها») یک پرمیشنِ جداگانه است، مستقل از
`add_project`/`edit_project` — کسی می‌تواند همه‌ی پروژه‌ها را ببیند بدونِ اینکه بتواند
پروژه بسازد/ویرایش کند، یا برعکس بتواند پروژه بسازد ولی فقط پروژه‌های خودش را ببیند.

**پروژه‌ی «شخصی» (`personal_owner`)** یک استثنای امنیتیِ سخت است: **فقط** مالکش می‌بیند،
حتی مالکِ سازمان/سوپریوزر هم نباید پروژه‌ی شخصیِ دیگران را ببیند. برای همین این تابع
دیگر برای مالک `None` («بدونِ محدودیت») برنمی‌گرداند، بلکه همیشه فهرستی برمی‌گرداند که
پروژه‌های شخصیِ متعلق به دیگران از آن حذف شده‌اند — تنها نقطه‌ی enforcement.
"""


def accessible_project_ids(request):
    """فهرستِ idِ پروژه‌های قابل‌دیدنِ کاربرِ جاری (دیگر هیچ‌وقت `None` نیست، چون پروژه‌های
    شخصیِ دیگران باید همیشه حذف شوند — حتی برای مالک). ممکن است خالی باشد."""
    from django.db.models import Q

    from .models import Project

    colleague = getattr(request.user, 'colleague', None)
    m = getattr(request, 'membership', None)
    unrestricted = bool(m and (m.role == 'owner' or m.can('view_all_projects')))

    if unrestricted:
        qs = Project.objects.all()
    else:
        if not colleague:
            return []
        # عضوِ پروژه‌ها؛ پروژه‌ی شخصیِ خودِ کاربر هم چون عضوش است می‌آید.
        qs = Project.objects.filter(members=colleague)

    # پروژه‌ی شخصیِ متعلق به دیگران را همیشه حذف کن (شرطِ سخت، مستقل از پرمیشن)
    if colleague:
        qs = qs.exclude(Q(personal_owner__isnull=False) & ~Q(personal_owner=colleague))
    else:
        qs = qs.exclude(personal_owner__isnull=False)

    return list(qs.values_list('id', flat=True))
