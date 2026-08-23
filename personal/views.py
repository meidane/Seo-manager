"""ویوِ "فضای شخصی" — داشبوردِ خصوصیِ کاربرِ admin (سوپریوزر).

فقط رندرِ اولیه اینجاست؛ تعامل‌ها (افزودن/ویرایش/تیک/جابه‌جایی) از `api.py` با JSON
انجام می‌شوند. همه‌چیز به `request.user` اسکوپ است و با `admin_only` گیت شده.
"""
from datetime import date, timedelta

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from core.jalali import WEEKDAY_NAMES, format_jalali, g2j, jalali_long

from .access import admin_only
from .models import Goal, Habit, HabitLog, PersonalTask, week_saturday

# ثانیه‌شمارِ عمر (هارد‌کد طبق درخواست): الان ۲۸ ساله، احتمالِ عمر تا ۷۵ سالگی
LIFE_AGE_NOW = 28
LIFE_EXPECTANCY = 75


def _week_days(saturday):
    """۷ روزِ هفته (شنبه..جمعه) از تاریخِ شنبه‌ی داده‌شده."""
    out = []
    today = date.today()
    for i in range(7):
        d = saturday + timedelta(days=i)
        out.append({
            'date': d, 'iso': d.isoformat(), 'jwd': i,
            'name': WEEKDAY_NAMES[i], 'day_fa': format_jalali(d, '%d', fa_digits=True),
            'is_today': d == today, 'is_future': d > today,
        })
    return out


@method_decorator(admin_only, name='dispatch')
class PersonalDashboardView(View):
    template_name = 'personal/index.html'

    def get(self, request):
        user = request.user
        today = date.today()

        # ── هفته‌ی اینباکس (ناوبریِ قبل/بعد) ──
        try:
            base = date.fromisoformat(request.GET.get('week', ''))
        except (ValueError, TypeError):
            base = today
        wk = week_saturday(base)
        wk_end = wk + timedelta(days=6)
        inbox = list(PersonalTask.objects.filter(user=user, week_start=wk).order_by('order', 'id'))

        # ── تسک‌های روزانه (planned = امروز) + تسک‌های سیستمیِ امروزِ خودم ──
        daily = list(PersonalTask.objects.filter(user=user, planned_date=today).order_by('order', 'id'))
        system_tasks = []
        colleague = getattr(user, 'colleague', None)
        if colleague:
            from tasks.models import Task
            system_tasks = list(
                Task.objects.filter(assignee=colleague, planned_date=today)
                .exclude(status=Task.DONE).select_related('project')[:50]
            )

        # ── عادت‌ها + شبکه‌ی هفته‌ی جاری ──
        cur_sat = week_saturday(today)
        week_days = _week_days(cur_sat)
        logs = {
            (l.habit_id, l.date): l.done
            for l in HabitLog.objects.filter(habit__user=user, date__range=(cur_sat, cur_sat + timedelta(days=6)))
        }
        habits = []
        for h in Habit.objects.filter(user=user, active=True).order_by('order', 'id'):
            wset = h.weekday_set()
            cells, expected, kept = [], 0, 0
            for wd in week_days:
                active = wd['jwd'] in wset
                done = logs.get((h.id, wd['date']), False)
                if active and not wd['is_future']:
                    expected += 1
                    if done:
                        kept += 1
                cells.append({**wd, 'active': active, 'done': done})
            habits.append({
                'obj': h, 'cells': cells,
                'pct': round(kept / expected * 100) if expected else 0,
            })

        # ── اهداف ──
        goals = []
        for g in Goal.objects.filter(user=user):
            total = max((g.end_date - g.start_date).days, 1)
            elapsed = (today - g.start_date).days
            elapsed = min(max(elapsed, 0), total)
            goals.append({
                'obj': g, 'total': total, 'elapsed': elapsed,
                'remaining': total - elapsed,
                'pct': round(elapsed / total * 100),
                'start_fa': jalali_long(g.start_date), 'end_fa': jalali_long(g.end_date),
                'start_num': format_jalali(g.start_date, fa_digits=True),
                'end_num': format_jalali(g.end_date, fa_digits=True),
            })

        # ── ثانیه‌شمارِ عمر (هارد‌کد) ──
        birth = date(today.year - LIFE_AGE_NOW, today.month, today.day)
        death = date(birth.year + LIFE_EXPECTANCY, birth.month, birth.day)

        ctx = {
            'page_title': 'فضای شخصی',
            'inbox': inbox,
            'week_start': wk, 'week_end': wk_end,
            'week_start_fa': jalali_long(wk), 'week_end_fa': jalali_long(wk_end),
            'prev_week': (wk - timedelta(days=7)).isoformat(),
            'next_week': (wk + timedelta(days=7)).isoformat(),
            'is_this_week': wk == cur_sat,
            'today_iso': today.isoformat(),
            'daily': daily, 'system_tasks': system_tasks,
            'week_days': week_days, 'habits': habits,
            'goals': goals,
            'life': {
                'birth_iso': birth.isoformat(), 'death_iso': death.isoformat(),
                'age_now': LIFE_AGE_NOW, 'expectancy': LIFE_EXPECTANCY,
            },
        }
        return render(request, self.template_name, ctx)
