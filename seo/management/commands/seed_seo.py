"""بستهٔ عمودیِ سئو — seedِ سادهٔ چند «نوع تسکِ سئو» با فیلدهای سفارشی و KPI.

هستهٔ سیستم عمومی است (فیلدهای پایه فقط: پروژه/مسئول/نوع/اولویت/عنوان/تاریخ/وضعیت/
تخمین/تکرار/توضیحات). موارد تخصصیِ سئو این‌جا به‌صورتِ فیلدِ سفارشیِ نوع تسک اضافه
می‌شوند — نه در هستهٔ Task. اجرای مکرر ایمن است، ولی **نوعِ موجود را دوباره دست
نمی‌زند** (همان فلسفه‌ی `accounts.seed_roles` — شاید سازمان خودش فیلدها را عوض کرده
باشد؛ برای گرفتنِ اسپکِ جدید روی سازمانی که قبلاً seed شده، باید نوع‌های قدیمی را
دستی حذف کنی یا دیتابیس را از نو بسازی).

## فیلدهای وصل‌شونده به ردیابیِ رتبه (`seo/CLAUDE.md`)
- `is_keyword_source` + `track_keyword_rank=True` روی یک فیلدِ `tags`: کلماتش با
  `is_page_link=True` همان تسک جفت می‌شوند و در `TrackedKeyword` ثبت/به‌روز می‌شوند
  (`seo/signals.py`) — یعنی «کلمات کلیدی»ِ انتشار/آپدیت/رپورتاژ.
- `is_keyword_source` بدونِ `track_keyword_rank` (مثلِ «کلمه کلیدی هدف»ِ رپورتاژ):
  فقط برای جستجوی «این کلمه برای کدام تسک‌ها کار شده» (بدونِ ثبتِ رتبه — چون معمولاً
  به صفحه‌ای دیگر اشاره می‌کند، نه صفحه‌ی همین تسک).
- `is_link_source` (مثلِ «لینک هدف»ِ رپورتاژ): همان جستجو ولی بر اساسِ لینک.
- `is_page_link`: این فیلدِ URL، لینکِ صفحه‌ایست که خودِ همین تسک تولید/آپدیت کرده.
"""
from django.core.management.base import BaseCommand

from accounts.models import Organization
from tasks.models import KPIChecklistItem, TaskTypeDef, TaskTypeField, TaskTypeKPI

TAGS = TaskTypeField.TAGS
TEXT = TaskTypeField.TEXT
NUMBER = TaskTypeField.NUMBER
URL = TaskTypeField.URL

# فیلدهای مشترکِ «کلماتِ کلیدیِ ردیابی‌شونده» — انتشار/آپدیت/رپورتاژ هر سه دارندش
_KEYWORD_FIELDS = [
    {'label': 'کلمات کلیدی', 'kind': TAGS, 'required': True,
     'is_keyword_source': True, 'track_keyword_rank': True,
     'placeholder': 'کلمه را بنویس، Enter یا کاما بزن'},
    {'label': 'تعداد کلمه', 'kind': NUMBER, 'required': True, 'is_word_source': True},
    {'label': 'مترادف و LSI', 'kind': TAGS, 'required': False,
     'placeholder': 'اختیاری — نیازی به ردیابیِ رتبه ندارد'},
    {'label': 'عنوان سئو', 'kind': TEXT, 'required': False},
]

SEO_TYPES = [
    {
        'name': 'انتشار', 'color': '#38BDF8', 'icon': '📄', 'review': True, 'order': 20,
        'fields': _KEYWORD_FIELDS + [
            # لینکِ صفحه فقط موقعِ «تکمیل/تیک‌زدنِ کار» الزامی است، نه موقعِ ساختِ تسک
            {'label': 'لینک صفحه', 'kind': URL, 'required': False, 'required_on_done': True,
             'is_page_link': True},
        ],
        'kpis': [
            ('محتوا', 10, True, [('رعایت اصول سئو', 4), ('تیتر مناسب', 2), ('رفع نیاز کاربر', 4)]),
            ('تصویر', 5, False, []),
        ],
    },
    {
        'name': 'آپدیت', 'color': '#FBBF24', 'icon': '♻️', 'review': True, 'order': 21,
        'fields': _KEYWORD_FIELDS + [
            # برخلافِ «انتشار»، اینجا لینکِ صفحه از همان لحظه‌ی ساختِ تسک الزامی است
            # (صفحه از قبل وجود دارد، پس لینکش را از ابتدا داریم).
            {'label': 'لینک صفحه', 'kind': URL, 'required': True, 'is_page_link': True},
        ],
        'kpis': [],
    },
    # «تسکِ فنی» عمداً اینجا نیست — `tasks.seed_task_types` از قبل یک نوعِ built-in به
    # همین نام («فنی»، `builtin_key='tech'`) با همین مشخصات (بدونِ فیلدِ سفارشی) می‌سازد؛
    # `unique_together(organization, name)` باعث می‌شد این‌جا هم بسازیمش، یک get_or_create
    # بی‌اثر بشود. اگر یک روز «فنی» نیاز به فیلدِ سئوی خودش پیدا کرد، همان رکورد را
    # ویرایش کن (`/settings/task-types/`)، رکوردِ دومِ هم‌نام نساز.
    {
        'name': 'رپورتاژ', 'color': '#F472B6', 'icon': '📰', 'review': True, 'order': 23,
        'fields': _KEYWORD_FIELDS + [
            # مثلِ «انتشار» ولی لینکِ صفحه اصلاً الزامی نیست (حتی موقعِ تکمیل) — رپورتاژ
            # ممکن است روی رسانه‌ای بیرونی منتشر شود که لینکش را کمی دیرتر می‌گیریم.
            {'label': 'لینک صفحه', 'kind': URL, 'required': False, 'is_page_link': True},
            # هدفِ تبلیغیِ رپورتاژ — کلمه/لینکِ صفحه‌ای *دیگر* که این رپورتاژ برایش
            # کار شده؛ فقط برای جستجوی «چه تسک‌هایی برای این کلمه/لینک انجام شده»،
            # بدونِ ردیابیِ رتبه (چون به تسکِ دیگری تعلق دارد).
            {'label': 'کلمه کلیدی هدف', 'kind': TAGS, 'required': False, 'is_keyword_source': True},
            {'label': 'لینک هدف', 'kind': URL, 'required': False, 'is_link_source': True},
        ],
        'kpis': [],
    },
    {
        'name': 'لینک‌سازی', 'color': '#2DD4A7', 'icon': '🔗', 'review': False, 'order': 24,
        'fields': [],  # فیلدهای هسته‌ای کافی است
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
                for i, f in enumerate(spec['fields']):
                    TaskTypeField.objects.create(
                        type_def=td, label=f['label'], kind=f.get('kind', TEXT),
                        options=f.get('options', ''), placeholder=f.get('placeholder', ''),
                        required=f.get('required', False),
                        required_on_done=f.get('required_on_done', False),
                        is_word_source=f.get('is_word_source', False),
                        is_keyword_source=f.get('is_keyword_source', False),
                        track_keyword_rank=f.get('track_keyword_rank', False),
                        is_link_source=f.get('is_link_source', False),
                        is_page_link=f.get('is_page_link', False),
                        order=i)
                for j, (ktitle, kmax, checklist, items) in enumerate(spec['kpis']):
                    kpi = TaskTypeKPI.objects.create(
                        type_def=td, title=ktitle, max_score=kmax,
                        has_checklist=checklist, order=j)
                    for n, (ititle, iscore) in enumerate(items):
                        KPIChecklistItem.objects.create(kpi=kpi, title=ititle, score=iscore, order=n)
        self.stdout.write(self.style.SUCCESS(
            f'انواع تسکِ سئو برای {orgs.count()} سازمان آماده شد ({made} نوع جدید).'))
