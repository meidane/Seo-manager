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

from .models import Task, TaskComment

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
    from colleagues.models import Colleague
    from projects.models import Project

    from .models import TaskTypeDef
    # همه‌ی پروژه‌ها (فعال‌ها اول) — نه فقط فعال؛ وگرنه اگر پروژه‌ای غیرفعال شود
    # یا هیچ پروژه‌ی فعالی نباشد، دراپ‌داونِ مودال خالی می‌شود و ذخیره‌ی تسک
    # با خطای «عنوان و پروژه لازم است» شکست می‌خورد.
    projects = Project.objects.order_by('status', 'name')  # active قبل از inactive
    return JsonResponse({
        'projects': [[p.id, p.name] for p in projects],
        'colleagues': [[c.id, c.full_name] for c in Colleague.objects.filter(status=Colleague.ACTIVE)],
        'typeChoices': list(Task.TYPE_CHOICES),
        'customTypes': [
            {'id': t.id, 'name': t.name, 'color': t.color, 'icon': t.icon,
             'builtin_key': t.builtin_key, 'fields': t.schema()}
            for t in TaskTypeDef.objects.filter(is_active=True)
        ],
    })


def _publish_url_error(task):
    """تسک انتشارِ «انجام‌شده» بدون لینک انتشار مجاز نیست (الزام لینک)."""
    if task.task_type == Task.PUBLISH and task.status == Task.DONE and not task.published_url:
        return 'برای تسک انتشارِ انجام‌شده، وارد کردن «لینک انتشار» الزامی است.'
    return None


@login_required
@require_http_methods(['POST'])
def task_create(request):
    data = _body(request)
    if not data.get('title') or not data.get('project'):
        return JsonResponse({'detail': 'عنوان و پروژه لازم است'}, status=400)
    task = Task(created_by=request.user, planned_date=date.today())
    apply_fields(task, data)
    err = _publish_url_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
    return JsonResponse(task.to_dict(), status=201)


@login_required
@require_http_methods(['GET', 'PATCH', 'DELETE'])
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
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
        })
        return JsonResponse(d)
    if request.method == 'DELETE':
        task.delete()
        return JsonResponse({'ok': True})
    # PATCH
    apply_fields(task, _body(request))
    err = _publish_url_error(task)
    if err:
        return JsonResponse({'detail': err}, status=400)
    task.save()
    return JsonResponse(task.to_dict())


@login_required
@require_http_methods(['PATCH'])
def task_status(request, pk):
    """تغییر سریع وضعیت (دراپ‌داون ردیف و drag کانبان)."""
    task = get_object_or_404(Task, pk=pk)
    data = _body(request)
    new_status = data.get('status')
    if new_status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'detail': 'وضعیت نامعتبر'}, status=400)
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
    return JsonResponse(task.to_dict())


@login_required
@require_http_methods(['PATCH'])
def task_review(request, pk):
    """تایید / نیاز به اصلاح (از فید بازبینی و صفحه‌ی بازبینی)."""
    task = get_object_or_404(Task, pk=pk)
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


def _next_workday(d: date, holidays: set) -> date:
    """اگر روز تعطیل بود (جمعه یا در جدول)، به اولین روز کاری بعد برو."""
    while d.weekday() == 3 or d in holidays:  # weekday()==3 → جمعه (Mon=0)
        d += timedelta(days=1)
    return d


@login_required
@require_http_methods(['POST'])
def task_bulk(request):
    """عملیات گروهی: تغییر/جابه‌جایی تاریخ، مسئول، وضعیت، پروژه، انجام‌شده."""
    data = _body(request)
    ids = data.get('ids', [])
    action = data.get('action')
    qs = Task.objects.filter(id__in=ids)
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


@login_required
@require_http_methods(['GET', 'POST'])
def task_comments(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'GET':
        items = [{'author': str(c.author), 'body': c.body,
                  'at': c.created_at.strftime('%Y-%m-%d %H:%M')} for c in task.comments.all()]
        return JsonResponse({'comments': items})
    body = _body(request).get('body', '').strip()
    if not body:
        return JsonResponse({'detail': 'متن لازم است'}, status=400)
    c = TaskComment.objects.create(task=task, author=request.user, body=body)
    return JsonResponse({'author': str(c.author), 'body': c.body,
                         'at': c.created_at.strftime('%Y-%m-%d %H:%M')}, status=201)
