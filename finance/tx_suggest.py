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
import json
import re
from collections import Counter, defaultdict

from django.db.models import Q

from core.jalali import format_jalali, to_en_digits

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
    sig_txs = defaultdict(list)       # sig -> [رفرنس‌ها] برای دکمهٔ «مشاهده»
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
        ref = {'id': a.id, 'date': a.date, 'desc': a.description or '',
               'amount': int((a.deposit or 0) + (a.withdrawal or 0)),
               'dir': adir, 'pids': pids, 'cids': cids}
        for sig in sigs:
            sig_txs[sig].append(ref)
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

        # ── رفرنس‌ها (برای دکمهٔ «مشاهده»): تراکنش‌های قبلیِ هم‌امضایی که این پیشنهاد از آن‌ها آمد ──
        pid_ch, cid_ch = s.get('project_id'), s.get('category_id')
        refs, seen = [], set()
        for sig in sg:
            for info in sig_txs.get(sig, []):
                if info['id'] in seen:
                    continue
                rel = ((pid_ch and pid_ch in info['pids'])
                       or (cid_ch and info['dir'] == d and cid_ch in info['cids']))
                if not rel:
                    continue
                seen.add(info['id'])
                names = ([pname[p] for p in info['pids'] if pname.get(p)]
                         + [cname[c] for c in info['cids'] if cname.get(c)])
                refs.append({
                    'date': format_jalali(info['date']),
                    'desc': info['desc'][:90],
                    'amount': f"{info['amount']:,}",
                    'dir': _DIR_LABEL.get(info['dir'], ''),
                    'label': ' · '.join(names),
                })
                if len(refs) >= 8:
                    break
            if len(refs) >= 8:
                break
        s['refs'] = refs
        s['refs_json'] = json.dumps(refs, ensure_ascii=False)
        out[t.id] = s
    return out


# ───────────── پیشنهادِ ماندگار (TxSuggestion): حافظه + MCP، تأیید/رد در جدول ─────────────
def unassigned_qs():
    """تراکنش‌های بدونِ پروژه/بابت/تفکیک."""
    from .models import Transaction
    return (Transaction.objects.filter(project__isnull=True, categories__isnull=True, splits__isnull=True)
            .distinct())


def persist_memory(txs):
    """برای تراکنش‌های بی‌تخصیصِ بدونِ پیشنهادِ فعال، پیشنهادِ حافظه را ذخیره کن.
    پیشنهادِ «رد‌شده» با همان مقدار دوباره ساخته نمی‌شود؛ پیشنهادِ MCPِ در انتظار دست نمی‌خورد. خروجی: تعدادِ تازه."""
    from .models import TxSuggestion
    txs = [t for t in txs if _is_unassigned(t)]
    if not txs:
        return 0
    existing = {s.transaction_id: s for s in TxSuggestion.objects.filter(transaction__in=txs)}
    todo = [t for t in txs if t.id not in existing or existing[t.id].status != TxSuggestion.PENDING]
    if not todo:
        return 0
    sugg = suggestions_for(todo)
    made = 0
    for t in todo:
        s = sugg.get(t.id)
        if not s:
            continue
        cats = [s['category_id']] if s.get('category_id') else []
        old = existing.get(t.id)
        if old and old.status == TxSuggestion.REJECTED and old.project_id == s.get('project_id') and old.categories == cats:
            continue
        obj = old or TxSuggestion(transaction=t)
        obj.source, obj.project_id, obj.categories, obj.note = TxSuggestion.MEMORY, s.get('project_id'), cats, ''
        obj.why, obj.refs, obj.status, obj.decided_at, obj.decided_by = s.get('why', ''), s.get('refs', []), TxSuggestion.PENDING, None, None
        obj.save()
        made += 1
    return made


def rereview_all():
    """دکمهٔ «بازبینیِ مجدد با AI»: حافظه روی **همهٔ** تراکنش‌های بی‌تخصیص (نه فقط صفحهٔ جاری).
    خروجی: (پیشنهادِ تازه، تعدادِ صفِ MCP = بی‌تخصیص‌های بدونِ پیشنهادِ فعال)."""
    from .models import TxSuggestion
    txs = list(unassigned_qs().prefetch_related('categories', 'splits'))
    made = 0
    for i in range(0, len(txs), 400):
        made += persist_memory(txs[i:i + 400])
    queue = unassigned_qs().exclude(suggestion__status=TxSuggestion.PENDING).count()
    return made, queue


def payload(s):
    """دادهٔ نمایشِ پیشنهاد در جدول (پروژه/بابت/توضیح در ستونِ خودشان + یک گروه دکمه)."""
    from .models import Category
    cats = list(Category.objects.filter(id__in=s.categories or []))
    return {'id': s.id, 'source': s.source, 'project_id': s.project_id or '', 'project_name': s.project.name if s.project_id else '',
            'categories': [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats],
            'category_ids': ','.join(str(c.id) for c in cats), 'note': s.note, 'why': s.why,
            'refs_json': json.dumps(s.refs or [], ensure_ascii=False)}


def apply_suggestion(s, user):
    """تأیید: پروژه می‌نشیند، بابت‌ها اضافه می‌شوند، توضیح اگر خالی بود نوشته می‌شود (وگرنه اضافه)."""
    from django.utils import timezone
    t = s.transaction
    fields = []
    if s.project_id:
        t.project_id = s.project_id
        fields.append('project')
    if s.note:
        t.note = s.note if not t.note else (t.note if s.note in t.note else f'{t.note} — {s.note}')[:255]
        fields.append('note')
    if fields:
        t.save(update_fields=fields + ['updated_at'])
    if s.categories:
        from .models import Category
        t.categories.add(*Category.objects.filter(id__in=s.categories))
    s.status, s.decided_at, s.decided_by = s.ACCEPTED, timezone.now(), user if getattr(user, 'pk', None) else None
    s.save(update_fields=['status', 'decided_at', 'decided_by'])
    return t


def reject_suggestion(s, user):
    from django.utils import timezone
    s.status, s.decided_at, s.decided_by = s.REJECTED, timezone.now(), user if getattr(user, 'pk', None) else None
    s.save(update_fields=['status', 'decided_at', 'decided_by'])
