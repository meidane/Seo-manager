"""منبعِ واحدِ «کدام اسکیل‌ها برای این درخواست» — هم MCP (`skills_start`) هم تبِ پروژه و «آزمایشِ تشخیص»ِ صفحهٔ اسکیل‌ها.

- `detect(org, ...)`: پروژه/نوعِ تسک را از هر سرنخی پیدا می‌کند: id/نام/دامنهٔ پروژه، کلیدِ سایتِ MCP، آدرس یا دامنه
  در متن، شمارهٔ تسک (#123)، نامِ پروژه یا نوعِ تسک در متن.
- `select(org, project_id, type_id, text)`: اسکیل‌ها را دسته می‌کند:
  load (متنِ کامل) = اجباری + «همیشه» (عمومی و همین پروژه) + «خودکار»هایی که نوعِ تسک یا کلیدواژه‌شان با درخواست جور است؛
  available = بقیهٔ مرتبط (فقط عنوان/خلاصه — با skill_get در صورتِ نیاز).
- `must_use_text(org)`: متنِ «اجباری» برای instructionsِ هر سه کانکتورِ MCP.
"""
import re

from django.db.models import Q

from .models import Skill

MUST_MAX = 6000  # سقفِ متنِ اجباری در instructions (توکن)
_URL = re.compile(r'(?:https?://)?(?:www\.)?([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', str(s or '').lower().replace('ي', 'ی').replace('ى', 'ی').replace('ك', 'ک')
                  .replace('‌', ' ').replace('ـ', '')).strip()


def live(org=None):
    qs = Skill.all_objects.filter(deleted_at__isnull=True, active=True)
    return qs.filter(organization=org) if org is not None else qs


def must_use_text(org):
    """متنِ کاملِ همهٔ اسکیل‌های اجباری + نامِ «همیشه»ها (برای instructions). خالی اگر هیچ نبود."""
    rows = list(live(org).filter(Q(scope=Skill.MUST) | Q(scope=Skill.GENERAL, apply=Skill.ALWAYS)).order_by('order', 'id'))
    must = [f'## {s.title}\n{s.body.strip()}' for s in rows if s.scope == Skill.MUST]
    always = [s.title for s in rows if s.scope == Skill.GENERAL]
    if not must and not always:
        return ''
    txt = '\n\n'.join(must)
    if len(txt) > MUST_MAX:
        txt = txt[:MUST_MAX] + '\n… (ادامه با skills_start)'
    out = ('اسکیل‌های اجباری (MUST USE — در هر دستور رعایت کن):\n' + txt) if must else ''
    if always:
        out += ('\n\n' if out else '') + ('اسکیل‌های همیشگی (برای هر تولیدِ محتوا؛ متنشان با skills_start از کانکتورِ «اسکیل‌ها»): '
                                        + '، '.join(always))
    return out


# ───────────── تشخیص ─────────────
def _domain(v):
    m = _URL.search(str(v or ''))
    return m.group(1).lower() if m else ''


def detect(org, project=None, site=None, task=None, type=None, text=''):  # noqa: A002
    """→ {'project': id|None, 'type': id|None, 'task': id|None, 'text': متنِ تجمیعی, 'how': [سرنخ‌ها]}."""
    from projects.models import Project
    from tasks.models import Task, TaskTypeDef
    how, pid, tid, task_id = [], None, None, None
    text = str(text or '')
    projects = list(Project.all_objects.filter(organization=org, personal_owner__isnull=True, deleted_at__isnull=True)
                    .values('id', 'name', 'domain'))
    by_dom = {_domain(p['domain']): p['id'] for p in projects if p['domain']}

    def from_domain(v, label):
        d = _domain(v)
        for dom, i in by_dom.items():
            if d and dom and (d == dom or d.endswith('.' + dom) or dom.endswith('.' + d)):
                how.append(f'{label}: {dom}')
                return i
        return None

    # ۱) شمارهٔ تسک (صریح یا «#123» در متن)
    m = re.search(r'#(\d{1,7})\b', text) if not task else None
    tnum = task or (m.group(1) if m else None)
    if tnum and str(tnum).isdigit():
        t = Task.all_objects.filter(organization=org, pk=int(tnum)).first()
        if t:
            task_id, pid, tid = t.pk, t.project_id, t.type_def_id
            text += ' ' + t.title
            how.append(f'تسکِ #{t.pk}')
    # ۲) پروژهٔ صریح (id/نام/دامنه)
    if project and not pid:
        s = norm(project)
        for p in projects:
            if s in (str(p['id']), norm(p['name']), _domain(p['domain'])):
                pid = p['id']
                how.append('پروژهٔ داده‌شده')
                break
        pid = pid or from_domain(project, 'دامنه')
    # ۳) کلیدِ سایتِ MCP → آدرسِ سایت → دامنهٔ پروژه
    if site and not pid:
        from mcpgate.models import MCPSite
        ms = MCPSite.objects.filter(organization=org, key__iexact=str(site).strip()).first()
        pid = from_domain(ms.url if ms else site, f'سایتِ {site}')
    # ۴) آدرس/دامنه یا نامِ پروژه در متن
    if not pid and text:
        for d in _URL.findall(text):
            pid = from_domain(d, 'دامنه در متن')
            if pid:
                break
    if not pid and text:
        nt = norm(text)
        hits = sorted((p for p in projects if len(norm(p['name'])) > 2 and norm(p['name']) in nt), key=lambda p: -len(p['name']))
        if hits:
            pid = hits[0]['id']
            how.append(f'نامِ پروژه در متن: {hits[0]["name"]}')
    # ۵) نوعِ تسک (صریح یا نامش در متن)
    types = list(TaskTypeDef.all_objects.filter(organization=org, is_active=True).values('id', 'name'))
    if type and not tid:
        s = norm(type)
        tid = next((t['id'] for t in types if s in (str(t['id']), norm(t['name']))), None)
        if tid:
            how.append('نوعِ داده‌شده')
    if not tid and text:
        nt = norm(text)
        hit = next((t for t in sorted(types, key=lambda t: -len(t['name'])) if len(t['name']) > 2 and norm(t['name']) in nt), None)
        if hit:
            tid = hit['id']
            how.append(f'نوع در متن: {hit["name"]}')
    return {'project': pid, 'type': tid, 'task': task_id, 'text': text, 'how': how}


def select(org, project_id=None, type_id=None, text=''):
    """→ (load, available): هر عضو = (skill, why). ترتیب: اجباری → همیشه → مرتبط با نوع/کلیدواژه → پروژه."""
    q = Q(scope__in=[Skill.MUST, Skill.GENERAL])
    if project_id:
        q |= Q(scope=Skill.PROJECT, project_id=project_id)
    nt = norm(text)
    load, avail = [], []
    for s in live(org).filter(q).select_related('project').prefetch_related('task_types', 'files'):
        tids = {t.id for t in s.task_types.all()}
        tag_hit = next((t for t in s.tag_list if norm(t) and norm(t) in nt), None)
        if s.scope == Skill.MUST:
            load.append((0, s, 'اجباری'))
        elif s.apply == Skill.ALWAYS:
            # «همیشه»یی که به نوعِ خاصی محدود شده فقط برای همان نوع
            if not tids or (type_id and type_id in tids):
                load.append((1 if s.scope == Skill.GENERAL else 3, s, 'همیشه' + (' (این پروژه)' if s.project_id else '')))
            else:
                avail.append((s, 'برای نوعِ دیگر'))
        elif s.apply == Skill.AUTO and type_id and type_id in tids:
            load.append((2, s, 'نوعِ تسک'))
        elif s.apply == Skill.AUTO and tag_hit:
            load.append((2, s, f'کلیدواژه: {tag_hit}'))
        elif s.apply == Skill.AUTO and s.scope == Skill.PROJECT and not tids and not s.tag_list:
            load.append((3, s, 'این پروژه'))      # اسکیلِ پروژه‌ای بدونِ شرط = همیشه برای همان پروژه
        else:
            avail.append((s, 'دستی' if s.apply == Skill.MANUAL else 'مرتبط نبود'))
    load.sort(key=lambda x: (x[0], x[1].order, x[1].id))
    avail.sort(key=lambda x: (x[0].scope != Skill.PROJECT, x[0].order, x[0].id))
    return [(s, why) for _, s, why in load], avail


def for_project(org, project_id=None):
    """همهٔ اسکیل‌های قابلِ‌استفاده برای پروژه (اجباری + عمومی + همین پروژه) — تبِ پروژه."""
    q = Q(scope__in=[Skill.MUST, Skill.GENERAL])
    if project_id:
        q |= Q(scope=Skill.PROJECT, project_id=project_id)
    order = {Skill.MUST: 0, Skill.GENERAL: 1, Skill.PROJECT: 2}
    return sorted(live(org).filter(q).select_related('project'), key=lambda s: (order[s.scope], s.order, s.id))
