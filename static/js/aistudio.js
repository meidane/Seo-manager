/* aistudio.js — تبِ «AI»ی سینگلِ پروژه (منبعِ واحدِ رندر و تعامل؛ API: aistudio/views.py).
   ۱) اتصالِ سایت/MCP — رمزها write-only (فقط وضعیتِ «تنظیم شده»؛ مقدار هرگز به مرورگر برنمی‌گردد)
   ۲) پرامپتِ عمومیِ پروژه
   ۳) پرامپت‌های اختصاصی (اتصالِ اختیاری به نوعِ تسک) + فایل‌های توضیح‌دار
      (کاربرد: شاخص / داخلِ متن / مرجع / سایر — توضیح و کاربرد با تغییر خودکار ذخیره می‌شود)
   «کپیِ پرامپتِ کامل» = عمومی + اختصاصی + فهرستِ فایل‌ها (برای چسباندن در ChatGPT).
   لودِ تنبل: اولین بازشدنِ تب. هندلرها delegated روی ریشهٔ تب‌اند (پایدار با بازرندر). */
(function () {
  'use strict';
  const root = document.getElementById('ai-tab');
  if (!root) return;
  const API = root.dataset.api, BASE = '/ai/api/';
  let S = null, loading = false;

  const esc = (s) => (s == null ? '' : String(s))
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const $ = (id) => document.getElementById(id);
  const val = (id) => (($(id) || {}).value || '').trim();
  const roleLabel = (k) => ((S.roles.find((r) => r[0] === k) || [])[1] || '');

  async function ensure() {
    if (S || loading) return;
    loading = true;
    try { S = await App.fetchJSON(API); render(); }
    catch (_) { root.innerHTML = '<div class="card glass"><div class="empty" style="padding:30px">بارگذاری ناموفق بود</div></div>'; }
    loading = false;
  }

  // ── رندر ──────────────────────────────────────────────────────────────
  const badge = (has) => has ? '<span class="tag t-ok">✓ تنظیم شده</span>' : '<span class="tag t-mute">تنظیم نشده</span>';

  function connHtml(c) {
    return `
    <section class="card glass ai-card" id="ai-conn">
      <div class="card-h"><h3>اتصالِ سایت و MCP</h3>
        <div class="side-c">${c.updated_fa ? `<span class="ai-meta">آخرین تغییر: ${esc(c.updated_fa)}${c.updated_by ? ' — ' + esc(c.updated_by) : ''}</span>` : ''}</div></div>
      <div class="ai-body">
        <div class="grid2">
          <div class="field"><label>آدرس سایت</label>
            <input class="input" id="ai-site" dir="ltr" placeholder="${esc(S.default_site_url || 'https://example.com')}" value="${esc(c.site_url)}"></div>
          <div class="field"><label>نام کاربریِ وردپرس</label>
            <input class="input" id="ai-user" dir="ltr" autocomplete="off" value="${esc(c.wp_username)}"></div>
        </div>
        <div class="field"><label>رمزِ برنامه (Application Password) ${badge(c.has_wp_password)}</label>
          <div class="ai-secret"><input class="input" id="ai-pass" type="password" dir="ltr" autocomplete="new-password"
            placeholder="${c.has_wp_password ? 'برای تغییر، مقدارِ جدید را وارد کن' : 'xxxx xxxx xxxx xxxx xxxx xxxx'}">
            ${c.has_wp_password ? '<button type="button" class="btn btn-sm" data-clear="wp_password">پاک کردن</button>' : ''}</div>
          <small class="ai-hint">رمزِ اصلیِ وردپرس را وارد نکن — در پیشخوان «کاربران ← شناسنامه ← Application Passwords» یک رمزِ جداگانه بساز (قابلِ لغو، بدونِ امکانِ ورود به پیشخوان).</small></div>
        <div class="grid2">
          <div class="field"><label>آدرسِ MCP <span class="ai-meta">(اختیاری)</span></label>
            <input class="input" id="ai-mcp" dir="ltr" placeholder="https://site.com/wp-json/easy-mcp-ai/v1/mcp" value="${esc(c.mcp_endpoint)}"></div>
          <div class="field"><label>توکنِ MCP ${badge(c.has_mcp_token)}</label>
            <div class="ai-secret"><input class="input" id="ai-token" type="password" dir="ltr" autocomplete="new-password"
              placeholder="${c.has_mcp_token ? 'برای تغییر، مقدارِ جدید را وارد کن' : 'API Token'}">
              ${c.has_mcp_token ? '<button type="button" class="btn btn-sm" data-clear="mcp_token">پاک کردن</button>' : ''}</div></div>
        </div>
        <div class="ai-actions">
          <button type="button" class="btn btn-p" id="ai-conn-save">ذخیرهٔ اتصال</button>
          <button type="button" class="btn" id="ai-test" title="ذخیره و سپس تستِ REST وردپرس از سرورِ پنل">تستِ اتصال</button>
          <span class="ai-test-res" id="ai-test-res"></span>
        </div>
        <small class="ai-hint">🔒 رمزها رمزنگاری‌شده ذخیره می‌شوند و دیگر در صفحه نمایش داده نمی‌شوند؛ هر تغییرشان در گزارشِ فعالیت ثبت می‌شود.</small>
      </div>
    </section>`;
  }

  function generalHtml(c) {
    return `
    <section class="card glass ai-card" id="ai-general">
      <div class="card-h"><h3>پرامپتِ عمومی</h3><div class="side-c"><span class="ai-meta" id="ai-gen-count"></span></div></div>
      <div class="ai-body">
        <small class="ai-hint">هر چیزی که برای همهٔ کارهای این سایت ثابت است: معرفیِ کسب‌وکار و محصولات، مخاطب، لحن و سبکِ نوشتن، کلماتِ ترجیحی/ممنوع، قواعدِ لینک‌دهی، ساختارِ مقاله، نکاتِ برند، رقبا…</small>
        <textarea class="input ai-ta ai-ta-lg" id="ai-gen" dir="auto" placeholder="مثلاً: استیل‌تک تولیدکنندهٔ ورق استیل رنگی است… مخاطب: پیمانکاران و طراحانِ داخلی… لحن: تخصصی ولی ساده…">${esc(c.general_prompt)}</textarea>
        <div class="ai-actions"><button type="button" class="btn btn-p" id="ai-gen-save">ذخیرهٔ پرامپتِ عمومی</button></div>
      </div>
    </section>`;
  }

  const emptyPrompts = () => '<div class="empty ai-pempty" style="padding:22px"><div class="ico">✦</div><h4>هنوز پرامپتِ اختصاصی‌ای نیست</h4></div>';

  function promptsHtml() {
    return `
    <section class="card glass ai-card" id="ai-prompts-card">
      <div class="card-h"><h3>پرامپت‌های اختصاصی</h3><div class="side-c"><button type="button" class="btn btn-sm btn-p" id="ai-add">＋ پرامپتِ جدید</button></div></div>
      <div class="ai-body">
        <small class="ai-hint">برای هر نوع کار یک پرامپت (انتشار، آپدیت، محصول، لینک‌سازیِ داخلی…). اگر به «نوعِ تسک» وصل شود، تسک‌های همان نوع خودکار همین پرامپت را می‌گیرند. برای هر فایل بنویس با آن چه کند — فایل را روی کارت رها کن یا «افزودنِ فایل» بزن.</small>
        <div id="ai-plist">${S.prompts.map(promptHtml).join('') || emptyPrompts()}</div>
      </div>
    </section>`;
  }

  const typeOptions = (sel) => '<option value="">— بدونِ اتصال به نوعِ تسک —</option>' +
    S.task_types.map(([id, n]) => `<option value="${id}"${id === sel ? ' selected' : ''}>${esc(n)}</option>`).join('');
  const roleOptions = (sel) => '<option value="">— کاربرد —</option>' +
    S.roles.map(([k, l]) => `<option value="${k}"${k === sel ? ' selected' : ''}>${esc(l)}</option>`).join('');

  function fileHtml(f) {
    const thumb = f.is_image
      ? `<a href="${esc(f.url)}" target="_blank" rel="noopener" class="ai-thumb"><img src="${esc(f.url)}" alt="" loading="lazy"></a>`
      : `<a href="${esc(f.url)}" target="_blank" rel="noopener" class="ai-thumb ai-thumb-doc">📄</a>`;
    return `<div class="ai-file" data-file="${f.id}">${thumb}
      <div class="ai-file-main">
        <div class="ai-file-top">
          <a href="${esc(f.url)}" target="_blank" rel="noopener" class="ai-fname" title="${esc(f.name)}">${esc(f.name)}</a>
          <span class="ai-fsize">${esc(f.size)}</span>
          <select class="ai-role" data-f="role" title="کاربردِ فایل">${roleOptions(f.role)}</select>
          <button type="button" class="ai-fdel" title="حذفِ فایل">×</button>
        </div>
        <input class="input ai-fdesc" data-f="description" placeholder="با این فایل چه کند؟ مثلاً: «تصویرِ شاخص را با همین سبک و رنگ بساز»" value="${esc(f.description)}">
      </div></div>`;
  }

  function promptHtml(p) {
    return `<div class="ai-prompt" data-prompt="${p.id}">
      <div class="ai-p-head">
        <input class="input ai-p-title" value="${esc(p.title)}" placeholder="عنوان (مثلاً: انتشارِ مقاله)">
        <select class="ai-p-type" title="اتصال به نوعِ تسک">${typeOptions(p.task_type)}</select>
        <button type="button" class="btn btn-sm ai-p-del" title="حذفِ پرامپت">حذف</button>
      </div>
      <textarea class="input ai-ta ai-p-body" dir="auto" placeholder="دستورِ اختصاصیِ این نوع کار…">${esc(p.body)}</textarea>
      <div class="ai-files">${p.files.map(fileHtml).join('')}</div>
      <div class="ai-p-foot">
        <label class="btn btn-sm ai-upload">📎 افزودنِ فایل<input type="file" multiple hidden class="ai-file-input"></label>
        <span class="ai-dirty" hidden>● تغییرِ ذخیره‌نشده</span>
        <span class="ai-spacer"></span>
        <button type="button" class="btn btn-sm ai-copy" title="پرامپتِ عمومی + همین پرامپت + فهرستِ فایل‌ها">📋 کپیِ پرامپتِ کامل</button>
        <button type="button" class="btn btn-sm btn-p ai-p-save">ذخیره</button>
      </div>
    </div>`;
  }

  function render() {
    root.innerHTML = connHtml(S.config) + generalHtml(S.config) + promptsHtml();
    genCount();
  }
  function refreshConn() { const el = $('ai-conn'); if (el) el.outerHTML = connHtml(S.config); }
  function genCount() {
    const t = $('ai-gen'), c = $('ai-gen-count');
    if (t && c) c.textContent = t.value.length.toLocaleString('fa-IR') + ' نویسه';
  }
  function markDirty(card, on) {
    const d = card.querySelector('.ai-dirty');
    if (d) d.hidden = !on;
    card.classList.toggle('dirty', on);
  }

  // ── اتصال ─────────────────────────────────────────────────────────────
  async function saveConn(silent) {
    const body = { site_url: val('ai-site'), wp_username: val('ai-user'), mcp_endpoint: val('ai-mcp') };
    const pw = val('ai-pass'), tk = val('ai-token');
    if (pw) body.wp_password = pw;
    if (tk) body.mcp_token = tk;
    S = await App.fetchJSON(API, { method: 'PATCH', body });
    refreshConn();
    if (!silent) App.toast('اتصال ذخیره شد', 'ok');
  }
  async function clearSecret(name) {
    if (!(await App.confirm('این رمز پاک شود؟'))) return;
    try {
      S = await App.fetchJSON(API, { method: 'PATCH', body: { clear: [name] } });
      refreshConn(); App.toast('پاک شد', 'ok');
    } catch (_) {}
  }
  async function testConn() {
    try {
      await saveConn(true);   // تست همیشه با مقادیرِ ذخیره‌شده
      const res = $('ai-test-res');
      res.className = 'ai-test-res'; res.textContent = 'در حالِ تست…';
      const r = await App.fetchJSON(root.dataset.test, { method: 'POST', body: {} });
      const el = $('ai-test-res');
      el.textContent = r.message; el.classList.add(r.ok ? 'ok' : 'bad');
    } catch (_) {}
  }

  // ── پرامپت‌ها ─────────────────────────────────────────────────────────
  async function saveGeneral() {
    try {
      S = await App.fetchJSON(API, { method: 'PATCH', body: { general_prompt: $('ai-gen').value } });
      App.toast('پرامپتِ عمومی ذخیره شد', 'ok');
    } catch (_) {}
  }
  async function addPrompt() {
    try {
      const p = await App.fetchJSON(root.dataset.promptCreate, { method: 'POST', body: {} });
      S.prompts.push(p);
      const list = $('ai-plist');
      const empty = list.querySelector('.ai-pempty');
      if (empty) empty.remove();
      list.insertAdjacentHTML('beforeend', promptHtml(p));
      const card = list.lastElementChild;
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.querySelector('.ai-p-title').select();
    } catch (_) {}
  }
  const readPrompt = (card) => ({
    title: card.querySelector('.ai-p-title').value,
    body: card.querySelector('.ai-p-body').value,
    task_type: card.querySelector('.ai-p-type').value || null,
  });
  async function savePrompt(card) {
    try {
      const p = await App.fetchJSON(BASE + 'prompts/' + card.dataset.prompt + '/', { method: 'PATCH', body: readPrompt(card) });
      const i = S.prompts.findIndex((x) => x.id === p.id);
      if (i >= 0) S.prompts[i] = p;
      markDirty(card, false); App.toast('ذخیره شد', 'ok');
    } catch (_) {}
  }
  async function delPrompt(card) {
    if (!(await App.confirm('این پرامپت و فایل‌هایش حذف شود؟'))) return;
    try {
      await App.fetchJSON(BASE + 'prompts/' + card.dataset.prompt + '/', { method: 'DELETE' });
      S.prompts = S.prompts.filter((p) => String(p.id) !== card.dataset.prompt);
      card.remove();
      if (!S.prompts.length) $('ai-plist').innerHTML = emptyPrompts();
      App.toast('حذف شد', 'ok');
    } catch (_) {}
  }

  // ── فایل‌ها ───────────────────────────────────────────────────────────
  async function upload(card, files) {
    if (!files || !files.length) return;
    const fd = new FormData();
    [...files].forEach((f) => fd.append('file', f));
    try {
      const r = await App.fetchJSON(BASE + 'prompts/' + card.dataset.prompt + '/files/', { method: 'POST', body: fd });
      const box = card.querySelector('.ai-files');
      r.files.forEach((f) => box.insertAdjacentHTML('beforeend', fileHtml(f)));
      const p = S.prompts.find((x) => String(x.id) === card.dataset.prompt);
      if (p) p.files.push(...r.files);
      if (r.skipped && r.skipped.length) App.toast('بزرگ‌تر از ۲۰ مگابایت بود و رد شد: ' + r.skipped.join('، '), 'warn');
      else if (r.files.length) App.toast('فایل اضافه شد — کاربرد و توضیحش را مشخص کن', 'ok');
    } catch (_) {}
  }
  async function saveFileMeta(el, field, value) {
    try {
      const f = await App.fetchJSON(BASE + 'files/' + el.dataset.file + '/', { method: 'PATCH', body: { [field]: value } });
      S.prompts.forEach((p) => p.files.forEach((x, i) => { if (x.id === f.id) p.files[i] = f; }));
      el.classList.add('saved'); setTimeout(() => el.classList.remove('saved'), 900);
    } catch (_) {}
  }
  async function delFile(el) {
    if (!(await App.confirm('این فایل حذف شود؟'))) return;
    try {
      await App.fetchJSON(BASE + 'files/' + el.dataset.file + '/', { method: 'DELETE' });
      const id = +el.dataset.file;
      S.prompts.forEach((p) => { p.files = p.files.filter((x) => x.id !== id); });
      el.remove();
    } catch (_) {}
  }

  // ── کپیِ پرامپتِ کامل (برای ChatGPT) ─────────────────────────────────
  function fullPrompt(card) {
    const p = readPrompt(card);
    const g = (($('ai-gen') || {}).value || '').trim();
    const site = val('ai-site') || S.default_site_url;
    const files = [...card.querySelectorAll('.ai-file')].map((el) => {
      const name = el.querySelector('.ai-fname').textContent.trim();
      const role = roleLabel(el.querySelector('.ai-role').value);
      const desc = el.querySelector('.ai-fdesc').value.trim();
      return `- ${name}${role ? ` [${role}]` : ''}${desc ? `: ${desc}` : ''}`;
    });
    let out = `پروژه: ${root.dataset.projectName}${site ? ' — ' + site : ''}\n\n`;
    if (g) out += '## دستورالعملِ عمومیِ پروژه\n' + g + '\n\n';
    out += '## ' + (p.title.trim() || 'دستورِ اختصاصی') + '\n' + p.body.trim();
    if (files.length) out += '\n\n## فایل‌های پیوست (جداگانه ضمیمه می‌شوند)\n' + files.join('\n');
    return out;
  }
  async function copyPrompt(card) {
    const text = fullPrompt(card);
    try { await navigator.clipboard.writeText(text); }
    catch (_) {
      const ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (__) {}
      ta.remove();
    }
    App.toast('پرامپتِ کامل کپی شد', 'ok');
  }

  // ── رویدادها (delegated روی ریشه) ─────────────────────────────────────
  root.addEventListener('click', (e) => {
    const t = e.target;
    if (t.closest('#ai-conn-save')) { saveConn(false).catch(() => {}); return; }
    if (t.closest('#ai-test')) { testConn(); return; }
    const clr = t.closest('[data-clear]');
    if (clr) { clearSecret(clr.dataset.clear); return; }
    if (t.closest('#ai-gen-save')) { saveGeneral(); return; }
    if (t.closest('#ai-add')) { addPrompt(); return; }
    const card = t.closest('.ai-prompt');
    if (!card) return;
    if (t.closest('.ai-p-save')) savePrompt(card);
    else if (t.closest('.ai-p-del')) delPrompt(card);
    else if (t.closest('.ai-copy')) copyPrompt(card);
    else if (t.closest('.ai-fdel')) delFile(t.closest('.ai-file'));
  });
  root.addEventListener('input', (e) => {
    if (e.target.id === 'ai-gen') genCount();
    const card = e.target.closest('.ai-prompt');
    if (card && e.target.matches('.ai-p-title, .ai-p-body')) markDirty(card, true);
  });
  root.addEventListener('change', (e) => {
    const card = e.target.closest('.ai-prompt');
    if (!card) return;
    if (e.target.matches('.ai-p-type')) markDirty(card, true);
    if (e.target.matches('.ai-file-input')) { upload(card, e.target.files); e.target.value = ''; return; }
    const f = e.target.closest('.ai-file');
    if (f && e.target.matches('[data-f]')) saveFileMeta(f, e.target.dataset.f, e.target.value);
  });
  // رها کردنِ فایل روی کارتِ پرامپت
  root.addEventListener('dragover', (e) => {
    const c = e.target.closest('.ai-prompt');
    if (c && e.dataTransfer && [...e.dataTransfer.types].includes('Files')) { e.preventDefault(); c.classList.add('drag'); }
  });
  root.addEventListener('dragleave', (e) => {
    const c = e.target.closest('.ai-prompt');
    if (c && !c.contains(e.relatedTarget)) c.classList.remove('drag');
  });
  root.addEventListener('drop', (e) => {
    const c = e.target.closest('.ai-prompt');
    if (!c) return;
    e.preventDefault(); c.classList.remove('drag');
    upload(c, e.dataTransfer.files);
  });

  // لودِ تنبل: اولین کلیک روی تب (یا اگر تب از قبل باز است، مثلاً با #ai)
  document.addEventListener('click', (e) => { if (e.target.closest('.tab[data-tab="ai"]')) ensure(); });
  if (root.classList.contains('on')) ensure();
})();
