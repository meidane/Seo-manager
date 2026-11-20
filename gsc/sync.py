"""همگام‌سازی: فهرستِ propertyها + جفت‌کردن با پروژه (دامنه) + دریافتِ روزانهٔ صفحه/کلمه. ایدمپوتنت: بازهٔ دریافتی اول پاک
و بعد درج می‌شود. هر بار از `synced_until - 3` (دادهٔ گوگل تا چند روز اصلاح می‌شود) تا ۲ روز قبل؛ بارِ اول `days_back` روز."""
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .client import Client, GSCError
from .models import GSCAccount, GSCPageDay, GSCQueryDay, GSCSite
from .urls_norm import host_of, page_key

CHUNK_DAYS = 30


def refresh_sites(acc):
    """propertyهای قابلِ‌دسترس → GSCSite؛ پروژهٔ هم‌دامنه خودکار جفت می‌شود (اگر هنوز دستی تعیین نشده)."""
    from projects.models import Project
    entries = Client(acc).sites()
    by_dom = {}
    for p in Project.all_objects.filter(organization=acc.organization, personal_owner__isnull=True, deleted_at__isnull=True):
        if p.domain:
            by_dom.setdefault(host_of(p.domain), p)
    seen = []
    for e in entries:
        if e.get('permissionLevel') == 'siteUnverifiedUser':
            continue
        s, _ = GSCSite.objects.get_or_create(organization=acc.organization, site_url=e['siteUrl'])
        s.permission = e.get('permissionLevel', '')
        if not s.project_id:
            s.project = by_dom.get(host_of(e['siteUrl']))
        s.save()
        seen.append(s.pk)
    return GSCSite.objects.filter(pk__in=seen)


def _f(v):
    return float(v or 0)


def sync_site(client, site, days_back=95, until=None):
    until = until or (date.today() - timedelta(days=2))
    start = (site.synced_until - timedelta(days=3)) if site.synced_until else (until - timedelta(days=days_back - 1))
    n = 0
    cur = start
    while cur <= until:
        end = min(cur + timedelta(days=CHUNK_DAYS - 1), until)
        q_rows = client.query(site.site_url, cur, end, ['date', 'page', 'query'])
        p_rows = client.query(site.site_url, cur, end, ['date', 'page'])
        with transaction.atomic():
            GSCQueryDay.objects.filter(site=site, date__range=(cur, end)).delete()
            GSCPageDay.objects.filter(site=site, date__range=(cur, end)).delete()
            GSCQueryDay.objects.bulk_create([GSCQueryDay(
                site=site, date=date.fromisoformat(r['keys'][0]), page=r['keys'][1][:1000], page_key=page_key(r['keys'][1]),
                query=r['keys'][2][:400], clicks=int(r.get('clicks', 0)), impressions=int(r.get('impressions', 0)),
                position=round(_f(r.get('position')), 2)) for r in q_rows], batch_size=2000)
            GSCPageDay.objects.bulk_create([GSCPageDay(
                site=site, date=date.fromisoformat(r['keys'][0]), page=r['keys'][1][:1000], page_key=page_key(r['keys'][1]),
                clicks=int(r.get('clicks', 0)), impressions=int(r.get('impressions', 0)),
                position=round(_f(r.get('position')), 2)) for r in p_rows], batch_size=2000)
            site.synced_until = end
            site.first_date = site.first_date or cur
            site.last_error = ''
            site.save(update_fields=['synced_until', 'first_date', 'last_error'])
        n += len(q_rows)
        cur = end + timedelta(days=1)
    return n


def sync_account(acc, site_ids=None, log=print):
    """کلِ حساب: propertyها + هر سایتِ فعالِ جفت‌شده با پروژه (یا همه اگر site_ids). خطای هر سایت جدا ثبت می‌شود."""
    acc.syncing = True
    acc.save(update_fields=['syncing'])
    total, err = 0, ''
    try:
        client = Client(acc)
        refresh_sites(acc)
        qs = GSCSite.objects.filter(organization=acc.organization, active=True)
        qs = qs.filter(pk__in=site_ids) if site_ids else qs.filter(project__isnull=False)
        for s in qs:
            try:
                n = sync_site(client, s, acc.days_back)
                total += n
                log(f'{s.site_url}: {n} ردیف')
            except GSCError as e:
                s.last_error = str(e)[:2000]
                s.save(update_fields=['last_error'])
                log(f'{s.site_url}: {e}')
    except GSCError as e:
        err = str(e)
    except Exception as e:  # noqa: BLE001
        err = f'{type(e).__name__}: {e}'
    acc.syncing = False
    acc.last_error = err[:2000]
    acc.last_sync = timezone.now() if not err else acc.last_sync
    acc.save(update_fields=['syncing', 'last_error', 'last_sync'])
    return total, err


def run_all(log=print):
    for acc in GSCAccount.objects.exclude(credentials_enc=''):
        log(f'— {acc.organization}')
        sync_account(acc, log=log)
