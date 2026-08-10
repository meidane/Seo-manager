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


def keyword_rows(project, period_days):
    """ردیف‌های تبِ «بر اساس کلمه کلیدی»."""
    start, end, prev_start, prev_end = _windows(period_days)
    since = date.today() - timedelta(days=SPARK_DAYS - 1)
    series = _series_by_keyword(project, since)
    rows = []
    for kw in project.tracked_keywords.all():
        by_date = series.get(kw.id, {})
        points = sorted(by_date.items())
        last_position = points[-1][1] if points else None
        cur = _window_position(by_date, start, end)
        prev = _window_position(by_date, prev_start, prev_end)
        change = (prev - cur) if (cur is not None and prev is not None) else None
        rows.append({
            'id': kw.id, 'keyword': kw.keyword, 'page_url': kw.page_url,
            'is_starred': kw.is_starred, 'is_manual': kw.is_manual,
            'last_position': last_position, 'change': change,
            'spark': sparkline_svg(points),
        })
    rows.sort(key=lambda r: (not r['is_starred'], r['last_position'] if r['last_position'] is not None else 9999))
    return rows


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
