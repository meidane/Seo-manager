"""همگام‌سازیِ خودکارِ روزانه بدونِ cron: با اولین درخواستِ هر سازمان بعد از ۲۰ ساعت، یک نخِ پس‌زمینه همگام می‌کند.
هزینه روی درخواست‌ها: هر ۱۰ دقیقه یک بار یک کوئریِ سبک (cache.add)؛ قفلِ اتمیکِ `sync.claim` جلوی اجرای هم‌زمان را می‌گیرد
(حتی با چند ورکرِ gunicorn یا cron). cron (`gsc_sync`) اختیاری است و با همین قفل تداخل ندارد."""
import threading

from django.core.cache import cache
from django.db import close_old_connections


def _run(acc_id):
    from .models import GSCAccount
    from .sync import sync_account
    close_old_connections()
    try:
        sync_account(GSCAccount.objects.get(pk=acc_id), log=lambda m: None, claimed=True)
    except Exception:  # noqa: BLE001 — خطا در acc.last_error ثبت می‌شود؛ نخِ پس‌زمینه نباید چیزی را بخواباند
        pass
    finally:
        close_old_connections()


class AutoSyncMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        org = getattr(request, 'organization', None)
        if org is not None and cache.add(f'gsc:autocheck:{org.pk}', 1, 600):
            try:
                from .models import GSCAccount
                from .sync import claim, due
                acc = GSCAccount.objects.filter(organization=org).first()
                if acc and due(acc) and claim(acc):
                    threading.Thread(target=_run, args=(acc.pk,), daemon=True).start()
            except Exception:  # noqa: BLE001
                pass
        return response
