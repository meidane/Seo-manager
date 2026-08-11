"""کوئری‌های مشترکِ تسک — منبعِ واحد برای هر جایی که همین منطق لازم است
(صفحه‌ی بازبینی + فیدِ بازبینیِ داشبورد + لیستِ تسک‌ها + لودِ تنبل + ویجتِ تایمر)،
تا چند جا به‌صورتِ موازی درست/نادرست نشوند."""
from datetime import date

from django.db.models import Q

from projects.access import accessible_project_ids

PAGE_SIZE = 50  # آستانه‌ی لودِ تنبلِ لیستِ تسک‌ها (اسکرول)


def reviewable_q(request):
    """این تسک برای کاربرِ جاری قابل‌بازبینی است؟ دو مسیرِ مستقلِ OR‌شده:
    (۱) `assignee.needs_review=True` و مدیرِ همان همکار خودِ کاربر است (مستقل از
    دسترسیِ سازمانیِ `review`)؛ (۲) `type_def.requires_review=True`، فقط اگر کاربر
    دسترسیِ سازمانیِ `review` را داشته باشد."""
    m = getattr(request, 'membership', None)
    q = Q(assignee__needs_review=True, assignee__manager__user=request.user)
    if m and m.can('review'):
        q |= Q(type_def__requires_review=True)
    return q


def build_task_queryset(request):
    """کوئری‌ستِ فیلترشده‌ی تسک‌ها بر اساسِ دسترسی + فیلترهای GET — منبعِ واحد برای
    `TaskListView` و APIِ لودِ تنبل (`api.task_rows_page`)، تا دو جا فیلترها را
    جداگانه (و شاید متفاوت) پیاده نکنند. بازه‌ی زمانی/گروه‌بندیِ روزانه اینجا نیست،
    چون آن دو به شکلِ فراخوان جدا اعمال می‌شوند.

    برمی‌گرداند: `(queryset, filters)` — `filters` کپیِ GET با یک تفاوت: اگر کاربر
    محدودیتِ `own_tasks_only` نداشت، «سرپرست» هم نبود (پایین) و هیچ `assignee`ای هم
    انتخاب نکرده بود (بارِ اولِ صفحه)، پیش‌فرض روی خودش قفل می‌شود (درخواستِ کاربر:
    «به‌صورتِ پیش‌فرض فقط تسک‌های خودش») — قابلِ تغییر با انتخابِ «همه‌ی همکاران» در دراپ‌داون."""
    from .models import Task

    g = request.GET
    base = Task.objects.filter(is_placeholder=False).select_related('project', 'assignee', 'type_def')

    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    # «سرپرست»: کسی که زیرمجموعه‌ی مستقیم دارد یا پرمیشنِ سازمانیِ ناظر بر بقیه دارد
    # (review/manage_colleagues/manage_projects) — باید پیش‌فرض همه‌چیزِ قابل‌دسترس را
    # ببیند، نه فقط تسکِ خودش (own_tasks_only همیشه اولویتِ محدودکننده دارد، پایین).
    has_reports = bool(my_colleague and my_colleague.reports.exists())
    is_manager_tier = has_reports or bool(m and (
        m.can('review') or m.can('manage_colleagues') or m.can('manage_projects')))

    # دسترسیِ پروژه‌محور: فقط مالک/دارنده‌ی manage_projects همه را می‌بیند؛ بقیه فقط
    # پروژه‌هایی که عضوشان هستند — **به‌علاوه‌ی تسک‌هایی که خودشان مسئولش‌اند** (تسکِ
    # دلیگیت‌شده، حتی بیرون از پروژه) **و به‌علاوه‌ی تسک‌هایی که مسئولش زیرمجموعه‌ی
    # مستقیمِ خودشان است** (سرپرست باید کارِ زیرمجموعه‌هایش را ببیند، حتی در پروژه‌ای که
    # خودش عضو نیست — همان الگویی که ویجتِ تایمر/بازبینی از قبل دارند).
    ids = accessible_project_ids(request)
    if ids is not None:
        q = Q(project_id__in=ids)
        if my_colleague:
            q |= Q(assignee_id=my_colleague.id)
            if has_reports:
                q |= Q(assignee__manager_id=my_colleague.id)
        base = base.filter(q)

    # own_tasks_only: محدودیتِ سخت — فقط تسک‌های خودش (نه پیش‌فرضِ قابل‌تغییر، برنده‌ی هرچیزِ دیگر)
    forced_own = bool(m and m.can('own_tasks_only'))
    if forced_own:
        base = base.filter(assignee_id=my_colleague.id if my_colleague else -1)

    filters = g.copy()
    if not forced_own and not is_manager_tier and my_colleague and 'assignee' not in g and 'group' not in g:
        filters['assignee'] = str(my_colleague.id)

    if filters.get('project'):
        base = base.filter(project_id=filters['project'])
    if filters.get('assignee'):
        base = base.filter(assignee_id=filters['assignee'])
    if filters.get('type_def'):
        base = base.filter(type_def_id=filters['type_def'])
    elif filters.get('type'):  # سازگاری با لینک‌های قدیمی (نوع built-inِ خام)
        base = base.filter(task_type=filters['type'])
    if filters.get('status'):
        base = base.filter(status=filters['status'])
    if filters.get('priority'):
        base = base.filter(priority=filters['priority'])
    if filters.get('review'):
        base = base.filter(review_status=filters['review'])
    if filters.get('overdue') == '1':
        base = base.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today())
    if filters.get('q'):
        base = base.filter(title__icontains=filters['q'])

    return base, filters


def group_done_by_day(qs, start, end):
    """تسک‌های done در بازه، گروه‌بندی‌شده بر اساسِ `done_date` (جدیدترین روز اول).
    منبعِ واحد برای تفکیکِ روزانه‌ی صفحه‌ی تسک‌ها (`?group=day`) و جدولِ روزانه‌ی داشبورد."""
    from core.jalali import format_jalali

    from .models import Task
    day_qs = qs.filter(status=Task.DONE, done_date__range=(start, end)).order_by('-done_date', 'planned_time')
    groups = {}
    for t in day_qs:
        groups.setdefault(t.done_date, []).append(t)
    return [
        {'date': d, 'date_fa': format_jalali(d), 'tasks': ts, 'count': len(ts)}
        for d, ts in sorted(groups.items(), reverse=True)
    ]


def running_timers_payload(request):
    """تسک‌های در حال اجرای تایمر برای کاربرِ جاری: خودش (`mine=True`، قابلِ استاپ) +
    زیرمجموعه‌های مستقیمش اگر مدیرشان است (`mine=False`، فقط‌خواندنی، با نامِ فرد).
    منبعِ واحد برای ویجتِ سراسری (context processor، بارِ اول) و APIِ
    `/tasks/api/running/` (پلِ ۳۰ثانیه‌ای)."""
    from .models import Task

    colleague = getattr(request.user, 'colleague', None)
    if not colleague:
        return []
    mine = Task.objects.filter(
        timer_started_at__isnull=False, assignee_id=colleague.id).select_related('project')
    subs = Task.objects.filter(
        timer_started_at__isnull=False, assignee__manager_id=colleague.id).select_related('project', 'assignee')
    out = [{
        'id': t.id, 'title': t.title, 'project': t.project.name if t.project_id else '',
        'spent': t.spent_minutes, 'started': t.timer_started_at.isoformat(), 'mine': True,
    } for t in mine]
    out += [{
        'id': t.id, 'title': t.title, 'project': t.project.name if t.project_id else '',
        'spent': t.spent_minutes, 'started': t.timer_started_at.isoformat(), 'mine': False,
        'assignee': t.assignee.full_name,
    } for t in subs]
    return out
