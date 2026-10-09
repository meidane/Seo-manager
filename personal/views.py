"""ویوِ "فضای شخصی" — داشبوردِ خصوصیِ یوزرِ admin.

بالای صفحه = **تقویمِ مشترک** (`calendarapp/_calendar.html`، فیکس روی خودِ کاربر، پنلِ
«تسک‌های بدون تاریخ» = همان اینباکس + فیلدِ افزودنِ سریع). پایین‌تر = عادت‌ها/اهداف/
یادداشت‌ها. تسک‌های شخصی = `tasks.Task` با نوعِ «شخصی» در پروژهٔ شخصیِ خودکارِ همکار.
عادت/هدف مدلِ اختصاصیِ همین اپ. فقط رندرِ اولیه اینجاست؛ تعامل با API.
"""
from datetime import date, timedelta

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from calendarapp.views import calendar_base_context
from core.jalali import WEEKDAY_NAMES, format_jalali, jalali_long

from .access import admin_only
from .api import PERSONAL_TYPE_NAME, personal_context
from .models import Goal, Habit, HabitLog, PersonalNote, week_saturday

# ثانیه‌شمارِ عمر (هارد‌کد طبق درخواست): الان ۲۸ ساله، احتمالِ عمر تا ۷۵ سالگی
LIFE_AGE_NOW = 28
LIFE_EXPECTANCY = 75


def _pct(done, total):
    return round(done / total * 100) if total else 0


@method_decorator(admin_only, name='dispatch')
class PersonalDashboardView(View):
    template_name = 'personal/index.html'

    def get(self, request):
        user = request.user
        today = date.today()
        me, pproject, ptype = personal_context(request)

        # ── عادت‌ها (هبیت ترکر؛ هفتهٔ جاری — بدونِ نوارِ بازه، چون بالای صفحه حالا تقویم است) ──
        hsat = week_saturday(today)
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
                if done and not wd['is_future']:
                    done_days += 1
                cells.append({**wd, 'active': active, 'done': done})
            habits.append({'obj': h, 'cells': cells, 'done_days': done_days,
                           'target': target_total, 'pct': min(100, _pct(done_days, target_total))})

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
            'me_colleague_id': me.id if me else '',
            'personal_project_id': pproject.id if pproject else '',
            'personal_type_id': ptype.id if ptype else '',
            'week_days': hdays, 'habits': habits,
            'hweek_fa': jalali_long(hsat) + ' – ' + jalali_long(hsat + timedelta(days=6)),
            'goals': goals,
            'life': {'birth_iso': birth.isoformat(), 'death_iso': death.isoformat(),
                     'age_now': LIFE_AGE_NOW, 'expectancy': LIFE_EXPECTANCY},
            'notes': PersonalNote.objects.filter(user=request.user),
        }
        ctx.update(calendar_base_context(request))  # projects/colleagues/task_types/months/years/jyear/jmonth
        return render(request, self.template_name, ctx)
