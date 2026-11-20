"""همگام‌سازی: فهرستِ propertyها + جفت‌کردن با پروژه (دامنه) + دریافتِ روزانهٔ صفحه/کلمه. ایدمپوتنت: بازهٔ دریافتی اول پاک
و بعد درج می‌شود. هر بار از `synced_until - 3` (دادهٔ گوگل تا چند روز اصلاح می‌شود) تا ۲ روز قبل؛ بارِ اول `days_back` روز."""
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .client import Client, GSCError
from .models import GSCAccount, GSCCredential, GSCDeviceDay, GSCPage, GSCPageDay, GSCQueryDay, GSCSite
from .urls_norm import host_of, page_key

KEEP_DAYS = 180   # حداکثر ۶ ماه داده (هم دریافت، هم نگه‌داری) — خواستِ کاربر
CHUNK_DAYS = 1   # روز‌به‌روز: هر درخواست سبک‌تر (سهمیهٔ «بار»ِ گوگل) و سقفِ ردیفِ هر پاسخ کمتر پر می‌شود


def refresh_sites(acc):
    """propertyهای قابلِ‌دسترسِ کلیدِ اصلی و کلیدهای اضافه → GSCSite؛ پروژهٔ هم‌دامنه خودکار جفت می‌شود (اگر هنوز دستی تعیین نشده).
    سایتی که فقط یک کلیدِ اضافه آن را می‌بیند، خودکار به همان کلید وصل می‌شود."""
    from projects.models import Project
    by_dom = {}
    for p in Project.all_objects.filter(organization=acc.organization, personal_owner__isnull=True, deleted_at__isnull=True):
        if p.domain:
            by_dom.setdefault(host_of(p.domain), p)
    seen, main_seen = [], set()
    keys = ([None] if acc.credentials_enc else []) + list(GSCCredential.objects.filter(organization=acc.organization))
    for cred in keys:
        for e in Client(acc, cred).sites():
            if e.get('permissionLevel') == 'siteUnverifiedUser':
                continue
            s, _ = GSCSite.objects.get_or_create(organization=acc.organization, site_url=e['siteUrl'])
            if cred is None:
                main_seen.add(s.pk)
            elif s.pk not in main_seen and not s.credential_id:
                s.credential = cred
            s.permission = e.get('permissionLevel', '')
            if not s.project_id:
                s.project = by_dom.get(host_of(e['siteUrl']))
            s.save()
            seen.append(s.pk)
    return GSCSite.objects.filter(pk__in=seen)


def _f(v):
    return float(v or 0)


def _page_ids(site, urls):
    """{url: page_id} — صفحه‌های تازه یک‌جا ساخته می‌شوند (هر صفحه یک بار، با کلیدِ نرمال‌شده)."""
    by_key = {}
    for u in urls:
        by_key.setdefault(page_key(u), u)
    have = dict(GSCPage.objects.filter(site=site, key__in=list(by_key)).values_list('key', 'id'))
    new = [GSCPage(site=site, key=k, url=u[:1000]) for k, u in by_key.items() if k not in have]
    if new:
        GSCPage.objects.bulk_create(new, batch_size=1000, ignore_conflicts=True)
        have = dict(GSCPage.objects.filter(site=site, key__in=list(by_key)).values_list('key', 'id'))
    return {u: have[page_key(u)] for u in urls}


def prune(site, until):
    """قدیمی‌تر از ۶ ماه پاک + صفحه‌هایی که دیگر هیچ داده‌ای ندارند."""
    cut = until - timedelta(days=KEEP_DAYS - 1)
    GSCQueryDay.objects.filter(site=site, date__lt=cut).delete()
    GSCPageDay.objects.filter(site=site, date__lt=cut).delete()
    GSCDeviceDay.objects.filter(site=site, date__lt=cut).delete()
    used = set(GSCQueryDay.objects.filter(site=site).values_list('page_id', flat=True).distinct()) | \
        set(GSCPageDay.objects.filter(site=site).values_list('page_id', flat=True).distinct())
    GSCPage.objects.filter(site=site).exclude(id__in=used).delete()
    if site.first_date and site.first_date < cut:
        site.first_date = cut
        site.save(update_fields=['first_date'])


def sync_site(client, site, days_back=95, until=None):
    until = until or (date.today() - timedelta(days=2))
    days_back = min(days_back, KEEP_DAYS)
    start = (site.synced_until - timedelta(days=3)) if site.synced_until else (until - timedelta(days=days_back - 1))
    start = max(start, until - timedelta(days=KEEP_DAYS - 1))
    n = 0
    cur = start
    while cur <= until:
        end = min(cur + timedelta(days=CHUNK_DAYS - 1), until)
        q_rows = client.query(site.site_url, cur, end, ['date', 'page', 'query'])
        p_rows = client.query(site.site_url, cur, end, ['date', 'page'])
        d_rows = client.query(site.site_url, cur, end, ['date', 'device'])
        with transaction.atomic():
            pid = _page_ids(site, {r['keys'][1] for r in q_rows} | {r['keys'][1] for r in p_rows})
            GSCQueryDay.objects.filter(site=site, date__range=(cur, end)).delete()
            GSCPageDay.objects.filter(site=site, date__range=(cur, end)).delete()
            GSCDeviceDay.objects.filter(site=site, date__range=(cur, end)).delete()
            GSCDeviceDay.objects.bulk_create([GSCDeviceDay(
                site=site, date=date.fromisoformat(r['keys'][0]), device=r['keys'][1][:10], clicks=int(r.get('clicks', 0)),
                impressions=int(r.get('impressions', 0)), position=round(_f(r.get('position')), 2)) for r in d_rows])
            GSCQueryDay.objects.bulk_create([GSCQueryDay(
                site=site, date=date.fromisoformat(r['keys'][0]), page_id=pid[r['keys'][1]],
                query=r['keys'][2][:400], clicks=int(r.get('clicks', 0)), impressions=int(r.get('impressions', 0)),
                position=round(_f(r.get('position')), 2)) for r in q_rows], batch_size=2000)
            GSCPageDay.objects.bulk_create([GSCPageDay(
                site=site, date=date.fromisoformat(r['keys'][0]), page_id=pid[r['keys'][1]],
                clicks=int(r.get('clicks', 0)), impressions=int(r.get('impressions', 0)),
                position=round(_f(r.get('position')), 2)) for r in p_rows], batch_size=2000)
            site.synced_until = end
            site.first_date = site.first_date or cur
            site.last_error = ''
            site.save(update_fields=['synced_until', 'first_date', 'last_error'])
        n += len(q_rows)
        cur = end + timedelta(days=1)
    prune(site, until)
    return n


STALE = timedelta(hours=3)


def claim(acc):
    """قفلِ اتمیک: True فقط برای یک اجرا (cron/دکمه/خودکار هم‌زمان دوبار همگام نکنند). قفلِ گیرکرده بعد از ۳ ساعت آزاد می‌شود."""
    from django.db.models import Q
    now = timezone.now()
    ok = GSCAccount.objects.filter(pk=acc.pk).filter(Q(syncing=False) | Q(sync_started__lt=now - STALE) |
                                                     Q(sync_started__isnull=True)).update(syncing=True, sync_started=now)
    if ok:
        acc.syncing, acc.sync_started = True, now
    return bool(ok)


def due(acc):
    """وقتِ همگام‌سازیِ خودکار است؟ کلید دارد و آخرین همگام‌سازیِ موفق (یا تلاش) بیش از ۲۰ ساعت پیش بوده."""
    if not acc.credentials_enc and not GSCCredential.objects.filter(organization=acc.organization).exists():
        return False
    times = [t for t in (acc.last_sync, acc.sync_started) if t]
    return not times or timezone.now() - max(times) > timedelta(hours=20)


def after_sync(client, site, log=print):
    """کارهای جانبی — هرکدام جدا، تا خطای یکی بقیه را نخواباند: سایت‌مپ، فهرستِ وردپرس (هفتگی)، رتبهٔ کلماتِ ردیابی‌شده، ایندکس."""
    from . import extras
    from .rankfill import fill_tracked
    for name, fn in (('sitemaps', lambda: extras.refresh_sitemaps(client, site)),
                     ('inventory', lambda: extras.refresh_inventory(site, log=log)),
                     ('rank', lambda: fill_tracked(site, log=log)),
                     ('inspect', lambda: extras.run_inspections(client, site, log=log))):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log(f'{site.site_url}: {name} — {type(e).__name__}: {e}')


def sync_account(acc, site_ids=None, log=print, claimed=False):
    """کلِ حساب: propertyها + هر سایتِ فعالِ جفت‌شده با پروژه (یا همه اگر site_ids). خطای هر سایت جدا ثبت می‌شود."""
    if not claimed and not claim(acc):
        log('همگام‌سازیِ دیگری در حالِ اجراست')
        return 0, ''
    total, err = 0, ''
    try:
        refresh_sites(acc)
        clients = {}
        qs = GSCSite.objects.filter(organization=acc.organization, active=True)
        qs = qs.filter(pk__in=site_ids) if site_ids else qs.filter(project__isnull=False)
        if not qs.exists():
            n_all = GSCSite.objects.filter(organization=acc.organization).count()
            log(f'هیچ سایتِ فعالِ جفت‌شده با پروژه نیست ({n_all} سایت پیدا شد) — در /settings/gsc/ برای هر سایت پروژه انتخاب کن'
                if n_all else 'هیچ سایتی پیدا نشد — ایمیلِ Service Account را در سرچ کنسولِ سایت‌ها اضافه کن')
        for s in qs:
            try:
                if s.credential_id not in clients:
                    clients[s.credential_id] = Client(acc, s.credential)
                n = sync_site(clients[s.credential_id], s, acc.days_back)
                total += n
                log(f'{s.site_url}: {n} ردیف')
                after_sync(clients[s.credential_id], s, log)
            except GSCError as e:
                s.last_error = str(e)[:2000]
                s.save(update_fields=['last_error'])
                log(f'{s.site_url}: {e}')
    except GSCError as e:
        err = str(e)
    except Exception as e:  # noqa: BLE001
        err = f'{type(e).__name__}: {e}'
    if err:
        log(f'خطا: {err}')
    else:
        log(f'تمام شد — {total} ردیف')
    acc.syncing = False
    acc.last_error = err[:2000]
    acc.last_sync = timezone.now() if not err else acc.last_sync
    acc.save(update_fields=['syncing', 'last_error', 'last_sync'])
    return total, err


def run_all(log=print):
    for acc in GSCAccount.objects.all():
        if not acc.credentials_enc and not GSCCredential.objects.filter(organization=acc.organization).exists():
            continue
        log(f'— {acc.organization}')
        sync_account(acc, log=log)
