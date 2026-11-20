# استقرارِ «Teams» روی سرورِ لینوکس

Django 5 + PostgreSQL + Gunicorn + systemd + Nginx. استاتیک را **WhiteNoise** می‌دهد
(نیازی به کانفیگِ استاتیک در Nginx نیست). گرفتنِ تغییرات از گیت با `./deploy.sh`.

فرض: اوبونتو ۲۲/۲۴، دامنه‌ی `teams.example.com` که رکوردِ A آن به IPِ سرور اشاره می‌کند،
و مسیرِ نصب `/var/www/teams`.

---

## ۱) بسته‌های سیستم
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git nginx postgresql libpq-dev
```

## ۲) دیتابیسِ PostgreSQL
```bash
sudo -u postgres psql <<'SQL'
CREATE USER teams WITH PASSWORD 'یک-رمزِ-قوی';
CREATE DATABASE teams OWNER teams;
ALTER ROLE teams SET client_encoding TO 'utf8';
ALTER ROLE teams SET timezone TO 'UTC';
SQL
```

## ۳) گرفتنِ کد از گیت (repo خصوصی → Deploy Key)
چون repo خصوصی است، روی سرور یک کلیدِ SSH بساز و کلیدِ عمومی را به‌عنوان
**Deploy Key** در گیت‌هاب اضافه کن:
```bash
ssh-keygen -t ed25519 -C "teams-server" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```
کلیدِ چاپ‌شده → GitHub → `meidane/Seo-manager` → **Settings → Deploy keys → Add deploy key**
(نیازی به دسترسیِ نوشتن نیست؛ فقط read کافی است). سپس:
```bash
sudo mkdir -p /var/www && sudo chown "$USER" /var/www
git clone git@github.com:meidane/Seo-manager.git /var/www/teams
cd /var/www/teams
```

## ۴) محیطِ پایتون
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ۵) فایلِ `.env`
```bash
cp deploy/.env.example .env
nano .env          # DEBUG=False، SECRET_KEY، دامنه‌ها، و مشخصاتِ Postgres را پر کن
```
تولیدِ مقادیرِ تصادفی:
```bash
python -c "import secrets;print(secrets.token_urlsafe(50))"                    # SECRET_KEY
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"  # FERNET_KEY
```

## ۶) آماده‌سازیِ اپ
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser        # یا: python manage.py seed_demo (دیتای نمونه)
```

## ۷) سرویسِ Gunicorn (systemd)
```bash
sudo cp deploy/teams.service /etc/systemd/system/teams.service
sudo chown -R www-data:www-data /var/www/teams   # تا www-data به media/DB بنویسد
sudo systemctl daemon-reload
sudo systemctl enable --now teams
sudo systemctl status teams
```

## ۸) Nginx
```bash
sudo cp deploy/nginx-teams.conf /etc/nginx/sites-available/teams
sudo nano /etc/nginx/sites-available/teams        # server_name را عوض کن
sudo ln -s /etc/nginx/sites-available/teams /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## ۹) HTTPS رایگان
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d teams.example.com
```

---

## گرفتنِ تغییرات (هر بار پس از push به گیت)
```bash
cd /var/www/teams
./deploy.sh                 # از origin/main می‌گیرد
# یا برای برنچِ دیگر:  ./deploy.sh نامِ-برنچ
```
`deploy.sh` این‌ها را انجام می‌دهد: `git reset --hard origin/<branch>` → نصبِ وابستگی →
`migrate` → `collectstatic` → `check --deploy` → `systemctl restart teams`.

> اگر `deploy.sh` بدونِ `sudo` اجرا می‌شود ولی `systemctl restart` رمز می‌خواهد،
> یک قانونِ sudoers بی‌رمز فقط برای همین دستور اضافه کن:
> `www-data ALL=(root) NOPASSWD: /bin/systemctl restart teams` (با `sudo visudo`).

### استقرارِ خودکار با هر push (اختیاری)
یک GitHub Action با `appleboy/ssh-action` که به سرور SSH بزند و `cd /var/www/teams && ./deploy.sh`
را اجرا کند؛ کلیدِ خصوصیِ SSH را در Secrets مخزن نگه‌دار.

## سرچ کنسول — همگام‌سازی
خودکار است (روزی یک بار با اولین استفاده از پنل، در پس‌زمینه) — cron **لازم نیست**. اگر خواستی مستقل از بازدید هم اجرا شود (اختیاری):
```
0 4 * * * cd /path/to/Seo-manager && .venv/bin/python manage.py gsc_sync >> /var/log/gsc_sync.log 2>&1
```
اگر سرور به گوگل دسترسی ندارد، در `/settings/gsc/` فیلدِ «پراکسی» را با آدرسِ یک پراکسیِ HTTP روی سرورِ خارج پر کن.

### واسطِ سرچ کنسول (پیشنهادی برای سرورِ ایران)
1. DNS: رکوردِ A برای `middle.lomin.co` → IPِ سرورِ خارج.
2. روی سرورِ خارج: `sudo bash deploy/gsc-relay.sh middle.lomin.co you@example.com` → «کلیدِ واسط» را چاپ می‌کند.
3. در پنل (تنظیمات ← سرچ کنسول): آدرسِ واسط `https://middle.lomin.co` + همان کلید.

اگر واسط را با نسخهٔ قدیمیِ اسکریپت (مسیرِ `/googleapis/`) نصب کرده‌ای، روی سرورِ خارج:
```
sudo sed -i -e "s#location /googleapis/ {#location /webmasters/ {#" -e "s#proxy_pass https://www.googleapis.com/;#proxy_pass https://www.googleapis.com;#" /etc/nginx/sites-available/gsc-relay
sudo nginx -t && sudo systemctl reload nginx
```

### (جایگزین) پراکسیِ سرچ کنسول روی سرورِ خارج (tinyproxy)
```
sudo apt install -y tinyproxy
# در /etc/tinyproxy/tinyproxy.conf:
#   Port 8888
#   Allow <IP سرورِ ایران>
#   BasicAuth gsc <رمزِ قوی>
sudo systemctl restart tinyproxy
sudo ufw allow from <IP سرورِ ایران> to any port 8888 proto tcp
```
تست از سرورِ ایران: `curl -x http://gsc:<رمز>@<IP خارج>:8888 -I https://oauth2.googleapis.com/token` (هر پاسخِ HTTP یعنی وصل است).
در پنل: `http://gsc:<رمز>@<IP خارج>:8888`.
