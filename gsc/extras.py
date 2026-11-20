"""کارهای جانبیِ همگام‌سازی (بعد از دادهٔ جست‌وجو): سایت‌مپ‌ها، صفِ URL Inspection، فهرستِ صفحه‌های وردپرس.

ایندکس: refresh_sitemaps · inspect_urls / run_inspections (صفِ خودکار با سقفِ روزانه) · refresh_inventory (فهرستِ صفحه‌ها از MCPSite)
"""
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .client import GSCError
from .models import GSCInspection, GSCPageDay, GSCSiteURL
from .urls_norm import host_of, page_key

INSPECT_DAILY = 300          # سقفِ خودکار در روز برای هر سایت (سهمیهٔ گوگل ~۲۰۰۰؛ بقیه برای «بررسی»ِ دستی)
INVENTORY_EVERY = timedelta(days=7)
SKIP_TYPES = {'attachment', 'nav_menu_item', 'wp_block', 'wp_template', 'wp_template_part', 'wp_navigation', 'wp_global_styles',
              'wp_font_family', 'wp_font_face', 'elementor_library', 'e-landing-page'}
TAXES = ('category', 'product_cat')


def _dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except ValueError:
        return None


# ───────────── سایت‌مپ ─────────────
def refresh_sitemaps(client, site):
    try:
        items = client.sitemaps(site.site_url)
    except GSCError:
        return
    site.sitemaps = [{'path': m.get('path', ''), 'last_downloaded': m.get('lastDownloaded', ''), 'last_submitted': m.get('lastSubmitted', ''),
                      'errors': int(m.get('errors') or 0), 'warnings': int(m.get('warnings') or 0), 'pending': bool(m.get('isPending')),
                      'type': m.get('type', ''), 'submitted': sum(int(c.get('submitted') or 0) for c in m.get('contents') or [])}
                     for m in items]
    site.save(update_fields=['sitemaps'])


# ───────────── ایندکس / کراول ─────────────
def _quota_left(site):
    today = date.today()
    if site.inspected_on != today:
        site.inspected_on, site.inspected_count = today, 0
        site.save(update_fields=['inspected_on', 'inspected_count'])
    return max(0, INSPECT_DAILY - site.inspected_count)


def inspect_urls(client, site, urls, count_quota=True):
    """هر نشانی را بررسی و در GSCInspection ذخیره می‌کند. خروجی: تعدادِ موفق."""
    n = 0
    for url in urls:
        k = page_key(url)
        obj, _ = GSCInspection.objects.get_or_create(site=site, key=k, defaults={'url': url[:1000]})
        try:
            r = client.inspect(site.site_url, url)
            obj.verdict = r.get('verdict', '')[:20]
            obj.coverage = r.get('coverageState', '')[:200]
            obj.indexing_state = r.get('indexingState', '')[:60]
            obj.robots = r.get('robotsTxtState', '')[:40]
            obj.fetch_state = r.get('pageFetchState', '')[:40]
            obj.last_crawl = _dt(r.get('lastCrawlTime'))
            obj.google_canonical = (r.get('googleCanonical') or '')[:1000]
            obj.user_canonical = (r.get('userCanonical') or '')[:1000]
            obj.error = ''
            n += 1
        except GSCError as e:
            obj.error = str(e)[:300]
            if '429' in str(e) or 'quota' in str(e).lower():
                obj.checked_at = timezone.now()
                obj.save()
                break
        obj.url, obj.checked_at = url[:1000], timezone.now()
        obj.save()
        if count_quota:
            site.inspected_count += 1
    if count_quota:
        site.save(update_fields=['inspected_count'])
    return n


def _due_urls(site):
    """به ترتیبِ اهمیت: صفحهٔ تسک‌های انجام‌شده (تا ایندکس شوند)، صفحه‌های تازهٔ وردپرس، صفحه‌های پربازدید."""
    from tasks.models import Task

    from .analysis import task_pages
    now = timezone.now()
    have = {i.key: i for i in GSCInspection.objects.filter(site=site)}

    def due(url, fresh_days, ok_days):
        i = have.get(page_key(url))
        if not i or not i.checked_at:
            return True
        age = now - i.checked_at
        return age > timedelta(days=ok_days if i.indexed else fresh_days)

    out, seen = [], set()

    def add(url):
        k = page_key(url)
        if k and k not in seen:
            seen.add(k)
            out.append(url)
    # ۱) صفحهٔ تسک‌ها (۱۲۰ روزِ اخیر): ایندکس‌نشده هر ۳ روز، ایندکس‌شده هر ۳۰ روز
    tasks = (Task.all_objects.filter(project=site.project, status='done', done_date__gte=date.today() - timedelta(days=120),
                                     deleted_at__isnull=True).select_related('type_def').prefetch_related('type_def__fields'))
    for t in tasks:
        for url, s, role in task_pages(t):
            if s.pk == site.pk and role == 'page' and due(url, 3, 30):
                add(url)
    # ۲) صفحه‌های تازهٔ وردپرس (۳۰ روزِ اخیر)
    for u in GSCSiteURL.objects.filter(site=site, published__gte=date.today() - timedelta(days=30)).values_list('url', flat=True):
        if due(u, 3, 30):
            add(u)
    # ۳) ۵۰ صفحهٔ پربازدیدِ ۲۸ روزِ اخیر: هفته‌ای یک بار
    if site.synced_until:
        from django.db.models import Sum
        top = (GSCPageDay.objects.filter(site=site, date__gt=site.synced_until - timedelta(days=28))
               .values('page__url').annotate(c=Sum('clicks')).order_by('-c')[:50])
        for r in top:
            if due(r['page__url'], 7, 7):
                add(r['page__url'])
    return out


def run_inspections(client, site, log=print):
    left = _quota_left(site)
    if not left:
        return 0
    urls = _due_urls(site)[:left]
    n = inspect_urls(client, site, urls) if urls else 0
    if urls:
        log(f'{site.site_url}: ایندکس {n}/{len(urls)} صفحه بررسی شد')
    return n


# ───────────── فهرستِ صفحه‌های وردپرس ─────────────
def mcp_site_for(site):
    from mcpgate.models import MCPSite
    for m in MCPSite.objects.filter(organization=site.organization, active=True):
        h = host_of(m.url)
        if h and (h == site.domain or h.endswith('.' + site.domain) or site.domain.endswith('.' + h)):
            return m
    return None


def _fetch_all(ms, path, fields, max_items=20000):
    from mcpgate import wp
    out, page = [], 1
    while len(out) < max_items:
        r = wp.request(ms, path, query={'per_page': 100, 'page': page, '_fields': fields}, timeout=60)
        rows = r['data'] or []
        out.extend(rows)
        if not rows or page >= (r['pages'] or 1):
            break
        page += 1
    return out


def refresh_inventory(site, force=False, log=print):
    """همهٔ نوشته/برگه/محصول/… منتشرشده + دسته‌ها و دسته‌های محصول از REST وردپرس (با دسترسیِ «سایت‌ها»ی MCP)."""
    import html
    import re
    from mcpgate import wp
    if not force and site.inventory_at and timezone.now() - site.inventory_at < INVENTORY_EVERY:
        return None
    ms = mcp_site_for(site)
    if not ms:
        site.inventory_error = 'این سایت در «اتصالِ MCP ← سایت‌ها» نیست (با همین دامنه) — فهرستِ صفحه‌ها از وردپرس گرفته می‌شود'
        site.save(update_fields=['inventory_error'])
        return None
    rows, err = {}, ''
    try:
        st = wp.discover(ms)
        for t, base in st['types'].items():
            if t in SKIP_TYPES:
                continue
            try:
                for it in _fetch_all(ms, 'wp/v2/' + base, 'link,date,title'):
                    link = it.get('link') or ''
                    if host_of(link) and page_key(link):
                        title = html.unescape(re.sub(r'<[^>]+>', '', ((it.get('title') or {}).get('rendered') or '')))[:300]
                        d = _dt(it.get('date'))
                        rows[page_key(link)] = GSCSiteURL(site=site, key=page_key(link), url=link[:1000], kind=t, title=title,
                                                          published=d.date() if d else None)
            except wp.WPError:
                continue   # نوعی که REST نمی‌دهد/دسترسی ندارد
        for t in TAXES:
            base = st['taxes'].get(t)
            if not base:
                continue
            try:
                for it in _fetch_all(ms, 'wp/v2/' + base, 'link,name,count'):
                    link = it.get('link') or ''
                    if page_key(link) and (it.get('count') or 0) > 0:
                        rows[page_key(link)] = GSCSiteURL(site=site, key=page_key(link), url=link[:1000], kind=t,
                                                          title=html.unescape(it.get('name') or '')[:300])
            except wp.WPError:
                continue
    except wp.WPError as e:
        err = str(e)[:300]
    if rows:
        with transaction.atomic():
            GSCSiteURL.objects.filter(site=site).delete()
            GSCSiteURL.objects.bulk_create(rows.values(), batch_size=1000)
        log(f'{site.site_url}: فهرستِ وردپرس {len(rows)} صفحه')
    site.inventory_at, site.inventory_error = timezone.now(), err or ('' if rows else 'هیچ صفحه‌ای از وردپرس برنگشت')
    site.save(update_fields=['inventory_at', 'inventory_error'])
    return len(rows)
