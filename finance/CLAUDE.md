# finance/ — حسابداری (پایه)

> پایه ساخته شده؛ جزئیات ظریف (منطق دقیق داشبورد/بدهی، keyboard-grid کامل، اکسل هر بانک)
> برای پالایش بعدی. فرانت مرجع: `mockups/finance*.html`.

## مدل‌ها
- **BankAccount** — `name, bank, color, card_number, initial_balance, is_active`.
  `balance` = اولیه + Σواریز − Σبرداشت (property).
- **Category** («بابت») — قابل‌گسترش: `name, color, is_salary, order`. `seed_categories`.
- **Transaction** — `bank_account, date(میلادی), time, description, deposit, withdrawal,
  balance, user_note` (از اکسل) + سه ستونِ ما: `project, category, note` + `import_hash` (dedup).
  `make_hash(...)` برای تشخیص تکراری.
- **Payroll / PayrollItem** — صورت‌حساب حقوق ماهانه؛ `total/remaining/status` (property).
- **Invoice / InvoiceLine** — فاکتور فروش/خدمات به یک پروژه. `number` خودکار و پشت‌سرهم
  در سطحِ سازمان (در `save()` = `Max(number)+1`، با `UniqueConstraint(organization, number)`).
  فیلدها: `issue_date(تاریخ ثبت, میلادی), project, description, due_date(تاریخ پرداخت)`.
  ردیف‌ها: `category(بابت), description, qty(پیش‌فرض ۱, Decimal), unit_price, tax, discount, order`.
  جمع‌ها **property** روی Invoice (منبع واحد = ردیف‌ها): `subtotal`(Σ تعداد×واحد)،
  `tax_total`، `discount_total`، `grand_total`(=subtotal+tax−discount). ردیف: `base`(تعداد×واحد)، `total`.

## ابزار
`utils.py`: `parse_amount` (اعداد فارسی/ویرگول → int)، `parse_excel_date` (شمسی/میلادی + ساعت).

## جریان ورود اکسل
`import_preview` (POST فایل+bank) → پارس با openpyxl (ستون‌ها: ردیف|تاریخ|شرح|واریز|برداشت|
مانده|توضیحات؛ هدر رد می‌شود) + پرچم تکراری → `import_confirm` فقط جدیدها را می‌سازد.
ستون «توضیحات کاربر» (آخر) هم در `user_note` و هم مستقیم در فیلد قابل‌ویرایشِ `note` می‌نشیند.

## URLها
`/finance/` داشبورد · `transactions/` · `import/` · `banks/` · `payroll/` · `invoices/`
(+`invoices/new/`, `invoices/<pk>/` صفحه‌ی فرمِ کاملِ فاکتور) + `api/...`
(bank_create/edit, category_create/delete, tx_edit/bulk, import_preview/confirm,
payroll_create/edit, invoice_create/edit). فاکتور با فرمِ صفحه‌ای (نه مودال) به‌خاطرِ ردیف‌های پویا.

## بازه‌ی تاریخ
`transactions` و `invoices` از `DateRangeMixin` استفاده می‌کنند (فیلترِ `date`/`issue_date`
با بازه‌ی سراسریِ session؛ پیکرِ بازه در topbar سراسری است). داشبورد هم از قبل داشت.

## دسترسی
کلِ اپ پشتِ پرمیشنِ سازمانیِ `manage_finance` است — `finance/access.py`
(`FinancePermMixin` روی CBVها، `require_finance` روی FBVهای API)، به‌علاوه لینکِ
«حسابداری» در سایدبار هم با همین پرمیشن مخفی/نمایان می‌شود.

## دستور
`python manage.py seed_categories` — بابت‌های پیش‌فرض.

## TODO (جزئیات نیازمند فکر بیشتر)
- داشبورد: بدهی/بستانکاری هر پروژه (نیاز به مفهوم صورتحساب)، اتصال کارت مالی داشبورد اصلی.
- تراکنش‌ها: حرکت کامل کیبوردی (جهت‌ها) مثل اکسل، عملیات گروهی توضیح.
- ایمپورت: نگاشت ستون دستی برای بانک‌های با ساختار متفاوت.
- خروجی اکسل، صورت‌حساب پرداختِ پروژه در گزارش‌ها.
