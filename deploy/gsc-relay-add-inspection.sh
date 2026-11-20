#!/usr/bin/env bash
# برای واسطی که قبلاً نصب شده: مسیرِ بررسیِ ایندکس (/v1/urlInspection/) را اضافه می‌کند. یک بار اجرا: sudo bash gsc-relay-add-inspection.sh
set -euo pipefail
F=/etc/nginx/sites-available/gsc-relay
grep -q 'urlInspection' "$F" && { echo "قبلاً اضافه شده"; exit 0; }
KEY=$(grep -o 'http_x_relay_key != "[^"]*"' "$F" | head -1 | sed 's/.*!= "\(.*\)"/\1/')
[ -n "$KEY" ] || { echo "کلیدِ واسط در $F پیدا نشد"; exit 1; }
cp "$F" "$F.bak"
python3 - "$F" "$KEY" <<'PY'
import sys
f, key = sys.argv[1], sys.argv[2]
s = open(f).read()
block = ('    location /v1/urlInspection/ {\n'
         f'        if ($http_x_relay_key != "{key}") {{ return 403 "relay: bad key"; }}\n'
         '        proxy_pass https://searchconsole.googleapis.com;\n'
         '        proxy_set_header Host searchconsole.googleapis.com;\n'
         '        proxy_set_header X-Relay-Key "";\n'
         '        proxy_ssl_server_name on;\n'
         '        proxy_read_timeout 120s;\n'
         '    }\n')
s = s.replace('    location / { return 404; }', block + '    location / { return 404; }')
open(f, 'w').write(s)
PY
nginx -t && systemctl reload nginx && echo "✅ مسیرِ بررسیِ ایندکس اضافه شد"
