"""تحلیلِ دادهٔ ذخیره‌شدهٔ سرچ کنسول — منبعِ واحدِ کارتِ تسک، تبِ پروژه و ابزارهای MCP.

ایندکس:
- site_for_url / task_pages      ← کدام property و کدام صفحه (لینکِ صفحهٔ تسک، یا لینک‌های هدفِ رپورتاژ)
- page_queries / page_series     ← کلماتِ یک صفحه (۳ ماه) + روندِ روزانه
- window / impact                ← قبل/بعدِ یک تاریخ (۲۸ روز) برای سنجیدنِ اثرِ تسک
- task_card                      ← همهٔ دادهٔ کارتِ زیرِ تسک
- project_analysis               ← تبِ «تحلیلِ سرچ کنسول»: افت، نزدیکِ صفحهٔ اول، CTR پایین، رقابتِ صفحه‌ها، اثرِ کارها
                                   + تغییرِ کلمات، بخش‌های سایت، دستگاه‌ها، ایندکس/سایت‌مپ، خلاصهٔ صفحه‌های بی‌نمایش
- target_keywords / inspection   ← کارتِ تسک: کلمهٔ هدفِ تسک (سرچ کنسول + افزونه) و وضعیتِ ایندکسِ صفحه
- unseen_pages                   ← فهرستِ کاملِ صفحه‌های بی‌نمایشِ وردپرس (فیلترِ نوع/جستجو/جدید)
جایگاه = میانگینِ وزنی با ایمپرشن (همان روشِ گوگل). همهٔ جمع‌ها با aggregate/annotate.
"""
from datetime import timedelta

from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast

from .models import GSCDeviceDay, GSCInspection, GSCPage, GSCPageDay, GSCQueryDay, GSCSite, GSCSiteURL
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
        if role == 'page':
            item['keywords'] = target_keywords(task, s, url)
        item['index'] = inspection(s, k)
        pages.append(item)
    return pages


def _task_keywords(task):
    """کلمه‌های هدفِ تسک: فیلدهای `is_keyword_source` (tags = چند کلمه؛ textarea = هر خط یکی)."""
    out = []
    if task.type_def_id:
        for f in task.type_def.fields.all():
            if f.is_keyword_source:
                v = (task.custom or {}).get(f.key)
                vals = v if isinstance(v, list) else str(v or '').replace('،', '\n').replace(',', '\n').splitlines()
                out += [str(x).strip() for x in vals if str(x).strip()]
    return list(dict.fromkeys(out))[:15]


def target_keywords(task, site, url, days=WIN):
    """برای هر کلمهٔ هدفِ تسک: جایگاهِ همین صفحه برای آن کلمه (۲۸ روزِ اخیر)، بهترین صفحهٔ سایت برای آن کلمه، و آخرین رتبهٔ افزونه."""
    from seo.match import norm_kw
    from seo.models import KeywordRankSnapshot
    kws = _task_keywords(task)
    if not kws or not site.synced_until:
        return []
    key = page_key(url)
    nk = {norm_kw(k): k for k in kws}
    rows = (GSCQueryDay.objects.filter(site=site, date__gt=site.synced_until - timedelta(days=days),
                                       query__in=set(nk) | {k.lower() for k in kws})
            .values('query', 'page__key', 'page__url').annotate(**_agg()))
    agg = {}
    for r in rows:
        k = nk.get(norm_kw(r['query']))
        if not k:
            continue
        a = agg.setdefault(k, {'page': None, 'best': None})
        f = _fmt(r['c'], r['i'], r['pw'])
        if r['page__key'] == key:
            a['page'] = f
        if not a['best'] or f['impressions'] > a['best']['impressions']:
            a['best'] = {**f, 'url': r['page__url'], 'same': r['page__key'] == key}
    ext = {}
    if task.project_id:
        for snap in (KeywordRankSnapshot.objects.filter(keyword__project_id=task.project_id, source='ext')
                     .select_related('keyword').order_by('-date')[:500]):
            ext.setdefault(norm_kw(snap.keyword.keyword), {'position': snap.position, 'date': snap.date.isoformat()})
    return [{'keyword': k, 'page': agg.get(k, {}).get('page'), 'best': agg.get(k, {}).get('best'), 'ext': ext.get(norm_kw(k))} for k in kws]


def inspection(site, key):
    i = GSCInspection.objects.filter(site=site, key=key).first()
    if not i or not i.checked_at:
        return None
    return {'indexed': i.indexed, 'verdict': i.verdict, 'coverage': i.coverage, 'error': i.error,
            'last_crawl': i.last_crawl.date().isoformat() if i.last_crawl else None, 'checked': i.checked_at.date().isoformat(),
            'canonical_mismatch': bool(i.google_canonical and i.user_canonical and page_key(i.google_canonical) != page_key(i.user_canonical)),
            'google_canonical': i.google_canonical}


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

    changes = _changes(sites, cur0, end, prev0, prev1)
    sections = _sections(cur, prev)
    devices = _devices(sites, cur0, end, prev0, prev1)
    index = _index(sites)
    unseen = _unseen_summary(sites, end)

    return {'until': end.isoformat(), 'sites': [s.site_url for s in sites],
            'changes': changes, 'sections': sections, 'devices': devices, 'index': index, 'unseen': unseen,
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
            'new_queries': t(['query', 'impressions', 'clicks', 'position'], [[x['query'], x['impressions'], x['clicks'], x['position']] for x in d['changes']['new']]),
            'lost_queries': t(['query', 'impressions_before', 'position_before'], [[x['query'], x['impressions'], x['position']] for x in d['changes']['lost']]),
            'movers': t(['query', 'position_before', 'position_now', 'gain'], [[x['query'], x['before'], x['after'], x['delta']] for x in d['changes']['up'] + d['changes']['down']]),
            'sections': t(['section', 'clicks_prev', 'clicks_now', 'position_now'], [[x['section'], x['previous']['clicks'], x['current']['clicks'], x['current']['position']] for x in d['sections']]),
            'devices': [[x['device'], x['current']['clicks'], x['previous']['clicks']] for x in d['devices']],
            'index': {k: (v if k in ('checked', 'indexed') else len(v)) for k, v in (d['index'] or {}).items()},
            'unseen_by_type': [[k['kind'], k['total'], k['unseen']] for k in d['unseen'].get('kinds', [])],
            'recent_work': t(['task', 'type', 'done', 'clicks_before', 'clicks_after', 'position_gain'], [[w['id'], w['type'], w['done'], w['clicks_before'], w['clicks_after'], w['position_delta']] for w in d['work']])}


# ───────────── بخش‌های تازهٔ تبِ پروژه ─────────────
def _q_window(sites, start, end):
    return {r['query']: r for r in GSCQueryDay.objects.filter(site__in=sites, date__range=(start, end))
            .values('query').annotate(**_agg())}


def _changes(sites, cur0, end, prev0, prev1, limit=20):
    """کلمه‌ها (کلِ سایت): تازه (حالا ≥۱۰ نمایش، قبلاً هیچ)، ازدست‌رفته (قبلاً ≥۲۰، حالا هیچ)، بیشترین بهتر/بدترشدنِ جایگاه."""
    cur, prev = _q_window(sites, cur0, end), _q_window(sites, prev0, prev1)
    f = lambda r: _fmt(r['c'], r['i'], r['pw'])  # noqa: E731
    new = sorted(({'query': q, **f(r)} for q, r in cur.items() if q not in prev and (r['i'] or 0) >= 10), key=lambda x: -x['impressions'])
    lost = sorted(({'query': q, **f(r)} for q, r in prev.items() if q not in cur and (r['i'] or 0) >= 20), key=lambda x: -x['impressions'])
    moves = []
    for q, r in cur.items():
        p = prev.get(q)
        if p and (r['i'] or 0) >= 20 and (p['i'] or 0) >= 20:
            a, b = f(p), f(r)
            if a['position'] and b['position']:
                moves.append({'query': q, 'before': a['position'], 'after': b['position'], 'delta': round(a['position'] - b['position'], 1),
                              'impressions': b['impressions'], 'clicks': b['clicks']})
    up = sorted([m for m in moves if m['delta'] >= 1], key=lambda m: -m['delta'])
    down = sorted([m for m in moves if m['delta'] <= -1], key=lambda m: m['delta'])
    return {'new': new[:limit], 'new_n': len(new), 'lost': lost[:limit], 'lost_n': len(lost), 'up': up[:limit], 'down': down[:limit]}


def _section_of(key):
    """steeltak.com/blog/x → /blog/ ؛ صفحه‌های سطحِ اول (/about، صفحهٔ اصلی) → «/» (ریشه)."""
    parts = key.split('/', 2)
    return '/' + parts[1] + '/' if len(parts) > 2 and parts[1] else '/'


def _sections(cur, prev):
    """بخش‌های سایت = اولین پوشهٔ نشانی (/blog/، /product/، …)؛ ۲۸ روزِ اخیر در برابرِ قبل."""
    agg = {}
    for which, src in (('c', cur), ('p', prev)):
        for (_, key), r in src.items():
            sec = _section_of(key)
            a = agg.setdefault(sec, {'c': [0, 0, 0.0, set()], 'p': [0, 0, 0.0, set()]})[which]
            a[0] += r['c'] or 0
            a[1] += r['i'] or 0
            a[2] += r['pw'] or 0
            a[3].add(key)
    out = []
    for sec, v in agg.items():
        c, p = v['c'], v['p']
        cf, pf = _fmt(c[0], c[1], c[2]), _fmt(p[0], p[1], p[2])
        out.append({'section': sec, 'pages': len(c[3] or p[3]), 'current': cf, 'previous': pf,
                    'clicks_delta': cf['clicks'] - pf['clicks'],
                    'position_delta': round(pf['position'] - cf['position'], 1) if cf['position'] and pf['position'] else None})
    out.sort(key=lambda x: -(x['current']['clicks'] + x['previous']['clicks']))
    return out[:15]


def _devices(sites, cur0, end, prev0, prev1):
    def w(a, b):
        return {r['device']: _fmt(r['c'], r['i'], r['pw']) for r in GSCDeviceDay.objects.filter(site__in=sites, date__range=(a, b))
                .values('device').annotate(**_agg())}
    c, p = w(cur0, end), w(prev0, prev1)
    label = {'MOBILE': 'موبایل', 'DESKTOP': 'دسکتاپ', 'TABLET': 'تبلت'}
    return [{'device': label.get(d, d), 'current': c.get(d) or _fmt(0, 0, 0), 'previous': p.get(d) or _fmt(0, 0, 0)}
            for d in ('MOBILE', 'DESKTOP', 'TABLET') if d in c or d in p]


def _index(sites):
    """ایندکس/کراول از URL Inspectionهای ذخیره‌شده + سایت‌مپ‌ها."""
    from datetime import date
    insp = list(GSCInspection.objects.filter(site__in=sites, checked_at__isnull=False))
    if not insp and not any(s.sitemaps for s in sites):
        return None
    titles = {u.key: u.title for u in GSCSiteURL.objects.filter(site__in=sites, key__in=[i.key for i in insp])}
    row = lambda i: {'url': i.url, 'key': i.key, 'title': titles.get(i.key, ''), 'coverage': i.coverage or i.error,  # noqa: E731
                     'last_crawl': i.last_crawl.date().isoformat() if i.last_crawl else None, 'checked': i.checked_at.date().isoformat()}
    stale = date.today() - timedelta(days=30)
    return {'checked': len(insp), 'indexed': sum(1 for i in insp if i.indexed),
            'not_indexed': [row(i) for i in insp if not i.indexed and not i.error][:100],
            'stale': [row(i) for i in insp if i.indexed and i.last_crawl and i.last_crawl.date() < stale][:50],
            'sitemaps': [m for s in sites for m in (s.sitemaps or [])]}


def _seen_keys(sites, end, days=90):
    return set(GSCPageDay.objects.filter(site__in=sites, date__gt=end - timedelta(days=days), impressions__gt=0)
               .values_list('page__key', flat=True).distinct())


def _unseen_summary(sites, end, new_days=21):
    """به تفکیکِ نوع: کل / با نمایش / بی‌نمایش (صفحه‌های تازه‌تر از ۲۱ روز جدا شمرده می‌شوند — هنوز فرصت نداشته‌اند)."""
    from datetime import date
    urls = list(GSCSiteURL.objects.filter(site__in=sites).values('key', 'kind', 'published'))
    if not urls:
        errs = [s.inventory_error for s in sites if s.inventory_error]
        return {'kinds': [], 'error': errs[0] if errs else '', 'pending': not any(s.inventory_at for s in sites)}
    seen, fresh = _seen_keys(sites, end), date.today() - timedelta(days=new_days)
    by = {}
    for u in urls:
        k = by.setdefault(u['kind'], {'kind': u['kind'], 'total': 0, 'seen': 0, 'unseen': 0, 'new': 0})
        k['total'] += 1
        if u['key'] in seen:
            k['seen'] += 1
        elif u['published'] and u['published'] > fresh:
            k['new'] += 1
        else:
            k['unseen'] += 1
    kinds = sorted(by.values(), key=lambda k: -k['total'])
    return {'kinds': kinds, 'total': sum(k['total'] for k in kinds), 'unseen_total': sum(k['unseen'] for k in kinds),
            'inventory_at': max((s.inventory_at for s in sites if s.inventory_at), default=None)}


def unseen_pages(project, kind='', q='', include_new=False, offset=0, limit=100, new_days=21):
    """فهرستِ صفحه‌های منتشرشدهٔ وردپرس که در ۹۰ روزِ اخیر هیچ نمایشی در گوگل نداشته‌اند (+ وضعیتِ ایندکس اگر بررسی شده)."""
    from datetime import date
    sites = list(GSCSite.objects.filter(project=project, active=True, synced_until__isnull=False))
    if not sites:
        return {'rows': [], 'total': 0}
    end = max(s.synced_until for s in sites)
    seen, fresh = _seen_keys(sites, end), date.today() - timedelta(days=new_days)
    qs = GSCSiteURL.objects.filter(site__in=sites).order_by('published', 'id')
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(url__icontains=q)
    rows = [u for u in qs if u.key not in seen and (include_new or not u.published or u.published <= fresh)]
    insp = {i.key: i for i in GSCInspection.objects.filter(site__in=sites, key__in=[u.key for u in rows[offset:offset + limit]])}
    out = []
    for u in rows[offset:offset + limit]:
        i = insp.get(u.key)
        out.append({'url': u.url, 'key': u.key, 'title': u.title, 'kind': u.kind, 'published': u.published.isoformat() if u.published else None,
                    'index': None if not i or not i.checked_at else {'indexed': i.indexed, 'coverage': i.coverage or i.error,
                                                                     'last_crawl': i.last_crawl.date().isoformat() if i.last_crawl else None}})
    return {'rows': out, 'total': len(rows), 'offset': offset, 'site': sites[0].pk}
