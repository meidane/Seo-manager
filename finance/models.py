"""مدل‌های حسابداری (پایه).

طراحی: چند بانک، تراکنش‌های واردشده از اکسل (واریز/برداشت)، دسته‌بندی «بابت»
(قابل‌گسترش)، و صورت‌حساب حقوق. سه ستونی که خودمان پر می‌کنیم روی هر تراکنش:
project / category(بابت) / note.

قانون تاریخ: `date` میلادی. مبالغ Decimal مثبت (واریز و برداشت جدا).
"""
import hashlib

from django.db import models

from accounts.tenancy import TenantManager, stamp_org
from core.models import TimeStampedModel


class BankAccount(TimeStampedModel):
    name = models.CharField('نام حساب', max_length=120)
    bank = models.CharField('بانک', max_length=60, blank=True)
    color = models.CharField('رنگ', max_length=7, default='#4183F2')
    card_number = models.CharField('شماره کارت/حساب', max_length=40, blank=True)
    initial_balance = models.DecimalField('مانده‌ی اولیه', max_digits=16, decimal_places=0, default=0)
    is_active = models.BooleanField('فعال', default=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'حساب بانکی'
        verbose_name_plural = 'حساب‌های بانکی'
        ordering = ['name']
        base_manager_name = 'all_objects'

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def balance(self):
        agg = self.transactions.aggregate(
            d=models.Sum('deposit'), w=models.Sum('withdrawal'))
        return (self.initial_balance or 0) + (agg['d'] or 0) - (agg['w'] or 0)


class Category(models.Model):
    """«بابت» — قابل‌گسترش توسط کاربر. مثلاً سئو، طراحی سایت، فنی، تولید محتوا، حقوق."""

    name = models.CharField('عنوان بابت', max_length=80)
    color = models.CharField('رنگ', max_length=7, default='#8FA0B8')
    is_salary = models.BooleanField('مربوط به حقوق', default=False)
    # بابتِ حقوقِ یک همکارِ مشخص (خودکار ساخته می‌شود؛ برای محاسبه‌ی مانده‌ی حساب با او)
    colleague = models.ForeignKey('colleagues.Colleague', verbose_name='همکار (حقوق)', on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_categories')
    order = models.PositiveIntegerField('ترتیب', default=0)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'بابت'
        verbose_name_plural = 'بابت‌ها'
        ordering = ['order', 'name']
        base_manager_name = 'all_objects'
        unique_together = ('organization', 'name')

    def save(self, *args, **kwargs):
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Transaction(TimeStampedModel):
    bank_account = models.ForeignKey(BankAccount, verbose_name='حساب', on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField('تاریخ')
    time = models.CharField('ساعت', max_length=8, blank=True)
    description = models.CharField('شرح سند', max_length=255, blank=True)
    deposit = models.DecimalField('واریز', max_digits=16, decimal_places=0, default=0)
    withdrawal = models.DecimalField('برداشت', max_digits=16, decimal_places=0, default=0)
    balance = models.DecimalField('مانده', max_digits=16, decimal_places=0, null=True, blank=True)
    user_note = models.CharField('توضیحات کاربر (اکسل)', max_length=255, blank=True)

    # سه ستونی که خودمان پر می‌کنیم
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    category = models.ForeignKey(Category, verbose_name='بابت', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    note = models.CharField('توضیحات', max_length=255, blank=True)

    import_hash = models.CharField('هش تشخیص تکراری', max_length=64, db_index=True, blank=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        ordering = ['-date', '-id']
        base_manager_name = 'all_objects'
        indexes = [
            models.Index(fields=['bank_account', 'date']),
            models.Index(fields=['project', 'category']),
        ]

    def save(self, *args, **kwargs):
        if self.organization_id is None and self.bank_account_id:
            self.organization_id = self.bank_account.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.date} — {self.description[:30]}'

    @staticmethod
    def make_hash(bank_id, date, description, deposit, withdrawal, balance):
        raw = f'{bank_id}|{date}|{description}|{deposit}|{withdrawal}|{balance}'
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class Invoice(TimeStampedModel):
    """فاکتور فروش/خدمات به یک پروژه.

    شماره‌ی فاکتور خودکار و پشت‌سرهم در سطحِ سازمان تولید می‌شود (`number`).
    مبالغِ ردیف‌ها در `InvoiceLine`؛ جمع‌ها property هستند (منبع واحد = خودِ ردیف‌ها).
    تاریخ‌ها میلادی (طبق قانونِ طلایی) و در نمایش شمسی می‌شوند.
    """

    number = models.PositiveIntegerField('شماره فاکتور', null=True, blank=True, db_index=True)
    issue_date = models.DateField('تاریخ ثبت فاکتور')
    project = models.ForeignKey('projects.Project', verbose_name='پروژه', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    description = models.TextField('توضیحات فاکتور', blank=True)
    due_date = models.DateField('تاریخ پرداخت', null=True, blank=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'فاکتور'
        verbose_name_plural = 'فاکتورها'
        ordering = ['-issue_date', '-number', '-id']
        base_manager_name = 'all_objects'
        constraints = [
            models.UniqueConstraint(fields=['organization', 'number'], name='uniq_invoice_number_per_org'),
        ]

    def save(self, *args, **kwargs):
        if self.organization_id is None and self.project_id:
            self.organization_id = self.project.organization_id
        stamp_org(self)
        if not self.number:
            last = (Invoice.all_objects
                    .filter(organization_id=self.organization_id)
                    .aggregate(m=models.Max('number'))['m'])
            self.number = (last or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f'فاکتور #{self.number}'

    # ── جمع‌ها (منبع واحد = ردیف‌ها) ──
    @property
    def subtotal(self):
        """جمعِ مبالغِ واحد (Σ تعداد×مبلغِ واحد)، بدون مالیات و تخفیف."""
        return sum((li.base for li in self.lines.all()), 0)

    @property
    def tax_total(self):
        return sum((li.tax for li in self.lines.all()), 0)

    @property
    def discount_total(self):
        return sum((li.discount for li in self.lines.all()), 0)

    @property
    def grand_total(self):
        """جمعِ کل = جمعِ مبالغِ واحد + مالیات − تخفیف."""
        return self.subtotal + self.tax_total - self.discount_total


class InvoiceLine(models.Model):
    """یک ردیفِ فاکتور. `total` = تعداد×مبلغِ واحد + مالیات − تخفیف."""

    invoice = models.ForeignKey(Invoice, verbose_name='فاکتور', on_delete=models.CASCADE, related_name='lines')
    category = models.ForeignKey(Category, verbose_name='بابت', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_lines')
    description = models.CharField('توضیحات', max_length=255, blank=True)
    qty = models.DecimalField('تعداد', max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField('مبلغ واحد', max_digits=16, decimal_places=0, default=0)
    tax = models.DecimalField('مالیات', max_digits=16, decimal_places=0, default=0)
    discount = models.DecimalField('تخفیف', max_digits=16, decimal_places=0, default=0)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'ردیف فاکتور'
        verbose_name_plural = 'ردیف‌های فاکتور'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.description[:30]} × {self.qty}'

    @property
    def base(self):
        """تعداد × مبلغِ واحد (بدون مالیات/تخفیف)."""
        return int(round(float(self.qty) * float(self.unit_price)))

    @property
    def total(self):
        return self.base + int(self.tax or 0) - int(self.discount or 0)


class Payroll(TimeStampedModel):
    """صورت‌حساب حقوق یک همکار در یک ماه شمسی."""

    colleague = models.ForeignKey('colleagues.Colleague', verbose_name='همکار', on_delete=models.CASCADE, related_name='payrolls')
    year = models.PositiveIntegerField('سال شمسی')
    month = models.PositiveIntegerField('ماه شمسی')
    paid_amount = models.DecimalField('پرداخت‌شده', max_digits=16, decimal_places=0, default=0)
    note = models.CharField('یادداشت', max_length=255, blank=True)

    organization = models.ForeignKey('accounts.Organization', verbose_name='سازمان', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'حقوق'
        verbose_name_plural = 'حقوق‌ها'
        ordering = ['-year', '-month']
        base_manager_name = 'all_objects'
        unique_together = [('colleague', 'year', 'month')]

    def save(self, *args, **kwargs):
        if self.organization_id is None and self.colleague_id:
            self.organization_id = self.colleague.organization_id
        stamp_org(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.colleague} — {self.year}/{self.month}'

    @property
    def month_name(self):
        from core.jalali import MONTH_NAMES
        if 1 <= (self.month or 0) <= 12:
            return MONTH_NAMES[self.month - 1]
        return str(self.month)

    @property
    def total(self):
        return self.items.aggregate(s=models.Sum('amount'))['s'] or 0

    @property
    def remaining(self):
        return self.total - (self.paid_amount or 0)

    @property
    def status(self):
        t = self.total
        if not t or self.paid_amount >= t:
            return 'paid'
        if self.paid_amount <= 0:
            return 'unpaid'
        return 'partial'


class PayrollItem(models.Model):
    payroll = models.ForeignKey(Payroll, verbose_name='حقوق', on_delete=models.CASCADE, related_name='items')
    title = models.CharField('عنوان', max_length=80)  # حقوق پایه، پاداش، …
    amount = models.DecimalField('مبلغ', max_digits=16, decimal_places=0, default=0)

    class Meta:
        verbose_name = 'جزء حقوق'
        verbose_name_plural = 'اجزای حقوق'
        ordering = ['id']

    def __str__(self):
        return f'{self.title}: {self.amount}'
