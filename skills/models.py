"""اسکیل‌ها = دانشِ کاریِ سازمان که کارمندها و هوش مصنوعی (MCPِ `/mcp/<token>/skills/`) طبقِ آن کار می‌کنند.

سه سطح (به ترتیبِ اولویت):
- `must`    — «اجباری»: اطلاعاتِ حیاتی که **موقعِ هر دستور** باید رعایت شود؛ متنِ کاملش در `instructions`ِ
              هر سه کانکتورِ MCP (سایت‌ها/پنل/اسکیل‌ها) تزریق می‌شود (`skills.text.must_use_text`).
- `general` — عمومیِ سازمان (روندِ رپورتاژ، قواعدِ نگارش، …).
- `project` — مخصوصِ یک پروژه (لحن/برند، کلماتِ ممنوع، صفحه‌های مهم، رقبا، …).
هر تغییر یک `SkillVersion` می‌سازد (چه از وب چه از MCP) → تاریخچه + بازگردانی به هر نسخه. حذف نرم (`deleted_at`)
تا بازگردانیِ ژورنالِ MCP هم کار کند.
"""
import os
import secrets

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
    # کِی به هوش مصنوعی داده شود (برای عمومی/پروژه؛ «اجباری» همیشه): always = همیشه کامل (مثلِ humanize/نحوهٔ نگارش)،
    # auto = وقتی مرتبط بود (نوعِ تسک یا کلیدواژه‌ها در متنِ درخواست)، manual = فقط وقتی صریحاً خواسته شود
    ALWAYS, AUTO, MANUAL = 'always', 'auto', 'manual'
    APPLY = [(ALWAYS, 'همیشه'), (AUTO, 'خودکار وقتی مرتبط است'), (MANUAL, 'فقط با درخواست')]
    apply = models.CharField('کِی استفاده شود', max_length=8, choices=APPLY, default=AUTO)
    category = models.CharField('دسته', max_length=60, blank=True, help_text='مثلاً نگارش، رپورتاژ، سئوی فنی')
    tags = models.CharField('کلیدواژه‌های تشخیص', max_length=400, blank=True,
                            help_text='با ویرگول؛ اگر یکی در درخواست بیاید اسکیل خودکار بار می‌شود (مثلاً مقاله، بلاگ، محصول)')
    task_types = models.ManyToManyField('tasks.TaskTypeDef', verbose_name='انواعِ تسک', blank=True, related_name='skills')
    order = models.PositiveIntegerField('ترتیب', default=0)
    active = models.BooleanField('فعال', default=True)
    # اسکیلِ سیستمیِ پیش‌فرض (مثلاً 'feedback' = راهنمای ثبتِ بازخورد) — با تغییرِ عنوان دوباره ساخته نشود
    key = models.CharField(max_length=40, blank=True, db_index=True)
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
    def tag_list(self):
        return [t.strip() for t in self.tags.replace('،', ',').split(',') if t.strip()]

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


def _token():
    return secrets.token_urlsafe(12)


class SkillFile(models.Model):
    """فایلِ ضمیمهٔ اسکیل (نمونه‌کد، عکسِ نمونه، قالب). لینکِ توکنی بدونِ ورود (`/skills/f/<token>/<نام>`) تا
    هوش مصنوعی/ابزارِ آپلودِ وردپرس بتواند بخواندش. حذف = نرم (بازگردانیِ MCP)."""
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='files')
    name = models.CharField('نام', max_length=200)
    file = models.FileField(upload_to='skills/%Y/%m/')
    size = models.PositiveBigIntegerField(default=0)
    note = models.CharField('توضیح', max_length=300, blank=True)
    token = models.CharField(max_length=24, unique=True, default=_token, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_objects = models.Manager()

    TEXT_EXT = {'txt', 'md', 'html', 'htm', 'css', 'js', 'json', 'php', 'py', 'xml', 'csv', 'svg', 'yml', 'yaml', 'ts', 'sql'}
    IMAGE_EXT = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'avif'}

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def ext(self):
        return os.path.splitext(self.name)[1].lstrip('.').lower()

    @property
    def kind(self):
        return 'image' if self.ext in self.IMAGE_EXT else 'text' if self.ext in self.TEXT_EXT else 'file'

    def public_path(self):
        from urllib.parse import quote
        return f'/skills/f/{self.token}/{quote(self.name)}'


class SkillFeedback(models.Model):
    """بازخورد برای بهبودِ اسکیل‌ها: اشتباه/کمبودی که هوش مصنوعی در گفتگو با نویسنده دید (ابزارِ MCPِ `skill_feedback`)
    یا مدیر دستی ثبت کرد. فعلاً نویسنده معلوم نیست (حسابِ ChatGPTِ مشترک). صفحه: `/skills/feedback/`."""
    CONFLICT, MISSING, REWORK, GUESS, QUALITY, OTHER = 'conflict', 'missing', 'rework', 'guess', 'quality', 'other'
    KINDS = [(CONFLICT, 'خلافِ اسکیل'), (MISSING, 'اطلاعاتِ ناقص'), (REWORK, 'دوباره‌کاری'), (GUESS, 'حدس/ابهام'),
             (QUALITY, 'کیفیتِ درخواست'), (OTHER, 'سایر')]
    OPEN, RESOLVED, DISMISSED = 'open', 'resolved', 'dismissed'
    STATUSES = [(OPEN, 'باز'), (RESOLVED, 'حل شد'), (DISMISSED, 'نادیده')]

    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    kind = models.CharField('نوع', max_length=12, choices=KINDS, default=OTHER)
    skill = models.ForeignKey(Skill, verbose_name='اسکیل', on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback')
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    summary = models.CharField('خلاصه', max_length=300)
    suggestion = models.TextField('پیشنهادِ اصلاح', blank=True)
    request = models.TextField('بخشی از درخواست', blank=True)
    source = models.CharField(max_length=8, default='mcp')   # mcp | web
    status = models.CharField('وضعیت', max_length=10, choices=STATUSES, default=OPEN, db_index=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-id']
        verbose_name = 'بازخوردِ اسکیل'
        verbose_name_plural = 'بازخوردهای اسکیل'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.summary

    @property
    def kind_label(self):
        return dict(self.KINDS).get(self.kind, self.kind)
