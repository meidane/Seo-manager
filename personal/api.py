"""API‌های JSON فضای شخصی — همه با `admin_only`.

تسک‌های شخصی همان `tasks.Task`اند؛ ساخت/جابه‌جایی اینجا (با دیفالت‌های شخصی که
سرورساید تحمیل می‌شوند)، ولی done/حذف/تغییرِ تاریخ/تایمر/ویرایش از همان `tasks/api.py`
(reuse، بدونِ منطقِ موازی — دسترسی هم چون پروژهٔ شخصی فقط برای خودِ admin است امن می‌ماند).
عادت/هدف مدلِ اختصاصیِ همین اپ‌اند و کاملاً اینجا مدیریت می‌شوند.
"""
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from core.jalali import parse_jalali

from .access import admin_only
from .models import Goal, Habit, HabitLog

PERSONAL_TYPE_NAME = 'شخصی'


def personal_context(request):
    """(همکارِ کاربر، پروژهٔ شخصیِ او، نوعِ تسکِ «شخصی») — منبعِ واحدِ دیفالت‌های شخصی."""
    from projects.models import Project
    from tasks.models import TaskTypeDef
    me = getattr(request.user, 'colleague', None)
    pproject = Project.objects.filter(personal_owner=me).first() if me else None
    ptype = TaskTypeDef.objects.filter(name=PERSONAL_TYPE_NAME).first()
    return me, pproject, ptype


def _personal_qs(request):
    from tasks.models import Task
    me, pproject, ptype = personal_context(request)
    if not (me and pproject and ptype):
        return Task.objects.none()
    return Task.objects.filter(project=pproject, assignee=me, type_def=ptype)


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _pdate(value):
    if not value:
        return None
    try:
        return parse_jalali(value)
    except (ValueError, TypeError):
        return None


# ── تسک‌های شخصی (Task با نوعِ «شخصی») ───────────────────────────────────
@admin_only
@require_http_methods(['POST'])
def ptask_add(request):
    """ثبتِ سریعِ اینباکس — بدونِ تاریخ (ایده)؛ دیفالت‌ها سرورساید تحمیل می‌شوند."""
    from tasks import history as taskhistory
    from tasks.models import Task
    me, pproject, ptype = personal_context(request)
    if not (me and pproject):
        return JsonResponse({'detail': 'پروفایل یا پروژهٔ شخصی یافت نشد'}, status=400)
    if not ptype:
        return JsonResponse({'detail': f'اول نوعِ تسکِ «{PERSONAL_TYPE_NAME}» را در تنظیمات بساز'}, status=400)
    title = (_body(request).get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    t = Task(created_by=request.user, project=pproject, assignee=me, type_def=ptype,
             task_type=ptype.builtin_key or Task.OTHER, title=title[:255], planned_date=None)
    t.save()
    taskhistory.record(t, taskhistory.TaskHistory.CREATED, request.user)
    return JsonResponse({'id': t.id, 'title': t.title})


@admin_only
@require_http_methods(['POST'])
def ptask_reorder(request):
    ids = _body(request).get('ids') or []
    qs = _personal_qs(request)
    for i, pk in enumerate(ids):
        qs.filter(pk=pk).update(board_order=i)
    return JsonResponse({'ok': True})


# ── عادت‌ها ──────────────────────────────────────────────────────────────
def _weekdays_str(value):
    if not isinstance(value, list):
        return ''
    return ','.join(str(int(x)) for x in value if str(x).isdigit() and 0 <= int(x) <= 6)


@admin_only
@require_http_methods(['POST'])
def habit_add(request):
    data = _body(request)
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    pol = data.get('polarity') if data.get('polarity') in (Habit.GOOD, Habit.BAD) else Habit.GOOD
    h = Habit.objects.create(user=request.user, title=title[:120],
                             weekdays=_weekdays_str(data.get('weekdays')), polarity=pol)
    return JsonResponse({'id': h.id}, status=201)


@admin_only
@require_http_methods(['PATCH', 'DELETE'])
def habit_detail(request, pk):
    h = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'DELETE':
        h.delete()
        return JsonResponse({'ok': True})
    data = _body(request)
    if 'title' in data:
        h.title = (data['title'] or '').strip()[:120]
    if 'weekdays' in data:
        h.weekdays = _weekdays_str(data['weekdays'])
    if 'polarity' in data and data['polarity'] in (Habit.GOOD, Habit.BAD):
        h.polarity = data['polarity']
    if 'active' in data:
        h.active = bool(data['active'])
    if not h.title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    h.save()
    return JsonResponse({'ok': True})


@admin_only
@require_http_methods(['POST'])
def habit_toggle(request):
    data = _body(request)
    h = get_object_or_404(Habit, pk=data.get('habit'), user=request.user)
    try:
        d = __import__('datetime').date.fromisoformat(data.get('date'))
    except (ValueError, TypeError):
        return JsonResponse({'detail': 'تاریخ نامعتبر'}, status=400)
    log = HabitLog.objects.filter(habit=h, date=d).first()
    if log:
        log.delete()
        return JsonResponse({'done': False})
    HabitLog.objects.create(habit=h, date=d, done=True)
    return JsonResponse({'done': True})


# ── اهداف ────────────────────────────────────────────────────────────────
@admin_only
@require_http_methods(['POST'])
def goal_add(request):
    data = _body(request)
    title = (data.get('title') or '').strip()
    start, end = _pdate(data.get('start_date')), _pdate(data.get('end_date'))
    if not title or not start or not end:
        return JsonResponse({'detail': 'عنوان، شروع و پایان لازم است'}, status=400)
    if end < start:
        return JsonResponse({'detail': 'پایان نباید قبل از شروع باشد'}, status=400)
    Goal.objects.create(user=request.user, title=title[:200], description=data.get('description') or '',
                        start_date=start, end_date=end)
    return JsonResponse({'ok': True}, status=201)


@admin_only
@require_http_methods(['PATCH', 'DELETE'])
def goal_detail(request, pk):
    g = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'DELETE':
        g.delete()
        return JsonResponse({'ok': True})
    data = _body(request)
    if 'title' in data:
        g.title = (data['title'] or '').strip()[:200]
    if 'description' in data:
        g.description = data['description'] or ''
    if 'start_date' in data and _pdate(data['start_date']):
        g.start_date = _pdate(data['start_date'])
    if 'end_date' in data and _pdate(data['end_date']):
        g.end_date = _pdate(data['end_date'])
    if not g.title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    if g.end_date < g.start_date:
        return JsonResponse({'detail': 'پایان نباید قبل از شروع باشد'}, status=400)
    g.save()
    return JsonResponse({'ok': True})
