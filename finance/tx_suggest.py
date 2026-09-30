"""شناساییِ هوشمندِ تراکنش‌های تکراری — پیشنهادِ خودکارِ پروژه/بابت (روشِ A: امضا + حافظه).

ایده: هر تراکنشِ تکراری یک **امضای پایدار** دارد (شمارهٔ شبا `IRxxxxxxxxxxxxxxxxxxxxxxxx`
یا شمارهٔ کارتِ ۱۶رقمی)؛ توکن‌های پرنوسان (ش.پ/کدِ رهگیری، تاریخ، مبلغ) را نادیده می‌گیریم.
از **تخصیص‌های قبلیِ خودِ کاربر** یاد می‌گیریم و برای تراکنشِ نوِ بی‌تخصیص، **پرتکرارترین**
پروژه/بابتِ همان امضا را پیشنهاد می‌کنیم (حتی با یک تراکنشِ قبلیِ هم‌امضا — خواستِ کاربر).

سه سیگنالِ **اولویت‌دار** (تلهٔ رفع‌شده: قبلاً جهت نادیده گرفته می‌شد و «برداشت» را «درآمد»
پیشنهاد می‌داد):
1. **جهت (واریز/برداشت)** — بابت (`category`) با جهت کلید می‌خورد؛ یک بابتِ درآمدی که از
   واریزها یاد گرفته شده هرگز روی یک **برداشت** پیشنهاد نمی‌شود (و برعکس). پروژه خنثی است.
2. **حساب/کارتِ همین تراکنش** — پیشنهادِ آمده از تراکنش‌های **همان bank_account** اولویتِ
   بالاتر دارد؛ فقط اگر نبود، به هم‌امضاهای سایرِ حساب‌ها برمی‌گردیم.
3. **امضای طرفِ مقابل** — شماره‌کارت/شبای **خودِ حساب‌های ما** از امضاها حذف می‌شود
   (`BankAccount.card_number`)، وگرنه شماره‌ای که در هر ردیف تکرار می‌شود همه را هم‌امضا و
   پیشنهاد را بی‌معنا می‌کرد.

هر پیشنهاد یک توضیحِ **«چرا؟»** (`why`) هم دارد (امضای مچ‌شده، جهت، تعداد، رقیب) تا کاربر
دلیلِ درست/غلط بودنش را بفهمد. هیچ کتابخانهٔ بیرونی لازم نیست؛ فقط regex + دیتای سازمان.
با هر تصحیحِ کاربر، حافظه بزرگ‌تر و دقیق‌تر می‌شود.
"""
import re
from collections import Counter, defaultdict

from django.db.models import Q

from core.jalali import to_en_digits

_IBAN = re.compile(r'IR\d{24}')
_CARD = re.compile(r'(?<!\d)\d{16}(?!\d)')

_DIR_LABEL = {'in': 'واریز', 'out': 'برداشت'}


def signatures(description, exclude=None):
    """مجموعهٔ امضاهای پایدارِ یک شرح (شبا + کارت). ارقامِ فارسی → لاتین؛ امضاهای `exclude`
    (حساب‌های خودمان) کنار گذاشته می‌شوند."""
    s = to_en_digits(description or '')
    sigs = set()
    for m in _IBAN.findall(s):
        sigs.add('ib:' + m)
    for m in _CARD.findall(s):
        sigs.add('cd:' + m)
    if exclude:
        sigs -= exclude
    return sigs


def _own_signatures():
    """امضای همهٔ حساب‌های خودمان (`BankAccount.card_number`) — از پیشنهاد حذف می‌شوند."""
    from .models import BankAccount
    own = set()
    for cn in BankAccount.objects.values_list('card_number', flat=True):
        own |= signatures(cn)
    return own


def _direction(t):
    """'in' اگر واریز، 'out' اگر برداشت، '' اگر هیچ‌کدام."""
    if (t.deposit or 0) > 0:
        return 'in'
    if (t.withdrawal or 0) > 0:
        return 'out'
    return ''


def _mask(sig):
    """نمایشِ کوتاهِ امضا برای توضیح: «کارت …۳۶۰۳» / «شبا …۵۷۲۰»."""
    val = sig[3:]
    return ('کارت …' + val[-4:]) if sig.startswith('cd:') else ('شبا …' + val[-4:])


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

    خروجی: `{tx_id: {project_id, project_name, category_id, category_name, count, dir,
    dir_label, why}}`. فقط امضاهای مرتبط با همین صفحه از حافظه تالّی می‌شوند (سبک).
    """
    from .models import Category, Transaction
    from projects.models import Project

    # فقط تراکنشِ بی‌تخصیص که جهتش مشخص است
    targets = [t for t in page_txs if _is_unassigned(t) and _direction(t)]
    if not targets:
        return {}
    own = _own_signatures()
    tinfo, target_sigs = {}, set()
    for t in targets:
        sg = signatures(t.description, exclude=own)
        tinfo[t.id] = (sg, _direction(t), t.bank_account_id)
        target_sigs |= sg
    if not target_sigs:
        return {}

    # ── حافظه (فقط امضاهای همین صفحه، از تراکنش‌های تخصیص‌دادهٔ سازمان) ──
    cat_dir = defaultdict(Counter)    # (sig, dir)        -> Counter(cat_id)
    cat_bank = defaultdict(Counter)   # (sig, dir, bank)  -> Counter(cat_id)  (اولویت: همان حساب)
    proj_any = defaultdict(Counter)   # sig               -> Counter(proj_id) (پروژه خنثیِ جهت)
    proj_bank = defaultdict(Counter)  # (sig, bank)       -> Counter(proj_id)
    assigned = (Transaction.objects
                .filter(Q(project__isnull=False) | Q(categories__isnull=False) | Q(splits__isnull=False))
                .distinct().prefetch_related('categories', 'splits'))
    for a in assigned:
        sigs = signatures(a.description, exclude=own) & target_sigs
        if not sigs:
            continue
        pids, cids = _assignment(a)
        if not pids and not cids:
            continue
        adir, abank = _direction(a), a.bank_account_id
        for sig in sigs:
            for c in cids:
                if adir:
                    cat_dir[(sig, adir)][c] += 1
                    if abank:
                        cat_bank[(sig, adir, abank)][c] += 1
            for p in pids:
                proj_any[sig][p] += 1
                if abank:
                    proj_bank[(sig, abank)][p] += 1

    pname = dict(Project.objects.values_list('id', 'name'))
    cname = dict(Category.objects.values_list('id', 'name'))
    out = {}
    for t in targets:
        sg, d, b = tinfo[t.id]

        # بابت: اول «همان حساب + همان جهت»، بعد «همان جهت» (هر حسابی)
        cat, cat_scope = Counter(), ''
        if b:
            for sig in sg:
                cat.update(cat_bank.get((sig, d, b), {}))
            if cat:
                cat_scope = 'account'
        if not cat:
            for sig in sg:
                cat.update(cat_dir.get((sig, d), {}))
            if cat:
                cat_scope = 'dir'

        # پروژه: اول «همان حساب»، بعد هر حساب (خنثیِ جهت)
        proj, proj_scope = Counter(), ''
        if b:
            for sig in sg:
                proj.update(proj_bank.get((sig, b), {}))
            if proj:
                proj_scope = 'account'
        if not proj:
            for sig in sg:
                proj.update(proj_any.get(sig, {}))
            if proj:
                proj_scope = 'any'

        if not cat and not proj:
            continue

        s = {'count': 0, 'dir': d, 'dir_label': _DIR_LABEL.get(d, '')}
        matched = '، '.join(sorted({_mask(sig) for sig in sg
                                    if sig in proj_any or (sig, d) in cat_dir}))
        parts = []
        if proj:
            top = proj.most_common(2)
            pid, cnt = top[0]
            s['project_id'] = pid
            s['project_name'] = pname.get(pid, '')
            s['count'] = max(s['count'], cnt)
            scope = 'همین حساب' if proj_scope == 'account' else 'همهٔ حساب‌ها'
            p = f'پروژه «{pname.get(pid, "")}» از {cnt} تراکنشِ هم‌امضا ({scope})'
            if len(top) > 1:
                p += f' — رقیب: «{pname.get(top[1][0], "")}» {top[1][1]}'
            parts.append(p)
        if cat:
            top = cat.most_common(2)
            cid, ccnt = top[0]
            s['category_id'] = cid
            s['category_name'] = cname.get(cid, '')
            s['count'] = max(s['count'], ccnt)
            scope = 'همین حساب' if cat_scope == 'account' else 'هر حساب'
            p = f'بابت «{cname.get(cid, "")}» از {ccnt} تراکنشِ {_DIR_LABEL.get(d, "")}ِ هم‌امضا ({scope})'
            if len(top) > 1:
                p += f' — رقیب: «{cname.get(top[1][0], "")}» {top[1][1]}'
            parts.append(p)
        s['why'] = (f'{matched} · {_DIR_LABEL.get(d, "")} — ' if matched else '') + '؛ '.join(parts)
        out[t.id] = s
    return out
