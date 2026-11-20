"""پرکردنِ رتبهٔ روزانهٔ کلماتِ ردیابی‌شده (`seo.TrackedKeyword`) از دادهٔ سرچ کنسول — بدونِ نیاز به سرچِ دستی با افزونه.

برای هر کلمه و هر روز: اگر همان صفحهٔ کلمه برای آن کوئری نمایش داشته، جایگاهِ همان صفحه؛ وگرنه صفحه‌ای از سایت که بیشترین
نمایش را داشته (`seen_url` همان صفحه). رکوردِ افزونه (`source=ext`) همیشه مقدم است و دست نمی‌خورد؛ این فقط روزهای خالی را
با `source=gsc` پر/به‌روز می‌کند. ایدمپوتنت (کلِ بازهٔ ذخیره‌شده هر بار).
"""
from seo.match import norm_kw

from .models import GSCQueryDay
from .urls_norm import page_key


def fill_tracked(site, log=print):
    from seo.models import KeywordRankSnapshot, TrackedKeyword
    p = site.project
    if not p or not p.track_keyword_rank or not site.synced_until:
        return 0
    tks = list(TrackedKeyword.all_objects.filter(project=p))
    if not tks:
        return 0
    by_kw = {}
    for t in tks:
        by_kw.setdefault(norm_kw(t.keyword), []).append(t)
    variants = set(by_kw) | {t.keyword.strip().lower() for t in tks}
    best = {}   # (tk_id, date) → (rank, position, url) ؛ rank: 0 = همان صفحه، 1 = صفحهٔ دیگر (بیشترین نمایش)
    for r in (GSCQueryDay.objects.filter(site=site, query__in=variants)
              .values('date', 'query', 'page__key', 'page__url', 'impressions', 'position')):
        for t in by_kw.get(norm_kw(r['query']), []):
            same = r['page__key'] == page_key(t.page_url)
            cand = (0 if same else 1, -r['impressions'], r['position'], r['page__url'])
            k = (t.id, r['date'])
            if k not in best or cand < best[k]:
                best[k] = cand
    if not best:
        return 0
    existing = {(s.keyword_id, s.date): s for s in KeywordRankSnapshot.objects.filter(keyword__in=tks, date__in={d for _, d in best})}
    new, upd = [], []
    for (tid, d), (_, _, pos, url) in best.items():
        position = max(1, round(pos))
        s = existing.get((tid, d))
        if s is None:
            new.append(KeywordRankSnapshot(keyword_id=tid, date=d, position=position, seen_url=(url or '')[:500], source='gsc'))
        elif s.source == 'gsc' and (s.position != position or s.seen_url != (url or '')[:500]):
            s.position, s.seen_url = position, (url or '')[:500]
            upd.append(s)
    KeywordRankSnapshot.objects.bulk_create(new, batch_size=1000, ignore_conflicts=True)
    KeywordRankSnapshot.objects.bulk_update(upd, ['position', 'seen_url'], batch_size=1000)
    if new or upd:
        log(f'{site.site_url}: رتبهٔ کلماتِ ردیابی‌شده — {len(new)} روزِ تازه، {len(upd)} به‌روز')
    return len(new) + len(upd)
