"""انواع تسکِ built-in **عمومی** (فنی/سایر) را به‌صورت رکورد TaskTypeDef برای هر
سازمان می‌سازد. انواع تخصصیِ سئوی قدیمی (انتشار/آپدیت/رپورتاژ/لینک‌سازی) دیگر اینجا
seed نمی‌شوند — جایشان را انواعِ سفارشیِ اپِ `seo` گرفته (`seed_seo`، فیلدِ سفارشی به‌جای
فیلدِ هارد‌کد). اگر این ۴ نوعِ قدیمی از اجرای قبلی هنوز فعال باشند، همین‌جا **بازنشسته**
می‌شوند (is_active=False؛ رکورد و تسک‌های موجودش دست‌نخورده می‌مانند).

چندشرکتی: برای همه‌ی سازمان‌ها (یا `--org <id>`) اجرا می‌شود. اجرای مکرر ایمن است.
"""
from django.core.management.base import BaseCommand

from accounts.models import Organization
from tasks.models import TYPE_COLORS, Task, TaskTypeDef

GENERIC_TYPES = ['tech', 'other']  # بدون فیلد تخصصی؛ به‌عنوان نوعِ عمومیِ built-in می‌مانند
LEGACY_SEO_TYPES = ['publish', 'update', 'reportage', 'linkbuilding']  # → seo.seed_seo
ICONS = {'publish': '📄', 'update': '♻️', 'tech': '🔧',
         'reportage': '📰', 'linkbuilding': '🔗', 'other': '▫️'}
LABELS = dict(Task.TYPE_CHOICES)


class Command(BaseCommand):
    help = 'ساخت انواع تسک عمومیِ پیش‌فرض (فنی/سایر) + بازنشستگیِ انواعِ سئوِ قدیمی برای هر سازمان'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=int, default=None, help='فقط این سازمان (id)')

    def handle(self, *args, **options):
        orgs = (Organization.objects.filter(id=options['org']) if options['org']
                else Organization.objects.all())
        if not orgs:
            self.stderr.write(self.style.WARNING('سازمانی یافت نشد.'))
            return
        total = 0
        retired = 0
        for org in orgs:
            for i, key in enumerate(GENERIC_TYPES):
                rgb = TYPE_COLORS.get(key, '143,160,184')
                hex_color = '#%02X%02X%02X' % tuple(int(x) for x in rgb.split(','))
                _, was_created = TaskTypeDef.all_objects.update_or_create(
                    organization=org, builtin_key=key,
                    defaults={'name': LABELS[key], 'color': hex_color,
                              'icon': ICONS.get(key, ''), 'order': i})
                total += was_created
            retired += TaskTypeDef.all_objects.filter(
                organization=org, builtin_key__in=LEGACY_SEO_TYPES, is_active=True,
            ).update(is_active=False)
        self.stdout.write(self.style.SUCCESS(
            f'انواع عمومی برای {orgs.count()} سازمان آماده شد ({total} رکورد جدید، '
            f'{retired} نوعِ سئوِ قدیمی بازنشسته شد).'))
