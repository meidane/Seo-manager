"""مدل‌های ردیابیِ رتبهٔ کلمات کلیدی — تنها بخشِ سئو که واقعاً از فیلدِ سفارشیِ
نوعِ تسک فراتر می‌رود و مدلِ خودش را می‌خواهد؛ هستهٔ Task دست‌نخورده می‌ماند.

یک منبعِ داده (`TrackedKeyword` + `KeywordRankSnapshot`)، دو نما در UI:
«بر اساس کلمه کلیدی» و «بر اساس لینک» (گروه‌بندیِ همین رکوردها روی `page_url`).

منبعِ ثبتِ رکورد: افزونهٔ مرورگر (خودکار، `is_manual=False`) یا مودالِ «افزودنِ صفحاتِ
مهم» در تبِ کلمات‌کلیدیِ پروژه (دستی، `is_manual=True` و پیش‌فرض ستاره‌دار). ستاره
بعداً مستقل قابلِ تغییر است (هم برای دستی‌ها هم اتومات‌ها).
"""
from django.db import models

from accounts.tenancy import TenantManager, stamp_org
from core.models import TimeStampedModel


class TrackedKeyword(TimeStampedModel):
    """یک (لینکِ صفحه، کلمهٔ کلیدی) که رتبه‌اش روزانه ثبت می‌شود."""

    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.CASCADE, related_name='tracked_keywords')
    page_url = models.URLField('لینک صفحه', max_length=500)
    keyword = models.CharField('کلمه کلیدی', max_length=255)
    is_manual = models.BooleanField('دستی (از مودالِ صفحات مهم)', default=False)
    is_starred = models.BooleanField('مهم (ستاره‌دار)', default=False)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'کلمه‌ی کلیدیِ ردیابی‌شده'
        verbose_name_plural = 'کلمات کلیدیِ ردیابی‌شده'
        base_manager_name = 'all_objects'
        unique_together = ('project', 'page_url', 'keyword')
        ordering = ['-is_starred', 'keyword']

    def save(self, *args, **kwargs):
        if self.organization_id is None and self.project_id:
            self.organization_id = self.project.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.keyword} — {self.page_url}'


class KeywordRankSnapshot(models.Model):
    """جایگاهِ یک `TrackedKeyword` در یک روزِ مشخص. حداکثر یک رکورد در روز
    (آخرین سرچِ همان روز جایگزین می‌شود — `api.rank_ingest`)."""

    keyword = models.ForeignKey(TrackedKeyword, verbose_name='کلمه کلیدی', on_delete=models.CASCADE, related_name='snapshots')
    date = models.DateField('تاریخ')
    position = models.PositiveIntegerField('جایگاه')
    seen_url = models.URLField('لینکِ دیده‌شده در نتیجه', max_length=500, blank=True)

    class Meta:
        verbose_name = 'رکورد جایگاه'
        verbose_name_plural = 'رکوردهای جایگاه'
        unique_together = ('keyword', 'date')
        ordering = ['date']

    def __str__(self):
        return f'{self.keyword.keyword} — {self.date} — #{self.position}'
