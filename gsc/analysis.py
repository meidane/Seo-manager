"""تحلیلِ دادهٔ ذخیره‌شدهٔ سرچ کنسول — منبعِ واحدِ کارتِ تسک، تبِ پروژه و ابزارهای MCP.

ایندکس:
- site_for_url / task_pages      ← کدام property و کدام صفحه (لینکِ صفحهٔ تسک، یا لینک‌های هدفِ رپورتاژ)
- page_queries / page_series     ← کلماتِ یک صفحه (۳ ماه) + روندِ روزانه
- window / impact                ← قبل/بعدِ یک تاریخ (۲۸ روز) برای سنجیدنِ اثرِ تسک
- task_card                      ← همهٔ دادهٔ کارتِ زیرِ تسک
- project_analysis               ← تبِ «تحلیلِ سرچ کنسول»: افت، نزدیکِ صفحهٔ اول، CTR پایین، رقابتِ صفحه‌ها، اثرِ کارها
جایگاه = میانگینِ وزنی با ایمپرشن (همان روشِ گوگل). همهٔ جمع‌ها با aggregate/annotate.
"""
from datetime import timedelta

from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast

from .models import GSCPage, GSCPageDay, GSCQueryDay, GSCSite
from .urls_norm import host_of, page_key

WIN = 28
# CTRِ مورد انتظارِ تقریبی برای جایگاه‌های ۱ تا ۵ (برای «CTR پایین»)
EXPECTED_CTR = {1: .28, 2: .15, 3: .10, 4: .07, 5: .05}


def _agg():
    return {'c': Sum('clicks'), 'i': Sum('impressions'), 'pw': Sum(F('position') * Cast('impressions', FloatField()))}


def _fmt(c, i, pw):
    c, i = int(c or 0), int(i or 0)
    return {'clicks': c, 'impressions': i, 'ctr': round(c * 100 / i, 2) if i else 0,
            'position': round((pw or 0) / i, 1) if i else None}


# ───────────── کدام صفحه ─────────────
def _sites(org):
    return list(GSCSite.objects.filter(organization=org, active=True))


def site_for_url(org, url, sites=None):
    h = host_of(url)
    if not h:
        return None
    for s in sites if sites is not None else _sites(org):
        d = s.domain
        if d and (h == d or h.endswith('.' + d)):
            return s
    return None


def _cost(t):
    try:
        from mcpgate.panel.reports import _cost as c
        return c(t)
    except Exception:  # noqa: BLE001
        return float(t.media_cost or 0)


def task_pages(task):
    """[(url, site, role)] — role: page (لینکِ صفحهٔ همین تسک) | target (لینکِ هدفِ رپورتاژ). فقط صفحه‌هایی که property دارند."""
    org = task.organization
    sites = _sites(org)
    if not sites:
        return []
    cand = []
    if task.page_link:
        cand.append((task.page_link.strip(), 'page'))
    if task.type_def_id:
        for f in task.type_def.fields.all():
            if f.is_link_source:
                cand += [(ln.strip(), 'target') for ln in str((task.custom or {}).get(f.key) or '').splitlines() if ln.strip()]
    out, seen = [], set()
    for url, role in cand:
        s = site_for_url(org, url, sites)
        k = page_key(url)
        if s and k not in seen:
            seen.add(k)
            out.append((url, s, role))
    return out[:5]


# ───────────── دادهٔ صفحه ─────────────
def _end(site):
    return site.synced_until


def _pid(site, key):
    """شمارهٔ صفحه (GSCPage) یا 0 اگر این صفحه در داده نیست — فیلترِ `page_id=0` نتیجهٔ خالی می‌دهد."""
    return GSCPage.objects.filter(site=site, key=key).values_list('id', flat=True).first() or 0


def page_queries(site, key, days=90, limit=200):
    end = _end(site)
    if not end:
        return []
    rows = (GSCQueryDay.objects.filter(page_id=_pid(site, key), date__gt=end - timedelta(days=days))
            .values('query').annotate(**_agg()).order_by('-c', '-i')[:limit])
    return [{'query': r['query'], **_fmt(r['c'], r['i'], r['pw'])} for r in rows]


def page_series(site, key, days=90):
    end = _end(site)
    if not end:
        return []
    rows = {r['date']: r for r in GSCPageDay.objects.filter(page_id=_pid(site, key), date__gt=end - timedelta(days=days))
            .values('date').annotate(**_agg())}
    out, d = [], end - timedelta(days=days - 1)
    while d <= end:
        r = rows.get(d)
        out.append({'date': d.isoformat(), **(_fmt(r['c'], r['i'], r['pw']) if r else _fmt(0, 0, 0))})
        d += timedelta(days=1)
    return out


def window(site, key, start, end):
    r = GSCPageDay.objects.filter(page_id=_pid(site, key), date__range=(start, end)).aggregate(**_agg())
    return _fmt(r['c'], r['i'], r['pw'])


def impact(site, key, pivot, days=WIN):
    """قبل/بعدِ تاریخِ انجام. اگر هنوز ۲۸ روز نگذشته، `days_after` کمتر است و بعد با همان تعداد روزِ قبل مقایسه می‌شود."""
    end = _end(site)
    if not end or not pivot or pivot >= end:
        return None
    n = min(days, (end - pivot).days)
    before = window(site, key, pivot - timedelta(days=n), pivot - timedelta(days=1))
    after = window(site, key, pivot + timedelta(days=1), pivot + timedelta(days=n))
    pos_d = (before['position'] - after['position']) if before['position'] and after['position'] else None
    return {'days': n, 'full': n >= days, 'before': before, 'after': after,
            'clicks_delta': after['clicks'] - before['clicks'], 'position_delta': round(pos_d, 1) if pos_d is not None else None}


def task_card(task):
    """کارتِ زیرِ تسک: برای هر صفحهٔ مرتبط کلماتِ ۳ ماه + نمودار + (اگر انجام شده) قبل/بعد."""
    pages = []
    for url, s, role in task_pages(task):
        k = page_key(url)
        item = {'url': url, 'role': role, 'site': s.site_url, 'until': s.synced_until.isoformat() if s.synced_until else None,
                'queries': page_queries(s, k), 'series': page_series(s, k)}
        if task.status == 'done' and task.done_date:
            item['impact'] = impact(s, k, task.done_date)
        pages.append(item)
    return pages


# ───────────── تحلیلِ پروژه ─────────────
def _pages_window(sites, start, end):
    return {(r['site'], r['page__key']): r for r in GSCPageDay.objects.filter(site__in=sites, date__range=(start, end))
            .values('site', 'page__key').annotate(**_agg())}


def project_analysis(project):
    from tasks.models import Task
    sites = list(GSCSite.objects.filter(project=project, active=True, synced_until__isnull=False))
    if not sites:
        return None
    end = max(s.synced_until for s in sites)
    cur0, prev0 = end - timedelta(days=WIN - 1), end - timedelta(days=2 * WIN - 1)
    prev1 = cur0 - timedelta(days=1)

    tot_c = GSCPageDay.objects.filter(site__in=sites, date__range=(cur0, end)).aggregate(**_agg())
    tot_p = GSCPageDay.objects.filter(site__in=sites, date__range=(prev0, prev1)).aggregate(**_agg())
    series = {r['date']: r for r in GSCPageDay.objects.filter(site__in=sites, date__gt=end - timedelta(days=90))
              .values('date').annotate(**_agg())}
    ser, d = [], end - timedelta(days=89)
    while d <= end:
        r = series.get(d)
        ser.append({'date': d.isoformat(), **(_fmt(r['c'], r['i'], r['pw']) if r else _fmt(0, 0, 0))})
        d += timedelta(days=1)

    # ۱) افتِ صفحه: کلیکِ ۲۸ روزِ اخیر ≥۳۰٪ کمتر از ۲۸ روزِ قبل (و حداقل ۱۰ کلیکِ قبلی)
    cur, prev = _pages_window(sites, cur0, end), _pages_window(sites, prev0, prev1)
    decline = []
    for k, p in prev.items():
        c = cur.get(k, {'c': 0, 'i': 0, 'pw': 0})
        pc, cc = int(p['c'] or 0), int(c['c'] or 0)
        if pc >= 10 and cc <= pc * .7:
            decline.append({'page': k[1], 'before': _fmt(p['c'], p['i'], p['pw']), 'after': _fmt(c['c'], c['i'], c['pw']),
                            'drop': round((pc - cc) * 100 / pc)})
    decline.sort(key=lambda x: -(x['before']['clicks'] - x['after']['clicks']))

    # کلمه×صفحهٔ ۲۸ روزِ اخیر (پایهٔ بقیه)
    qp = list(GSCQueryDay.objects.filter(site__in=sites, date__range=(cur0, end))
              .values('query', 'page__key').annotate(**_agg()).filter(i__gte=20).order_by('-i')[:5000])
    rows = [{'query': r['query'], 'page': r['page__key'], **_fmt(r['c'], r['i'], r['pw'])} for r in qp]

    # ۲) نزدیکِ صفحهٔ اول: جایگاه ۸ تا ۲۰ با نمایشِ زیاد
    striking = sorted([r for r in rows if r['position'] and 8 <= r['position'] <= 20 and r['impressions'] >= 50],
                      key=lambda r: -r['impressions'])
    # ۳) CTR پایین: جایگاه ≤۵ ولی CTR کمتر از نصفِ انتظار
    low_ctr = sorted([r for r in rows if r['position'] and r['position'] <= 5.5 and r['impressions'] >= 100
                      and r['ctr'] / 100 < EXPECTED_CTR.get(max(1, round(r['position'])), .05) * .5],
                     key=lambda r: -r['impressions'])
    # ۴) رقابتِ صفحه‌ها (کانیبالیزیشن): یک کلمه، ≥۲ صفحه که هرکدام ≥۱۵٪ نمایشِ آن کلمه را دارند
    byq = {}
    for r in rows:
        byq.setdefault(r['query'], []).append(r)
    cannibal = []
    for q, lst in byq.items():
        tot = sum(x['impressions'] for x in lst)
        strong = [x for x in lst if x['impressions'] >= tot * .15]
        if len(strong) >= 2 and tot >= 50:
            cannibal.append({'query': q, 'impressions': tot,
                             'pages': [{'page': x['page'], 'impressions': x['impressions'], 'clicks': x['clicks'],
                                        'position': x['position']} for x in sorted(strong, key=lambda x: -x['impressions'])]})
    cannibal.sort(key=lambda x: -x['impressions'])

    # ۵) اثرِ کارها: تسک‌های انجام‌شدهٔ ۶ ماهِ اخیر که صفحه (یا هدفِ رپورتاژ) در سرچ کنسول دارند
    work = []
    tasks = (Task.all_objects.filter(project=project, status='done', done_date__gte=end - timedelta(days=180),
                                     done_date__lt=end, deleted_at__isnull=True)
             .select_related('type_def').prefetch_related('type_def__fields').order_by('-done_date'))
    for t in tasks[:300]:
        tp = task_pages(t)
        if not tp:
            continue
        ims = [impact(s, page_key(u), t.done_date) for u, s, _ in tp]
        ims = [x for x in ims if x]
        if not ims:
            continue
        cd = sum(x['clicks_delta'] for x in ims)
        pds = [x['position_delta'] for x in ims if x['position_delta'] is not None]
        cost = _cost(t) if any(r == 'target' for _, _, r in tp) else 0
        work.append({'id': t.id, 'title': t.title, 'type': t.type_def.name if t.type_def_id else t.get_task_type_display(),
                     'done': t.done_date.isoformat(), 'days': min(x['days'] for x in ims), 'full': all(x['full'] for x in ims),
                     'page': tp[0][0], 'clicks_before': sum(x['before']['clicks'] for x in ims),
                     'clicks_after': sum(x['after']['clicks'] for x in ims), 'clicks_delta': cd,
                     'position_delta': round(sum(pds) / len(pds), 1) if pds else None,
                     'cost': cost or None, 'cost_per_click': round(cost / cd) if cost and cd > 0 else None})
    by_type = {}
    for w in work:
        if not w['full']:
            continue
        g = by_type.setdefault(w['type'], {'type': w['type'], 'n': 0, 'clicks': 0, 'pos': [], 'cost': 0, 'pos_n': 0})
        g['n'] += 1
        g['clicks'] += w['clicks_delta']
        if w['position_delta'] is not None:
            g['pos'].append(w['position_delta'])
        g['cost'] += w['cost'] or 0
    types = [{'type': g['type'], 'n': g['n'], 'avg_clicks': round(g['clicks'] / g['n'], 1),
              'avg_position': round(sum(g['pos']) / len(g['pos']), 1) if g['pos'] else None,
              'cost_per_click': round(g['cost'] / g['clicks']) if g['cost'] and g['clicks'] > 0 else None}
             for g in by_type.values()]
    types.sort(key=lambda g: -g['avg_clicks'])

    return {'until': end.isoformat(), 'sites': [s.site_url for s in sites],
            'total': {'current': _fmt(tot_c['c'], tot_c['i'], tot_c['pw']), 'previous': _fmt(tot_p['c'], tot_p['i'], tot_p['pw'])},
            'series': ser, 'decline': decline[:20], 'striking': striking[:25], 'low_ctr': low_ctr[:20],
            'cannibal': cannibal[:15], 'work': work[:60], 'by_type': types}


# ───────────── خلاصهٔ فشرده برای MCP (کم‌توکن) ─────────────
def page_brief(org, url, days=90, limit=40):
    """{page, until, total_28d, queries: {cols, rows}} یا None اگر صفحه در سرچ کنسول نباشد."""
    s = site_for_url(org, url)
    if not s or not s.synced_until:
        return None
    k = page_key(url)
    qs = page_queries(s, k, days, limit)
    end = s.synced_until
    tot = window(s, k, end - timedelta(days=WIN - 1), end)
    if not qs and not tot['impressions']:
        return None
    return {'page': url, 'until': end.isoformat(), 'last_28d': tot, 'days': days,
            'queries': {'cols': ['query', 'clicks', 'impressions', 'ctr', 'position'],
                        'rows': [[q['query'], q['clicks'], q['impressions'], q['ctr'], q['position']] for q in qs]}}


def briefs_for(org, text='', task=None):
    """صفحه‌های مرتبط با یک درخواست: لینک‌های داخلِ متن + صفحهٔ تسک → خلاصهٔ هرکدام (حداکثر ۳)."""
    import re
    urls = re.findall(r'https?://[^\s<>"\'،]+', str(text or ''))
    if task is not None:
        urls = [u for u, _, _ in task_pages(task)] + urls
    out, seen = [], set()
    for u in urls:
        k = page_key(u)
        if k in seen:
            continue
        seen.add(k)
        b = page_brief(org, u)
        if b:
            out.append(b)
        if len(out) >= 3:
            break
    return out


def project_brief(project, limit=10):
    """تحلیلِ پروژه به شکلِ جدول‌های کوتاه برای MCP."""
    d = project_analysis(project)
    if not d:
        return None
    t = lambda cols, rows: {'cols': cols, 'rows': rows[:limit]}  # noqa: E731
    return {'until': d['until'], 'last_28d': d['total']['current'], 'previous_28d': d['total']['previous'],
            'decline': t(['page', 'clicks_before', 'clicks_after', 'drop_%'], [[x['page'], x['before']['clicks'], x['after']['clicks'], x['drop']] for x in d['decline']]),
            'striking_distance': t(['query', 'page', 'impressions', 'clicks', 'position'], [[x['query'], x['page'], x['impressions'], x['clicks'], x['position']] for x in d['striking']]),
            'low_ctr': t(['query', 'page', 'position', 'impressions', 'ctr'], [[x['query'], x['page'], x['position'], x['impressions'], x['ctr']] for x in d['low_ctr']]),
            'cannibalization': t(['query', 'pages'], [[x['query'], [p['page'] for p in x['pages']]] for x in d['cannibal']]),
            'work_by_type': t(['type', 'n', 'avg_click_gain', 'avg_position_gain', 'cost_per_click'], [[g['type'], g['n'], g['avg_clicks'], g['avg_position'], g['cost_per_click']] for g in d['by_type']]),
            'recent_work': t(['task', 'type', 'done', 'clicks_before', 'clicks_after', 'position_gain'], [[w['id'], w['type'], w['done'], w['clicks_before'], w['clicks_after'], w['position_delta']] for w in d['work']])}
