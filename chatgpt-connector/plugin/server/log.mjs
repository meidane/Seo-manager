// لاگِ ساده روی فایل (ChatGPT-WP\logs\app.log، چرخشی در ۱MB) — برای عیب‌یابی روی کامپیوترِ کاربر.
// هرگز روی stdout نمی‌نویسد (stdoutِ سرورِ MCP فقط مالِ پروتکل است).
import { appendFileSync, statSync, renameSync, mkdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { HOME } from './config.mjs';

const DIR = join(HOME, 'logs');
const FILE = join(DIR, 'app.log');
const who = process.argv[1]?.includes('panel') ? 'panel' : 'mcp';

export function log(level, msg) {
  const line = `${new Date().toISOString()} [${who}] ${level} ${String(msg).replace(/\s+/g, ' ').slice(0, 2000)}\n`;
  try {
    if (!existsSync(DIR)) mkdirSync(DIR, { recursive: true });
    try { if (statSync(FILE).size > 1024 * 1024) renameSync(FILE, FILE + '.1'); } catch { /* هنوز نیست */ }
    appendFileSync(FILE, line, 'utf8');
  } catch { /* لاگ نباید برنامه را بخواباند */ }
  if (level !== 'debug') process.stderr.write(line);
}
export const LOG_FILE = FILE;
