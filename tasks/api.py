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

from core.jalali import parse_jalali
from core.models import Holiday
from projects.access import accessible_project_ids

from .models import Task, TaskComment


def _task_perm_ok(request, task, perm):
    """دسترسیِ ویرایش/حذفِ یک تسکِ مشخص: نقش باید `perm` را داشته باشد؛ اگر
    `own_tasks_only` هم داشت، فقط روی تسکِ خودش (assignee = همکارِ متصل به کاربر)."""
    m = getattr(request, 'membership', None)
    if not m or not m.can(perm):
        return False
    if m.can('own_tasks_only'):
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
    بدونِ `own_tasks_only` (کسی که به‌طورِ کلی مسئولِ مدیریتِ تسک‌هاست، منطقی است که
    بتواند تایمرشان را هم کنترل کند — نیازی به تیک‌زدنِ جداگانه‌ی `edit_time` نیست
    فقط برای دکمه‌ی پلی؛ آن پرمیشن مخصوصِ ویرایشِ دستیِ عددِ زمان می‌ماند)."""
    return bool(m and (m.can('edit_time') or (m.can('edit_task') and not m.can('own_tasks_only'))))


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
INT_FIELDS = ['word_count', 'current_rank', 'link_count', 'estimate_minutes']
DECIMAL_FIELDS = ['media_cost']
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
    for f in DECIMAL_FIELDS:
        if f in data:
            setattr(task, f, data[f] or None)
    for key, attr in FK_FIELDS.items():
        if key in data:
            setattr(task, attr, data[key] or None)
    if 'type_def' in data:
        task.type_def_id = data['type_def'] or None
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
    # اگر وضعیت به «انجام شده» رفت و done_date خالی بود، امروز را بگذار
    if task.status == Task.DONE and not task.done_date:
        task.done_date = date.today()
    # تسکِ «نیاز به اصلاح» که دوباره انجام شد → «بررسی‌نشده» (برای بازبینی مجدد مدیر)
    if task.status == Task.DONE and task.review_status == Task.NEEDS_FIX:
        task.review_status = Task.UNREVIEWED


@login_required
@require_http_methods(['GET'])
def form_data(request):
    """داده‌ی لازم برای مودال تسک (پروژه‌ها، همکاران، انواع built-in و سفارشی).
    مودال هنگام باز شدن این را یک‌بار می‌گیرد تا از هر صفحه‌ای کار کند."""
    from colleagues.models import Colleague, ensure_colleague_for_user
    from projects.models import Project

    from .models import TaskTypeDef

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
    own_tasks_only = bool(m and m.can('own_tasks_only'))
    my_colleague = getattr(request.user, 'colleague', None)
    return JsonResponse({
        'projects': [[p.id, p.name] for p in projects],
        'colleagues': [[c.id, c.full_name] for c in Colleague.objects.filter(status=Colleague.ACTIVE)],
        'typeChoices': list(Task.TYPE_CHOICES),
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
@require_http_methods(['GET'])
def task_rows_page(request):
    """صفحه‌بندیِ جعبه‌ی «انجام‌شده‌ها» برای لودِ تنبل (اسکرول، بیش از PAGE_SIZE تا) —
    فقط این جعبه صفحه‌بندی دارد؛ «این‌هفته/عقب‌افتاده» و «آینده» طبیعتاً محدودند
    (`tasks/views.py: BOX_CAP`). همان فیلترها/دسترسیِ TaskListView را از
    `build_task_queryset` می‌گیرد تا با صفحه‌ی اول (رندرِ سرور) دقیقاً هماهنگ بماند."""
    from django.template.loader import render_to_string

    from colleagues.models import Colleague
    from core.columns import get_columns
    from core.models import ColumnConfig
    from projects.models import Project

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
        'extra_columns': get_columns(ColumnConfig.TASKS, ColumnConfig.PAGE),
        'status_choices': Task.STATUS_CHOICES,
        'all_projects': visible_projects.order_by('status', 'name'),
        'all_colleagues': Colleague.objects.order_by('status', 'full_name'),
    }, request=request)
    return JsonResponse({'html': html, 'has_more': has_more, 'page': page})


def _publish_url_error(task):
    """تسک انتشارِ «انجام‌شده» بدون لینک انتشار مجاز نیست (الزام لینک)."""
    if task.task_type == Task.PUBLISH and task.status == Task.DONE and not task.published_url:
        return 'برای تسک انتشارِ انجام‌شده، وارد کردن «لینک انتشار» الزامی است.'
    return None


@login_required
@require_http_methods(['POST'])
def task_create(request):
    m = getattr(request, 'membership', None)
    my_colleague = getattr(request.user, 'colleague', None)
    can_edit = bool(m and m.can('edit_task'))
    # بدونِ edit_task هم هرکسی با پروفایلِ همکار می‌تواند برای خودش تسک بسازد
    # (own_tasks_only نسخه‌ی محدودکننده‌ی همین چیز است، نه یک قابلیتِ جدا)
    if not can_edit and not my_colleague:
        return JsonResponse({'detail': 'دسترسیِ ساختِ تسک را نداری'}, status=403)
    data = _body(request)
    if not data.get('title') or not data.get('project'):
        return JsonResponse({'detail': 'عنوان و پروژه لازم است'}, status=400)
    ids = accessible_project_ids(request)
    if ids is not None and int(data['project']) not in ids:
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    if not can_edit or (m and m.can('own_tasks_only')):
        data['assignee'] = my_colleague.id if my_colleague else None
    task = Task(created_by=request.user, planned_date=date.today())
    apply_fields(task, data)
    err = _publish_url_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
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
            'recurrence': task.recurrence_id,
        })
        return JsonResponse(d)
    if request.method == 'DELETE':
        if not _task_perm_ok(request, task, 'delete_task'):
            return JsonResponse({'detail': 'دسترسیِ حذفِ این تسک را نداری'}, status=403)
        task.delete()
        return JsonResponse({'ok': True})
    # PATCH
    if not _task_perm_ok(request, task, 'edit_task'):
        return JsonResponse({'detail': 'دسترسیِ ویرایشِ این تسک را نداری'}, status=403)
    data = _body(request)
    ids = accessible_project_ids(request)
    if 'project' in data and data['project'] and ids is not None and int(data['project']) not in ids:
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    m = getattr(request, 'membership', None)
    if m and m.can('own_tasks_only'):
        colleague = getattr(request.user, 'colleague', None)
        data['assignee'] = colleague.id if colleague else None
    was_done = task.status == Task.DONE
    apply_fields(task, data)
    err = _publish_url_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
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
    was_done = task.status == Task.DONE
    task.status = new_status
    fields = ['status', 'done_date', 'updated_at']
    if new_status == Task.DONE and not task.done_date:
        task.done_date = date.today()
    # تسکی که «نیاز به اصلاح» بوده، با انجام‌شدنِ دوباره به «بررسی‌نشده» برمی‌گردد
    # تا مدیر دوباره بازبینی کند.
    if new_status == Task.DONE and task.review_status == Task.NEEDS_FIX:
        task.review_status = Task.UNREVIEWED
        fields.append('review_status')
    err = _publish_url_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save(update_fields=fields)
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
    `can_manage_any_timer` (edit_time یا edit_task-بدونِ-own_tasks_only) دارد — یعنی
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
        task.save(update_fields=['timer_started_at', 'updated_at'])
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
    دسترسیِ سازمانیِ `review` دارد، یا مدیرِ مستقیمِ همکارِ این تسک باشد."""
    task = get_object_or_404(Task, pk=pk)
    m = getattr(request, 'membership', None)
    is_org_reviewer = bool(m and m.can('review'))
    is_direct_manager = bool(
        task.assignee_id and task.assignee.manager_id
        and task.assignee.manager.user_id == request.user.id)
    if not is_org_reviewer and not is_direct_manager:
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
    # «نیاز به اصلاح» → تسک از حالت انجام‌شده برمی‌گردد تا دوباره انجام شود
    if status == Task.NEEDS_FIX and task.status == Task.DONE:
        task.status = Task.DOING
        task.done_date = None
        fields += ['status', 'done_date']
    task.save(update_fields=fields)
    # ثبت در تاریخچه‌ی نیاز به اصلاح (فقط وقتی needs_fix با یادداشت است)
    if status == Task.NEEDS_FIX and note_html:
        from .models import TaskReviewNote
        TaskReviewNote.objects.create(task=task, note=note_html, author=request.user)
    return JsonResponse({'ok': True, 'review_status': task.review_status, 'status': task.status})


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
    if m.can('own_tasks_only'):
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
