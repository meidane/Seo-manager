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
