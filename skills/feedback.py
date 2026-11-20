"""بازخورد برای بهبودِ اسکیل‌ها — منبعِ واحد (MCP + صفحهٔ `/skills/feedback/`).

ایندکس:
- FEEDBACK_SKILL / ensure_skill(org)  ← اسکیلِ پیش‌فرضِ «ثبتِ بازخورد» (عمومی·همیشه، key='feedback')؛ متنش را کاربر کامل می‌کند
- record(org, items, source)         ← ساختِ ردیف‌ها (کمکیِ ابزارِ MCPِ `skill_feedback`)
- alarms(org)                         ← هشدار: تکرارِ یک نوع/اسکیل در ۷ روز (≥ ALARM_REPEAT)
- append_to_skill(fb, user)           ← «افزودن به اسکیل»: پیشنهادِ اصلاح به تهِ متنِ اسکیل (نسخهٔ تازه) + حل‌شده
فعلاً نویسنده معلوم نیست (حسابِ ChatGPTِ مشترک) — فیلدِ نویسنده عمداً نداریم.
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import Skill, SkillFeedback

ALARM_REPEAT = 3
ALARM_DAYS = 7

FEEDBACK_SKILL = {
    'key': 'feedback',
    'title': 'ثبتِ بازخورد برای بهبودِ اسکیل‌ها',
    'summary': 'وقتی درخواستِ نویسنده باعثِ افتِ کیفیت شد، با skill_feedback یک خطِ کوتاه ثبت کن.',
    'category': 'بازخورد',
    'body': (
        '## کِی بازخورد ثبت کنی\n'
        'در طولِ گفتگو هر وقت یکی از این‌ها پیش آمد، **بی‌آن‌که کار را متوقف کنی**، ابزارِ `skill_feedback` را بزن:\n'
        '- **خلافِ اسکیل** (`conflict`): نویسنده چیزی خواست که با یکی از اسکیل‌ها تناقض دارد.\n'
        '- **اطلاعاتِ ناقص** (`missing`): کلمهٔ کلیدی، لینک، مخاطب، طول یا هدفِ متن را نداد و مجبور شدی بپرسی.\n'
        '- **دوباره‌کاری** (`rework`): خروجی را چند بار با تغییرِ مبهم برگرداند.\n'
        '- **حدس/ابهام** (`guess`): مجبور شدی چیزی را حدس بزنی چون اسکیل یا درخواست روشن نبود.\n'
        '- **کیفیتِ درخواست** (`quality`): شکلِ درخواست (خیلی کلی، چند کار در یک پیام، …) کیفیت را پایین آورد.\n'
        '\n'
        '## چه بنویسی\n'
        '- `summary`: یک جملهٔ کوتاه از اشتباه (بدونِ کپیِ کاملِ گفتگو).\n'
        '- `skill`: id یا عنوانِ اسکیلِ مرتبط (اگر هست).\n'
        '- `suggestion`: یک قاعدهٔ کوتاه که اگر به اسکیل اضافه شود، دفعهٔ بعد این اتفاق نمی‌افتد.\n'
        '- `request`: فقط تکهٔ مرتبطِ درخواست (حداکثر چند خط).\n'
        '\n'
        '## نمونه‌ها\n'
        '(اینجا را با اشتباه‌های رایجِ تیمِ خودتان کامل کنید.)\n'
    ),
}


def ensure_skill(org):
    """اسکیلِ پیش‌فرضِ بازخورد را اگر نیست می‌سازد (یک بار برای هر سازمان؛ حذف‌شده هم «هست» حساب می‌شود تا برنگردد)."""
    if not org:
        return None
    s = Skill.all_objects.filter(organization=org, key=FEEDBACK_SKILL['key']).first()
    if s:
        return s
    s = Skill(organization=org, scope=Skill.GENERAL, apply=Skill.ALWAYS, key=FEEDBACK_SKILL['key'], order=900,
              **{k: v for k, v in FEEDBACK_SKILL.items() if k != 'key'})
    s.save(source='web', note='اسکیلِ پیش‌فرض')
    return s


KIND_ALIAS = {k: k for k, _ in SkillFeedback.KINDS} | {v: k for k, v in SkillFeedback.KINDS}


def record(org, items, source='mcp', resolve_skill=None, resolve_project=None):
    out = []
    for it in items[:30]:
        summary = str(it.get('summary') or '').strip()
        if not summary:
            continue
        fb = SkillFeedback(organization=org, source=source, summary=summary[:300],
                           kind=KIND_ALIAS.get(str(it.get('kind') or '').strip().lower(), SkillFeedback.OTHER),
                           suggestion=str(it.get('suggestion') or '').strip()[:4000],
                           request=str(it.get('request') or '').strip()[:2000])
        if it.get('skill') and resolve_skill:
            fb.skill = resolve_skill(it['skill'])
        if it.get('project') and resolve_project:
            fb.project_id = resolve_project(it['project'])
        fb.save()
        out.append(fb)
    return out


def alarms(org_qs=None):
    """تکرارهای بازِ ۷ روزِ اخیر: هر (نوع، اسکیل) با ≥ ALARM_REPEAT مورد."""
    qs = org_qs if org_qs is not None else SkillFeedback.objects.all()
    since = timezone.now() - timedelta(days=ALARM_DAYS)
    kinds = dict(SkillFeedback.KINDS)
    rows = (qs.filter(status=SkillFeedback.OPEN, created_at__gte=since)
            .values('kind', 'skill_id', 'skill__title').annotate(n=Count('id')).filter(n__gte=ALARM_REPEAT).order_by('-n'))
    return [{'kind': r['kind'], 'kind_label': kinds.get(r['kind'], r['kind']), 'skill': r['skill_id'],
             'skill_title': r['skill__title'] or '', 'n': r['n']} for r in rows]


def append_to_skill(fb, user):
    if not fb.skill_id or not fb.suggestion.strip():
        return False
    s = fb.skill
    s.body = (s.body.rstrip() + '\n\n' + '- ' + fb.suggestion.strip()).strip()
    s.save(actor=user, source='web', note=f'از بازخوردِ #{fb.id}')
    fb.status, fb.resolved_by, fb.resolved_at = SkillFeedback.RESOLVED, user, timezone.now()
    fb.save()
    return True
