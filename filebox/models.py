"""بخشِ «فایل‌ها»: فایل‌های عمومیِ سازمان با لینکِ اشتراکی (بدونِ ورود). عمداً ساده: آپلود، تغییرِ نام، کپیِ لینک، حذف.
لینک = `/f/<token>/` — توکن ثابت می‌ماند، پس جایگزین‌کردنِ محتوا یا تغییرِ نام لینکِ قبلی را خراب نمی‌کند."""
import secrets

from django.conf import settings
from django.db import models

from accounts.tenancy import TenantManager, stamp_org


def _token():
    return secrets.token_urlsafe(9)


class SharedFile(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    name = models.CharField('نام', max_length=200)
    file = models.FileField(upload_to='shared/%Y/%m/')
    size = models.PositiveBigIntegerField(default=0)
    token = models.CharField(max_length=24, unique=True, default=_token, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('organization', 'name')]
        verbose_name = 'فایل'
        verbose_name_plural = 'فایل‌ها'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def ext(self):
        return self.name.rsplit('.', 1)[-1].lower() if '.' in self.name else ''

    @property
    def kind(self):
        e = self.ext
        if e in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'svg'):
            return 'image'
        return {'pdf': 'file-pdf', 'doc': 'file-word', 'docx': 'file-word', 'xls': 'file-excel', 'xlsx': 'file-excel',
                'csv': 'file-excel', 'zip': 'file-zip', 'rar': 'file-zip', '7z': 'file-zip', 'mp4': 'file-video',
                'mov': 'file-video', 'webm': 'file-video', 'mp3': 'file-audio', 'wav': 'file-audio', 'm4a': 'file-audio'}.get(e, 'file')
