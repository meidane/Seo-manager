# finance/ — حسابداری (پایه)

> پایه ساخته شده؛ جزئیات ظریف (منطق دقیق داشبورد/بدهی، keyboard-grid کامل، اکسل هر بانک)
> برای پالایش بعدی. فرانت مرجع: `mockups/finance*.html`.

## مدل‌ها
- **BankAccount** — `name, bank, color, card_number, initial_balance, is_active`.
  `balance` = اولیه + Σواریز − Σبرداشت (property).
- **Category** («بابت») — قابل‌گسترش: `name, color, is_salary, order, colleague(FK اختیاری)`. `seed_categories`.
  **بابتِ حقوقِ هر همکار خودکار است:** با ساختِ هر Colleague یک بابتِ «حقوق <نام>»
  (`is_salary=True`, `colleague=آن همکار`) ساخته می‌شود — `finance/signals.py`
  (`post_save` روی Colleague؛ نامش با تغییرِ نامِ همکار هم‌گام می‌شود). همکارانِ موجود با
  data-migration `0005` backfill شدند. منطق را جای دیگر تکرار نکن.
- **Transaction** — `bank_account, date(میلادی), time, description, deposit, withdrawal,
  balance, user_note` (از اکسل) + سه ستونِ ما: `project, category, note` + `import_hash` (dedup).
  `make_hash(...)` برای تشخیص تکراری.
- **Payroll / PayrollItem** — صورت‌حساب حقوق ماهانه؛ `total/remaining/status/month_name` (property).
  تبِ حقوق ستون‌ها: همکار · ماه(نام، `month_name`) · اجزا · جمع · **مانده‌ی «کل حساب با همکار»**
  (وضعیت حذف شد). مانده = Σ تعهدِ همه‌ی حقوق‌های همکار − Σ برداشتِ تراکنش‌های بابتِ حقوقِ او
  (`category__colleague`) — در `PayrollListView` محاسبه و به‌صورت dict `balances` پاس داده می‌شود.
  ویرایشِ کاملِ حقوق (همکار/ماه/اجزا) از همان مودال، `payroll_edit` با آرایه‌ی `items` بازساخت می‌کند.
  مودالِ صدور/ویرایش: ماه با **نام** (`فروردین…اسفند`, context `months`)، اجزا تک‌ردیفی با **Enter=ردیف بعد**.
- **Invoice / InvoiceLine** — فاکتور فروش/خدمات به یک پروژه. `number` خودکار و پشت‌سرهم
  در سطحِ سازمان (در `save()` = `Max(number)+1`، با `UniqueConstraint(organization, number)`).
  فیلدها: `issue_date(تاریخ ثبت, میلادی), project, description, due_date(تاریخ پرداخت)`.
  ردیف‌ها: `category(بابت), description, qty(پیش‌فرض ۱, Decimal), unit_price, tax, discount, order`.
  جمع‌ها **property** روی Invoice (منبع واحد = ردیف‌ها): `subtotal`(Σ تعداد×واحد)،
  `tax_total`، `discount_total`، `grand_total`(=subtotal+tax−discount). ردیف: `base`(تعداد×واحد)، `total`.

## ابزار
`utils.py`: `parse_amount` (اعداد فارسی/ویرگول → int)، `parse_excel_date` (شمسی/میلادی + ساعت).

## جریان ورود اکسل (چندبانکه)
`import_preview` (POST فایل+bank+**format**) → `_parse_workbook(f, fmt)` → پرچم تکراری →
`import_confirm` فقط جدیدها را می‌سازد. بانکِ مقصد **اجباری** است (دراپ‌داون پیش‌فرض خالی).
- **قالب انتخابی** (`format`): `saman`/`mehr`/`tejarat`/`other` یا خالی=**تشخیص خودکار**.
  دراپ‌داونِ UI در `import.html` (+ راهنمای ساختارِ هر قالب زیرِ باکسِ آپلود). «سایر»=
  همان پارسرِ کلاسیکِ سامان.
- **تشخیص خودکار** (`_detect_format`): با امضای هدر (`_FMT_SIGNATURE`) — مهر با «زمان
  تراکنش»+«مبلغ»، تجارت با «موجودی حساب»+«شرح تراکنش/RRN»، سامان با «شرح سند»+«واریز».
  ترتیب مهم است (تجارت هم «شرح سند/واریز» دارد، پس مهر→تجارت→سامان).
- **پارسرِ هر بانک** (منبعِ واحدِ نگاشتِ ستون، `finance/views.py`):
  - `_parse_saman` (کلاسیک/موبایلت): 0=ردیف 1=تاریخ(+ساعتِ چندخطی) 2=شرح 3=واریز 4=برداشت 5=مانده 6=توضیحات.
  - `_parse_mehr`: 1=شرح 6=مبلغ(**علامت‌دار**: +واریز/−برداشت) 8=نوع 9=زمان تراکنش 11=مانده؛
    ردیف‌های خالیِ بینابین با تاریخِ نامعتبر رد می‌شوند.
  - `_parse_tejarat`: هدر پایینِ «خلاصه‌ی دوره»؛ 6=شرح سند 7=شرح تراکنش 10=واریز 11=برداشت 12=موجودی 13=زمان 14=تاریخ.
- تاریخ/مبلغ همه از `utils.parse_excel_date`/`parse_amount` (رقمِ فارسی + جالی + استخراجِ ساعت + حفظِ علامت).
- ستون «توضیحات کاربر» (سامان) هم در `user_note` و هم مستقیم در فیلد قابل‌ویرایشِ `note` می‌نشیند.
- **افزودنِ بانکِ جدید:** یک `_parse_xxx` بنویس + امضایش را به `_FMT_SIGNATURE`/`_PARSERS`/
  `_FORMAT_LABEL` و یک `<option>` به دراپ‌داونِ `import.html` اضافه کن.

## گزارش / گردش حساب (`ledger`)
تبِ «گزارش» (`LedgerView`، `/finance/ledger/`) — مثلِ صورت‌حسابِ بانکی. **شرطِ طلایی:**
دقیقاً **یا** پروژه **یا** بابت انتخاب شود (XOR)؛ هر دو یا هیچ‌کدام → صفحه‌ی راهنمای خالی.
- **پروژه:** فاکتورهای پروژه (issue_date) = برداشت؛ تراکنش‌های پروژه = واریز/برداشت.
- **بابت:** تراکنش‌های آن بابت؛ اگر بابتِ حقوق بود (`category.colleague`)، حقوق‌های همکار در
  بازه هم واریز می‌شوند، تاریخ = **اولِ ماهِ ثبت** (`j2g(year,month,1)`).
- مانده‌ی تجمعی (Σواریز−Σبرداشت) در هر ردیف + جمعِ نهایی (واریز/برداشت/مانده) در tfoot.
- بازه از پیکرِ سراسریِ topbar (DateRangeMixin). بانک فیلترِ اختیاریِ تراکنش‌هاست.

## مانده و هشدارها
- **`balances.py` (منبع واحدِ مانده):** `project_balances/project_balance` (Σواریزِ تراکنش −
  Σفاکتورها − Σبرداشتِ تراکنش) و `salary_balances/salary_balance` (Σتعهدِ حقوق − Σبرداشتِ
  بابتِ حقوق). id‌ها با `_int_ids` به int نرمال می‌شوند (کلیدهای annotate int‌اند؛ GET رشته می‌دهد).
- **ستونِ مانده:** فاکتورها (`مانده‌ی پروژه`) و حقوق (`مانده کل حساب`) هر کدام لینک به تبِ گزارش
  با پروژه/بابتِ همان ردیف (`ledger?project=` / `ledger?category=<salary_cat>`).
- **`alerts.py: compute_alerts()`** (هشدارهای نرم، بدونِ بلاک): مانده‌ی بانکِ منفی، مانده‌ی
  پروژه‌ی مثبت (شاید فاکتور جا افتاده)، اضافه‌پرداختِ حقوق. روی داشبورد (`fin_alerts`)، بنرِ
  متنیِ تبِ گزارش (`ledger_alert`)، و به‌صورتِ توستِ هشدار بعدِ نسبت‌دهیِ تراکنش
  (`tx_edit` → `warning` از `_tx_anomaly_warning`؛ فقط اطلاع‌رسانی، ثبت انجام می‌شود).

## جستجوی بابت
همه‌ی انتخاب‌گرهای بابت **قابلِ جستجو**اند: فیلترِ تراکنش (سرچ‌باکس روی چک‌باکس‌ها،
**اعمالِ فوری** بدونِ دکمه‌ی «اعمال»)، درون‌جدولِ تراکنش (`input.tx-cat` + `datalist#tx-cats-dl`
+ نگاشتِ `CAT_MAP` نام→id)، و فیلترِ گزارش (`datalist#lg-cats` + hidden `category`).
**دراپ‌داونِ چندانتخابی** (`.ms/.ms-drop` در `style.css`): `.filters` حالا `position:relative;
z-index:30` دارد چون `.glass` با `backdrop-filter` یک stacking context می‌سازد و بدونِ آن
جدولِ بعدی روی دراپ‌داون می‌افتاد (کلیک روی چک‌باکس‌ها کار نمی‌کرد).

## URLها
`/finance/` داشبورد · `transactions/` · `import/` · `banks/` · `payroll/` · `invoices/` · `ledger/`
(+`invoices/new/`, `invoices/<pk>/` صفحه‌ی فرمِ کاملِ فاکتور) + `api/...`
(bank_create/edit, category_create/delete, tx_edit/bulk, import_preview/confirm,
payroll_create/edit, invoice_create/edit). فاکتور با فرمِ صفحه‌ای (نه مودال) به‌خاطرِ ردیف‌های پویا.

## بازه‌ی تاریخ
- `invoices` از `DateRangeMixin` (session سراسری) استفاده می‌کند.
- `transactions` **بازه را اجباری اعمال نمی‌کند** — پیش‌فرض همه‌ی تراکنش‌ها؛ بازه فقط وقتی
  کاربر صریح `?range=`/`?from=&to=` بدهد اعمال می‌شود (`views._optional_range`). داشبورد از قبل داشت.

## تراکنش‌ها (فیلتر/صفحه‌بندی)
- پیش‌فرض: همه، **۱۰۰تایی صفحه‌بندی** (`Paginator`؛ `?page=`؛ `qs_params` سایرِ فیلترها را در لینکِ صفحه نگه می‌دارد).
- **صفحه‌بندیِ شماره‌دار** (۱ ۲ ۳ … ۲۰): پارشالِ `finance/_pagination.html` (منبعِ واحد) با
  `page_range = paginator.get_elided_page_range(...)` از ویو؛ CSS: `.pagi/.pg` در `style.css`.
- **دراپ‌داونِ پروژه/بابت = `rich-select`** (کلاسِ `rich-select` + `data-color`/`data-img`،
  همان ویجتِ تسک‌ها، `static/js/richselect.js`) — در فیلتر/inline/گروهی/گزارش/فاکتور. فیلترِ
  «بابت» عمداً چندانتخابیِ چک‌باکسی (`.ms`) مانده، نه rich-select (تک‌انتخابی). واحدِ پول: **ریال**.
- کارتِ بانک (صفحه‌ی بانک‌ها + داشبورد) کلیک‌پذیر است → `transactions?bank=<id>`؛ کارت دکمه‌ی «ویرایش» هم دارد (`bank_edit` PATCH).
- **بابت چندانتخابی** (`?category=`های متعدد → `category_id__in`؛ دراپ‌داونِ چک‌باکسی در فیلتر).
- **جستجو** (`?q=`) روی `description`(شرح سند) + `note`(توضیحات).
- ستونِ **بانک** (`bank_account.name`) کنارِ شرح سند نمایش داده می‌شود.

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
