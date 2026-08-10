"""بستهٔ عمودیِ سئو — seedِ سادهٔ چند «نوع تسکِ سئو» با فیلدهای سفارشی و KPI.

هستهٔ سیستم عمومی است (فیلدهای پایه فقط: پروژه/مسئول/نوع/اولویت/عنوان/تاریخ/وضعیت/
تخمین/تکرار/توضیحات). موارد تخصصیِ سئو این‌جا به‌صورتِ فیلدِ سفارشیِ نوع تسک اضافه
می‌شوند — نه در هستهٔ Task. اجرای مکرر ایمن است. per سازمان (یا `--org`).
"""
from django.core.management.base import BaseCommand

from accounts.models import Organization
from tasks.models import KPIChecklistItem, TaskTypeDef, TaskTypeField, TaskTypeKPI

# (label, kind, is_word_source, options)
SEO_TYPES = [
    {
        'name': 'انتشار محتوا', 'color': '#38BDF8', 'icon': '📄', 'review': True, 'order': 20,
        'fields': [
            ('کلمات کلیدی', 'text', False, ''),
            ('تعداد کلمه', 'number', True, ''),
            ('عنوان سئو', 'text', False, ''),
            ('لینک انتشار', 'url', False, ''),
        ],
        'kpis': [
            ('محتوا', 10, True, [('رعایت اصول سئو', 4), ('تیتر مناسب', 2), ('رفع نیاز کاربر', 4)]),
            ('تصویر', 5, False, []),
        ],
    },
    {
        'name': 'رپورتاژ آگهی', 'color': '#F472B6', 'icon': '📰', 'review': True, 'order': 21,
        'fields': [
            ('نام رسانه', 'text', False, ''),
            ('هزینه رپورتاژ', 'number', False, ''),
            ('انکر تکست', 'text', False, ''),
            ('لینک مقصد', 'url', False, ''),
            ('لینک انتشار', 'url', False, ''),
        ],
        'kpis': [],
    },
    {
        'name': 'لینک‌سازی خارجی', 'color': '#2DD4A7', 'icon': '🔗', 'review': False, 'order': 22,
        'fields': [
            ('نوع لینک', 'select', False, 'کامنت، پروفایل، فروم، دایرکتوری، سوشال'),
            ('تعداد لینک', 'number', False, ''),
            ('لینک مقصد', 'url', False, ''),
        ],
        'kpis': [],
    },
]


class Command(BaseCommand):
    help = 'ساخت انواع تسکِ سئو (با فیلدهای سفارشی و KPI) برای هر سازمان'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=int, default=None, help='فقط این سازمان (id)')

    def handle(self, *args, **options):
        orgs = (Organization.objects.filter(id=options['org']) if options['org']
                else Organization.objects.all())
        made = 0
        for org in orgs:
            for spec in SEO_TYPES:
                td, created = TaskTypeDef.all_objects.get_or_create(
                    organization=org, name=spec['name'],
                    defaults={'color': spec['color'], 'icon': spec['icon'],
                              'order': spec['order'], 'requires_review': spec['review']})
                if not created:
                    continue  # نوع از قبل هست؛ دوباره فیلد/‌KPI اضافه نکن
                made += 1
                for i, (label, kind, wsrc, opts) in enumerate(spec['fields']):
                    TaskTypeField.objects.create(
                        type_def=td, label=label, kind=kind, options=opts,
                        is_word_source=wsrc, order=i)
                for j, (ktitle, kmax, checklist, items) in enumerate(spec['kpis']):
                    kpi = TaskTypeKPI.objects.create(
                        type_def=td, title=ktitle, max_score=kmax,
                        has_checklist=checklist, order=j)
                    for n, (ititle, iscore) in enumerate(items):
                        KPIChecklistItem.objects.create(kpi=kpi, title=ititle, score=iscore, order=n)
        self.stdout.write(self.style.SUCCESS(
            f'انواع تسکِ سئو برای {orgs.count()} سازمان آماده شد ({made} نوع جدید).'))
