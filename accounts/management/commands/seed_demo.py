"""سازمانِ نمایشیِ واقع‌گرایانه: نقش‌ها (built-in + دو نقشِ سفارشی: «مدیرِ ارشد» و
«تولید محتوا»)، ۵ فردِ واقعیِ نمونه با دسترسیِ متفاوت، ۱۴ پروژه‌ی واقعی (نام/دامنه/رنگ)
و چند تسکِ نمونه (عقب‌افتاده/این‌هفته/آینده/انجام‌شده/در‌انتظارِ‌بازبینی).

اجرای مکرر ایمن است (get_or_create/update_or_create). بعدِ هر پاک‌کردنِ DB:

    python manage.py seed_demo
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts import tenancy
from accounts.models import Membership, Organization, Role, seed_roles
from accounts.permissions import PERMS
from colleagues.models import Colleague
from projects.models import Project
from seo.models import KeywordRankSnapshot, TrackedKeyword
from tasks.models import Task, TaskTypeDef

User = get_user_model()

ORG_NAME = 'آژانس دمو'

# «مدیرِ ارشد» = همه‌ی دسترسی‌ها جز حسابداری (برای مدیرانِ سئو/طراحی)
SENIOR_PERMS = [p for p in PERMS if p != 'manage_finance']
# «تولید محتوا» = دسترسی به همه‌ی پروژه‌ها و تسک‌ها، بدونِ حسابداری/گزارش/تنظیمات/حذف
CONTENT_PERMS = [
    'view_all_projects', 'add_project', 'edit_project', 'project_files',
    'project_colleagues_access', 'project_credentials',
    'edit_task', 'view_other_tasks', 'edit_time',
]
CUSTOM_ROLES = [
    {'key': 'senior', 'name': 'مدیرِ ارشد', 'perms': SENIOR_PERMS},
    {'key': 'content', 'name': 'تولید محتوا', 'perms': CONTENT_PERMS},
]

# (username, password, نام‌کامل, کلیدِ نقش, یوزرنیمِ مدیرِ مستقیم, needs_review)
PEOPLE = [
    ('admin', 'admin1234', 'امیر گودرزی', 'owner', None, False),
    ('fsalehi', 'Salehi123!', 'فاطمه صالحی', 'senior', None, False),
    ('sebrahimi', 'Sara123!', 'سارا ابراهیمی', 'senior', None, False),
    ('amoradi', 'Moradi123!', 'امیر مرادی', 'content', 'fsalehi', True),
    ('mziarati', 'Ziarati123!', 'مهتاب زیارتی', 'content', 'fsalehi', True),
]

# (نام, دامنه, رنگ)
PROJECTS = [
    ('تی تی بول', 'ttbol.ir', '#D4AF37'),                       # طلایی
    ('ایران سان لایت', 'Iransunlight.com', '#34D399'),          # سبز
    ('ایت پت شاپ', 'Eatpetshop.com', '#A78BFA'),                # بنفش
    ('عرشیان کلینیک', 'Arshianclinic.com', '#38BDF8'),          # آبی
    ('شکوه دندان', 'Shokohdandan.com', '#A78BFA'),              # بنفش
    ('تاودکور', 'Taav.ir', '#FBBF24'),                          # زرد
    ('استیل تک', 'steeltak.com', '#16A34A'),                    # سبز پررنگ
    ('کاسیو دات ای ار', 'Casio.ir', '#1E3A8A'),                 # سرمه‌ای
    ('عدل و حق', 'adlohagh.com', '#92400E'),                     # قهوه‌ای
    ('بازرگانی هادی', 'HBCindustries.com', '#EF4444'),          # قرمز
    ('دکتر رفعتی', 'Drrafati.com', '#A78BFA'),                  # بنفش
    ('گلرنگ الکترونیک', 'Golrangelectronic.com', '#EF4444'),   # قرمز
    ('مسترقلیون', 'Mrghelion.com', '#FBBF24'),                  # زرد
    ('لیفتراک مقدم', 'Lifttruckmoghadam.com', '#FBBF24'),       # زرد
]


class Command(BaseCommand):
    help = 'سازمانِ دمو + نقش‌ها + ۵ فردِ واقعیِ نمونه + ۱۴ پروژه + تسک‌های نمونه'

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(name=ORG_NAME)
        seed_roles(org)
        for r in CUSTOM_ROLES:
            Role.objects.update_or_create(
                organization=org, key=r['key'],
                defaults={'name': r['name'], 'perms': r['perms'], 'is_builtin': False})

        colleagues = self._people(org)

        call_command('seed_task_types', '--org', org.id)
        try:
            call_command('seed_seo', '--org', org.id)
        except Exception:  # noqa: BLE001
            pass
        call_command('seed_holidays')
        try:
            call_command('seed_categories', '--org', org.id)
        except Exception:  # noqa: BLE001
            pass

        self._projects_and_tasks(org, colleagues)

        self.stdout.write(self.style.SUCCESS(f'\nسازمانِ «{org.name}» آماده شد. کاربرهای تست:\n'))
        role_names = dict(Role.objects.filter(organization=org).values_list('key', 'name'))
        for username, password, full_name, role_key, _mgr, _nr in PEOPLE:
            self.stdout.write(f'  {username:<12} / {password:<14} — {full_name} ({role_names.get(role_key, role_key)})')
        self.stdout.write(self.style.SUCCESS(
            f'\n{len(PROJECTS)} پروژه ساخته شد. همه با همین یوزر/پسورد لاگین می‌کنند.'))

    def _people(self, org):
        colleagues = {}
        for username, password, full_name, role_key, _mgr, _nr in PEOPLE:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                if username == 'admin':
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            Membership.objects.update_or_create(
                user=user, organization=org, defaults={'role': role_key, 'is_active': True})
            colleague, _c = Colleague.objects.update_or_create(
                user=user, organization=org,
                defaults={'full_name': full_name, 'status': Colleague.ACTIVE})
            colleagues[username] = colleague

        # مدیر + needs_review (تولیدِ محتوا زیرِ نظرِ صالحی، بازبینیِ تسک‌هایشان با اوست)
        for username, _pw, _fn, _rk, mgr_username, needs_review in PEOPLE:
            c = colleagues[username]
            changed = []
            if mgr_username:
                c.manager = colleagues[mgr_username]
                changed.append('manager')
            if needs_review:
                c.needs_review = True
                changed.append('needs_review')
            if changed:
                c.save(update_fields=changed + ['updated_at'])
        return colleagues

    def _projects_and_tasks(self, org, colleagues):
        tenancy.set_current_org(org)
        try:
            salehi = colleagues['fsalehi']
            team = [colleagues['fsalehi'], colleagues['sebrahimi'],
                    colleagues['amoradi'], colleagues['mziarati']]
            projects = []
            for idx, (name, domain, color) in enumerate(PROJECTS):
                p, _ = Project.objects.update_or_create(
                    organization=org, name=name,
                    defaults={'domain': domain, 'color': color, 'status': Project.ACTIVE,
                              'manager': salehi,
                              # چند پروژه‌ی اول ردیابیِ رتبه دارند تا تبِ «کلمات کلیدی»
                              # از همان seedِ اول قابل‌دمو باشد (بقیه عمداً خاموش‌اند).
                              'track_keyword_rank': idx < 3})
                p.members.set(team)  # صالحی مسئول + همه عضو (تولید محتوا هم view_all_projects دارد)
                projects.append(p)

            other_type = TaskTypeDef.objects.filter(organization=org, builtin_key='other').first()
            today = date.today()
            content_people = [colleagues['amoradi'], colleagues['mziarati']]

            def mk(title, project, assignee, planned_delta, status, done_delta=None, timer_ago=None):
                t, _ = Task.objects.update_or_create(
                    organization=org, project=project, assignee=assignee, title=title,
                    defaults={
                        'task_type': 'other', 'type_def': other_type,
                        'planned_date': today + timedelta(days=planned_delta), 'status': status,
                        'done_date': (today + timedelta(days=done_delta)) if done_delta is not None else None,
                    })
                if timer_ago is not None:
                    from django.utils import timezone
                    t.timer_started_at = timezone.now() - timedelta(minutes=timer_ago)
                    t.save(update_fields=['timer_started_at'])
                return t

            # نمونه‌های واقع‌گرایانه روی چند پروژه، دستِ تولیدِ محتوا
            mk('نگارشِ مقالهٔ «بهترین غذای گربه»', projects[2], content_people[0], -3, Task.DOING, timer_ago=18)
            mk('بهینه‌سازیِ صفحهٔ محصولِ لامپِ خورشیدی', projects[1], content_people[1], -2, Task.TODO)
            mk('بازنویسیِ متای صفحهٔ خدمات', projects[3], content_people[0], 1, Task.TODO)
            mk('تولیدِ محتوای دستهٔ لیفتراکِ دیزلی', projects[13], content_people[1], 2, Task.TODO)
            mk('پستِ وبلاگ: مراقبت از دندان', projects[4], content_people[0], 5, Task.TODO)
            mk('کلمهٔ کلیدیِ «قیمت ساعت کاسیو»', projects[7], content_people[1], 12, Task.TODO)
            mk('گزارشِ ماهانهٔ سئو — تی‌تی‌بول', projects[0], content_people[0], -6, Task.DONE, done_delta=-2)
            mk('انتشارِ مقالهٔ حقوقی', projects[8], content_people[1], -7, Task.DONE, done_delta=-3)
            # در انتظارِ بازبینی (زیرِ نظرِ صالحی) — صفِ /tasks/review/ از ابتدا خالی نباشد
            rt = mk('محتوای صفحهٔ فرودِ کلینیک (نیازمندِ بازبینی)', projects[3],
                    content_people[0], -1, Task.PENDING)
            if not rt.needs_review:
                rt.needs_review = True
                rt.save(update_fields=['needs_review'])

            self._seo_demo_tasks(org, projects[0], content_people[0])
        finally:
            tenancy.set_current_org(None)

    def _seo_demo_tasks(self, org, project, assignee):
        """دو تسکِ «انتشار» روی اولین پروژهٔ ردیابیِ‌رتبه‌دار — یکی تمام‌شده (با
        کلمات‌کلیدی+لینک، تا سیگنالِ `seo.signals` بلافاصله TrackedKeyword بسازد و
        `seo/CLAUDE.md`ی «مانده‌ی رتبه» از همان seedِ اول قابل‌دمو باشد) و یکی هنوز
        برنامه‌ریزی‌شده (برای تبِ «کلمات کلیدی برنامه‌ریزی‌شده»)."""
        publish = TaskTypeDef.objects.filter(organization=org, name='انتشار').first()
        if not publish:
            return
        fmap = {f.label: f.key for f in publish.fields.all()}
        today = date.today()

        done_task, _ = Task.objects.update_or_create(
            organization=org, project=project, assignee=assignee,
            title='راهنمای خرید لامپ خورشیدی', type_def=publish,
            defaults={
                'task_type': 'other', 'planned_date': today - timedelta(days=20),
                'status': Task.DONE, 'done_date': today - timedelta(days=14),
                'custom': {
                    fmap['کلمات کلیدی']: ['لامپ خورشیدی', 'قیمت لامپ خورشیدی'],
                    fmap['تعداد کلمه']: 1450,
                    fmap['لینک صفحه']: f'https://{project.domain}/lamp-khorshidi',
                },
            })
        kw = TrackedKeyword.all_objects.filter(
            project=project, keyword='لامپ خورشیدی', page_url=done_task.custom[fmap['لینک صفحه']]).first()
        if kw:
            KeywordRankSnapshot.objects.get_or_create(
                keyword=kw, date=today - timedelta(days=18), defaults={'position': 17})
            KeywordRankSnapshot.objects.get_or_create(
                keyword=kw, date=today - timedelta(days=2), defaults={'position': 9})

        Task.objects.update_or_create(
            organization=org, project=project, assignee=assignee,
            title='مقایسهٔ باتری خورشیدی ۱۰۰ آمپر با ۲۰۰ آمپر', type_def=publish,
            defaults={
                'task_type': 'other', 'planned_date': today + timedelta(days=9),
                'status': Task.TODO,
                'custom': {
                    fmap['کلمات کلیدی']: ['باتری خورشیدی', 'قیمت باتری خورشیدی ۱۰۰ آمپر'],
                    fmap['تعداد کلمه']: 900,
                },
            })
