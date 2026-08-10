# projects/

## مدل‌ها
- **Project** — `name, domain, color, project_types(CSV), status, archived_at, amount,
  contract_start/end, description, client_*, manager(FK Colleague), members(M2M), wp_*(فاز۳)`.
  `archive()/restore()` (غیرفعال، نه حذف). `types_list/types_display, is_active`.
- **Credential** — پسورد با **Fernet** (`core/crypto.py`): `set_password/reveal_password`.
  هر «نمایش» در `ActivityLog` ثبت می‌شود.

## فایل‌ها / URLها
- `views.py` — List (جدولی، بازه، آخرین‌گزارش) · Detail (تب‌ها) · CRUD · archive/restore
  · API دسترسی‌ها (`credential_create/reveal/delete`) · **فایل‌ها** (`project_files`,
  `project_file_delete` — Attachment روی پروژه، drag&drop).
  **ستون‌های جدولِ لیست سفارشی‌سازی‌شدنی‌اند:** فقط ستونِ «پروژه» ثابت است، بقیه از
  `core.columns.get_columns('projects','page')` می‌آیند (annotate: planned/done/remaining/
  overdue/minutes/words + پایتونی: progress/state) — تنظیم در `/settings/columns/`.
- `forms.py` — نوع/تیم چک‌باکسی، تاریخ‌های `jdate`، توضیحات `rich-editor` + `clean_html`.
- تب‌های سینگل: نمای‌کلی(آمار بازه) · تسک‌ها · تقویم(embed) · فایل‌ها · دسترسی‌ها · گزارش‌ها · حسابداری(placeholder).

## نکات
- «آخرین پرداخت» در لیست فعلاً `—` است؛ بعد از ساخت `finance` وصل شود.
