# connector/ — انبارِ همگام‌سازیِ برنامهٔ دسکتاپِ ChatGPT-WP

پنل فقط **انبار** است؛ ویرایش و منطقِ ادغام در برنامهٔ دسکتاپ است (`chatgpt-connector/plugin/server/sync.mjs`).
عمداً ساده: بدونِ مدیریتِ سایت/پرامپت در پنل، بدونِ دسترسیِ جدا برای هر نفر (هر توکنِ سازمان همه‌چیز را می‌بیند).

- **مدل‌ها:** `SyncStore` (یکی برای هر سازمان: `data_enc` = config.jsonِ برنامه **رمزنگاری‌شده با Fernet** چون رمزِ
  وردپرس داخلش است، `version` با هر پوش +۱) و `SyncFile` (مسیرِ نسبیِ `files/...` + sha1، یکتا در سازمان؛ فایلِ قدیمی
  را django-cleanup پاک می‌کند). اسکوپ با FKِ صریح، نه TenantManager.
- **API** (`api.py`، فقط توکن — `seo.api.token_required` + `csrf_exempt`): `GET/POST connector/api/state/`
  (POST با `base_version`؛ ناهمخوان → **409** + وضعیتِ فعلی؛ به‌روزرسانیِ شرطیِ اتمیک روی `version`)،
  `GET/POST connector/api/file/`، `POST connector/api/file/delete/`. سقفِ فایل ۲۰MB (nginx ۲۵M).
- **صفحه:** `/settings/chatgpt-sync/` (`views.SyncPageView`) — وضعیت + فهرستِ سایت‌ها (بدونِ رمز) + راهنمای اتصال.
  گیت: `manage_api_tokens` (تب در `settings/_nav.html` هم با همین).
- تاریخچه: جایگزینِ اپِ حذف‌شدهٔ `aistudio` (تبِ AIِ پروژه) — جدول‌های یتیمش در `docs/CLEANUP.md`.
