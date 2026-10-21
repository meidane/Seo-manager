// نصبِ یک‌کلیکی (بدونِ PowerShell): کپیِ پلاگین به ChatGPT Desktop + ثبت در marketplace +
// ساختِ پوشهٔ ChatGPT-WP با اکسلِ قالب + میان‌برِ «پنل» روی دسکتاپ. اجرای دوباره = به‌روزرسانی (اکسلِ کاربر دست نمی‌خورد).
import { existsSync, mkdirSync, cpSync, rmSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { homedir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const PLUGIN_NAME = 'seo-wp-connector';
export const SRC = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const DEST = join(homedir(), '.codex', 'plugins', PLUGIN_NAME);
export const MARKET = join(homedir(), '.agents', 'plugins', 'marketplace.json');
export const CWP_HOME = process.env.CWP_HOME || join(homedir(), 'ChatGPT-WP');
export const VERSION = JSON.parse(readFileSync(join(SRC, 'plugin.json'), 'utf8')).version;

function readJson(p, fallback) {
  try { return JSON.parse(readFileSync(p, 'utf8').replace(/^﻿/, '')); } catch { return fallback; }
}

export function installedVersion() {
  const pj = readJson(join(DEST, 'plugin.json'), null);
  return pj?.version || null;
}

export function marketplaceOk() {
  const m = readJson(MARKET, null);
  return !!m?.plugins?.some?.(p => p.name === PLUGIN_NAME);
}

function desktopDirs() {
  const dirs = new Set();
  if (process.platform === 'win32') {
    try {
      const out = execFileSync('reg', ['query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders', '/v', 'Desktop'], { encoding: 'utf8' });
      const m = out.match(/Desktop\s+REG_\w+\s+(.+)/);
      if (m) dirs.add(m[1].trim().replace(/%([^%]+)%/g, (x, v) => process.env[v] ?? x));
    } catch { /* نبود */ }
  }
  for (const d of [join(homedir(), 'Desktop'), join(homedir(), 'OneDrive', 'Desktop')]) if (existsSync(d)) dirs.add(d);
  return [...dirs].filter(d => existsSync(d));
}

function launcher() {
  const node = process.execPath;
  return ['@echo off', 'chcp 65001 >nul', 'title ChatGPT-WP',
    `"${node}" "${join(DEST, 'app', 'panel.mjs')}"`, 'if errorlevel 1 pause', ''].join('\r\n');
}

export function install({ log = console.log, src = SRC } = {}) {
  const steps = [];
  const say = m => { steps.push(m); log(m); };

  // ۱) کپیِ پلاگین
  if (!existsSync(join(src, 'plugin.json')) || !existsSync(join(src, 'node_modules'))) {
    throw new Error('فایل‌های برنامه کامل نیست. اول zip را Extract کن (کلیکِ راست ← Extract All) و INSTALL.cmd را از پوشهٔ بازشده اجرا کن.');
  }
  const version = JSON.parse(readFileSync(join(src, 'plugin.json'), 'utf8')).version;
  if (resolve(src) !== resolve(DEST)) {
    mkdirSync(dirname(DEST), { recursive: true });
    try { rmSync(DEST, { recursive: true, force: true }); } catch { /* اگر قفل بود رونویسی می‌کنیم */ }
    cpSync(src, DEST, { recursive: true, force: true });
    say(`✓ نسخهٔ ${version} نصب شد: ${DEST}`);
  } else say('✓ پلاگین از قبل در جای خودش است.');

  // ۲) ثبت در marketplaceِ شخصی (بقیهٔ پلاگین‌ها حفظ می‌شوند)
  mkdirSync(dirname(MARKET), { recursive: true });
  const market = readJson(MARKET, null) || { name: 'local-private', interface: { displayName: 'Local Private Plugins' }, plugins: [] };
  if (!Array.isArray(market.plugins)) market.plugins = [];
  market.plugins = market.plugins.filter(p => p?.name !== PLUGIN_NAME);
  market.plugins.push({
    name: PLUGIN_NAME,
    source: { source: 'local', path: `./.codex/plugins/${PLUGIN_NAME}` },
    policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' },
    category: 'Productivity',
  });
  writeFileSync(MARKET, JSON.stringify(market, null, 2), 'utf8');
  say(`✓ در فهرستِ پلاگین‌های محلی ثبت شد: ${MARKET}`);

  // ۳) پوشهٔ کاری + اکسل (اگر نبود)
  for (const d of ['', 'images', 'files', 'backups']) mkdirSync(join(CWP_HOME, d), { recursive: true });
  const excel = join(CWP_HOME, 'sites.xlsx');
  if (!existsSync(excel)) { copyFileSync(join(src, 'template', 'sites.xlsx'), excel); say(`✓ فایلِ تنظیمات ساخته شد: ${excel}`); }
  else say(`✓ فایلِ تنظیماتِ قبلی حفظ شد: ${excel}`);
  writeFileSync(join(CWP_HOME, 'ChatGPT-WP Panel.cmd'), launcher(), 'utf8');

  // ۴) میان‌بر روی دسکتاپ
  for (const d of desktopDirs()) {
    try { writeFileSync(join(d, 'ChatGPT-WP Panel.cmd'), launcher(), 'utf8'); say(`✓ میان‌برِ پنل روی دسکتاپ: ${d}`); } catch { /* مهم نیست */ }
  }
  say('(اکسل، عکس‌ها، فایل‌ها و لاگین‌های مرورگر دست نخوردند.)');
  say('');
  say('حالا ChatGPT Desktop را کامل ببند و دوباره باز کن ← Plugins ← Local Private Plugins ← «SEO WordPress Connector» را فعال کن (در حالتِ Work).');
  return { ok: true, steps, version };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [maj] = process.versions.node.split('.').map(Number);
  if (maj < 18) { console.error(`Node.js ${process.versions.node} قدیمی است؛ نسخهٔ LTS جدید را از nodejs.org نصب کن.`); process.exit(1); }
  try { install(); } catch (e) { console.error('نصب ناموفق: ' + e.message); process.exit(1); }
}
