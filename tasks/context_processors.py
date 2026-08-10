"""تسک‌های در حال اجرای تایمر را برای ویجتِ سراسری (گوشهٔ صفحه) فراهم می‌کند."""
from .models import Task


def running_timers(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or getattr(request, 'organization', None) is None:
        return {}
    running = list(Task.objects.filter(timer_started_at__isnull=False)
                   .select_related('project')[:8])
    return {'running_timers': [{
        'id': t.id, 'title': t.title, 'project': t.project.name if t.project_id else '',
        'spent': t.spent_minutes, 'started': t.timer_started_at.isoformat(),
    } for t in running]}
