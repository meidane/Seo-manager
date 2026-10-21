// ابزارهای متنی مشترک: نرمال‌سازیِ فارسی، امتیازِ شباهت، Markdown→HTML، HTML→متن/سرفصل.
// بدونِ وابستگی؛ هم سرورِ MCP و هم پنل از همین می‌خوانند (منبعِ واحد).

const ZWNJ = '‌';

/** نرمال‌سازی برای مقایسه/جست‌وجو: ي/ك عربی، اعداد، اعراب، نیم‌فاصله → فاصله. */
export function norm(s) {
  return String(s ?? '')
    .replace(/[يى]/g, 'ی').replace(/ك/g, 'ک').replace(/[ۀة]/g, 'ه').replace(/[أإٱ]/g, 'ا')
    .replace(/[ً-ٰٟ]/g, '')
    .replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
    .replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)))
    .replace(new RegExp(ZWNJ, 'g'), ' ')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

const STOP = new Set(('و در به از که با این آن را برای تا یا هم اما اگر چه چرا چگونه چطور است هست بود شود ' +
  'می کند کرد های ها ای یک بر نیز ولی همه هر خود دیگر بین پس روی زیر بی the a an of to in for and or on with is are')
  .split(' '));

export function tokens(s) {
  return norm(s).split(' ').filter(t => t && !STOP.has(t));
}

/** امتیازِ ارتباطِ عبارت با عنوان/اسلاگ (۰ تا ~۲). */
export function relevance(phrase, title, slug = '') {
  const kt = tokens(phrase);
  if (!kt.length) return 0;
  const hay = norm(title + ' ' + decodeSafe(slug).replace(/[-_]/g, ' '));
  const ht = new Set(hay.split(' '));
  let hit = 0;
  for (const t of kt) if (ht.has(t) || (t.length > 3 && hay.includes(t))) hit++;
  let score = hit / kt.length;
  if (hay.includes(norm(phrase))) score += 1;
  return Math.round(score * 100) / 100;
}

export function decodeSafe(s) {
  try { return decodeURIComponent(s); } catch { return s; }
}

/** رجکسِ «شل» برای پیدا کردنِ عبارتِ فارسی در HTMLِ خام (ی/ي، ک/ك، فاصله/نیم‌فاصله). */
export function looseRegex(phrase, flags = 'g') {
  let out = '';
  for (const ch of String(phrase).trim()) {
    if (/[یيى]/.test(ch)) out += '[یيى]';
    else if (/[کك]/.test(ch)) out += '[کك]';
    else if (/[هۀة]/.test(ch)) out += '[هۀة]';
    else if (/\s/.test(ch) || ch === ZWNJ) out += '[\\s\\u200c]*';
    else out += ch.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&');
  }
  out = out.replace(/(\[\\s\\u200c\]\*)+/g, '[\\s\\u200c]+');
  return new RegExp(out, flags);
}

// ───────────── HTML → متن ─────────────
const ENT = { nbsp: ' ', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", zwnj: ZWNJ, laquo: '«', raquo: '»', hellip: '…', ndash: '–', mdash: '—' };
export function decodeEntities(s) {
  return String(s ?? '').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') {
      const n = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return ENT[e.toLowerCase()] ?? m;
  });
}

export function stripTags(html) {
  return decodeEntities(String(html ?? '')
    .replace(/<(script|style|noscript|svg)[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' '))
    .replace(/\s+/g, ' ').trim();
}

export function htmlToText(html) {
  return decodeEntities(String(html ?? '')
    .replace(/<(script|style|noscript|svg)[\s\S]*?<\/\1>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<h([1-6])[^>]*>/gi, (m, l) => '\n\n' + '#'.repeat(+l) + ' ')
    .replace(/<li[^>]*>/gi, '\n- ')
    .replace(/<\/(p|div|h[1-6]|li|tr|table|ul|ol|blockquote|section|figure)>/gi, '\n')
    .replace(/<[^>]+>/g, ''))
    .split('\n').map(l => l.replace(/[ \t ]+/g, ' ').trim()).join('\n')
    .replace(/\n{3,}/g, '\n\n').trim();
}

export function wordCount(text) {
  const t = String(text ?? '').trim();
  return t ? t.split(/\s+/).length : 0;
}

/** سرفصل‌ها + متنِ هر بخش از HTML (سمتِ نود؛ برای محتوای خودِ سایت و http_fetch). */
export function htmlSections(html, { level = 'outline', sectionChars = 220, maxChars = 20000 } = {}) {
  const src = String(html ?? '').replace(/<(script|style|noscript|svg)[\s\S]*?<\/\1>/gi, '');
  const re = /<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi;
  const sections = [];
  let last = 0, cur = { l: 0, h: '(مقدمه)', body: '' }, m;
  while ((m = re.exec(src))) {
    cur.body += src.slice(last, m.index);
    sections.push(cur);
    cur = { l: +m[1], h: stripTags(m[2]), body: '' };
    last = re.lastIndex;
  }
  cur.body += src.slice(last);
  sections.push(cur);
  let budget = maxChars;
  const out = [];
  for (const s of sections) {
    const text = stripTags(s.body);
    if (s.l === 0 && !text) continue;
    const row = { l: s.l, h: s.h, w: wordCount(text) };
    if (level !== 'outline') {
      const lim = level === 'full' ? budget : Math.min(sectionChars, budget);
      row.t = text.length > lim ? text.slice(0, lim) + '…' : text;
      budget -= row.t.length;
    }
    out.push(row);
    if (budget <= 0) { out.push({ l: 0, h: '…(بقیه به‌خاطرِ سقفِ طول حذف شد)' }); break; }
  }
  return out;
}

// ───────────── Markdown → HTML (ساده و کافی برای مقاله) ─────────────
function inline(s) {
  return s
    .replace(/!\[([^\]]*)\]\(([^)\s]+|<[^>]+>)(?:\s+"([^"]*)")?\)/g, (m, alt, src, title) =>
      `<img src="${src.replace(/^<|>$/g, '')}" alt="${alt.replace(/"/g, '&quot;')}"${title ? ` title="${title}"` : ''} />`)
    .replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (m, t, href, title) =>
      `<a href="${href}"${title ? ` title="${title}"` : ''}>${t}</a>`)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
}

export function looksLikeHtml(s) {
  return /<(p|h[1-6]|ul|ol|div|table|figure|img|section|!--\s*wp:)[\s>]/i.test(String(s ?? ''));
}

export function markdownToHtml(md) {
  const lines = String(md ?? '').replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  let i = 0;
  const isTableSep = l => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
  const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => inline(c.trim()));
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/))) {
      const l = m[1].length; out.push(`<h${l}>${inline(m[2])}</h${l}>`); i++; continue;
    }
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { out.push('<hr />'); i++; continue; }
    if (/^\s*</.test(line)) { // بلوکِ HTMLِ خام تا خطِ خالی
      const buf = [];
      while (i < lines.length && lines[i].trim()) buf.push(lines[i++]);
      out.push(buf.join('\n')); continue;
    }
    if ((m = line.match(/^\s*!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\s*$/))) {
      const cap = m[3] ? `<figcaption>${m[3]}</figcaption>` : '';
      out.push(`<figure>${inline(line.trim())}${cap}</figure>`); i++; continue;
    }
    if (line.trim().startsWith('|') && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const head = cells(line); i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]));
      out.push('<table><thead><tr>' + head.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>' +
        rows.map(r => '<tr>' + r.map(c => `<td>${c}</td>`).join('') + '</tr>').join('') + '</tbody></table>');
      continue;
    }
    if (/^\s*>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ''));
      out.push(`<blockquote><p>${inline(buf.join(' '))}</p></blockquote>`); continue;
    }
    const ul = /^\s*[-*+]\s+/, ol = /^\s*[0-9۰-۹]+[.)]\s+/;
    if (ul.test(line) || ol.test(line)) {
      const tag = ol.test(line) ? 'ol' : 'ul', re = tag === 'ol' ? ol : ul;
      const items = [];
      while (i < lines.length && re.test(lines[i])) {
        let item = lines[i++].replace(re, '');
        while (i < lines.length && lines[i].trim() && !ul.test(lines[i]) && !ol.test(lines[i]) && /^\s{2,}/.test(lines[i])) item += ' ' + lines[i++].trim();
        items.push(`<li>${inline(item)}</li>`);
      }
      out.push(`<${tag}>${items.join('')}</${tag}>`); continue;
    }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\s*[-*+]\s|\s*[0-9۰-۹]+[.)]\s|\s*>|\s*<|\s*\|)/.test(lines[i])) buf.push(lines[i++].trim());
    if (!buf.length) { buf.push(lines[i++].trim()); }
    out.push(`<p>${inline(buf.join(' '))}</p>`);
  }
  return out.join('\n');
}

/** خروجیِ فشرده برای مدل: JSONِ بی‌فاصله + سقفِ طول. */
export function compact(data, maxChars = 20000) {
  const s = typeof data === 'string' ? data : JSON.stringify(data);
  return s.length > maxChars ? s.slice(0, maxChars) + `…[بریده شد: ${s.length - maxChars} نویسهٔ دیگر؛ با max_chars بیشتر یا فیلتر دوباره بخواه]` : s;
}

export function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, '').toLowerCase(); } catch { return ''; }
}
