"""بخشِ «فایل‌ها»: فایل‌های عمومیِ سازمان با لینکِ اشتراکی (بدونِ ورود) + پوشه‌بندی.
لینک = آدرسِ ثابتِ مسیری که به نام و پسوندِ فایل ختم می‌شود: `/f/<سازمان>/<پوشه>/<زیرپوشه>/<نام.پسوند>`
(جایگزین‌کردنِ محتوا لینک را عوض نمی‌کند؛ تغییرِ نام/جابه‌جایی چون مسیر عوض می‌شود، لینک هم عوض می‌شود).
لینکِ قدیمیِ `/f/<token>/` هم برای لینک‌هایی که قبلاً پخش شده‌اند همچنان کار می‌کند."""
from urllib.parse import quote
import secrets

from django.conf import settings
from django.db import models

from accounts.tenancy import TenantManager, stamp_org


def _token():
    return secrets.token_urlsafe(9)


class SharedFolder(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    name = models.CharField('نام', max_length=120)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['name']
        verbose_name = 'پوشه'
        verbose_name_plural = 'پوشه‌ها'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def chain(self):
        """پوشه‌ها از ریشه تا خودش."""
        out, f, seen = [], self, set()
        while f and f.pk not in seen:
            seen.add(f.pk)
            out.append(f)
            f = f.parent
        return out[::-1]


def org_key(org):
    """بخشِ سازمان در لینکِ عمومی = id (نه نامِ سازمان — خواستِ کاربر: نام در لینک دیده نشود)."""
    return str(getattr(org, 'pk', '') or '0')


class SharedFile(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    name = models.CharField('نام', max_length=200)
    file = models.FileField(upload_to='shared/%Y/%m/')
    folder = models.ForeignKey(SharedFolder, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    size = models.PositiveBigIntegerField(default=0)
    token = models.CharField(max_length=24, unique=True, default=_token, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'فایل'
        verbose_name_plural = 'فایل‌ها'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def public_path(self):
        """مسیرِ ثابتِ لینکِ عمومی: /f/<id سازمان>/<پوشه‌ها>/<نام.پسوند> (URL-encoded)."""
        from accounts.models import Organization
        org = Organization.objects.filter(pk=self.organization_id).first()
        parts = [org_key(org)] + [d.name for d in (self.folder.chain() if self.folder_id else [])] + [self.name]
        return '/f/' + '/'.join(quote(p, safe='') for p in parts)

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
