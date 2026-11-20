# یک‌باره: ادغامِ TrackedKeywordهای تکراری که افزونه قبل از جفت‌کردنِ نرمال‌شده ساخته بود (همان کلمه با ی/ک/نیم‌فاصلهٔ
# متفاوت روی همان صفحه با نشانیِ کدشده/www/اسلشِ متفاوت). اصلی = ستاره‌دار/دستی/قدیمی‌ترین؛ تاریخچهٔ بقیه به آن منتقل
# می‌شود (در روزِ مشترک، بهترین جایگاه می‌ماند). منطق کپیِ ثابت است (نه import از کد) تا مهاجرت در آینده نشکند.
import re
from urllib.parse import unquote, urlsplit

from django.db import migrations


def _host(v):
    v = str(v or '').strip()
    if '://' not in v:
        v = 'http://' + v
    h = (urlsplit(v).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def _pk(url):
    url = str(url or '').strip()
    if not url:
        return ''
    if '://' not in url:
        url = 'http://' + url
    return (_host(url) + (unquote(urlsplit(url).path or '/').rstrip('/') or '/')).lower()


def _kw(s):
    s = str(s or '').lower().replace('ي', 'ی').replace('ى', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    s = s.replace('‌', ' ').replace('‏', '').replace('ـ', '')
    s = re.sub(r'[«»"\'،,.!?؟:;()\[\]]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def forward(apps, schema_editor):
    TK = apps.get_model('seo', 'TrackedKeyword')
    Snap = apps.get_model('seo', 'KeywordRankSnapshot')
    groups = {}
    for t in TK.objects.all().order_by('id'):
        groups.setdefault((t.project_id, _kw(t.keyword), _pk(t.page_url)), []).append(t)
    for ts in groups.values():
        if len(ts) < 2:
            continue
        ts.sort(key=lambda t: (not t.is_starred, not t.is_manual, t.id))
        keep, dups = ts[0], ts[1:]
        have = {s.date: s for s in Snap.objects.filter(keyword=keep)}
        for d in dups:
            keep.is_starred = keep.is_starred or d.is_starred
            for s in Snap.objects.filter(keyword=d):
                k = have.get(s.date)
                if k is None:
                    s.keyword_id = keep.id
                    s.save()
                    have[s.date] = s
                elif s.position < k.position:
                    k.position, k.seen_url = s.position, s.seen_url
                    k.save()
            d.delete()
        keep.save()


class Migration(migrations.Migration):
    dependencies = [('seo', '0003_keywordranksnapshot_source')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
