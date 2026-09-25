"""پردازنده‌های زمینه (context processors) سراسری."""


def notifications(request):
    """زنگولهٔ اعلان‌ها + بَجِ «بازبینی» برای هدر/سایدبار (بارِ اولِ صفحه، بدونِ AJAX).
    سبک: فقط شمارش + ۸ اعلانِ اخیر. بَجِ بازبینی = تعدادِ تسکِ بازبینی‌نشدهٔ قابل‌بازبینیِ کاربر."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    from .models import Notification
    qs = Notification.objects.filter(user=user)
    ctx = {
        'notif_unread': qs.filter(read=False).count(),
        'notif_recent': list(qs[:8]),
    }
    # بَجِ بازبینی: فقط اگر کاربر اصلاً مسیرِ بازبینی دارد (وگرنه کوئری نمی‌زنیم)
    try:
        from tasks.models import Task
        from tasks.queries import reviewable_q
        m = getattr(request, 'membership', None)
        my_c = getattr(user, 'colleague', None)
        has_path = bool((m and m.can('review')) or (my_c and my_c.reports.exists()))
        if has_path:
            ctx['review_pending_count'] = Task.objects.filter(
                status__in=[Task.DONE, Task.PENDING], review_status=Task.UNREVIEWED
            ).filter(reviewable_q(request)).count()
    except Exception:  # noqa: BLE001
        pass
    return ctx
