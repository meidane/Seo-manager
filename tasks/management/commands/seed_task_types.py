"""انواع تسک built-in را به‌صورت رکورد TaskTypeDef برای هر سازمان می‌سازد تا در
بخش مدیریت انواع (/settings/task-types/) قابل ویرایش/افزودن‌فیلد باشند.

هر رکورد builtin_key دارد تا فیلدهای هسته‌ای و آمار داشبورد کار کنند.
چندشرکتی: برای همه‌ی سازمان‌ها (یا `--org <id>`) اجرا می‌شود. اجرای مکرر ایمن است.
"""
from django.core.management.base import BaseCommand

from accounts.models import Organization
from tasks.models import TYPE_COLORS, Task, TaskTypeDef

ICONS = {'publish': '📄', 'update': '♻️', 'tech': '🔧',
         'reportage': '📰', 'linkbuilding': '🔗', 'other': '▫️'}


class Command(BaseCommand):
    help = 'ساخت انواع تسک پیش‌فرض برای هر سازمان (قابل‌مدیریت)'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=int, default=None, help='فقط این سازمان (id)')

    def handle(self, *args, **options):
        orgs = (Organization.objects.filter(id=options['org']) if options['org']
                else Organization.objects.all())
        if not orgs:
            self.stderr.write(self.style.WARNING('سازمانی یافت نشد.'))
            return
        total = 0
        for org in orgs:
            for i, (key, label) in enumerate(Task.TYPE_CHOICES):
                rgb = TYPE_COLORS.get(key, '143,160,184')
                hex_color = '#%02X%02X%02X' % tuple(int(x) for x in rgb.split(','))
                _, was_created = TaskTypeDef.all_objects.update_or_create(
                    organization=org, builtin_key=key,
                    defaults={'name': label, 'color': hex_color,
                              'icon': ICONS.get(key, ''), 'order': i})
                total += was_created
        self.stdout.write(self.style.SUCCESS(
            f'انواع پیش‌فرض برای {orgs.count()} سازمان آماده شد ({total} رکورد جدید).'))
