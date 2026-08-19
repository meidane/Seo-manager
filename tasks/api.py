"""API‌های JSON تسک — بدون DRF، فقط JsonResponse.

توابع کمکی برای پارس تاریخ شمسی و اعمال فیلدهای مجاز روی تسک اینجا متمرکز
شده‌اند تا هم create و هم update از یک منبع بخوانند.
"""
import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.jalali import parse_jalali, today_jalali
from core.models import Holiday
from projects.access import accessible_project_ids

from . import history as taskhistory
from .models import Task, TaskComment


def _stop_timer(task):
    """اگر تایمرِ تسک در حالِ اجراست، متوقفش کن (زمانِ سپری‌شده را به spent_minutes
    اضافه کن) — روی نمونه اعمال می‌شود، بدونِ save (فراخوان خودش ذخیره می‌کند).
    هرجا وضعیت به DONE/PENDING می‌رود («تکمیلِ کار») باید صدا زده شود."""
    if not task.timer_started_at:
        return
    elapsed = int((timezone.now() - task.timer_started_at).total_seconds() // 60)
    task.spent_minutes = (task.spent_minutes or 0) + max(0, elapsed)
    task.timer_started_at = None


def _task_perm_ok(request, task, perm):
    """دسترسیِ ویرایش/حذفِ یک تسکِ مشخص: نقش باید `perm` را داشته باشد؛ اگر
    `view_other_tasks` نداشت، فقط روی تسکِ خودش (assignee = همکارِ متصل به کاربر)."""
    m = getattr(request, 'membership', None)
    if not m or not m.can(perm):
        return False
    if not m.can('view_other_tasks'):
        colleague = getattr(request.user, 'colleague', None)
        return bool(colleague and task.assignee_id == colleague.id)
    return True


def _is_own_task(request, task):
    """این تسک مسئولش خودِ کاربرِ جاری است؟ («تسکِ دلیگیت‌شده» — مستقل از edit_task/
    عضویتِ پروژه: کسی که کاری برایش تعریف شده باید بتواند خودش را ببیند/انجامش دهد،
    حتی اگر عضوِ آن پروژه یا دارای دسترسیِ ویرایشِ عمومیِ تسک نباشد)."""
    colleague = getattr(request.user, 'colleague', None)
    return bool(colleague and task.assignee_id == colleague.id)


def can_manage_any_timer(m):
    """می‌تواند تایمرِ تسکِ **هرکسِ دیگری** را هم استارت/استاپ کند (نه فقط خودش)؟
    `edit_time` (پرمیشنِ صریح، برای ویرایشِ دستیِ زمان هم لازم است) یا `edit_task`
    به‌همراهِ `view_other_tasks` (کسی که به‌طورِ کلی مسئولِ مدیریتِ تسک‌هاست، منطقی است
    که بتواند تایمرشان را هم کنترل کند — نیازی به تیک‌زدنِ جداگانه‌ی `edit_time` نیست
    فقط برای دکمه‌ی پلی؛ آن پرمیشن مخصوصِ ویرایشِ دستیِ عددِ زمان می‌ماند)."""
    return bool(m and (m.can('edit_time') or (m.can('edit_task') and m.can('view_other_tasks'))))


def _task_visible_ok(request, task):
    """این تسک برای کاربرِ جاری قابل‌مشاهده است؟ پروژه‌اش در فهرستِ دسترسی است، یا
    خودش مسئولِ همین تسک است (تسکِ دلیگیت‌شده بیرون از پروژه)."""
    ids = accessible_project_ids(request)
    if ids is None or task.project_id in ids:
        return True
    return _is_own_task(request, task)

# فیلدهایی که مستقیم از بدنه‌ی JSON پذیرفته می‌شوند (بقیه محاسباتی/سیستمی‌اند)
TEXT_FIELDS = [
    'title', 'description', 'seo_title', 'keywords', 'lsi_keywords',
    'published_url', 'source_url', 'media_name', 'anchor_text', 'target_url',
    'update_type', 'link_type', 'review_note',
]
CHOICE_FIELDS = ['task_type', 'status', 'priority']
INT_FIELDS = ['word_count', 'current_rank', 'link_count', 'estimate_minutes', 'report_month', 'report_year']
DECIMAL_FIELDS = ['media_cost']
BOOL_FIELDS = ['needs_review']
FK_FIELDS = {'project': 'project_id', 'assignee': 'assignee_id'}


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _pdate(value):
    """رشته‌ی شمسی → date میلادی؛ خالی → None."""
    if not value:
        return None
    try:
        return parse_jalali(value)
    except (ValueError, TypeError):
        return None


def apply_fields(task: Task, data: dict):
    """اعمال فیلدهای مجاز از dict روی نمونه‌ی تسک (بدون save)."""
    for f in TEXT_FIELDS + CHOICE_FIELDS:
        if f in data:
            setattr(task, f, data[f] or '')
    if 'description' in data:
        from core.htmlsan import clean_html
        task.description = clean_html(data['description'])
    for f in INT_FIELDS:
        if f in data:
            setattr(task, f, data[f] or None)
    # ماهِ گزارش بدونِ سال → پیش‌فرض سالِ جالیِ جاری (نمایشِ «مرداد ۱۴۰۵» همیشه سال دارد)
    if task.report_month and not task.report_year:
        task.report_year = today_jalali().year
    for f in DECIMAL_FIELDS:
        if f in data:
            setattr(task, f, data[f] or None)
    for f in BOOL_FIELDS:
        if f in data:
            setattr(task, f, bool(data[f]))
    for key, attr in FK_FIELDS.items():
        if key in data:
            setattr(task, attr, data[key] or None)
    if 'type_def' in data:
        task.type_def_id = data['type_def'] or None
        # task_type (builtin_key) را با نوعِ انتخاب‌شده هم‌گام کن — رنگ/BUCKET/فیلترِ نوع از آن می‌آید
        if task.type_def_id:
            from .models import TaskTypeDef
            td = TaskTypeDef.objects.filter(pk=task.type_def_id).first()
            if td:
                task.task_type = td.builtin_key or Task.OTHER
    if 'custom' in data and isinstance(data['custom'], dict):
        task.custom = data['custom']
    # اگر نوعِ سفارشی یک فیلد را «منبع تعداد کلمه» علامت زده باشد، word_count را از آن پر کن
    if task.type_def_id and isinstance(task.custom, dict):
        src = task.type_def.fields.filter(is_word_source=True).first()
        if src and task.custom.get(src.key) not in (None, ''):
            try:
                task.word_count = int(task.custom[src.key])
            except (ValueError, TypeError):
                pass
    if 'planned_date_iso' in data and data['planned_date_iso']:
        # از drag تقویم می‌آید: میلادی ISO
        try:
            task.planned_date = date.fromisoformat(data['planned_date_iso'])
        except (ValueError, TypeError):
            pass
    if 'planned_date' in data:
        d = _pdate(data['planned_date'])
        if d:
            task.planned_date = d
    if 'planned_time' in data and data['planned_time']:
        task.planned_time = data['planned_time']
    if 'done_date' in data:
        task.done_date = _pdate(data['done_date'])
    # تسکِ نیازمندِ بازبینی نمی‌تواند مستقیم «انجام‌شده» شود — فقط «تکمیل/در انتظارِ
    # بازبینی»؛ فقط تاییدِ مدیر (task_review) آن را DONE می‌کند (پایینِ همین فایل).
    if task.needs_review and task.status == Task.DONE:
        task.status = Task.PENDING
    # اگر وضعیت به «انجام شده» رفت و done_date خالی بود، امروز را بگذار
    if task.status == Task.DONE and not task.done_date:
        task.done_date = date.today()
    # تسکِ «نیاز به اصلاح» که دوباره انجام شد → «بررسی‌نشده» (برای بازبینی مجدد مدیر)
    if task.status in (Task.DONE, Task.PENDING) and task.review_status == Task.NEEDS_FIX:
        task.review_status = Task.UNREVIEWED
    # تکمیل/انجام‌شدنِ کار یعنی دیگر کاری روی آن در جریان نیست — تایمرِ فعال را استاپ کن
    if task.status in (Task.DONE, Task.PENDING):
        _stop_timer(task)


@login_required
@require_http_methods(['GET'])
def form_data(request):
    """داده‌ی لازم برای مودال تسک (پروژه‌ها، همکاران، انواع built-in و سفارشی).
    مودال هنگام باز شدن این را یک‌بار می‌گیرد تا از هر صفحه‌ای کار کند."""
    from colleagues.models import Colleague, ensure_colleague_for_user
    from projects.models import Project

    from .models import ReportPeriod, TaskTypeDef

    if getattr(request, 'organization', None):
        ensure_colleague_for_user(request.user, request.organization)
    # همه‌ی پروژه‌های قابل‌دسترسِ کاربر (فعال‌ها اول) — نه فقط فعال؛ وگرنه اگر پروژه‌ای
    # غیرفعال شود یا هیچ پروژه‌ی فعالی نباشد، دراپ‌داونِ مودال خالی می‌شود و ذخیره‌ی تسک
    # با خطای «عنوان و پروژه لازم است» شکست می‌خورد. **قابل‌دسترس‌بودن** هم اینجا رعایت
    # می‌شود، وگرنه تسکی که در پروژه‌ی خارج از دسترس ساخته شود بلافاصله در لیست ناپدید
    # می‌شود (چون TaskListView با همین فهرست فیلتر می‌کند).
    ids = accessible_project_ids(request)
    projects = Project.objects.order_by('status', 'name')
    if ids is not None:
        projects = projects.filter(id__in=ids)
    m = getattr(request, 'membership', None)
    own_tasks_only = bool(m and not m.can('view_other_tasks'))
    my_colleague = getattr(request.user, 'colleague', None)
    return JsonResponse({
        # [id, name, color, logo_url] — logo/color برای دراپ‌داونِ غنیِ مودال (richselect)
        'projects': [[p.id, p.name, p.color, (p.logo.url if p.logo else '')] for p in projects],
        # [id, name, needs_review, color, avatar_url]
        'colleagues': [[c.id, c.full_name, c.needs_review, c.color, (c.avatar.url if c.avatar else '')]
                        for c in Colleague.objects.filter(status=Colleague.ACTIVE)],
        'typeChoices': list(Task.TYPE_CHOICES),
        'reportMonths': list(Task.REPORT_MONTH_CHOICES),  # [[1,'فروردین'],…] برای دراپ‌داونِ «ماه گزارش»
        'reportYear': today_jalali().year,  # پیش‌فرضِ سالِ گزارش (جالیِ جاری)
        # ماه‌های گزارشِ تعریف‌شده در تنظیمات (منبعِ واحد) — [[value,label],…] value='سال-ماه'
        'reportPeriods': [[p.value, p.label] for p in ReportPeriod.objects.all()],
        'customTypes': [
            {'id': t.id, 'name': t.name, 'color': t.color, 'icon': t.icon,
             'builtin_key': t.builtin_key, 'fields': t.schema(),
             'kpis': [k.to_dict() for k in t.kpis.prefetch_related('items')]}
            for t in TaskTypeDef.objects.filter(is_active=True).prefetch_related('kpis')
        ],
        'myColleagueId': my_colleague.id if my_colleague else None,
        'ownTasksOnly': own_tasks_only,
        'editTask': bool(m and m.can('edit_task')),
        'deleteTask': bool(m and m.can('delete_task')),
        # هرکسی که پروفایلِ همکار دارد می‌تواند برای خودش تسکِ جدید بسازد، حتی بدونِ
        # edit_task — مودال با این پرچم دکمه‌ی ذخیره را برای «تسکِ جدید» نشان می‌دهد و
        # دراپ‌داونِ مسئول را روی خودش قفل می‌کند (اگر edit_task هم نداشته باشد).
        'createTask': bool(my_colleague),
    })


@login_required
@require_http_methods(['POST'])
def task_restore(request, pk):
    """بازیابیِ تسکِ حذف‌شده (از سطلِ زباله). نیازمندِ `delete_task`."""
    task = get_object_or_404(Task.objects.deleted(), pk=pk)
    if not _task_perm_ok(request, task, 'delete_task'):
        return JsonResponse({'detail': 'دسترسیِ بازیابیِ این تسک را نداری'}, status=403)
    task.deleted_at = None
    task.deleted_by = None
    task.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])
    taskhistory.record(task, taskhistory.TaskHistory.RESTORED, request.user)
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['GET'])
def task_rows_page(request):
    """صفحه‌بندیِ جعبه‌ی «انجام‌شده‌ها» برای لودِ تنبل (اسکرول، بیش از PAGE_SIZE تا) —
    فقط این جعبه صفحه‌بندی دارد؛ «این‌هفته/عقب‌افتاده» و «آینده» طبیعتاً محدودند
    (`tasks/views.py: BOX_CAP`). همان فیلترها/دسترسیِ TaskListView را از
    `build_task_queryset` می‌گیرد تا با صفحه‌ی اول (رندرِ سرور) دقیقاً هماهنگ بماند."""
    from django.template.loader import render_to_string

    from colleagues.models import Colleague
    from core.columns import visible_task_columns
    from projects.models import Project

    from .models import TaskTypeDef
    from .queries import PAGE_SIZE, build_task_queryset

    base, filters = build_task_queryset(request)
    if filters.get('group') == 'day':
        return JsonResponse({'detail': 'صفحه‌بندی برای حالتِ تفکیکِ روزانه نیست'}, status=400)
    try:
        page = max(1, int(request.GET.get('page') or 1))
    except (TypeError, ValueError):
        page = 1
    qs = base.filter(status=Task.DONE).order_by('-done_date', '-id')
    start_i, end_i = (page - 1) * PAGE_SIZE, page * PAGE_SIZE
    rows = list(qs[start_i:end_i])
    has_more = qs[end_i:end_i + 1].exists()
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    ids = accessible_project_ids(request)
    visible_projects = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
    html = render_to_string('tasks/_rows.html', {
        'tasks': rows,
        'can_edit_task': bool(m and m.can('edit_task')),
        'can_edit_time': bool(m and m.can('edit_time')),
        'can_manage_any_timer': can_manage_any_timer(m),
        'my_colleague_id': my_colleague.id if my_colleague else None,
        'extra_columns': visible_task_columns(filters.get('type_def')),
        'editable': bool(m and m.can('edit_task')) and bool(filters.get('type_def')),
        'status_choices': Task.STATUS_CHOICES,
        'all_projects': visible_projects.order_by('status', 'name'),
        'all_colleagues': Colleague.objects.order_by('status', 'full_name'),
        'all_types': TaskTypeDef.objects.filter(is_active=True),
    }, request=request)
    return JsonResponse({'html': html, 'has_more': has_more, 'page': page})


@login_required
@require_http_methods(['GET'])
def task_row(request, pk):
    """رندرِ یک ردیفِ تنها (`_rows.html`) — برای درج/جایگزینیِ بدونِ رفرش بعد از ذخیرهٔ مودال."""
    from django.template.loader import render_to_string

    from colleagues.models import Colleague
    from core.columns import visible_task_columns
    from projects.models import Project

    from .models import TaskTypeDef

    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'دسترسی نداری'}, status=403)
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    ids = accessible_project_ids(request)
    visible_projects = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
    html = render_to_string('tasks/_rows.html', {
        'tasks': [task],
        'can_edit_task': bool(m and m.can('edit_task')),
        'can_edit_time': bool(m and m.can('edit_time')),
        'can_manage_any_timer': can_manage_any_timer(m),
        'my_colleague_id': my_colleague.id if my_colleague else None,
        'extra_columns': visible_task_columns(request.GET.get('type_def')),
        'editable': bool(m and m.can('edit_task')) and bool(request.GET.get('type_def')),
        'hide_project': request.GET.get('hide_project') == '1',
        'status_choices': Task.STATUS_CHOICES,
        'all_projects': visible_projects.order_by('status', 'name'),
        'all_colleagues': Colleague.objects.order_by('status', 'full_name'),
        'all_types': TaskTypeDef.objects.filter(is_active=True),
    }, request=request)
    return JsonResponse({'html': html})


def _publish_url_error(task):
    """تسک انتشارِ «انجام‌شده» بدون لینک انتشار مجاز نیست (الزام لینک؛ فقط برای نوعِ
    built-inِ قدیمیِ publish — انواعِ سفارشیِ جدید از `_custom_fields_error` پایین
    استفاده می‌کنند، `required`/`required_on_done` روی خودِ فیلد)."""
    if task.task_type == Task.PUBLISH and task.status == Task.DONE and not task.published_url:
        return 'برای تسک انتشارِ انجام‌شده، وارد کردن «لینک انتشار» الزامی است.'
    return None


def _field_is_empty(field, value):
    if field.kind == field.TAGS:
        return not isinstance(value, list) or len(value) == 0
    return value in (None, '', [])


def _custom_fields_error(task):
    """فیلدهای سفارشیِ الزامیِ نوعِ تسک را چک می‌کند — `required`(همیشه) و
    `required_on_done`(فقط وقتی وضعیت done است). منبعِ واحدِ این اعتبارسنجی؛ در
    `task_create`/`task_detail` PATCH/`task_status` هر سه صدا زده می‌شود (مثلِ
    `_publish_url_error`، همان الگو)."""
    if not task.type_def_id:
        return None
    custom = task.custom or {}
    for f in task.type_def.fields.all():
        value = custom.get(f.key)
        empty = _field_is_empty(f, value)
        if f.required and empty:
            return f'فیلدِ «{f.label}» الزامی است.'
        if f.required_on_done and task.status == Task.DONE and empty:
            return f'برای تکمیلِ این تسک، «{f.label}» الزامی است.'
    return None


@login_required
@require_http_methods(['POST'])
def task_create(request):
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    can_edit = bool(m and m.can('edit_task'))
    # بدونِ edit_task هم هرکسی با پروفایلِ همکار می‌تواند برای خودش تسک بسازد
    # (نبودِ view_other_tasks نسخه‌ی محدودکننده‌ی همین چیز است، نه یک قابلیتِ جدا)
    if not can_edit and not my_colleague:
        return JsonResponse({'detail': 'دسترسیِ ساختِ تسک را نداری'}, status=403)
    data = _body(request)
    if not data.get('title') or not data.get('project'):
        return JsonResponse({'detail': 'عنوان و پروژه لازم است'}, status=400)
    ids = accessible_project_ids(request)
    if ids is not None and int(data['project']) not in ids:
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    if not can_edit or (m and not m.can('view_other_tasks')):
        data['assignee'] = my_colleague.id if my_colleague else None
    # پیش‌فرضِ «نیاز به بازبینی»: اگر کلاینت صریحاً نفرستاده بود، از تنظیمِ خودِ
    # مسئول (Colleague.needs_review) می‌آید — مودال معمولاً این را از قبل پر می‌فرستد،
    # این‌جا فقط برای مسیرهای دیگر (بولک/افزونه) که مودال را دور می‌زنند.
    if 'needs_review' not in data and data.get('assignee'):
        from colleagues.models import Colleague
        assignee = Colleague.objects.filter(pk=data['assignee']).first()
        if assignee:
            data['needs_review'] = assignee.needs_review
    task = Task(created_by=request.user, planned_date=date.today())
    apply_fields(task, data)
    err = _publish_url_error(task) or _custom_fields_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
    taskhistory.record(task, taskhistory.TaskHistory.CREATED, request.user)
    # تکرارشونده: قاعده را بساز و اولین پیش‌نما را تولید کن (تولید تنبل)
    rec = data.get('recurrence')
    if rec and rec.get('freq'):
        _attach_recurrence(task, rec)
    return JsonResponse(task.to_dict(), status=201)


def _attach_recurrence(task, rec):
    """قاعده‌ی تکرار را بساز، به تسک وصل کن و اولین پیش‌نما را تولید کن."""
    from .models import RecurrenceRule
    from .recurrence import start_series
    freq = rec.get('freq')
    if freq not in dict(RecurrenceRule.FREQ_CHOICES):
        return
    weekdays = ''
    if isinstance(rec.get('weekdays'), list):
        weekdays = ','.join(str(int(x)) for x in rec['weekdays'] if str(x).isdigit())
    rule = RecurrenceRule.objects.create(
        freq=freq, interval=max(1, int(rec.get('interval') or 1)),
        weekdays=weekdays, start_date=task.planned_date,
        end_date=_pdate(rec.get('end_date')) or None,
        count=int(rec['count']) if rec.get('count') else None,
        skip_holidays=bool(rec.get('skip_holidays', True)))
    task.recurrence = rule
    task.save(update_fields=['recurrence'])
    start_series(task)


@login_required
@require_http_methods(['GET', 'PATCH', 'DELETE'])
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'به این تسک دسترسی نداری'}, status=403)
    if request.method == 'GET':
        # نمای کامل برای پرکردن مودال ویرایش
        d = task.to_dict()
        d.update({
            'update_type': task.update_type, 'priority': task.priority,
            'description': task.description, 'seo_title': task.seo_title,
            'keywords': task.keywords, 'lsi_keywords': task.lsi_keywords,
            'source_url': task.source_url, 'current_rank': task.current_rank,
            'estimate_minutes': task.estimate_minutes, 'media_name': task.media_name,
            'media_cost': str(task.media_cost) if task.media_cost else '',
            'anchor_text': task.anchor_text, 'target_url': task.target_url,
            'link_type': task.link_type, 'link_count': task.link_count,
            'review_status': task.review_status, 'review_note': task.review_note,
            'review_notes': _review_notes(task),
            'type_def': task.type_def_id, 'custom': task.custom or {},
            'recurrence': task.recurrence_id, 'report_month': task.report_month,
            'report_year': task.report_year,
            'history': _history_payload(task),
        })
        return JsonResponse(d)
    if request.method == 'DELETE':
        if not _task_perm_ok(request, task, 'delete_task'):
            return JsonResponse({'detail': 'دسترسیِ حذفِ این تسک را نداری'}, status=403)
        # حذفِ نرم — به سطلِ زباله می‌رود (قابلِ بازیابی از تبِ «حذف‌شده‌ها»)
        _stop_timer(task)
        task.deleted_at = timezone.now()
        task.deleted_by = request.user
        task.save(update_fields=['deleted_at', 'deleted_by', 'spent_minutes', 'timer_started_at', 'updated_at'])
        taskhistory.record(task, taskhistory.TaskHistory.DELETED, request.user)
        return JsonResponse({'ok': True})
    # PATCH
    if not _task_perm_ok(request, task, 'edit_task'):
        return JsonResponse({'detail': 'دسترسیِ ویرایشِ این تسک را نداری'}, status=403)
    data = _body(request)
    ids = accessible_project_ids(request)
    if 'project' in data and data['project'] and ids is not None and int(data['project']) not in ids:
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    m = getattr(request, 'membership', None)
    if m and not m.can('view_other_tasks'):
        colleague = getattr(request.user, 'colleague', None)
        data['assignee'] = colleague.id if colleague else None
    was_done = task.status == Task.DONE
    before = taskhistory.snapshot(task)
    apply_fields(task, data)
    err = _publish_url_error(task) or _custom_fields_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
    changes = taskhistory.diff(task, before)
    if changes:
        taskhistory.record(task, taskhistory.TaskHistory.UPDATED, request.user, changes)
    if not was_done and task.status == Task.DONE and task.recurrence_id and not task.is_placeholder:
        from .recurrence import advance
        advance(task)
    return JsonResponse(task.to_dict())


@login_required
@require_http_methods(['PATCH'])
def task_status(request, pk):
    """تغییر سریع وضعیت (دراپ‌داون ردیف و drag کانبان). مسئولِ خودِ تسک هم می‌تواند
    وضعیتِ تسکِ خودش را عوض کند (تمامش کند)، حتی بدونِ edit_task — دلیگیت‌شده."""
    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'به این تسک دسترسی نداری'}, status=403)
    if not _task_perm_ok(request, task, 'edit_task') and not _is_own_task(request, task):
        return JsonResponse({'detail': 'دسترسیِ ویرایشِ این تسک را نداری'}, status=403)
    data = _body(request)
    new_status = data.get('status')
    if new_status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'detail': 'وضعیت نامعتبر'}, status=400)
    # تسکِ نیازمندِ بازبینی مستقیم «انجام‌شده» نمی‌شود — فقط «تکمیل/در انتظارِ بازبینی»
    if task.needs_review and new_status == Task.DONE:
        new_status = Task.PENDING
    old_status = task.status
    was_done = task.status == Task.DONE
    task.status = new_status
    fields = ['status', 'done_date', 'updated_at']
    if new_status == Task.DONE and not task.done_date:
        task.done_date = date.today()
    # تسکی که «نیاز به اصلاح» بوده، با انجام‌شدنِ دوباره به «بررسی‌نشده» برمی‌گردد
    # تا مدیر دوباره بازبینی کند.
    if new_status in (Task.DONE, Task.PENDING) and task.review_status == Task.NEEDS_FIX:
        task.review_status = Task.UNREVIEWED
        fields.append('review_status')
    # تکمیل/انجام‌شدنِ کار یعنی دیگر کاری روی آن در جریان نیست — تایمرِ فعال را استاپ کن
    if new_status in (Task.DONE, Task.PENDING):
        _stop_timer(task)
        fields += ['spent_minutes', 'timer_started_at']
    err = _publish_url_error(task) or _custom_fields_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save(update_fields=fields)
    if old_status != new_status:
        taskhistory.record(task, taskhistory.TaskHistory.UPDATED, request.user,
                           {'وضعیت': [dict(Task.STATUS_CHOICES).get(old_status, old_status),
                                      dict(Task.STATUS_CHOICES).get(new_status, new_status)]})
    # تکرارشونده: با ورود به «انجام‌شده» رخدادِ بعدی تولید می‌شود (یک‌بار)
    if not was_done and new_status == Task.DONE and task.recurrence_id and not task.is_placeholder:
        from .recurrence import advance
        advance(task)
    return JsonResponse(task.to_dict())


@login_required
@require_http_methods(['GET'])
def running_timers(request):
    """تسک‌های در حال اجرای تایمر برای کاربرِ جاری (+ زیرمجموعه‌هایش) — ویجتِ سراسری."""
    from .queries import running_timers_payload
    return JsonResponse({'running': running_timers_payload(request)})


@login_required
@require_http_methods(['POST', 'PATCH'])
def task_timer(request, pk):
    """تایمرِ کارِ تسک. POST {action:start|stop}: مسئولِ خودِ تسک، یا کسی که
    `can_manage_any_timer` (edit_time یا edit_task-به‌همراهِ-view_other_tasks) دارد — یعنی
    مدیر/سرپرست هم می‌تواند تایمرِ تسکِ دیگران را استارت/استاپ کند، نه فقط خودشان.
    استارتِ یک تسک هر تایمرِ دیگرِ در حالِ اجرای همان مسئول را خودکار استاپ می‌کند
    (هر مسئول هم‌زمان فقط یک تایمرِ فعال). PATCH {minutes} (ویرایشِ دستیِ عدد): فقط edit_time."""
    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'به این تسک دسترسی نداری'}, status=403)
    m = getattr(request, 'membership', None)
    can_edit_time = bool(m and m.can('edit_time'))
    if request.method == 'PATCH':
        if not can_edit_time:
            return JsonResponse({'detail': 'دسترسیِ ویرایشِ زمان را نداری'}, status=403)
        try:
            task.spent_minutes = max(0, int(_body(request).get('minutes') or 0))
        except (ValueError, TypeError):
            return JsonResponse({'detail': 'عدد نامعتبر'}, status=400)
        task.save(update_fields=['spent_minutes', 'updated_at'])
        return JsonResponse({'spent_minutes': task.spent_minutes, 'timer_running': bool(task.timer_started_at)})
    # POST start/stop — مسئولِ خودِ تسک، یا کسی که اجازه‌ی مدیریتِ تایمرِ دیگران را دارد
    if not _is_own_task(request, task) and not can_manage_any_timer(m):
        return JsonResponse({'detail': 'دسترسیِ استارت/استاپِ تایمرِ این تسک را نداری'}, status=403)
    action = _body(request).get('action')
    now = timezone.now()
    stopped = None
    # تسکِ انجام‌شده تایمرش قابلِ استارت نیست (تکمیل‌شده — کار تمام است)
    if action == 'start' and task.status == Task.DONE:
        return JsonResponse({'detail': 'تسکِ انجام‌شده تایمر ندارد'}, status=400)
    if action == 'start' and not task.timer_started_at:
        # هر کاربر هم‌زمان فقط یک تایمرِ فعال — تایمرِ دیگرِ همین مسئول را خودکار استاپ کن
        if task.assignee_id:
            other = Task.objects.filter(
                assignee_id=task.assignee_id, timer_started_at__isnull=False).exclude(pk=task.pk).first()
            if other:
                elapsed_o = int((now - other.timer_started_at).total_seconds() // 60)
                other.spent_minutes = (other.spent_minutes or 0) + max(0, elapsed_o)
                other.timer_started_at = None
                other.save(update_fields=['spent_minutes', 'timer_started_at', 'updated_at'])
                stopped = {'id': other.id, 'spent_minutes': other.spent_minutes}
        task.timer_started_at = now
        fields = ['timer_started_at', 'updated_at']
        # پلی‌زدن یعنی کار شروع شد — وضعیت به «در حال انجام» می‌رود (فقط از «در انتظار»)
        if task.status == Task.TODO:
            task.status = Task.DOING
            fields.append('status')
        task.save(update_fields=fields)
    elif action == 'stop' and task.timer_started_at:
        elapsed = int((now - task.timer_started_at).total_seconds() // 60)
        task.spent_minutes = (task.spent_minutes or 0) + max(0, elapsed)
        task.timer_started_at = None
        task.save(update_fields=['spent_minutes', 'timer_started_at', 'updated_at'])
    elif action not in ('start', 'stop'):
        return JsonResponse({'detail': 'action نامعتبر'}, status=400)
    resp = {'spent_minutes': task.spent_minutes, 'timer_running': bool(task.timer_started_at),
            'timer_started': task.timer_started_at.isoformat() if task.timer_started_at else None}
    if stopped:
        resp['stopped_id'] = stopped['id']
        resp['stopped_spent'] = stopped['spent_minutes']
    return JsonResponse(resp)


@login_required
@require_http_methods(['PATCH'])
def task_review(request, pk):
    """تایید / نیاز به اصلاح (از فید بازبینی و صفحه‌ی بازبینی). مجاز برای کسی که
    دسترسیِ سازمانیِ `review` دارد، یا در زنجیره‌ی مدیریتیِ همکارِ این تسک باشد (مدیرِ
    مستقیم یا مدیرِ مدیرش، در هر عمقی — همان معیارِ `queries.reviewable_q`)."""
    from colleagues.access import all_subordinate_ids

    task = get_object_or_404(Task, pk=pk)
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    is_org_reviewer = bool(m and m.can('review'))
    is_in_manager_chain = bool(task.assignee_id and task.assignee_id in all_subordinate_ids(my_colleague))
    if not is_org_reviewer and not is_in_manager_chain:
        return JsonResponse({'detail': 'دسترسیِ بازبینیِ این تسک را نداری'}, status=403)
    data = _body(request)
    status = data.get('review_status')
    if status not in dict(Task.REVIEW_CHOICES):
        return JsonResponse({'detail': 'وضعیت بازبینی نامعتبر'}, status=400)
    from core.htmlsan import clean_html
    task.review_status = status
    note_html = ''
    if 'review_note' in data:
        note_html = clean_html(data['review_note'])
        task.review_note = note_html
    task.reviewed_by = request.user
    task.reviewed_at = timezone.now()
    fields = ['review_status', 'review_note', 'reviewed_by', 'reviewed_at', 'updated_at']
    # «نیاز به اصلاح» → تسک از حالت انجام‌شده/تکمیل‌شده برمی‌گردد تا دوباره انجام شود
    if status == Task.NEEDS_FIX and task.status in (Task.DONE, Task.PENDING):
        task.status = Task.DOING
        task.done_date = None
        fields += ['status', 'done_date']
    # «تایید» → تسکِ «تکمیل/در انتظارِ بازبینی» رسماً «انجام‌شده» می‌شود (تنها راهِ رسیدن
    # به DONE برای تسکِ needs_review همین‌جاست، نه دراپ‌داونِ وضعیت).
    elif status == Task.APPROVED and task.status == Task.PENDING:
        task.status = Task.DONE
        if not task.done_date:
            task.done_date = date.today()
        _stop_timer(task)
        fields += ['status', 'done_date', 'spent_minutes', 'timer_started_at']
    task.save(update_fields=fields)
    # ثبت در تاریخچه‌ی نیاز به اصلاح (فقط وقتی needs_fix با یادداشت است)
    if status == Task.NEEDS_FIX and note_html:
        from .models import TaskReviewNote
        TaskReviewNote.objects.create(task=task, note=note_html, author=request.user)
    return JsonResponse({'ok': True, 'review_status': task.review_status, 'status': task.status})


def _history_payload(task):
    """تاریخچه‌ی تسک برای مودال (جدیدترین اول)."""
    from core.jalali import format_jalali
    out = []
    has_created = False
    for h in task.history.select_related('user')[:60]:
        lt = timezone.localtime(h.created_at)
        if h.action == taskhistory.TaskHistory.CREATED:
            has_created = True
        out.append({
            'action': h.action, 'action_label': h.get_action_display(),
            'user': (h.user.get_full_name() or h.user.get_username()) if h.user else 'سیستم',
            'when': format_jalali(lt) + ' ' + lt.strftime('%H:%M'),
            'changes': h.changes or {},
        })
    # تسک‌های قدیمی (پیش از افزودنِ تاریخچه) رکوردِ «ساخته شد» ندارند — از created_at بساز
    if not has_created and task.created_at:
        lt = timezone.localtime(task.created_at)
        out.append({
            'action': 'created', 'action_label': 'ساخته شد',
            'user': (task.created_by.get_full_name() or task.created_by.get_username()) if task.created_by else 'سیستم',
            'when': format_jalali(lt) + ' ' + lt.strftime('%H:%M'),
            'changes': {},
        })
    return out


def _review_notes(task):
    """تاریخچه‌ی نیاز به اصلاح برای مودال (جدیدترین اول)."""
    from django.utils import timezone as _tz
    from core.jalali import format_jalali
    out = []
    for n in task.review_notes.select_related('author'):
        lt = _tz.localtime(n.created_at)
        out.append({
            'note': n.note,
            'author': n.author.get_full_name() or n.author.get_username() if n.author else '',
            'when': format_jalali(lt) + ' ' + lt.strftime('%H:%M'),
        })
    return out


# ── API: KPI (نمایش به کارمند + امتیازدهیِ مدیر) ───────────────────────────

@login_required
@require_http_methods(['GET'])
def task_kpis(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'به این تسک دسترسی نداری'}, status=403)
    kpis = list(task.type_def.kpis.prefetch_related('items')) if task.type_def_id else []
    scores = {s.kpi_id: s for s in task.kpi_scores.all()}
    out, total, cap = [], 0, 0
    for k in kpis:
        s = scores.get(k.id)
        kd = k.to_dict()
        kd['given'] = s.score if s else None
        kd['checked'] = s.checked_items if s else []
        out.append(kd)
        cap += k.cap
        total += (s.score if s else 0)
    return JsonResponse({
        'kpis': out, 'total': total, 'cap': cap, 'has': bool(kpis),
        'quality_score': task.quality_score,
    })


@login_required
@require_http_methods(['POST'])
def task_quality_score(request, pk):
    """امتیازِ سادهٔ ۱ تا ۱۰ برای وقتی نوعِ تسک هیچ KPIای ندارد (جایگزینِ سیستمِ کامل)."""
    task = get_object_or_404(Task, pk=pk)
    try:
        score = int(_body(request).get('score'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'امتیازِ نامعتبر'}, status=400)
    if not 1 <= score <= 10:
        return JsonResponse({'detail': 'امتیاز باید بین ۱ تا ۱۰ باشد'}, status=400)
    task.quality_score = score
    task.save(update_fields=['quality_score'])
    return JsonResponse({'ok': True, 'quality_score': task.quality_score})


@login_required
@require_http_methods(['POST'])
def task_kpi_score(request, pk):
    from .models import TaskKPIScore, TaskTypeKPI
    task = get_object_or_404(Task, pk=pk)
    for item in _body(request).get('scores', []):
        kpi = TaskTypeKPI.objects.filter(pk=item.get('kpi'), type_def_id=task.type_def_id).first()
        if not kpi:
            continue
        score = max(0, min(int(item.get('score') or 0), kpi.cap or kpi.max_score))
        TaskKPIScore.objects.update_or_create(
            task=task, kpi=kpi,
            defaults={'score': score, 'checked_items': item.get('checked_items') or [],
                      'scored_by': request.user})
    return JsonResponse({'ok': True})


# ── API: حذفِ کلِ سریِ تکرار ────────────────────────────────────────────────

@login_required
@require_http_methods(['DELETE'])
def recurrence_delete(request, pk):
    from .models import RecurrenceRule
    rule = get_object_or_404(RecurrenceRule, pk=pk)  # org-scoped
    # تسک‌های آینده/انجام‌نشده و پیش‌نماها حذف؛ تسک‌های انجام‌شده می‌مانند (recurrence=None)
    Task.all_objects.filter(recurrence=rule).exclude(status=Task.DONE).delete()
    rule.delete()
    return JsonResponse({'ok': True})


def _next_workday(d: date, holidays: set) -> date:
    """اگر روز تعطیل بود (جمعه یا در جدول)، به اولین روز کاری بعد برو."""
    while d.weekday() == 3 or d in holidays:  # weekday()==3 → جمعه (Mon=0)
        d += timedelta(days=1)
    return d


@login_required
@require_http_methods(['POST'])
def task_bulk(request):
    """عملیات گروهی: تغییر/جابه‌جایی تاریخ، مسئول، وضعیت، پروژه، انجام‌شده."""
    m = getattr(request, 'membership', None)
    if not m or not m.can('edit_task'):
        return JsonResponse({'detail': 'دسترسیِ ویرایشِ تسک را نداری'}, status=403)
    data = _body(request)
    ids = data.get('ids', [])
    action = data.get('action')
    qs = Task.objects.filter(id__in=ids)
    if not m.can('view_other_tasks'):
        colleague = getattr(request.user, 'colleague', None)
        qs = qs.filter(assignee_id=colleague.id if colleague else -1)
    if not ids or not action:
        return JsonResponse({'detail': 'ids و action لازم است'}, status=400)

    skip_holidays = data.get('skip_holidays')
    holidays = set(Holiday.objects.filter(is_off=True).values_list('date', flat=True)) if skip_holidays else set()

    if action == 'set_date':
        d = _pdate(data.get('date'))
        if not d:
            return JsonResponse({'detail': 'تاریخ نامعتبر'}, status=400)
        for t in qs:
            t.planned_date = _next_workday(d, holidays) if skip_holidays else d
            t.save(update_fields=['planned_date', 'updated_at'])
    elif action == 'shift_date':
        days = int(data.get('days', 0))
        for t in qs:
            nd = t.planned_date + timedelta(days=days)
            t.planned_date = _next_workday(nd, holidays) if skip_holidays else nd
            t.save(update_fields=['planned_date', 'updated_at'])
    elif action == 'set_assignee':
        qs.update(assignee_id=data.get('assignee') or None)
    elif action == 'set_status':
        qs.update(status=data.get('status'))
    elif action == 'set_project':
        qs.update(project_id=data.get('project'))
    elif action == 'mark_done':
        dd = _pdate(data.get('done_date')) or date.today()
        qs.update(status=Task.DONE, done_date=dd)
    else:
        return JsonResponse({'detail': 'action ناشناخته'}, status=400)

    return JsonResponse({'ok': True, 'count': len(ids)})


def _comment_dict(c, user):
    """یک گزارش (کامنت) برای فرانت؛ `mine` = قابل ویرایش/حذف توسط کاربر فعلی."""
    from django.utils import timezone as _tz
    from core.jalali import format_jalali
    lt = _tz.localtime(c.created_at)
    return {
        'id': c.id,
        'author': (c.author.get_full_name() or c.author.get_username()) if c.author else '',
        'body': c.body,
        'at': format_jalali(lt) + ' ' + lt.strftime('%H:%M'),
        'mine': bool(c.author_id == user.id or user.is_staff),
    }


@login_required
@require_http_methods(['GET', 'POST'])
def task_comments(request, pk):
    """گزارش‌های کار روی یک تسک (لیست/افزودن). بدنه HTML (TinyMCE) پاکسازی می‌شود."""
    task = get_object_or_404(Task, pk=pk)
    if not _task_visible_ok(request, task):
        return JsonResponse({'detail': 'به این تسک دسترسی نداری'}, status=403)
    if request.method == 'GET':
        items = [_comment_dict(c, request.user) for c in task.comments.select_related('author')]
        return JsonResponse({'comments': items})
    from core.htmlsan import clean_html
    body = clean_html(_body(request).get('body', '')).strip()
    if not body:
        return JsonResponse({'detail': 'متن گزارش لازم است'}, status=400)
    c = TaskComment.objects.create(task=task, author=request.user, body=body)
    return JsonResponse(_comment_dict(c, request.user), status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def task_comment_edit(request, pk):
    """ویرایش/حذف یک گزارش — فقط نویسنده یا کاربر ادمین."""
    c = get_object_or_404(TaskComment, pk=pk)
    if not (c.author_id == request.user.id or request.user.is_staff):
        return JsonResponse({'detail': 'اجازه‌ی این کار را نداری'}, status=403)
    if request.method == 'DELETE':
        c.delete()
        return JsonResponse({'ok': True})
    from core.htmlsan import clean_html
    body = clean_html(_body(request).get('body', '')).strip()
    if not body:
        return JsonResponse({'detail': 'متن گزارش لازم است'}, status=400)
    c.body = body
    c.save(update_fields=['body'])
    return JsonResponse(_comment_dict(c, request.user))
