// تستِ سرتاسریِ سرورِ MCP روی وردپرسِ ساختگی (فقط توسعه):
//   node dev/mock_wp.mjs 8766 &   سپس   CWP_HOME=<tmp> CWP_BROWSER_PATH=<chromium> node dev/test_mcp.mjs
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'plugin');
const srv = spawn(process.execPath, [join(root, 'server', 'index.mjs')], { stdio: ['pipe', 'pipe', 'inherit'], env: process.env });
const rl = createInterface({ input: srv.stdout });
const waiting = new Map();
let id = 0;
rl.on('line', l => {
  let m; try { m = JSON.parse(l); } catch { console.error('NON-JSON STDOUT:', l); process.exitCode = 1; return; }
  waiting.get(m.id)?.(m); waiting.delete(m.id);
});
const rpc = (method, params) => new Promise(res => { const i = ++id; waiting.set(i, res); srv.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: i, method, params }) + '\n'); });
const call = async (name, args) => {
  const r = await rpc('tools/call', { name, arguments: args });
  const text = r.result.content.find(c => c.type === 'text')?.text;
  const hasImg = r.result.content.some(c => c.type === 'image');
  const tag = r.result.isError ? 'ERR' : 'OK ';
  console.log(`\n== ${tag} ${name} ${hasImg ? '[image]' : ''}\n${text.slice(0, 1800)}`);
  try { return { err: r.result.isError, data: JSON.parse(text) }; } catch { return { err: r.result.isError, data: text }; }
};

const only = process.argv.slice(2);
const want = n => !only.length || only.includes(n);
const init = await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
console.log('init', init.result.serverInfo, init.result.protocolVersion);
srv.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
const tl = await rpc('tools/list', {});
console.log('tools:', tl.result.tools.map(t => t.name).join(', '), '| schema bytes:', JSON.stringify(tl.result.tools).length);

if (want('wp')) {
  await call('sites', {});
  await call('sites', { site: 'test', prompt: 'دسته' });
  await call('wp_check', { site: 'test' });
  await call('wp_find', { site: 'test', query: 'لوله' });
  await call('wp_get', { site: 'test', type: 'post', id: 11 });
  await call('wp_get', { site: 'test', type: 'product_cat', id: 31, format: 'html' });
  await call('wp_internal_links', { site: 'test', keywords: ['ورق استیل 304', 'لوله استیل', 'استیل طلایی'] });
  const saved = await call('wp_save_post', { site: 'test', title: 'لوله استیل صنعتی', categories: ['آموزش', 'دسته تازه'],
    content: '# لوله استیل صنعتی\n\nمقدمه با **پررنگ** و [لینک](https://x.com).\n\n![عکس لوله](pipe.png)\n\n## انواع\n\n- درزدار\n- بدون درز\n\n| سایز | وزن |\n|---|---|\n| 1 | 2 |\n',
    seo: { title: 'لوله استیل', description: 'توضیح', focus_keyword: 'لوله استیل' } });
  await call('wp_get', { site: 'test', type: 'post', id: saved.data.id, format: 'html' });
  await call('wp_save_post', { site: 'test', title: 'دومی', content: 'متن ساده', featured_image: 'none' });
  await call('wp_save_post', { site: 'test', title: 'سومی', content: 'متن' }); // پیش‌فرض: تصویرِ شاخصِ پوشه (باید reuse شود)
  await call('wp_save_term', { site: 'test', id: 31, description: '## انواع لوله\n\nمتنِ **جدید** دسته.', seo: { title: 'خرید لوله استیل' } });
  await call('wp_link_opportunities', { site: 'test', target_url: saved.data.link, keywords: ['لوله استیل'] });
  await call('wp_add_link', { site: 'test', id: 11, anchor: 'لوله استیل', url: saved.data.link });
  await call('wp_add_link', { site: 'test', id: 11, anchor: 'لوله استیل', url: saved.data.link, dry_run: false });
  await call('wp_add_link', { site: 'test', id: 12, anchor: 'لوله استیل', url: saved.data.link }); // فقط داخلِ لینک هست → skipped
  await call('wp_api', { site: 'test', path: 'wp/v2/posts', query: { per_page: 2, _fields: 'id,title' } });
  await call('wp_api', { site: 'test', path: 'wp/v2/nope' });
  await call('files_list', { folder: 'backups' });
  await call('file_read', { path: 'images/pipe.png' });
}
if (want('browser')) {
  const base = 'http://127.0.0.1:8766';
  await call('page_outline', { url: base + '/competitor' });
  await call('page_outline', { url: base + '/competitor', level: 'sections' });
  await call('page_outline', { urls: [base + '/competitor', base + '/competitor?2'] });
  await call('browser_run', { url: base + '/competitor', script: 'return await page.$$eval("h2", e => e.map(x => x.textContent))', screenshot: true });
  await call('http_fetch', { url: base + '/competitor', mode: 'outline' });
  await call('competitor_research', { keyword: 'لوله استیل', site: 'test', n: 2, extra_urls: [base + '/competitor'], suggest: false, engine: 'bing' });
}
srv.stdin.end();
