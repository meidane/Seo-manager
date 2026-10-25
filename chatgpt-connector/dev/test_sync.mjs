// تستِ همگام‌سازی (فقط توسعه): CWP_HOME=<پوشهٔ یک کامپیوتر> node dev/test_sync.mjs <action> [args]
// actions: setup <url> <token> | add-site <key> | edit-prompt <key> <title> | add-file <key> <name> <text> | del-file <rel> | del-site <key> | sync | dump
import { writeFileSync, mkdirSync, unlinkSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
const C = await import('../plugin/server/config.mjs');
const Y = await import('../plugin/server/sync.mjs');
const [act, a, b, c] = process.argv.slice(2);
if (act === 'setup') Y.saveSyncSettings({ url: a, token: b, interval: 5, enabled: true });
if (act === 'add-site') C.updateConfig(d => { d.sites.push(C.newSite({ key: a, url: `https://${a}.ir`, user: 'u', password: 'p' })); });
if (act === 'edit-prompt') C.updateConfig(d => { d.sites.find(s => s.key === a).prompts[0].title = b; });
if (act === 'add-file') { const p = join(C.HOME, 'files', a, b); mkdirSync(dirname(p), { recursive: true }); writeFileSync(p, c); }
if (act === 'del-file') unlinkSync(join(C.HOME, a));
if (act === 'del-site') C.updateConfig(d => { d.sites = d.sites.filter(s => s.key !== a); });
if (act === 'sync') console.log(JSON.stringify(await Y.syncNow('manual')));
if (act === 'dump') {
  const d = C.rawConfig();
  const files = existsSync(join(C.HOME, 'files')) ? readdirSync(join(C.HOME, 'files'), { recursive: true }).filter(f => /\.\w+$/.test(f)) : [];
  console.log(JSON.stringify({ sites: d.sites.map(s => `${s.key}:${s.prompts[0]?.title}`), deleted: d.deleted.length, files }));
}
process.exit(0);
