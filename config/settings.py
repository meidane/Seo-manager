"""
تنظیمات جنگو برای پلتفرم مدیریت پروژه‌های سئو.

توسعه با SQLite، تولید با PostgreSQL. همه‌ی تاریخ‌ها در دیتابیس میلادی ذخیره
می‌شوند و تبدیل شمسی فقط در لایه‌ی نمایش انجام می‌گیرد.
"""
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── امنیت ──────────────────────────────────────────────────────────────
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-dev-key-change-me-in-production-0123456789',
)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# ── اپلیکیشن‌ها ────────────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

LOCAL_APPS = [
    'accounts',
    'core',
    'dashboard',
    'colleagues',
    'projects',
    'tasks',
    'calendarapp',
    'reports',
    'finance',
]

THIRD_PARTY_APPS = [
    'django_cleanup.apps.CleanupConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.tenancy.CurrentOrgMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.date_range',
                'accounts.context_processors.org',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── دیتابیس ────────────────────────────────────────────────────────────
if config('DB_ENGINE', default='sqlite') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='seo_platform'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── اعتبارسنجی رمز ─────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'accounts:login'

# ── بین‌المللی‌سازی ────────────────────────────────────────────────────
LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ── فایل‌های استاتیک و رسانه ───────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── آپلود ──────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # ۲۰ مگابایت

# ── رمزنگاری دسترسی‌ها (Fernet) ────────────────────────────────────────
# در تولید باید یک کلید پایدار در .env قرار گیرد؛ در نبودش از SECRET_KEY مشتق می‌شود.
FERNET_KEY = config('FERNET_KEY', default='')

# ── کش ─────────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── تنظیمات سراسری برنامه ──────────────────────────────────────────────
# پنجشنبه: کاری (پیش‌فرض) یا نیمه‌تعطیل
THURSDAY_IS_WORKDAY = config('THURSDAY_IS_WORKDAY', default=True, cast=bool)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
