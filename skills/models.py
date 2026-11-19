"""اسکیل‌ها = دانشِ کاریِ سازمان که کارمندها و هوش مصنوعی (MCPِ `/mcp/<token>/skills/`) طبقِ آن کار می‌کنند.

سه سطح (به ترتیبِ اولویت):
- `must`    — «اجباری»: اطلاعاتِ حیاتی که **موقعِ هر دستور** باید رعایت شود؛ متنِ کاملش در `instructions`ِ
              هر سه کانکتورِ MCP (سایت‌ها/پنل/اسکیل‌ها) تزریق می‌شود (`skills.text.must_use_text`).
- `general` — عمومیِ سازمان (روندِ رپورتاژ، قواعدِ نگارش، …).
- `project` — مخصوصِ یک پروژه (لحن/برند، کلماتِ ممنوع، صفحه‌های مهم، رقبا، …).
هر تغییر یک `SkillVersion` می‌سازد (چه از وب چه از MCP) → تاریخچه + بازگردانی به هر نسخه. حذف نرم (`deleted_at`)
تا بازگردانیِ ژورنالِ MCP هم کار کند.
"""
from django.conf import settings
from django.db import models

from accounts.tenancy import TenantManager, stamp_org

VERSIONED = ('scope', 'project_id', 'title', 'summary', 'body', 'active')


class Skill(models.Model):
    MUST, GENERAL, PROJECT = 'must', 'general', 'project'
    SCOPES = [(MUST, 'اجباری (Must use)'), (GENERAL, 'عمومی'), (PROJECT, 'پروژه')]

    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    scope = models.CharField('سطح', max_length=10, choices=SCOPES, default=GENERAL)
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='skills')
    title = models.CharField('عنوان', max_length=200)
    summary = models.CharField('خلاصهٔ یک‌خطی', max_length=300, blank=True,
                               help_text='هوش مصنوعی اول فقط همین را می‌بیند و اگر لازم بود متنِ کامل را می‌خواند')
    body = models.TextField('متن', blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)
    active = models.BooleanField('فعال', default=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'اسکیل'
        verbose_name_plural = 'اسکیل‌ها'

    def __str__(self):
        return self.title

    @property
    def scope_label(self):
        return dict(self.SCOPES).get(self.scope, self.scope)

    def save(self, *args, actor=None, source=None, note='', **kwargs):
        """هر تغییرِ محتوایی → یک نسخهٔ تازه. source: web|mcp (پیش‌فرض از دستهٔ جاریِ ژورنالِ MCP)."""
        stamp_org(self)
        if self.scope != self.PROJECT:
            self.project = None
        if actor is not None:
            self.updated_by = actor
        old = Skill.all_objects.filter(pk=self.pk).values(*VERSIONED).first() if self.pk else None
        super().save(*args, **kwargs)
        if old is None or any(old[k] != getattr(self, k) for k in VERSIONED):
            if source is None:
                from mcpgate.journal import current_batch
                source = 'mcp' if current_batch() else 'web'
            SkillVersion.objects.create(skill=self, title=self.title, summary=self.summary, body=self.body,
                                        scope=self.scope, project_id=self.project_id, user=actor or self.updated_by,
                                        source=source, note=note[:200])


class SkillVersion(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='versions')
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField(blank=True)
    scope = models.CharField(max_length=10)
    project_id = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    source = models.CharField(max_length=8, default='web')  # web | mcp
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
