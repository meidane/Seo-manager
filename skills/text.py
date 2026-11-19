"""منبعِ واحدِ «کدام اسکیل‌ها برای کجا» + متنِ اجباری (must use) که در `instructions`ِ هر سه کانکتورِ MCP می‌آید."""
from django.db.models import Q

from .models import Skill

MUST_MAX = 6000  # سقفِ متنِ اجباری در instructions (توکن)


def live(org=None):
    qs = Skill.all_objects.filter(deleted_at__isnull=True, active=True)
    return qs.filter(organization=org) if org is not None else qs


def must_use_text(org):
    """متنِ کاملِ همهٔ اسکیل‌های اجباری (برای تزریق در instructions). خالی اگر هیچ نبود."""
    parts = [f'## {s.title}\n{s.body.strip()}' for s in live(org).filter(scope=Skill.MUST).order_by('order', 'id')]
    if not parts:
        return ''
    txt = '\n\n'.join(parts)
    if len(txt) > MUST_MAX:
        txt = txt[:MUST_MAX] + '\n… (ادامه با skills_start)'
    return 'اسکیل‌های اجباری (MUST USE — در هر دستور رعایت کن):\n' + txt


def for_project(org, project_id=None):
    """اسکیل‌های مرتبط: اجباری + عمومی + همان پروژه (به ترتیب)."""
    q = Q(scope__in=[Skill.MUST, Skill.GENERAL])
    if project_id:
        q |= Q(scope=Skill.PROJECT, project_id=project_id)
    order = {Skill.MUST: 0, Skill.GENERAL: 1, Skill.PROJECT: 2}
    return sorted(live(org).filter(q).select_related('project'), key=lambda s: (order[s.scope], s.order, s.id))
