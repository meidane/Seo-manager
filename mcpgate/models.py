"""دروازهٔ MCP: پنل سرورِ MCP است و درخواستِ ChatGPT/Claude را با دسترسیِ ذخیره‌شده به سایت می‌رساند.

مسیر: ChatGPT/Claude → `/mcp/<token>/` (پنل) → REST وردپرس (Application Password) یا MCPِ Novamira روی سایت.
عمداً بدونِ محدودیت (به خواستِ کاربر): هر مسیرِ REST، اجرای PHP/فایل از طریقِ Novamira.
اسکوپِ سازمان با FKِ صریح است (نه TenantManager)، چون endpoint بدونِ سشن و فقط با توکن صدا زده می‌شود.
"""
import secrets

from django.db import models

from core.crypto import decrypt, encrypt


def new_token():
    return secrets.token_urlsafe(24)


class MCPGate(models.Model):
    """یکی برای هر سازمان. توکن خام ذخیره می‌شود (نه هش) تا آدرسِ اتصال همیشه در صفحه قابلِ کپی باشد."""
    organization = models.OneToOneField('accounts.Organization', on_delete=models.CASCADE, related_name='mcp_gate')
    token = models.CharField('توکن', max_length=64, unique=True, default=new_token)
    enabled = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دروازهٔ MCP'

    def __str__(self):
        return f'MCP — {self.organization}'


class MCPSite(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='mcp_sites')
    key = models.CharField('نامِ کوتاه', max_length=80)
    url = models.CharField('آدرس', max_length=300)
    wp_user = models.CharField('نامِ کاربری', max_length=150, blank=True)
    password_enc = models.TextField('رمزِ برنامه (رمزنگاری‌شده)', blank=True)
    mcp_path = models.CharField('مسیرِ MCPِ سایت (Novamira)', max_length=200, blank=True, default='mcp/novamira')
    notes = models.TextField('یادداشت', blank=True)
    active = models.BooleanField('فعال', default=True)
    last_check = models.JSONField('آخرین تست', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'سایتِ MCP'
        unique_together = [('organization', 'key')]
        ordering = ['key']

    def __str__(self):
        return self.key

    @property
    def password(self):
        if not self.password_enc:
            return ''
        try:
            return decrypt(self.password_enc)
        except Exception:  # noqa: BLE001
            return ''

    @password.setter
    def password(self, value):
        self.password_enc = encrypt(value) if value else ''

    def brief(self):
        return {'id': self.id, 'key': self.key, 'url': self.url, 'user': self.wp_user, 'has_password': bool(self.password_enc),
                'mcp_path': self.mcp_path, 'notes': self.notes, 'active': self.active, 'last_check': self.last_check}


class MCPLog(models.Model):
    """لاگِ هر فراخوانیِ ابزار + نسخهٔ قبلیِ چیزی که ویرایش شد (`backup`)."""
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='+')
    site = models.CharField(max_length=80, blank=True)
    tool = models.CharField(max_length=80)
    summary = models.CharField(max_length=300, blank=True)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True)
    ms = models.PositiveIntegerField(default=0)
    backup = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
