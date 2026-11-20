"""سرچ کنسول (Google Search Console) — اتصال با Service Account، همگام‌سازیِ شبانه، ذخیرهٔ محلی.

- `GSCAccount`: یکی برای هر سازمان؛ کلیدِ JSONِ Service Account رمزنگاری‌شده + پراکسیِ اختیاری (واسطِ سرورِ خارج).
- `GSCSite`: هر property (`sc-domain:x.com` یا `https://x.com/`) + پروژهٔ جفت‌شده (خودکار با دامنه).
- `GSCQueryDay` (روز × صفحه × کلمه) و `GSCPageDay` (روز × صفحه، جمعِ دقیق‌ترِ صفحه چون کلماتِ ناشناس در اولی نیستند).
  `page_key` = نشانیِ نرمال‌شده (`urls.page_key`) تا لینکِ تسک (http/www/اسلش/درصد-کد) با دادهٔ گوگل جور شود.
اسکوپ با FKِ صریح به سازمان/سایت (مثلِ mcpgate) — همگام‌سازی بیرون از درخواست اجرا می‌شود.
"""
import json

from django.db import models

from core.crypto import decrypt, encrypt


class GSCAccount(models.Model):
    organization = models.OneToOneField('accounts.Organization', on_delete=models.CASCADE, related_name='gsc_account')
    credentials_enc = models.TextField(blank=True)
    client_email = models.CharField(max_length=300, blank=True)
    proxy = models.CharField('پراکسی (اختیاری)', max_length=300, blank=True,
                             help_text='مثلاً http://user:pass@host:port — برای وقتی سرور به گوگل دسترسی ندارد')
    days_back = models.PositiveIntegerField('روزهای سابقه در اولین همگام‌سازی', default=95)
    last_sync = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    syncing = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'حسابِ سرچ کنسول'

    @property
    def credentials(self):
        try:
            return json.loads(decrypt(self.credentials_enc)) if self.credentials_enc else None
        except Exception:  # noqa: BLE001
            return None

    @credentials.setter
    def credentials(self, data):
        self.credentials_enc = encrypt(json.dumps(data)) if data else ''
        self.client_email = (data or {}).get('client_email', '')


class GSCCredential(models.Model):
    """کلیدِ اضافه (Service Account دیگر، ترجیحاً در پروژهٔ دیگرِ Google Cloud) برای سایت‌های پرداده — تا سهمیهٔ پروژهٔ
    اصلی مصرف نشود. هر `GSCSite` می‌تواند کلیدِ خودش را داشته باشد؛ خالی = کلیدِ اصلیِ `GSCAccount`."""
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='+')
    name = models.CharField(max_length=80)
    credentials_enc = models.TextField()
    client_email = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    credentials = GSCAccount.credentials

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class GSCSite(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='+')
    site_url = models.CharField(max_length=300)
    permission = models.CharField(max_length=40, blank=True)
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True, related_name='gsc_sites')
    credential = models.ForeignKey(GSCCredential, on_delete=models.SET_NULL, null=True, blank=True, related_name='sites')
    active = models.BooleanField(default=True)
    synced_until = models.DateField(null=True, blank=True)   # آخرین روزِ ذخیره‌شده
    first_date = models.DateField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        unique_together = [('organization', 'site_url')]
        ordering = ['site_url']

    def __str__(self):
        return self.site_url

    @property
    def domain(self):
        from .urls_norm import host_of
        return host_of(self.site_url)


class GSCQueryDay(models.Model):
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='query_days')
    date = models.DateField()
    page = models.CharField(max_length=1000)
    page_key = models.CharField(max_length=700, db_index=False)
    query = models.CharField(max_length=400)
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    position = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['site', 'page_key', 'date']), models.Index(fields=['site', 'date']),
                   models.Index(fields=['site', 'query'])]


class GSCPageDay(models.Model):
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='page_days')
    date = models.DateField()
    page = models.CharField(max_length=1000)
    page_key = models.CharField(max_length=700)
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    position = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['site', 'page_key', 'date']), models.Index(fields=['site', 'date'])]
