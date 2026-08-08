"""انواع تسک built-in را به‌صورت رکورد TaskTypeDef می‌سازد تا در بخش مدیریت
انواع (/settings/task-types/) قابل ویرایش/افزودن‌فیلد باشند.

هر رکورد builtin_key دارد تا فیلدهای هسته‌ای و آمار داشبورد کار کنند.
اجرای مکرر ایمن است (update_or_create)."""
from django.core.management.base import BaseCommand

from tasks.models import TYPE_COLORS, Task, TaskTypeDef


class Command(BaseCommand):
    help = 'ساخت انواع تسک پیش‌فرض به‌صورت رکورد قابل‌مدیریت'

    def handle(self, *args, **options):
        icons = {'publish': '📄', 'update': '♻️', 'tech': '🔧',
                 'reportage': '📰', 'linkbuilding': '🔗', 'other': '▫️'}
        created = 0
        for i, (key, label) in enumerate(Task.TYPE_CHOICES):
            rgb = TYPE_COLORS.get(key, '143,160,184')
            hex_color = '#%02X%02X%02X' % tuple(int(x) for x in rgb.split(','))
            _, was_created = TaskTypeDef.objects.update_or_create(
                builtin_key=key,
                defaults={'name': label, 'color': hex_color,
                          'icon': icons.get(key, ''), 'order': i},
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f'انواع پیش‌فرض آماده شد ({created} جدید، {len(Task.TYPE_CHOICES) - created} به‌روزرسانی).'))
