"""ابزارهای مشترکِ MCPِ پنل: درخواستِ ساختگی به نامِ کاربرِ توکن، تبدیلِ تاریخ، پیداکردنِ پروژه/فرد/نوع با
نام یا دامنه (سمتِ سرور — تا هوش مصنوعی مجبور نباشد اول همه‌چیز را فهرست کند) و خروجیِ جدولیِ فشرده."""
import difflib
import re
from datetime import date

from django.test import RequestFactory

from core.jalali import format_jalali, j2g, to_en_digits

MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


class ToolError(Exception):
    pass


def fake_request(gate):
    """درخواستی که کدِ موجودِ پنل (apply_fields، دسترسی‌ها) آن را مثلِ کاربرِ لاگین‌شده ببیند."""
    from accounts.models import Membership
    org = gate.organization
    user = gate.user
    if user is None:
        m = Membership.objects.filter(organization=org, role='owner', is_active=True).select_related('user').first() \
            or Membership.objects.filter(organization=org, is_active=True).select_related('user').first()
        user = m.user if m else None
    req = RequestFactory().post('/mcp/')
    req.user = user
    req.organization = org
    req.membership = Membership.objects.filter(organization=org, user=user).first() if user else None
    req.session = {}
    return req


# ───────────── تاریخ ─────────────
def pdate(v):
    """ISO (2024-05-01) یا شمسی (1403/02/12، 1403-2-12، ارقامِ فارسی) → date. سال < ۱۷۰۰ = شمسی."""
    if v in (None, ''):
        return None
    if isinstance(v, date):
        return v
    s = to_en_digits(str(v)).strip()
    m = re.match(r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})', s)
    if not m:
        raise ToolError(f'تاریخِ نامعتبر: {v} (YYYY/MM/DD شمسی یا ISO)')
    y, mo, d = map(int, m.groups())
    try:
        return j2g(y, mo, d) if y < 1700 else date(y, mo, d)
    except ValueError as e:
        raise ToolError(f'تاریخِ نامعتبر: {v}') from e


def jd(d):
    return format_jalali(d) if d else None


def report_month(v):
    """«1403-07» / «1403/7» / «مهر 1403» / «none» → (year, month) یا (None, None)."""
    if v in (None, '', 'none', 'بدون'):
        return None, None
    s = to_en_digits(str(v)).strip()
    for i, name in enumerate(MONTHS, 1):
        if name in s:
            y = re.search(r'\d{4}', s)
            from core.jalali import today_jalali
            return (int(y.group()) if y else today_jalali().year), i
    m = re.match(r'^(\d{4})[/\-](\d{1,2})', s)
    if m:
        return int(m.group(1)), int(m.group(2))
    raise ToolError(f'ماهِ گزارشِ نامعتبر: {v} (مثلاً 1403-07)')


def minutes(v):
    """«1:30» یا «90» یا 1.5h → دقیقه."""
    if v in (None, ''):
        return None
    s = to_en_digits(str(v)).strip().lower()
    if ':' in s:
        h, m = s.split(':', 1)
        return int(h or 0) * 60 + int(m or 0)
    if s.endswith('h'):
        return round(float(s[:-1]) * 60)
    return int(float(s))


# ───────────── پیداکردن (نام/دامنه/شناسه) ─────────────
def _norm(s):
    s = to_en_digits(str(s or '')).lower().strip()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s).split('/')[0] if '.' in s and ' ' not in s else s
    return s.replace('ي', 'ی').replace('ك', 'ک').replace('‌', ' ').strip()


class Resolver:
    """کشِ سبک برای یک فراخوانی: پروژه/فرد/نوع/بابت با id، نام یا دامنه."""

    def __init__(self):
        self._c = {}

    def _items(self, kind):
        if kind in self._c:
            return self._c[kind]
        if kind == 'project':
            from projects.models import Project
            rows = [(p.id, p.name, p.domain or '') for p in Project.objects.filter(personal_owner__isnull=True)]
        elif kind == 'colleague':
            from colleagues.models import Colleague
            rows = [(c.id, c.full_name, c.user.username if c.user_id else '') for c in Colleague.objects.select_related('user')]
        elif kind == 'type':
            from tasks.models import TaskTypeDef
            rows = [(t.id, t.name, t.builtin_key or '') for t in TaskTypeDef.objects.filter(is_active=True)]
        elif kind == 'category':
            from finance.models import Category
            rows = [(c.id, c.name, '') for c in Category.objects.all()]
        else:
            rows = []
        self._c[kind] = rows
        return rows

    def get(self, kind, v, required=True):
        """id یا None؛ نبود → ToolError با پیشنهادِ نزدیک‌ترین‌ها."""
        if v in (None, '', 0):
            return None
        rows = self._items(kind)
        s = _norm(v)
        if s.isdigit() and any(r[0] == int(s) for r in rows):
            return int(s)
        for r in rows:
            if s in (_norm(r[1]), _norm(r[2])) and s:
                return r[0]
        hits = [r for r in rows if s and (s in _norm(r[1]) or (r[2] and s in _norm(r[2])))]
        if len(hits) == 1:
            return hits[0][0]
        names = {_norm(r[1]): r for r in rows}
        close = difflib.get_close_matches(s, list(names), n=3, cutoff=0.6)
        if len(close) == 1 and not hits:
            return names[close[0]][0]
        if not required:
            return None
        sug = [f'{r[1]}#{r[0]}' for r in (hits or [names[c] for c in close])][:4]
        label = {'project': 'پروژه', 'colleague': 'فرد', 'type': 'نوعِ تسک', 'category': 'بابت'}[kind]
        raise ToolError(f'{label} «{v}» پیدا نشد' + (f' — منظورت: {"، ".join(sug)}؟' if sug else ''))

    def name(self, kind, pk):
        return next((r[1] for r in self._items(kind) if r[0] == pk), None) if pk else None


def table(cols, rows, **extra):
    """خروجیِ فشرده: {'cols': [...], 'rows': [[...], ...]} — یک بار نامِ ستون، نه برای هر ردیف."""
    return {'cols': cols, 'rows': rows, **extra}


def call_view(gate, view, method, body=None, *args, **kwargs):
    """یک ویوِ JSONِ موجودِ پنل را با کاربرِ توکن صدا بزن (منطقِ پنل تکرار نشود). خروجی: (status, dict)."""
    import json as _json
    base = fake_request(gate)
    rf = RequestFactory()
    data = _json.dumps(body or {}, ensure_ascii=False)
    req = getattr(rf, method.lower())('/mcp/', data=data, content_type='application/json') if method.upper() != 'GET' \
        else rf.get('/mcp/', body or {})
    for a in ('user', 'organization', 'membership', 'session'):
        setattr(req, a, getattr(base, a))
    req._dont_enforce_csrf_checks = True
    resp = view(req, *args, **kwargs)
    try:
        payload = _json.loads(resp.content or b'{}')
    except ValueError:
        payload = {}
    return resp.status_code, payload
