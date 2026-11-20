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
    # واسط (relay): یک دامنهٔ خودت روی سرورِ خارج (مثلاً https://middle.lomin.co) که با nginx درخواست را به گوگل می‌رساند —
    # پنل فقط HTTPSِ عادی به آن می‌زند. اگر پر باشد بر پراکسی مقدم است. `relay_key` = هدرِ X-Relay-Key (تا واسط عمومی نشود).
    relay_url = models.CharField('آدرسِ واسط', max_length=300, blank=True)
    relay_key = models.CharField('کلیدِ واسط', max_length=200, blank=True)
    days_back = models.PositiveIntegerField('روزهای سابقه در اولین همگام‌سازی', default=95)
    last_sync = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    syncing = models.BooleanField(default=False)
    sync_started = models.DateTimeField(null=True, blank=True)   # برای قفل: قفلِ قدیمی‌تر از ۳ ساعت = گیرکرده (ری‌استارتِ سرور)

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
    sitemaps = models.JSONField(default=list, blank=True)            # [{path, last_downloaded, errors, warnings, pending, type}]
    inventory_at = models.DateTimeField(null=True, blank=True)       # آخرین دریافتِ فهرستِ صفحه‌ها از وردپرس
    inventory_error = models.CharField(max_length=300, blank=True)
    inspected_on = models.DateField(null=True, blank=True)           # شمارشِ سهمیهٔ روزانهٔ URL Inspection
    inspected_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('organization', 'site_url')]
        ordering = ['site_url']

    def __str__(self):
        return self.site_url

    @property
    def domain(self):
        from .urls_norm import host_of
        return host_of(self.site_url)


class GSCPage(models.Model):
    """هر صفحه یک بار (آدرس طولانی است و در هر ردیفِ روزانه تکرار می‌شد → حجم ۳-۴ برابر). `key` = `urls_norm.page_key`."""
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='pages')
    key = models.CharField(max_length=700)
    url = models.CharField(max_length=1000)

    class Meta:
        unique_together = [('site', 'key')]


class GSCQueryDay(models.Model):
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='query_days')
    date = models.DateField()
    page = models.ForeignKey(GSCPage, on_delete=models.CASCADE, related_name='+')
    query = models.CharField(max_length=400)
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    position = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['page', 'date'], name='gsc_qday_page_date'),
                   models.Index(fields=['site', 'date'], name='gsc_qday_site_date')]


class GSCPageDay(models.Model):
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='page_days')
    date = models.DateField()
    page = models.ForeignKey(GSCPage, on_delete=models.CASCADE, related_name='+')
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    position = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['page', 'date'], name='gsc_pday_page_date'),
                   models.Index(fields=['site', 'date'], name='gsc_pday_site_date')]


class GSCDeviceDay(models.Model):
    """کلِ سایت به تفکیکِ دستگاه (MOBILE/DESKTOP/TABLET) — سه ردیف در روز، ناچیز."""
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='device_days')
    date = models.DateField()
    device = models.CharField(max_length=10)
    clicks = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    position = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['site', 'date'], name='gsc_dev_site_date')]


class GSCInspection(models.Model):
    """نتیجهٔ URL Inspection (ایندکس/کراول) — فقط برای صفحه‌های مهم (سهمیهٔ روزانهٔ گوگل محدود است):
    صفحهٔ تسک‌ها، صفحه‌های پربازدید، و هر صفحه‌ای که کاربر دستی «بررسی» بزند."""
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='inspections')
    key = models.CharField(max_length=700)
    url = models.CharField(max_length=1000)
    verdict = models.CharField(max_length=20, blank=True)          # PASS | NEUTRAL | FAIL | …
    coverage = models.CharField(max_length=200, blank=True)        # «Submitted and indexed» / «Crawled - currently not indexed» …
    indexing_state = models.CharField(max_length=60, blank=True)
    robots = models.CharField(max_length=40, blank=True)
    fetch_state = models.CharField(max_length=40, blank=True)
    last_crawl = models.DateTimeField(null=True, blank=True)
    google_canonical = models.CharField(max_length=1000, blank=True)
    user_canonical = models.CharField(max_length=1000, blank=True)
    error = models.CharField(max_length=300, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('site', 'key')]

    @property
    def indexed(self):
        return self.verdict == 'PASS'


class GSCSiteURL(models.Model):
    """فهرستِ همهٔ صفحه‌های منتشرشدهٔ سایت از وردپرس (از اتصالِ «سایت‌ها»ی MCP) — برای «صفحه‌های بی‌نمایش».
    kind = نوعِ محتوا (post/page/product/…) یا طبقه‌بندی (category/product_cat). هفته‌ای یک بار تازه می‌شود."""
    site = models.ForeignKey(GSCSite, on_delete=models.CASCADE, related_name='site_urls')
    key = models.CharField(max_length=700)
    url = models.CharField(max_length=1000)
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=300, blank=True)
    published = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [('site', 'key')]
        indexes = [models.Index(fields=['site', 'kind'], name='gsc_surl_site_kind')]
