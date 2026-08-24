"""ویوِ "فضای شخصی" — داشبوردِ خصوصیِ یوزرِ admin.

تسک‌های شخصی = `tasks.Task` با نوعِ «شخصی» در پروژهٔ شخصیِ خودکارِ همکار (فقط خودش
می‌بیند؛ در تقویم/لیست هم همین‌طور). عادت/هدف مدلِ اختصاصیِ همین اپ. فقط رندرِ اولیه
اینجاست؛ تعامل با API (بخشی reuseِ `tasks/api.py`، بخشی `personal/api.py`).
"""
from datetime import date, timedelta
from urllib.parse import urlencode

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from core.jalali import WEEKDAY_NAMES, format_jalali, jalali_long
from projects.access import accessible_project_ids

from .access import admin_only
from .api import PERSONAL_TYPE_NAME, personal_context
from .models import Goal, Habit, HabitLog, week_saturday

# ثانیه‌شمارِ عمر (هارد‌کد طبق درخواست): الان ۲۸ ساله، احتمالِ عمر تا ۷۵ سالگی
LIFE_AGE_NOW = 28
LIFE_EXPECTANCY = 75


def _iso(value, fallback):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return fallback


def _pct(done, total):
    return round(done / total * 100) if total else 0


@method_decorator(admin_only, name='dispatch')
class PersonalDashboardView(View):
    template_name = 'personal/index.html'

    def get(self, request):
        from tasks.models import Task

        user = request.user
        today = date.today()
        me, pproject, ptype = personal_context(request)

        # پارامترهای ناوبری (سه ناوبرِ مستقل: اینباکسِ هفتگی، روزِ تسک‌های امروز، هفتهٔ هبیت)
        wk = week_saturday(_iso(request.GET.get('week'), today))
        day = _iso(request.GET.get('day'), today)
        hsat = week_saturday(_iso(request.GET.get('hweek'), today))
        wk_end = wk + timedelta(days=6)

        def nav(**over):
            p = {'week': wk.isoformat(), 'day': day.isoformat(), 'hweek': hsat.isoformat()}
            p.update(over)
            return '?' + urlencode(p)

        # ── تسک‌های شخصی (Task با نوعِ «شخصی») ──
        ptasks = Task.objects.none()
        if me and pproject and ptype:
            ptasks = Task.objects.filter(project=pproject, assignee=me, type_def=ptype)

        # اینباکسِ هفتگی: تسک‌های ثبت‌شده در همان هفته (بر اساسِ created_at)؛
        # برنامه‌ریزی‌شده/انجام‌شده‌ها ته می‌روند و کم‌رنگ می‌شوند.
        inbox = list(ptasks.filter(created_at__date__range=(wk, wk_end)).order_by('board_order', 'id'))
        for t in inbox:
            t.dim = bool(t.planned_date) or t.is_done
        inbox.sort(key=lambda t: t.dim)  # پایدار: فعال‌ها بالا، بقیه ته
        wk_done = sum(1 for t in inbox if t.is_done)

        # تسک‌های روزِ انتخاب‌شده: شخصی‌ها (قابل‌ویرایش) + سیستمی‌های همان روز (فقط‌خواندنی)
        from .models import DailyPlan
        daily = list(ptasks.filter(planned_date=day).order_by('board_order', 'id'))
        for t in daily:  # تضمینِ رکوردِ تاریخچهٔ روز (برای نمودار)، idempotent
            DailyPlan.objects.get_or_create(task=t, date=day, defaults={'user': user})
        system_tasks = []
        if me:
            sys_qs = Task.objects.filter(assignee=me, planned_date=day).exclude(status=Task.DONE)
            if pproject:
                sys_qs = sys_qs.exclude(project=pproject)
            ids = accessible_project_ids(request)
            if ids is not None:
                sys_qs = sys_qs.filter(project_id__in=ids)
            system_tasks = list(sys_qs.select_related('project')[:50])

        # درصدِ روز = انجام‌شده / کلِ تسک‌های همان روزِ من (شخصی + سیستمی)
        day_done = day_total = 0
        if me:
            dq = Task.objects.filter(assignee=me, planned_date=day)
            ids = accessible_project_ids(request)
            if ids is not None:
                dq = dq.filter(project_id__in=ids)
            day_total = dq.count()
            day_done = dq.filter(status=Task.DONE).count()

        # ── عادت‌ها (هفتگی، با ناوبری؛ همه‌ی روزها قابلِ‌کلیک، روزهای هدف پررنگ‌تر) ──
        hdays = []
        for i in range(7):
            d = hsat + timedelta(days=i)
            hdays.append({'date': d, 'iso': d.isoformat(), 'jwd': i, 'name': WEEKDAY_NAMES[i],
                          'is_today': d == today, 'is_future': d > today})
        logs = {(l.habit_id, l.date): l.done
                for l in HabitLog.objects.filter(habit__user=user, date__range=(hsat, hsat + timedelta(days=6)))}
        habits = []
        for h in Habit.objects.filter(user=user, active=True).order_by('order', 'id'):
            wset = h.weekday_set()
            target_total = len(wset) or 7  # مخرج = روزهای هدفِ هفته (بی‌روز = روزانه)
            cells, done_days = [], 0
            for wd in hdays:
                active = wd['jwd'] in wset
                done = logs.get((h.id, wd['date']), False)
                # هر روزی که انجام شده حساب می‌شود (حتی اگر روزِ هدف نبوده) — تعدادِ انجام مهم است
                if done and not wd['is_future']:
                    done_days += 1
                cells.append({**wd, 'active': active, 'done': done})
            habits.append({'obj': h, 'cells': cells, 'done_days': done_days,
                           'target': target_total, 'pct': min(100, _pct(done_days, target_total))})

        # ── نمودارِ هفتگیِ باکسِ روزانه (برنامه‌ریزی/انجام/درصد/ساعت در هفتهٔ حاویِ روزِ انتخابی) ──
        cw_sat = week_saturday(day)
        cplans = list(DailyPlan.objects.filter(
            user=user, date__range=(cw_sat, cw_sat + timedelta(days=6)),
            task__deleted_at__isnull=True).select_related('task'))
        chart = []
        for i in range(7):
            d = cw_sat + timedelta(days=i)
            dps = [p for p in cplans if p.date == d]
            planned = len(dps)
            done = sum(1 for p in dps if p.done)
            minutes = sum((p.task.spent_minutes or 0) for p in dps)
            chart.append({'name': WEEKDAY_NAMES[i], 'day_fa': format_jalali(d, '%d', fa_digits=True),
                          'planned': planned, 'done': done, 'pct': _pct(done, planned),
                          'hours': round(minutes / 60, 1), 'is_today': d == today, 'is_future': d > today,
                          'is_sel': d == day})

        # ── اهداف ──
        goals = []
        for g in Goal.objects.filter(user=user):
            total = max((g.end_date - g.start_date).days, 1)
            elapsed = min(max((today - g.start_date).days, 0), total)
            goals.append({'obj': g, 'total': total, 'elapsed': elapsed, 'remaining': total - elapsed,
                          'pct': _pct(elapsed, total),
                          'start_fa': jalali_long(g.start_date), 'end_fa': jalali_long(g.end_date),
                          'start_num': format_jalali(g.start_date, fa_digits=True),
                          'end_num': format_jalali(g.end_date, fa_digits=True)})

        # ── ثانیه‌شمارِ عمر ──
        birth = date(today.year - LIFE_AGE_NOW, today.month, today.day)
        death = date(birth.year + LIFE_EXPECTANCY, birth.month, birth.day)

        ctx = {
            'page_title': 'فضای شخصی',
            'setup_needed': not (me and pproject and ptype),
            'type_name': PERSONAL_TYPE_NAME,
            'inbox': inbox, 'wk_done': wk_done, 'wk_total': len(inbox), 'wk_pct': _pct(wk_done, len(inbox)),
            'week_start_fa': jalali_long(wk), 'week_end_fa': jalali_long(wk_end),
            'is_this_week': wk == week_saturday(today),
            'inbox_prev': nav(week=(wk - timedelta(days=7)).isoformat()),
            'inbox_next': nav(week=(wk + timedelta(days=7)).isoformat()),
            'daily': daily, 'system_tasks': system_tasks,
            'day_done': day_done, 'day_total': day_total, 'day_pct': _pct(day_done, day_total),
            'day_fa': jalali_long(day), 'is_today': day == today,
            'day_prev': nav(day=(day - timedelta(days=1)).isoformat()),
            'day_next': nav(day=(day + timedelta(days=1)).isoformat()),
            'chart': chart,
            'cweek_fa': jalali_long(cw_sat) + ' – ' + jalali_long(cw_sat + timedelta(days=6)),
            'cweek_prev': nav(day=(day - timedelta(days=7)).isoformat()),
            'cweek_next': nav(day=(day + timedelta(days=7)).isoformat()),
            'week_days': hdays, 'habits': habits,
            'hweek_fa': jalali_long(hsat) + ' – ' + jalali_long(hsat + timedelta(days=6)),
            'is_this_hweek': hsat == week_saturday(today),
            'hweek_prev': nav(hweek=(hsat - timedelta(days=7)).isoformat()),
            'hweek_next': nav(hweek=(hsat + timedelta(days=7)).isoformat()),
            'goals': goals,
            'life': {'birth_iso': birth.isoformat(), 'death_iso': death.isoformat(),
                     'age_now': LIFE_AGE_NOW, 'expectancy': LIFE_EXPECTANCY},
        }
        return render(request, self.template_name, ctx)
