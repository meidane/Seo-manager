"""aistudio — تنظیماتِ هوش مصنوعیِ هر پروژه (تبِ «AI»ی سینگلِ پروژه).

- `ProjectAI` (یک‌به‌یک با پروژه): اتصالِ سایت (آدرس + نام کاربری + رمزِ برنامهٔ وردپرس) و
  MCP (آدرس + توکن) + **پرامپتِ عمومی** (همهٔ دانسته‌های ثابتِ پروژه: لحن، مخاطب، محصولات، قواعد).
- `AIPrompt`: پرامپت‌های اختصاصی (انتشار/آپدیت/…)، اختیاراً متصل به یک نوعِ تسک تا تسک‌های همان
  نوع خودکار همین پرامپت را بگیرند. فایل‌های هر پرامپت = `core.Attachment` (منبعِ واحدِ فایل) با
  `description` و `role` (کاربرد: تصویرِ شاخص/داخلِ متن/مرجع/سایر).

**رمزها write-only‌اند:** با Fernet (`core/crypto.py`) ذخیره می‌شوند و هیچ‌وقت به مرورگر
برنمی‌گردند (API فقط `has_*` می‌دهد). دسترسی: پرمیشنِ `project_ai` + دسترسی به خودِ پروژه.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from core.crypto import decrypt, encrypt

# کاربردِ فایلِ پیوستِ پرامپت (منبعِ واحدِ گزینه‌ها؛ API همین را به JS می‌دهد).
FILE_ROLES = [
    ('featured', 'تصویرِ شاخص'),
    ('inline', 'تصویرِ داخلِ متن'),
    ('reference', 'نمونه/مرجع'),
    ('other', 'سایر'),
]
FILE_ROLE_KEYS = {k for k, _ in FILE_ROLES}


class ProjectAI(models.Model):
    """اتصال + پرامپتِ عمومیِ یک پروژه. اسکوپِ سازمان از طریقِ خودِ پروژه است (مثلِ Credential)."""

    project = models.OneToOneField('projects.Project', verbose_name='پروژه',
                                   on_delete=models.CASCADE, related_name='ai_config')
    site_url = models.URLField('آدرس سایت', blank=True, max_length=300)
    wp_username = models.CharField('نام کاربری وردپرس', max_length=150, blank=True)
    wp_password_enc = models.TextField('رمزِ برنامهٔ وردپرس (رمزنگاری‌شده)', blank=True)
    mcp_endpoint = models.URLField('آدرس MCP', blank=True, max_length=500)
    mcp_token_enc = models.TextField('توکنِ MCP (رمزنگاری‌شده)', blank=True)
    general_prompt = models.TextField('پرامپتِ عمومی', blank=True)
    updated_at = models.DateTimeField('آخرین تغییر', auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='آخرین ویرایشگر',
                                   on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # نامِ منطقیِ رمز → فیلدِ رمزنگاری‌شده (منبعِ واحد برای set/get/has)
    SECRETS = {'wp_password': 'wp_password_enc', 'mcp_token': 'mcp_token_enc'}

    class Meta:
        verbose_name = 'تنظیماتِ AIِ پروژه'
        verbose_name_plural = 'تنظیماتِ AIِ پروژه‌ها'

    def __str__(self):
        return f'AI — {self.project}'

    def set_secret(self, name, raw):
        """رمز را رمزنگاری و ذخیره می‌کند؛ مقدارِ خالی = پاک‌کردن."""
        setattr(self, self.SECRETS[name], encrypt(raw) if raw else '')

    def get_secret(self, name):
        """فقط سمتِ سرور (تستِ اتصال / پل) — هرگز به قالب/مرورگر نده."""
        return decrypt(getattr(self, self.SECRETS[name]))

    def has_secret(self, name):
        return bool(getattr(self, self.SECRETS[name]))


class AIPrompt(models.Model):
    """پرامپتِ اختصاصیِ یک نوع کار (انتشار/آپدیت/محصول/لینک‌سازیِ داخلی/…)."""

    project = models.ForeignKey('projects.Project', verbose_name='پروژه',
                                on_delete=models.CASCADE, related_name='ai_prompts')
    title = models.CharField('عنوان', max_length=120)
    task_type = models.ForeignKey('tasks.TaskTypeDef', verbose_name='نوعِ تسکِ متصل',
                                  on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                                  help_text='تسک‌های این نوع در این پروژه خودکار همین پرامپت را می‌گیرند.')
    body = models.TextField('متنِ پرامپت', blank=True)
    order = models.PositiveSmallIntegerField('ترتیب', default=0)
    files = GenericRelation('core.Attachment')  # حذفِ پرامپت ← حذفِ فایل‌هایش
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین تغییر', auto_now=True)

    class Meta:
        verbose_name = 'پرامپتِ اختصاصی'
        verbose_name_plural = 'پرامپت‌های اختصاصی'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.title} — {self.project}'
