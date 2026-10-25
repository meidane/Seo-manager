"""انبارِ همگام‌سازیِ برنامهٔ دسکتاپِ ChatGPT-WP (`chatgpt-connector/`) — یکی برای هر سازمان.

پنل فقط «انبار» است و منطقِ ادغام سمتِ برنامهٔ دسکتاپ است (`plugin/server/sync.mjs`):
- `SyncStore.data` = همان config.jsonِ برنامه (تنظیمات + سایت‌ها/پرامپت‌ها/رقبا/رمزها)، **رمزنگاری‌شده**
  با Fernet (`core/crypto.py`) چون رمزِ برنامهٔ وردپرس داخلش است. `version` با هر پوش +۱ می‌شود
  (پوش با `base_version` قدیمی → 409 تا برنامه اول ادغام کند).
- `SyncFile` = فایل‌های آپلودشده در برنامه (`files/<سایت>/...`) با مسیرِ نسبی + sha1.
اسکوپِ سازمان صریح است (FK)، چون API با توکن صدا زده می‌شود نه سشن.
"""
import json

from django.db import models

from core.crypto import decrypt, encrypt


class SyncStore(models.Model):
    organization = models.OneToOneField('accounts.Organization', on_delete=models.CASCADE, related_name='chatgpt_sync')
    data_enc = models.TextField('داده (رمزنگاری‌شده)', blank=True)
    version = models.PositiveIntegerField('نسخه', default=0)
    updated_at = models.DateTimeField('آخرین تغییر', null=True, blank=True)
    updated_by = models.CharField('توسط', max_length=150, blank=True)

    class Meta:
        verbose_name = 'انبارِ همگام‌سازی ChatGPT-WP'

    def get_data(self):
        if not self.data_enc:
            return {}
        try:
            return json.loads(decrypt(self.data_enc))
        except Exception:  # noqa: BLE001 — کلیدِ عوض‌شده/دادهٔ خراب نباید پنل را بخواباند
            return {}

    def set_data(self, data):
        self.data_enc = encrypt(json.dumps(data, ensure_ascii=False))


class SyncFile(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='chatgpt_sync_files')
    path = models.CharField('مسیر', max_length=500)
    file = models.FileField(upload_to='chatgpt_sync/%Y/%m/')
    sha1 = models.CharField(max_length=40)
    size = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=150, blank=True)

    class Meta:
        unique_together = [('organization', 'path')]
        ordering = ['path']
