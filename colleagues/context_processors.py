"""context processor برای بخشِ «همکاران» در سایدبار (حضورغیابِ امروز).

فقط وقتی worktracker پیکربندی شده باشد کار می‌کند — وگرنه هیچ کوئری/فراخوانی‌ای انجام
نمی‌شود (روی هستهٔ سیستم بی‌اثر است). داده‌ی امروز کش می‌شود (`today_all`، ۶۰ثانیه).
"""


def sidebar_attendance(request):
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return {}
    from . import worktracker as wt
    if not wt.is_configured():
        return {}
    from .models import Colleague
    cols = list(Colleague.objects.filter(status=Colleague.ACTIVE)
                .exclude(worktracker_username='').order_by('full_name'))
    if not cols:
        return {}
    today = wt.today_all()

    # آخرین تسکِ انجام‌شده‌ی هر همکار (یک کوئری، اولین رخداد per assignee)
    from tasks.models import Task
    last_tasks = {}
    for t in (Task.objects.filter(assignee_id__in=[c.id for c in cols], status=Task.DONE)
              .order_by('-done_date', '-id').values('assignee_id', 'title', 'done_date')[:400]):
        last_tasks.setdefault(t['assignee_id'], t)

    items = [{'c': c, 'wt': today.get(c.worktracker_username), 'last_task': last_tasks.get(c.id)}
             for c in cols]
    # آنلاین‌ها اول
    items.sort(key=lambda x: not (x['wt'] and x['wt'].get('online')))
    return {'sidebar_attendance': items}
