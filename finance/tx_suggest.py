"""شناساییِ هوشمندِ تراکنش‌های تکراری — پیشنهادِ خودکارِ پروژه/بابت (روشِ A: امضا + حافظه).

ایده: هر تراکنشِ تکراری یک **امضای پایدار** دارد (شمارهٔ شبا `IRxxxxxxxxxxxxxxxxxxxxxxxx`
یا شمارهٔ کارتِ ۱۶رقمی)؛ توکن‌های پرنوسان (ش.پ/کدِ رهگیری، تاریخ، مبلغ) را نادیده می‌گیریم.
از **تخصیص‌های قبلیِ خودِ کاربر** یاد می‌گیریم: برای هر امضا می‌شماریم به چه پروژه/بابتی
خورده، و برای تراکنشِ نوِ بی‌تخصیص، **پرتکرارترین** پروژه/بابتِ همان امضا را پیشنهاد می‌کنیم
(حتی با یک تراکنشِ قبلیِ هم‌امضا هم پیشنهاد می‌دهیم — خواستِ کاربر). چون از IBAN/کارت کلید
می‌سازیم، جهتِ واریز/برداشت مهم نیست (همان IBAN در هر دو سمت ظاهر می‌شود). هیچ کتابخانهٔ
بیرونی لازم نیست؛ فقط regex + دیتای خودِ سازمان. با هر تأیید، حافظه بزرگ‌تر و دقیق‌تر می‌شود.
"""
import re
from collections import Counter

from django.db.models import Q

from core.jalali import to_en_digits

_IBAN = re.compile(r'IR\d{24}')
_CARD = re.compile(r'(?<!\d)\d{16}(?!\d)')


def signatures(description):
    """مجموعهٔ امضاهای پایدارِ یک شرح (شبا + کارت). ارقامِ فارسی → لاتین."""
    s = to_en_digits(description or '')
    sigs = set()
    for m in _IBAN.findall(s):
        sigs.add('ib:' + m)
    for m in _CARD.findall(s):
        sigs.add('cd:' + m)
    return sigs


def _assignment(t):
    """(مجموعهٔ project_id، مجموعهٔ category_id) از خودِ تراکنش یا اسپلیت‌هایش."""
    pids, cids = set(), set()
    if t.project_id:
        pids.add(t.project_id)
    for c in t.categories.all():
        cids.add(c.id)
    for s in t.splits.all():
        if s.project_id:
            pids.add(s.project_id)
        if s.category_id:
            cids.add(s.category_id)
    return pids, cids


def _is_unassigned(t):
    return not t.project_id and not t.categories.all() and not t.splits.all()


def suggestions_for(page_txs):
    """برای تراکنش‌های بی‌تخصیصِ صفحه، پیشنهادِ پروژه/بابت می‌سازد.

    خروجی: `{tx_id: {project_id, project_name, category_id, category_name, count}}`.
    فقط امضاهای مرتبط با همین صفحه از حافظه تالّی می‌شوند (سبک).
    """
    from .models import Category, Transaction
    from projects.models import Project

    targets = [t for t in page_txs if _is_unassigned(t)]
    if not targets:
        return {}
    target_sigs = set()
    for t in targets:
        target_sigs |= signatures(t.description)
    if not target_sigs:
        return {}

    # حافظه فقط برای امضاهای همین صفحه — از تراکنش‌های تخصیص‌دادهٔ سازمان (tenant-scoped)
    mem = {}  # sig -> {'proj': Counter, 'cat': Counter}
    assigned = (Transaction.objects
                .filter(Q(project__isnull=False) | Q(categories__isnull=False) | Q(splits__isnull=False))
                .distinct().prefetch_related('categories', 'splits'))
    for t in assigned:
        sigs = signatures(t.description) & target_sigs
        if not sigs:
            continue
        pids, cids = _assignment(t)
        if not pids and not cids:
            continue
        for sig in sigs:
            d = mem.setdefault(sig, {'proj': Counter(), 'cat': Counter()})
            for p in pids:
                d['proj'][p] += 1
            for c in cids:
                d['cat'][c] += 1
    if not mem:
        return {}

    pname = dict(Project.objects.values_list('id', 'name'))
    cname = dict(Category.objects.values_list('id', 'name'))
    out = {}
    for t in targets:
        proj, cat = Counter(), Counter()
        for sig in signatures(t.description):
            d = mem.get(sig)
            if d:
                proj.update(d['proj'])
                cat.update(d['cat'])
        if not proj and not cat:
            continue
        s = {'count': 0}
        if proj:
            pid, cnt = proj.most_common(1)[0]
            s['project_id'] = pid
            s['project_name'] = pname.get(pid, '')
            s['count'] = max(s['count'], cnt)
        if cat:
            cid, ccnt = cat.most_common(1)[0]
            s['category_id'] = cid
            s['category_name'] = cname.get(cid, '')
            s['count'] = max(s['count'], ccnt)
        out[t.id] = s
    return out
