#!/usr/bin/env bash
# واسطِ سرچ کنسول روی سرورِ خارج (Ubuntu/Debian) — یک‌بار اجرا کن:
#   sudo bash gsc-relay.sh middle.lomin.co you@example.com
# خروجی: «کلیدِ واسط» که در پنل (تنظیمات ← سرچ کنسول) وارد می‌کنی.
# کار: nginx + گواهیِ رایگانِ Let's Encrypt؛ فقط دو مسیر را به گوگل می‌رساند و بدونِ کلید 403 می‌دهد:
#   /oauth2/...      → https://oauth2.googleapis.com/...
#   /googleapis/...  → https://www.googleapis.com/...
set -euo pipefail
DOMAIN="${1:?دامنه را بده: sudo bash gsc-relay.sh middle.lomin.co you@example.com}"
EMAIL="${2:?ایمیل (برای Let's Encrypt) را بده}"
KEY="${RELAY_KEY:-$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)}"

apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx

cat > /etc/nginx/sites-available/gsc-relay <<CONF
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ { root /var/www/html; }

    location /oauth2/ {
        if (\$http_x_relay_key != "${KEY}") { return 403 "relay: bad key"; }
        proxy_pass https://oauth2.googleapis.com/;
        proxy_set_header Host oauth2.googleapis.com;
        proxy_set_header X-Relay-Key "";
        proxy_ssl_server_name on;
        proxy_read_timeout 120s;
    }
    location /googleapis/ {
        if (\$http_x_relay_key != "${KEY}") { return 403 "relay: bad key"; }
        proxy_pass https://www.googleapis.com/;
        proxy_set_header Host www.googleapis.com;
        proxy_set_header X-Relay-Key "";
        proxy_ssl_server_name on;
        proxy_read_timeout 120s;
    }
    location / { return 404; }
}
CONF
ln -sf /etc/nginx/sites-available/gsc-relay /etc/nginx/sites-enabled/gsc-relay
nginx -t
systemctl reload nginx

# HTTPS (certbot همین server را به 443 می‌برد و 80 را به https ریدایرکت می‌کند)
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect
systemctl reload nginx

if command -v ufw >/dev/null && ufw status | grep -q active; then ufw allow 80/tcp; ufw allow 443/tcp; fi

echo
echo "✅ واسط آماده است: https://${DOMAIN}"
echo "   کلیدِ واسط (در پنل وارد کن): ${KEY}"
echo "   تست: curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Relay-Key: ${KEY}' https://${DOMAIN}/oauth2/token   (عددِ 4xx از گوگل یعنی سالم است؛ 403 با کلیدِ غلط)"
