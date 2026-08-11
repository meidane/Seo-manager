"""دسترسیِ پروژه‌محور — «فقط مالکِ سازمان و کسی که `manage_projects` دارد همه‌چیز را
می‌بیند»؛ بقیه باید عضوِ `Project.members` باشند. منبعِ واحد؛ همه‌جا (پروژه‌ها/تسک‌ها/
تقویم/داشبورد/همکاران) از همین یک تابع می‌خوانند.

**تله‌ی رفع‌شده:** قبلاً فقط `role == 'owner'` بدونِ محدودیت بود — نقشِ سفارشی‌ای که
`manage_projects` (یا هر ترکیبِ دیگری از دسترسی‌ها) داشت هم تا وقتی به‌صراحت به
`Project.members` هر پروژه اضافه نمی‌شد، عملاً هیچ پروژه/تسکی نمی‌دید (`ids=[]`) —
یعنی «دادنِ دسترسی» از تنظیمات عملاً بی‌اثر بود (نمی‌توانست حتی تسک بسازد). چون
`manage_projects` یعنی «مدیریتِ همه‌ی پروژه‌ها»، منطقاً باید مثلِ مالک نامحدود باشد."""


def accessible_project_ids(request):
    """`None` = بدونِ محدودیت (مالکِ سازمان یا دارنده‌ی `manage_projects`). وگرنه
    فهرستِ idِ پروژه‌هایی که همکارِ متصل‌به‌کاربرِ جاری عضوشان است (ممکن است خالی باشد)."""
    m = getattr(request, 'membership', None)
    if m and (m.role == 'owner' or m.can('manage_projects')):
        return None
    colleague = getattr(request.user, 'colleague', None)
    if not colleague:
        return []
    from .models import Project
    return list(Project.objects.filter(members=colleague).values_list('id', flat=True))
