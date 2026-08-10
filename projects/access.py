"""دسترسیِ پروژه‌محور — «فقط مالکِ سازمان همه‌چیز را می‌بیند»؛ بقیه (حتی مدیر) باید
عضوِ `Project.members` باشند. منبعِ واحد؛ همه‌جا (پروژه‌ها/تسک‌ها/تقویم/داشبورد/
همکاران) از همین یک تابع می‌خوانند.
"""


def accessible_project_ids(request):
    """`None` = بدونِ محدودیت (مالکِ سازمان). وگرنه فهرستِ idِ پروژه‌هایی که
    همکارِ متصل‌به‌کاربرِ جاری عضوشان است (ممکن است خالی باشد)."""
    m = getattr(request, 'membership', None)
    if m and m.role == 'owner':
        return None
    colleague = getattr(request.user, 'colleague', None)
    if not colleague:
        return []
    from .models import Project
    return list(Project.objects.filter(members=colleague).values_list('id', flat=True))
