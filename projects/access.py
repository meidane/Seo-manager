"""دسترسیِ پروژه‌محور — «فقط مالکِ سازمان و کسی که `view_all_projects` دارد همه‌چیز را
می‌بیند»؛ بقیه باید عضوِ `Project.members` باشند. منبعِ واحد؛ همه‌جا (پروژه‌ها/تسک‌ها/
تقویم/داشبورد/همکاران) از همین یک تابع می‌خوانند.

`view_all_projects` («فعال‌سازیِ همه‌ی پروژه‌ها») یک پرمیشنِ جداگانه است، مستقل از
`add_project`/`edit_project` — کسی می‌تواند همه‌ی پروژه‌ها را ببیند بدونِ اینکه بتواند
پروژه بسازد/ویرایش کند، یا برعکس بتواند پروژه بسازد ولی فقط پروژه‌های خودش را ببیند.
"""


def accessible_project_ids(request):
    """`None` = بدونِ محدودیت (مالکِ سازمان یا دارنده‌ی `view_all_projects`). وگرنه
    فهرستِ idِ پروژه‌هایی که همکارِ متصل‌به‌کاربرِ جاری عضوشان است (ممکن است خالی باشد)."""
    m = getattr(request, 'membership', None)
    if m and (m.role == 'owner' or m.can('view_all_projects')):
        return None
    colleague = getattr(request.user, 'colleague', None)
    if not colleague:
        return []
    from .models import Project
    return list(Project.objects.filter(members=colleague).values_list('id', flat=True))
