#!/usr/bin/env bash
# ساختِ zipِ قابلِ‌تحویل: dist/ChatGPT-WP-<version>.zip  (INSTALL.cmd + README + plugin با node_modules)
set -euo pipefail
cd "$(dirname "$0")/.."
VER=$(node -p "require('./plugin/plugin.json').version")
python3 dev/make_template.py >/dev/null
(cd plugin && npm install --omit=dev --no-audit --no-fund --silent)
rm -rf dist && mkdir -p dist
python3 - "$VER" <<'PY'
import os, sys, zipfile
ver = sys.argv[1]
root = f'ChatGPT-WP-{ver}'
out = f'dist/{root}.zip'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in ('INSTALL.cmd', 'README-FA.md'):
        z.write(f, f'{root}/{f}')
    for base, dirs, files in os.walk('plugin'):
        dirs[:] = [d for d in dirs if d not in ('.cache',)]
        for f in files:
            if f in ('package-lock.json',) and base == 'plugin':
                continue
            p = os.path.join(base, f)
            z.write(p, f'{root}/{p}')
print(out, round(os.path.getsize(out) / 1e6, 1), 'MB')
PY
