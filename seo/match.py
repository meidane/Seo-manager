"""منبعِ واحدِ «این (کلمه، نشانی) کدام TrackedKeyword است؟» — افزونه و سرچ کنسول هر دو از همین استفاده می‌کنند.

قبلاً افزونه فقط با برابریِ دقیقِ رشته جفت می‌کرد؛ نشانیِ کمی متفاوت (http/https، www، اسلشِ آخر، فارسیِ کدشده/نشده) یا کلمهٔ
متفاوت در ی/ک/نیم‌فاصله یک TrackedKeywordِ تکراری می‌ساخت و رتبه هیچ‌وقت به کلمهٔ تسک نمی‌رسید.
"""
import re

from gsc.urls_norm import page_key


def norm_kw(s):
    s = str(s or '').lower().replace('ي', 'ی').replace('ى', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    s = s.replace('‌', ' ').replace('‏', '').replace('ـ', '')
    s = re.sub(r'[«»"\'،,.!?؟:;()\[\]]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def find_tracked(project, keyword, url, tracked=None):
    """اول همان کلمه روی همان صفحه (نشانیِ نرمال‌شده)، بعد همان کلمه روی هر صفحه‌ای از پروژه (کلمهٔ تسک ولی صفحهٔ دیگری
    از سایت در نتایج آمده — رتبه برای همان کلمه ثبت و `seen_url` نشان می‌دهد کدام صفحه آمد). None = کلمهٔ تازه."""
    from .models import TrackedKeyword
    nk, pk = norm_kw(keyword), page_key(url)
    cands = [t for t in (tracked if tracked is not None else TrackedKeyword.all_objects.filter(project=project)) if norm_kw(t.keyword) == nk]
    if not cands:
        return None
    same = [t for t in cands if page_key(t.page_url) == pk]
    if same:
        return same[0]
    return sorted(cands, key=lambda t: (not t.is_starred, not t.is_manual, t.id))[0]
