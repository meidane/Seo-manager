"""خلاصه‌سازیِ رتبهٔ کلمات کلیدی برای تبِ «کلمات کلیدی» پروژه — دو نما (کلمه/لینک)
از یک منبع (`TrackedKeyword` + `KeywordRankSnapshot`). یک کوئری برای خواندنِ همهٔ
اسنپ‌شات‌های ۹۰‌روزهٔ اخیر، بقیه (پنجره‌ها، اسپارک‌لاین، میانگین) در پایتون روی همان
دیکشنریِ کوچک — نه حلقهٔ پایتونی روی کوئری‌ست جداگانه به‌ازای هر ردیف.
"""
from collections import defaultdict
from datetime import date, timedelta

from django.utils.html import format_html

from .models import KeywordRankSnapshot

PERIOD_CHOICES = [(30, '۳۰ روز'), (90, '۹۰ روز'), (180, '۱۸۰ روز')]
SPARK_DAYS = 90  # «نمودار کوچک ۳ ماه اخیر» — همیشه ثابت، مستقل از انتخاب بازه


def resolve_period(request):
    try:
        days = int(request.GET.get('kw_period', 30))
    except (TypeError, ValueError):
        days = 30
    return days if days in dict(PERIOD_CHOICES) else 30


def _windows(days):
    """بازهٔ جاری + بازهٔ قبلیِ هم‌طول (برای «تغییر نسبت به بازهٔ قبل»)."""
    end = date.today()
    start = end - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return start, end, prev_start, prev_end


def _window_position(by_date, start, end):
    """جدیدترین جایگاهِ موجود در بازه؛ None اگر داده‌ای نبود."""
    days_in_range = sorted((d for d in by_date if start <= d <= end), reverse=True)
    return by_date[days_in_range[0]] if days_in_range else None


def sparkline_svg(points, width=90, height=24):
    """points: [(date, position)] صعودی؛ جایگاهِ کوچک‌تر (بهتر) بالای نمودار می‌آید."""
    if len(points) < 2:
        return ''
    positions = [p for _, p in points]
    lo, hi = min(positions), max(positions)
    span = (hi - lo) or 1
    n = len(points)
    xs = [round(i / (n - 1) * width, 1) for i in range(n)]
    ys = [round(2 + (p - lo) / span * (height - 4), 1) for p in positions]
    path = ' '.join(f'{x},{y}' for x, y in zip(xs, ys))
    color = '#6FE3C4' if positions[-1] <= positions[0] else '#FF9AAB'
    return format_html(
        '<svg viewBox="0 0 {} {}" class="rk-spark" preserveAspectRatio="none">'
        '<polyline points="{}" fill="none" stroke="{}" stroke-width="1.6"/></svg>',
        width, height, path, color)


def _series_by_keyword(project, since):
    """{keyword_id: {date: position}} برای همهٔ کلماتِ پروژه از `since` به بعد — یک کوئری."""
    rows = KeywordRankSnapshot.objects.filter(
        keyword__project=project, date__gte=since,
    ).values_list('keyword_id', 'date', 'position')
    out = defaultdict(dict)
    for kid, d, pos in rows:
        out[kid][d] = pos
    return out


def _keyword_planned_dates(project):
    """{کلمه: جدیدترین planned_date} از تسک‌هایی که این کلمه را در فیلدِ ردیابیِ رتبه
    دارند — یک عبور روی تسک‌های پروژه (نه یک کوئری به‌ازای هر کلمه)."""
    from tasks.models import Task
    out = {}
    tasks = (Task.objects.filter(project=project, type_def__isnull=False)
             .select_related('type_def').prefetch_related('type_def__fields')
             .order_by('planned_date'))  # صعودی → آخرین رونویسی، جدیدترین می‌ماند
    for t in tasks:
        for f in _keyword_source_fields(t.type_def):
            if not f.track_keyword_rank:
                continue
            for kw in (t.custom or {}).get(f.key) or []:
                out[kw] = t.planned_date
    return out


def keyword_rows(project, period_days):
    """ردیف‌های تبِ «بر اساس کلمه کلیدی»."""
    start, end, prev_start, prev_end = _windows(period_days)
    since = date.today() - timedelta(days=SPARK_DAYS - 1)
    series = _series_by_keyword(project, since)
    planned_dates = _keyword_planned_dates(project)
    rows = []
    for kw in project.tracked_keywords.all():
        by_date = series.get(kw.id, {})
        points = sorted(by_date.items())
        last_position = points[-1][1] if points else None
        cur = _window_position(by_date, start, end)
        prev = _window_position(by_date, prev_start, prev_end)
        change = (prev - cur) if (cur is not None and prev is not None) else None
        target_date = planned_dates.get(kw.keyword)
        rows.append({
            'id': kw.id, 'keyword': kw.keyword, 'page_url': kw.page_url,
            'is_starred': kw.is_starred, 'is_manual': kw.is_manual,
            'last_position': last_position, 'change': change,
            'spark': sparkline_svg(points),
            'progress': rank_progress(kw, target_date) if target_date else None,
        })
    rows.sort(key=lambda r: (not r['is_starred'], r['last_position'] if r['last_position'] is not None else 9999))
    return rows


def nearest_snapshot(tracked_keyword, target_date):
    """نزدیک‌ترین رکوردِ جایگاه به `target_date` (چه قبل چه بعد، هرکدام نزدیک‌تر بود)."""
    snaps = list(tracked_keyword.snapshots.all())
    if not snaps:
        return None
    return min(snaps, key=lambda s: abs((s.date - target_date).days))


def _elapsed_label(d1, d2):
    from core.jalali import to_fa_digits
    days = abs((d2 - d1).days)
    if not days:
        return 'همون روز'
    if days < 30:
        return f'{to_fa_digits(days)} روز'
    if days < 365:
        return f'{to_fa_digits(days // 30)} ماه'
    return f'{to_fa_digits(days // 365)} سال'


def rank_progress(tracked_keyword, target_date):
    """جایگاهِ نزدیک به `target_date` (معمولاً `planned_date`ی تسکی که این کلمه را
    تولید کرده) در برابرِ جدیدترین جایگاهِ ثبت‌شده — برای «+۲ بعد از ۳ ماه» در
    تبِ کلمات کلیدی. اگر فقط همان یک رکورد باشد یا اصلاً رکوردی نباشد، None."""
    near = nearest_snapshot(tracked_keyword, target_date)
    if not near:
        return None
    latest = tracked_keyword.snapshots.order_by('-date').first()
    out = {'near_date': near.date, 'near_position': near.position,
           'latest_date': latest.date, 'latest_position': latest.position,
           'delta': None, 'elapsed_label': ''}
    if latest.id != near.id:
        # مثبت یعنی بهبود (جایگاهِ کوچک‌تر = بهتر؛ مثلاً از #۱۰ به #۸ → +۲)
        out['delta'] = near.position - latest.position
        out['elapsed_label'] = _elapsed_label(near.date, latest.date)
    return out


def _keyword_source_fields(type_def):
    return [f for f in type_def.fields.all() if f.kind == f.TAGS and f.is_keyword_source]


def scheduled_rows(project):
    """تسک‌های هنوز انجام‌نشده که فیلدِ «کلمهٔ کلیدیِ ردیابی‌شونده» دارند — تبِ «کلمات
    کلیدی برنامه‌ریزی‌شده» (صفحاتِ جدیدی که در راه‌اند)، جدیدترین تاریخِ برنامه اول."""
    from tasks.models import Task
    rows = []
    tasks = (Task.objects.filter(project=project, type_def__isnull=False)
             .exclude(status=Task.DONE).select_related('type_def', 'assignee')
             .prefetch_related('type_def__fields').order_by('-planned_date'))
    for t in tasks:
        kw_field = next((f for f in _keyword_source_fields(t.type_def) if f.track_keyword_rank), None)
        if not kw_field:
            continue
        keywords = (t.custom or {}).get(kw_field.key) or []
        if not keywords:
            continue
        rows.append({'task': t, 'keywords': keywords})
    return rows


def tasks_for_keyword(project, keyword):
    """تسک‌های انجام‌شده‌ای که این کلمهٔ کلیدی را در فیلدِ کلمه‌کلیدی/کلمه‌کلیدیِ‌هدفشان
    دارند — جدیدترین اول («روی کلمه کلیک شد، چه تسک‌هایی برایش کار شده»)."""
    from tasks.models import Task
    out = []
    tasks = (Task.objects.filter(project=project, type_def__isnull=False, status=Task.DONE)
             .select_related('type_def', 'assignee').prefetch_related('type_def__fields')
             .order_by('-done_date'))
    for t in tasks:
        for f in _keyword_source_fields(t.type_def):
            if keyword in ((t.custom or {}).get(f.key) or []):
                out.append(t)
                break
    return out


def tasks_for_link(project, link):
    """مشابهِ `tasks_for_keyword` ولی بر اساسِ فیلدِ «لینکِ هدف» (`is_link_source`)."""
    from tasks.models import Task
    out = []
    tasks = (Task.objects.filter(project=project, type_def__isnull=False, status=Task.DONE)
             .select_related('type_def', 'assignee').prefetch_related('type_def__fields')
             .order_by('-done_date'))
    for t in tasks:
        for f in t.type_def.fields.all():
            if f.is_link_source and (t.custom or {}).get(f.key) == link:
                out.append(t)
                break
    return out


def page_rows(project, period_days):
    """ردیف‌های تبِ «بر اساس لینک» — گروه‌بندیِ همان دادهٔ کلمات روی `page_url`."""
    start, end, prev_start, prev_end = _windows(period_days)
    since = date.today() - timedelta(days=SPARK_DAYS - 1)
    series = _series_by_keyword(project, since)
    by_page = defaultdict(list)
    starred_pages = set()
    for kw in project.tracked_keywords.all():
        by_page[kw.page_url].append(kw.id)
        if kw.is_starred:
            starred_pages.add(kw.page_url)

    rows = []
    for page_url, kw_ids in by_page.items():
        lasts, curs, prevs = [], [], []
        daily = defaultdict(list)
        for kid in kw_ids:
            by_date = series.get(kid, {})
            for d, pos in by_date.items():
                daily[d].append(pos)
            if by_date:
                lasts.append(sorted(by_date.items())[-1][1])
            c = _window_position(by_date, start, end)
            p = _window_position(by_date, prev_start, prev_end)
            if c is not None:
                curs.append(c)
            if p is not None:
                prevs.append(p)
        avg_points = sorted((d, round(sum(v) / len(v), 1)) for d, v in daily.items())
        avg_position = round(sum(lasts) / len(lasts), 1) if lasts else None
        cur_avg = round(sum(curs) / len(curs), 1) if curs else None
        prev_avg = round(sum(prevs) / len(prevs), 1) if prevs else None
        change = round(prev_avg - cur_avg, 1) if (cur_avg is not None and prev_avg is not None) else None
        rows.append({
            'page_url': page_url, 'keyword_count': len(kw_ids),
            'is_starred': page_url in starred_pages,
            'avg_position': avg_position, 'change': change,
            'spark': sparkline_svg(avg_points),
        })
    rows.sort(key=lambda r: (not r['is_starred'], r['avg_position'] if r['avg_position'] is not None else 9999))
    return rows
