"""API‌های JSON فضای شخصی — بدون DRF. همه با `admin_only` + اسکوپِ `user`.

هر رکورد با `get_object_or_404(Model, pk=pk, user=request.user)` واکشی می‌شود تا
حتی سوپریوزرِ دیگری هم به دادهٔ کسِ دیگر دست نزند.
"""
import json
from datetime import date, timedelta

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from core.jalali import parse_jalali

from .access import admin_only
from .models import Goal, Habit, HabitLog, PersonalTask, week_saturday


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _pdate(value):
    """رشته‌ی شمسی → date میلادی؛ خالی/نامعتبر → None."""
    if not value:
        return None
    try:
        return parse_jalali(value)
    except (ValueError, TypeError):
        return None


def _weekdays_str(value):
    """لیستِ روزها → رشته‌ی «۰,۲,۵» (فقط ۰..۶)."""
    if not isinstance(value, list):
        return ''
    return ','.join(str(int(x)) for x in value if str(x).isdigit() and 0 <= int(x) <= 6)


# ── تسک‌های شخصی ─────────────────────────────────────────────────────────
@admin_only
@require_http_methods(['POST'])
def ptask_add(request):
    data = _body(request)
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    base = _iso(data.get('week')) or date.today()
    planned = _pdate(data.get('planned_date')) or (date.today() if data.get('plan_today') else None)
    t = PersonalTask.objects.create(
        user=request.user, title=title[:255],
        week_start=week_saturday(base), planned_date=planned,
    )
    return JsonResponse(_task_dict(t), status=201)


@admin_only
@require_http_methods(['PATCH', 'DELETE'])
def ptask_detail(request, pk):
    t = get_object_or_404(PersonalTask, pk=pk, user=request.user)
    if request.method == 'DELETE':
        t.delete()
        return JsonResponse({'ok': True})
    data = _body(request)
    if 'title' in data:
        t.title = (data['title'] or '').strip()[:255]
    if 'note' in data:
        t.note = data['note'] or ''
    if 'kind' in data:
        t.kind = (data['kind'] or '')[:40]
    if 'done' in data:
        t.done = bool(data['done'])
    if 'playing' in data:
        # فقط یک تسکِ در حالِ اجرا هم‌زمان
        if data['playing']:
            PersonalTask.objects.filter(user=request.user, playing=True).exclude(pk=t.pk).update(playing=False)
        t.playing = bool(data['playing'])
    if 'planned_date' in data:
        # مقدارِ شمسی (از دیت‌پیکر) یا خالی برای پاک‌کردن
        t.planned_date = _pdate(data['planned_date'])
    if 'plan_today' in data and data['plan_today']:
        t.planned_date = date.today()
    if not t.title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    t.save()
    return JsonResponse(_task_dict(t))


@admin_only
@require_http_methods(['POST'])
def ptask_reorder(request):
    ids = _body(request).get('ids') or []
    for i, pk in enumerate(ids):
        PersonalTask.objects.filter(pk=pk, user=request.user).update(order=i)
    return JsonResponse({'ok': True})


def _iso(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _task_dict(t):
    return {
        'id': t.id, 'title': t.title, 'note': t.note, 'kind': t.kind,
        'done': t.done, 'playing': t.playing,
        'planned_date': t.planned_date.isoformat() if t.planned_date else None,
    }


# ── عادت‌ها ──────────────────────────────────────────────────────────────
@admin_only
@require_http_methods(['POST'])
def habit_add(request):
    data = _body(request)
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    pol = data.get('polarity') if data.get('polarity') in (Habit.GOOD, Habit.BAD) else Habit.GOOD
    h = Habit.objects.create(
        user=request.user, title=title[:120],
        weekdays=_weekdays_str(data.get('weekdays')), polarity=pol,
    )
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
    d = _iso(data.get('date'))
    if not d:
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
    Goal.objects.create(
        user=request.user, title=title[:200], description=data.get('description') or '',
        start_date=start, end_date=end,
    )
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
    if 'start_date' in data:
        s = _pdate(data['start_date'])
        if s:
            g.start_date = s
    if 'end_date' in data:
        e = _pdate(data['end_date'])
        if e:
            g.end_date = e
    if not g.title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    if g.end_date < g.start_date:
        return JsonResponse({'detail': 'پایان نباید قبل از شروع باشد'}, status=400)
    g.save()
    return JsonResponse({'ok': True})
