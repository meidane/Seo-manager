"""یک سازمانِ نمایشیِ کامل می‌سازد: نقش‌ها (built-in + یک نقشِ سفارشی)، چند کاربرِ تست
با یوزر/پسوردِ ثابت و سطحِ دسترسیِ متفاوت (برای تستِ دقیقاً همان چیزهایی که این پروژه
رویشان حساس است: عضویتِ پروژه، تسکِ دلیگیت‌شده، دیدِ زیرمجموعه، view_other_tasks،
زنجیره‌ی مدیریتیِ سه‌سطحی برای تستِ بازبینیِ مدیرِ بالادست)، چند پروژه، چند تسکِ نمونه
(عقب‌افتاده/این‌هفته/آینده/انجام‌شده/در‌انتظارِ‌بازبینی) و تعطیلات/بابت‌های مالی.

اجرای مکرر ایمن است (get_or_create/update_or_create همه‌جا) — بعدِ پاک‌کردنِ دیتابیس یا
هر وقت خواستی محیطِ تست را دوباره بسازی همین یک دستور کافی است:

    python manage.py seed_demo
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts import tenancy
from accounts.models import Membership, Organization, Role, seed_roles
from colleagues.models import Colleague
from projects.models import Project
from tasks.models import Task, TaskTypeDef

User = get_user_model()

ORG_NAME = 'آژانس دمو'

# نقشِ سفارشیِ «سرپرستِ تیم» — عمداً view_all_projects/manage_people ندارد، تا
# سناریوی «سرپرستِ محدود به پروژه‌ی خودش + زیرمجموعه‌هایش» (نه دسترسیِ سازمانی) هم
# قابل‌تست باشد؛ نقشِ built-in «سرپرست» (manager) خودش view_all_projects دارد (نامحدود در همه‌جا).
TEAMLEAD_ROLE = {
    'key': 'teamlead', 'name': 'سرپرستِ تیم (محدود)',
    'perms': ['edit_task', 'review', 'edit_time', 'view_reports'],
}

# (username, password, نام‌کامل, کلیدِ نقش, یوزرنیمِ مدیرِ مستقیم یا None)
# زنجیره‌ی مدیریتیِ سه‌سطحی عمداً اینجاست (admin1 → teamlead1 → member1/member2) تا
# تستِ «مدیرِ بالادستی هم پندینگِ زیرمجموعه‌ی زیرمجموعه‌اش را ببیند» ممکن باشد
# (`tasks/queries.py: all_subordinate_ids`، بدونِ آن فقط مدیرِ مستقیم می‌دید).
PEOPLE = [
    ('admin', 'admin1234', 'مدیرِ سیستم (سوپریوزر)', 'owner', None),
    ('admin1', 'Admin123!', 'مدیرِ کل', 'admin', None),
    ('teamlead1', 'Teamlead123!', 'سرپرستِ تیم', 'teamlead', 'admin1'),
    ('member1', 'Member123!', 'عضوِ تیمِ یک', 'member', 'teamlead1'),
    ('member2', 'Member123!', 'عضوِ تیمِ دو', 'member', 'teamlead1'),
    ('viewer1', 'Viewer123!', 'ناظر', 'viewer', None),
]


class Command(BaseCommand):
    help = 'سازمانِ دمو + نقش‌ها + چند کاربرِ تست با دسترسیِ متفاوت + پروژه/تسکِ نمونه'

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(name=ORG_NAME)
        seed_roles(org)
        Role.objects.update_or_create(
            organization=org, key=TEAMLEAD_ROLE['key'],
            defaults={'name': TEAMLEAD_ROLE['name'], 'perms': TEAMLEAD_ROLE['perms'], 'is_builtin': False})

        colleagues = self._people(org)

        call_command('seed_task_types', '--org', org.id)
        call_command('seed_holidays')
        try:
            call_command('seed_categories', '--org', org.id)
        except Exception:
            pass

        self._projects_and_tasks(org, colleagues)

        self.stdout.write(self.style.SUCCESS(f'\nسازمانِ «{org.name}» آماده شد. کاربرهای تست:\n'))
        for username, password, full_name, role_key, manager in PEOPLE:
            role_name = dict((r['key'], r['name']) for r in [TEAMLEAD_ROLE]).get(
                role_key, dict(Role.objects.filter(organization=org).values_list('key', 'name')).get(role_key, role_key))
            self.stdout.write(f'  {username:<12} / {password:<14} — {full_name} ({role_name})')
        self.stdout.write(self.style.SUCCESS(
            '\nهمه با همین یوزر/پسورد لاگین می‌کنند (سازمانِ فعال خودکار همین «آژانس دمو» است).'))

    def _people(self, org):
        """کاربر + Membership + Colleague برای هر فرد؛ زیرمجموعه‌ها به مدیرشان وصل می‌شوند."""
        colleagues = {}
        for username, password, full_name, role_key, _mgr in PEOPLE:
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

        # زیرمجموعه‌ها را به مدیرشان وصل کن؛ member1 هم برای تستِ صفِ بازبینیِ سرپرست،
        # needs_review می‌گیرد (مستقل از پرمیشنِ سازمانیِ review — فقط مدیرِ مستقیمش می‌بیند).
        for username, _pw, _fn, _rk, mgr_username in PEOPLE:
            if not mgr_username:
                continue
            c = colleagues[username]
            c.manager = colleagues[mgr_username]
            if username == 'member1':
                c.needs_review = True
            c.save(update_fields=['manager', 'needs_review'])
        return colleagues

    def _projects_and_tasks(self, org, colleagues):
        tenancy.set_current_org(org)
        try:
            proj_a, _ = Project.objects.update_or_create(
                organization=org, name='پروژه‌ی الف', defaults={'domain': 'alef.example.com', 'status': Project.ACTIVE})
            proj_a.members.set([colleagues['teamlead1'], colleagues['member1']])

            proj_b, _ = Project.objects.update_or_create(
                organization=org, name='پروژه‌ی ب', defaults={'domain': 'be.example.com', 'status': Project.ACTIVE})
            proj_b.members.set([colleagues['teamlead1']])

            # پروژه‌ی پ: عمداً هیچ‌کدام از کاربرهای تست عضوش نیستند — تسکِ زیر برای
            # تستِ «دیدِ تسکِ دلیگیت‌شده/زیرمجموعه بیرون از عضویتِ پروژه» است.
            proj_c, _ = Project.objects.update_or_create(
                organization=org, name='پروژه‌ی پ', defaults={'domain': 'pe.example.com', 'status': Project.ACTIVE})

            other_type = TaskTypeDef.objects.filter(organization=org, builtin_key='other').first()
            today = date.today()

            def mk(title, project, assignee, planned_date, status, done_date=None, timer_ago_min=None):
                t, _ = Task.objects.update_or_create(
                    organization=org, project=project, assignee=assignee, title=title,
                    defaults={
                        'task_type': 'other', 'type_def': other_type,
                        'planned_date': planned_date, 'status': status, 'done_date': done_date,
                    })
                if timer_ago_min is not None:
                    from django.utils import timezone
                    t.timer_started_at = timezone.now() - timedelta(minutes=timer_ago_min)
                    t.save(update_fields=['timer_started_at'])
                return t

            # جعبه‌ی «این‌هفته + عقب‌افتاده‌ها»
            mk('نوشتنِ مقاله‌ی سئو (عقب‌افتاده)', proj_a, colleagues['member1'],
               today - timedelta(days=4), Task.DOING, timer_ago_min=25)
            mk('بهینه‌سازیِ صفحه‌ی محصول', proj_a, colleagues['member1'], today + timedelta(days=2), Task.TODO)
            mk('بازبینیِ استراتژیِ محتوا', proj_a, colleagues['teamlead1'], today + timedelta(days=1), Task.TODO)
            # جعبه‌ی «آینده»
            mk('طراحیِ لندینگ‌پیجِ جدید', proj_a, colleagues['member1'], today + timedelta(days=15), Task.TODO)
            # جعبه‌ی «انجام‌شده‌ها»
            mk('گزارشِ ماهانه‌ی ترافیک', proj_a, colleagues['member1'],
               today - timedelta(days=6), Task.DONE, done_date=today - timedelta(days=2))
            # تسکِ دلیگیت‌شده: member2 نه عضوِ پروژه‌ی پ است نه teamlead1 — باید فقط
            # همین یکی را ببینند (member2: تسکِ خودش، teamlead1: تسکِ زیرمجموعه‌اش)
            mk('اصلاحِ متای صفحه‌ی اصلی (دلیگیت‌شده)', proj_c, colleagues['member2'],
               today + timedelta(days=1), Task.TODO)
            # تسکِ در انتظارِ بازبینی: همین موقعِ seed یک نمونه‌ی pending می‌سازد تا
            # صفِ بازبینی (/tasks/review/) از همان لحظه‌ی اول خالی نباشد — هم برای
            # teamlead1 (مدیرِ مستقیمِ member1) هم برای admin1 (مدیرِ بالادستیِ teamlead1،
            # `all_subordinate_ids` باید تا اینجا هم برسد) قابل‌مشاهده و قابل‌تاییدست.
            review_task = mk('محتوای صفحه‌ی فرود (نیازمندِ بازبینی)', proj_a, colleagues['member1'],
                              today - timedelta(days=1), Task.PENDING)
            if not review_task.needs_review:
                review_task.needs_review = True
                review_task.save(update_fields=['needs_review'])
        finally:
            tenancy.set_current_org(None)
