"""تسک‌های در حال اجرای تایمر را برای ویجتِ سراسری (گوشهٔ صفحه) فراهم می‌کند."""
from .queries import running_timers_payload


def running_timers(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or getattr(request, 'organization', None) is None:
        return {}
    return {'running_timers': running_timers_payload(request)}
