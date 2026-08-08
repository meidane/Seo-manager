# accounts/

- **User** (custom, `AUTH_USER_MODEL='accounts.User'`) — `team(FK)`, `avatar`. همه‌ی کاربران
  فعلاً به همه‌ی بخش‌ها دسترسی دارند؛ محدودیت دسترسی برای بعد.
- **Team** — آماده‌ی چندتیمی (فاز۳)، فعلاً بدون استفاده.
- ورود/خروج: `views.LoginView/LogoutView`؛ تمپلیت `registration/login.html`.
  `LOGIN_URL/REDIRECT` در settings.

> اگر فیلد به User اضافه کردی، مراقب migration و `createsuperuser` باش.
