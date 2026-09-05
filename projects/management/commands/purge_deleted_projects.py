"""پاک‌سازیِ کاملِ پروژه‌های حذف‌شده‌ای که بیش از ۳۰ روز در سطلِ زباله مانده‌اند.

حذفِ نرمِ پروژه (`Project.deleted_at`) ۳۰ روز قابلِ‌بازگردانی است؛ این دستور موارد
منقضی را برای همیشه hard-delete می‌کند (cascade: تسک/فاکتور/دسترسی‌ها). روی cron/زمان‌بند
روزانه اجرا کن. `--days` مهلت را override می‌کند؛ `--dry-run` فقط گزارش می‌دهد.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import Project


class Command(BaseCommand):
    help = 'حذفِ کاملِ پروژه‌هایی که بیش از N روز در سطلِ زباله‌اند (پیش‌فرض ۳۰).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=Project.TRASH_DAYS)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        qs = Project.all_objects.filter(deleted_at__isnull=False, deleted_at__lt=cutoff)
        n = qs.count()
        if options['dry_run']:
            for p in qs:
                self.stdout.write(f'[dry-run] «{p.name}» (حذف‌شده {p.deleted_at:%Y-%m-%d})')
            self.stdout.write(self.style.WARNING(f'{n} پروژه واجدِ پاک‌سازیِ کامل است (dry-run).'))
            return
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'{n} پروژه‌ی منقضی برای همیشه حذف شد.'))
