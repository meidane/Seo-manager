// فایل‌های محلی: فهرستِ پوشهٔ عکس‌ها/فایل‌ها، و خواندنِ فایلِ مرجع (txt/md/html/csv/json/docx/xlsx/عکس).
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, extname } from 'node:path';
import { inflateRawSync } from 'node:zlib';
import { createRequire } from 'node:module';
import { DIRS, HOME, resolvePath } from './config.mjs';
import { htmlToText } from './text.mjs';

const require = createRequire(import.meta.url);
const IMG = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif' };

export function filesList({ folder = 'images', limit = 50, contains = '' }) {
  const dir = folder === 'images' ? DIRS.images : folder === 'files' ? DIRS.files : folder === 'backups' ? DIRS.backups : resolvePath(folder);
  if (!existsSync(dir)) return { folder: dir, files: [] };
  const out = [];
  const walk = (d, depth) => {
    for (const name of readdirSync(d)) {
      if (name.startsWith('.') || name.startsWith('~$')) continue;
      const p = join(d, name);
      let st; try { st = statSync(p); } catch { continue; }
      if (st.isDirectory()) { if (depth < 2) walk(p, depth + 1); continue; }
      if (contains && !name.toLowerCase().includes(contains.toLowerCase())) continue;
      out.push({ path: p, kb: Math.round(st.size / 1024), modified: st.mtime.toISOString().slice(0, 16).replace('T', ' ') });
    }
  };
  walk(dir, 0);
  out.sort((a, b) => b.modified.localeCompare(a.modified));
  return { folder: dir, total: out.length, files: out.slice(0, limit) };
}

// zip خوانِ حداقلی (docx + بستهٔ به‌روزرسانی) — بدونِ وابستگی
export function unzipAll(buf, filter = () => true) {
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw new Error('فایلِ zip معتبر نیست');
  let off = buf.readUInt32LE(eocd + 16);
  const n = buf.readUInt16LE(eocd + 10), out = [];
  for (let k = 0; k < n; k++) {
    const flags = buf.readUInt16LE(off + 8), method = buf.readUInt16LE(off + 10), csize = buf.readUInt32LE(off + 20);
    const nlen = buf.readUInt16LE(off + 28), xlen = buf.readUInt16LE(off + 30), clen = buf.readUInt16LE(off + 32);
    const local = buf.readUInt32LE(off + 42);
    const name = buf.toString(flags & 0x800 ? 'utf8' : 'latin1', off + 46, off + 46 + nlen).replace(/\\/g, '/');
    if (!name.endsWith('/') && filter(name)) {
      const start = local + 30 + buf.readUInt16LE(local + 26) + buf.readUInt16LE(local + 28);
      const data = buf.subarray(start, start + csize);
      out.push({ name, data: method === 0 ? data : inflateRawSync(data) });
    }
    off += 46 + nlen + xlen + clen;
  }
  return out;
}
const unzipEntry = (buf, wanted) => unzipAll(buf, n => n === wanted)[0]?.data || null;

export function fileRead({ path, max_chars = 20000 }) {
  const p = resolvePath(path);
  if (!existsSync(p)) throw new Error(`فایل پیدا نشد: ${p}`);
  const ext = extname(p).toLowerCase();
  const cut = s => (s.length > max_chars ? s.slice(0, max_chars) + `…[${s.length - max_chars} نویسهٔ دیگر]` : s);
  if (IMG[ext]) {
    const buf = readFileSync(p);
    if (buf.length > 4 * 1024 * 1024) return { path: p, note: 'عکس بزرگ‌تر از ۴MB است؛ فقط مسیر برگشت (برای آپلود از همین مسیر استفاده کن).' };
    return { path: p, image: buf.toString('base64'), mime: IMG[ext] };
  }
  if (ext === '.docx') {
    const xml = unzipEntry(readFileSync(p), 'word/document.xml');
    const text = String(xml || '').replace(/<w:p[ >][\s\S]*?<\/w:p>/g, m => m.replace(/<w:tab\/>/g, '\t').replace(/<[^>]+>/g, '') + '\n').replace(/<[^>]+>/g, '');
    return { path: p, text: cut(text.replace(/\n{3,}/g, '\n\n').trim()) };
  }
  if (['.xlsx', '.xls', '.ods'].includes(ext)) {
    const XLSX = require('xlsx');
    const wb = XLSX.read(readFileSync(p), { type: 'buffer' });
    const text = wb.SheetNames.map(n => `## ${n}\n` + XLSX.utils.sheet_to_csv(wb.Sheets[n]).split('\n').slice(0, 300).join('\n')).join('\n\n');
    return { path: p, text: cut(text) };
  }
  if (ext === '.pdf') return { path: p, note: 'خواندنِ PDF پشتیبانی نمی‌شود؛ متنش را در یک فایلِ txt/docx بگذار.' };
  const raw = readFileSync(p, 'utf8').replace(/^﻿/, '');
  return { path: p, text: cut(/\.html?$/.test(ext) ? htmlToText(raw) : raw) };
}

export const homeInfo = () => ({ home: HOME, images: DIRS.images, files: DIRS.files, backups: DIRS.backups });
