"""کوئری‌های مشترکِ تسک — منبعِ واحد برای هر جایی که همین منطق لازم است
(صفحه‌ی بازبینی + فیدِ بازبینیِ داشبورد + لیستِ تسک‌ها + لودِ تنبل + ویجتِ تایمر)،
تا چند جا به‌صورتِ موازی درست/نادرست نشوند."""
from datetime import date

from django.db.models import Q

from colleagues.access import all_subordinate_ids, is_manager_tier
from projects.access import accessible_project_ids

PAGE_SIZE = 50  # آستانه‌ی لودِ تنبلِ لیستِ تسک‌ها (اسکرول)


def reviewable_q(request):
    """این تسک برای کاربرِ جاری قابل‌بازبینی است؟ دو مسیرِ مستقلِ OR‌شده:
    (۱) `Task.needs_review=True` (پیش‌فرضش از `assignee.needs_review` می‌آید، ولی
    هرباره تسک قابلِ‌تغییرِ دستی است) و مسئولِ همین تسک **در هر عمقی** زیرِدستِ کاربرِ
    جاری است (`all_subordinate_ids` بالا — نه فقط مدیرِ مستقیم؛ مدیرِ یک مدیر هم زنجیره‌ای
    همین حق را دارد) — مستقل از دسترسیِ سازمانیِ `review` (تعیینِ مدیر یعنی اجازه‌ی
    بازبینیِ کارِ زیرمجموعه)؛ (۲) دسترسیِ سازمانیِ `review` (نظارتِ فراگیر، مستقل از
    زنجیره‌ی مدیریتی — مثلاً مالک/مدیرِ کل که شاید اصلاً `Colleague.manager` برایش ست
    نشده) → همه‌ی تسک‌های `needs_review` **و** همه‌ی `type_def.requires_review` را می‌بیند."""
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    sub_ids = all_subordinate_ids(my_colleague)
    q = Q(needs_review=True, assignee_id__in=sub_ids)
    if m and m.can('review'):
        q |= Q(needs_review=True) | Q(type_def__requires_review=True)
    return q


def build_task_queryset(request):
    """کوئری‌ستِ فیلترشده‌ی تسک‌ها بر اساسِ دسترسی + فیلترهای GET — منبعِ واحد برای
    `TaskListView` و APIِ لودِ تنبل (`api.task_rows_page`)، تا دو جا فیلترها را
    جداگانه (و شاید متفاوت) پیاده نکنند. بازه‌ی زمانی/گروه‌بندیِ روزانه اینجا نیست،
    چون آن دو به شکلِ فراخوان جدا اعمال می‌شوند.

    برمی‌گرداند: `(queryset, filters)` — `filters` کپیِ GET با یک تفاوت: اگر کاربر
    `view_other_tasks` نداشت، «سرپرست» هم نبود (پایین) و هیچ `assignee`ای هم
    انتخاب نکرده بود (بارِ اولِ صفحه)، پیش‌فرض روی خودش قفل می‌شود (درخواستِ کاربر:
    «به‌صورتِ پیش‌فرض فقط تسک‌های خودش») — قابلِ تغییر با انتخابِ «همه‌ی همکاران» در دراپ‌داون."""
    from .models import Task

    g = request.GET
    base = Task.objects.filter(is_placeholder=False).select_related('project', 'assignee', 'type_def').prefetch_related('type_def__fields')

    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    # «سرپرست»: کسی که زیرمجموعه‌ی مستقیم دارد یا پرمیشنِ سازمانیِ ناظر بر بقیه دارد
    # (review/manage_people/view_all_projects) — باید پیش‌فرض همه‌چیزِ قابل‌دسترس را
    # ببیند، نه فقط تسکِ خودش (نبودِ view_other_tasks همیشه اولویتِ محدودکننده دارد، پایین).
    has_reports = bool(my_colleague and my_colleague.reports.exists())
    manager_tier = is_manager_tier(request)

    # دسترسیِ پروژه‌محور: فقط مالک/دارنده‌ی view_all_projects همه را می‌بیند؛ بقیه فقط
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

    # view_other_tasks (مثبت/افزاینده): نبودش یعنی محدودیتِ سخت — فقط تسک‌های خودش
    # (نه پیش‌فرضِ قابل‌تغییر، برنده‌ی هرچیزِ دیگر). جایگزینِ نقشِ منفیِ own_tasks_only.
    forced_own = bool(m and not m.can('view_other_tasks'))
    if forced_own:
        base = base.filter(assignee_id=my_colleague.id if my_colleague else -1)

    filters = g.copy()
    if not forced_own and not manager_tier and my_colleague and 'assignee' not in g and 'group' not in g:
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
    if filters.get('report_month'):
        base = base.filter(report_month=filters['report_month'])
    if filters.get('report_year'):
        base = base.filter(report_year=filters['report_year'])
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
    """تسک‌های در حال اجرای تایمر — «چه کسی الان دارد کار می‌کند»: خودِ کاربر
    (`mine=True`، قابلِ استاپ) + بقیه (`mine=False`، فقط‌خواندنی، با نامِ فرد)، که
    دامنه‌شان بسته به جایگاهِ کاربر فرق می‌کند:
    - دسترسیِ سازمانیِ ناظر (`review`/`manage_people`/`view_all_projects`، مثلِ
      مالک/مدیرِ کل) → **همه‌ی** تایمرهای در حالِ اجرای کلِّ سازمان.
    - وگرنه، اگر زیرمجموعه دارد → خودش + زیرمجموعه‌ها در هر عمقی (نه فقط مستقیم؛
      `colleagues.access.all_subordinate_ids`).
    - وگرنه فقط خودش.
    منبعِ واحد برای ویجتِ سراسری (context processor، بارِ اول) و APIِ
    `/tasks/api/running/` (پلِ ۳۰ثانیه‌ای). **تله‌ی رفع‌شده:** قبلاً فقط زیرمجموعه‌ی
    مستقیم را می‌دید و اصلاً راهی برای دیدنِ سازمانی نداشت — مالک/مدیرِ کل که خودش
    مستقیماً مدیرِ کسی نیست، ویجتش همیشه خالی بود."""
    from .models import Task
    from colleagues.access import all_subordinate_ids

    colleague = getattr(request.user, 'colleague', None)
    m = getattr(request, 'membership', None)
    org_wide = bool(m and (m.can('review') or m.can('manage_people') or m.can('view_all_projects')))

    running = Task.objects.filter(timer_started_at__isnull=False).select_related('project', 'assignee')
    if org_wide:
        pass  # همه‌چیز
    elif colleague:
        sub_ids = all_subordinate_ids(colleague)
        running = running.filter(Q(assignee_id=colleague.id) | Q(assignee_id__in=sub_ids))
    else:
        return []

    my_id = colleague.id if colleague else None
    out = []
    for t in running:
        mine = t.assignee_id == my_id
        row = {
            'id': t.id, 'title': t.title, 'project': t.project.name if t.project_id else '',
            'spent': t.spent_minutes, 'started': t.timer_started_at.isoformat(), 'mine': mine,
        }
        if not mine:
            row['assignee'] = t.assignee.full_name if t.assignee_id else '—'
        out.append(row)
    out.sort(key=lambda r: not r['mine'])  # مالِ خودِ کاربر همیشه اول
    return out
