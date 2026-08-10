/* tasks.js — مودال تسک (built-in + انواع سفارشی)، لیست/کانبان، عملیات گروهی.
   از هر صفحه‌ای کار می‌کند: داده‌ی فرم را یک‌بار از /tasks/api/formdata/ می‌گیرد.
   به App (app.js) و TASK_SCHEMA (task-schema.js) وابسته است. */
(function () {
  'use strict';
  const S = window.TASK_SCHEMA;
  const ALWAYS = ['project', 'assignee', 'task_type', 'title', 'planned_date', 'status', 'priority', 'description', 'estimate_minutes'];

  let cfg = null;
  async function ensureCfg() {
    if (!cfg) cfg = await App.fetchJSON('/tasks/api/formdata/');
    return cfg;
  }

  const opt = (v, l, sel) => `<option value="${v}"${String(v) === String(sel) ? ' selected' : ''}>${l}</option>`;
  function field(id, label, inner) {
    return `<div class="field" data-f="${id}"><label>${label}</label>${inner}</div>`;
  }

  // همه‌ی انواع از رکوردهای TaskTypeDef (built-in + سفارشی). اگر seed نشده باشد، از typeChoices می‌سازد.
  function typeList() {
    if (cfg.customTypes && cfg.customTypes.length) return cfg.customTypes;
    return cfg.typeChoices.map(([k, l]) => ({ id: 'b:' + k, name: l, builtin_key: k, fields: [] }));
  }
  function findType(v) { return typeList().find((t) => String(t.id) === String(v)); }
  function typeOptions(sel) {
    return typeList().map((t) => opt(t.id, (t.icon ? t.icon + ' ' : '') + t.name, sel)).join('');
  }

  function modalHtml(t) {
    t = t || {};
    const _bt = typeList().find((x) => x.builtin_key === (t.type || 'publish'));
    const typeSel = t.type_def || (_bt ? _bt.id : (typeList()[0] || {}).id);
    return `
    <div class="modal-h"><h3>${t.id ? 'ویرایش تسک' : 'تسک جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
    <div class="modal-b" id="tform">
      ${reviewNotesHtml(t)}
      <div class="grid3">
        ${field('project', 'پروژه', `<select id="f-project">${cfg.projects.map(([v, l]) => opt(v, l, t.project_id)).join('')}</select>`)}
        ${field('assignee', 'مسئول', `<select id="f-assignee"><option value="">—</option>${cfg.colleagues.map(([v, l]) => opt(v, l, t.assignee_id)).join('')}</select>`)}
        ${field('task_type', 'نوع تسک', `<select id="f-task_type">${typeOptions(typeSel)}</select>`)}
      </div>
      <div class="grid2">
        ${field('update_type', 'زیرنوع', `<select id="f-update_type"><option value="">—</option><option value="minor"${t.update_type === 'minor' ? ' selected' : ''}>سطحی</option><option value="major"${t.update_type === 'major' ? ' selected' : ''}>اساسی</option></select>`)}
        ${field('priority', 'اولویت', `<select id="f-priority"><option value="low">کم</option><option value="med">متوسط</option><option value="high">زیاد</option></select>`)}
      </div>
      ${field('title', 'عنوان', `<input id="f-title" class="input" value="${esc(t.title)}">`)}
      <div class="grid3">
        ${field('planned_date', 'تاریخ برنامه (شمسی)', `<input id="f-planned_date" class="input jdate" dir="ltr" readonly placeholder="۱۴۰۵/۰۵/۱۵" value="${t.planned_date_fa || ''}">`)}
        ${field('status', 'وضعیت', `<select id="f-status"><option value="todo">در انتظار</option><option value="doing">در حال انجام</option><option value="done">انجام شده</option></select>`)}
        ${field('estimate_minutes', 'تخمین زمان (دقیقه)', `<input id="f-estimate_minutes" class="input" type="number" dir="ltr" placeholder="۶۰" value="${t.estimate_minutes || ''}">`)}
      </div>

      ${recurBarHtml(t)}
      ${t.id ? '<div id="kpi-box" style="display:none;margin-top:8px"></div>' : ''}

      <!-- فیلدهای سفارشی نوع (داینامیک) -->
      <div id="custom-fields" style="display:none"></div>

      <!-- فیلدهای built-in محتوایی -->
      <div class="grid2">
        ${field('word_count', 'تعداد کلمه', `<input id="f-word_count" class="input" type="number" value="${t.word_count || ''}">`)}
        ${field('seo_title', 'عنوان سئو', `<input id="f-seo_title" class="input" value="${esc(t.seo_title)}">`)}
      </div>
      ${field('keywords', 'کلمات کلیدی', `<input id="f-keywords" class="input" value="${esc(t.keywords)}">`)}
      ${field('lsi_keywords', 'کلمات LSI', `<input id="f-lsi_keywords" class="input" value="${esc(t.lsi_keywords)}">`)}
      ${field('current_rank', 'جایگاه فعلی', `<input id="f-current_rank" class="input" type="number" value="${t.current_rank || ''}">`)}
      ${field('published_url', 'لینک انتشار', `<input id="f-published_url" class="input" dir="ltr" value="${esc(t.published_url)}">`)}
      ${field('source_url', 'آدرس مطلب فعلی', `<input id="f-source_url" class="input" dir="ltr" value="${esc(t.source_url)}">`)}
      <div class="grid2">
        ${field('media_name', 'نام رسانه', `<input id="f-media_name" class="input" value="${esc(t.media_name)}">`)}
        ${field('media_cost', 'هزینه رپورتاژ', `<input id="f-media_cost" class="input" type="number" value="${t.media_cost || ''}">`)}
      </div>
      <div class="grid2">
        ${field('anchor_text', 'انکر تکست', `<input id="f-anchor_text" class="input" value="${esc(t.anchor_text)}">`)}
        ${field('target_url', 'لینک مقصد', `<input id="f-target_url" class="input" dir="ltr" value="${esc(t.target_url)}">`)}
      </div>
      <div class="grid2">
        ${field('link_type', 'نوع لینک', `<select id="f-link_type"><option value="">—</option><option value="comment">کامنت</option><option value="profile">پروفایل</option><option value="forum">فروم</option><option value="directory">دایرکتوری</option><option value="social">سوشال</option><option value="other">سایر</option></select>`)}
        ${field('link_count', 'تعداد لینک', `<input id="f-link_count" class="input" type="number" value="${t.link_count || ''}">`)}
      </div>
      ${field('description', 'توضیحات', `<textarea id="f-description" class="rich-editor" rows="3">${esc(t.description)}</textarea>`)}

      <!-- گزارش کار (فقط برای تسک موجود) -->
      ${t.id ? `<div class="report-sec">
        <label style="font-weight:700">گزارش</label>
        <textarea id="f-report" class="rich-editor" rows="3"></textarea>
        <div style="margin-top:6px;display:flex;gap:8px;align-items:center">
          <button type="button" class="btn btn-sm btn-p" id="report-send">ارسال گزارش</button>
          <button type="button" class="btn btn-sm" id="report-cancel" style="display:none">لغو ویرایش</button>
        </div>
        <div id="report-list" class="report-list"></div>
      </div>` : ''}
    </div>
    <div class="modal-f">
      <button class="btn btn-p" id="t-save">ذخیره</button>
      ${t.id ? '' : '<button class="btn" id="t-save-next">ذخیره و ایجاد بعدی</button>'}
      <button class="btn" onclick="App.closeModal()">انصراف</button>
      ${t.id ? '<button class="btn" id="t-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}
    </div>`;
  }

  function esc(v) { return (v == null ? '' : String(v)).replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  // ── نوار تکرار (فقط تسک جدید؛ برای تسکِ موجودِ تکرارشونده فقط بنر حذف سری) ──
  function recurBarHtml(t) {
    if (t.id) {
      if (t.recurrence) return `<div class="rec-bar" style="color:var(--text-dim)">🔁 این تسک بخشی از یک سری تکرار است.
        <button type="button" class="btn btn-sm" id="rec-del" data-id="${t.recurrence}" style="color:var(--danger)">حذف کل سریِ آینده</button></div>`;
      return '';
    }
    const wk = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];  // شنبه=۰ .. جمعه=۶
    return `<div class="rec-wrap"><label>تکرار</label>
      <div class="rec-bar" id="rec-opts">
        <span class="rec-opt on" data-freq="">یک‌بار</span>
        <span class="rec-opt" data-freq="daily">روزانه</span>
        <span class="rec-opt" data-freq="weekly">هفتگی</span>
        <span class="rec-opt" data-freq="monthly">ماهانه</span>
      </div>
      <div class="rec-bar" id="rec-cfg" style="display:none">
        <label style="margin:0">هر</label><input class="input" id="rec-interval" type="number" dir="ltr" value="1" style="max-width:60px">
        <b id="rec-unit"></b>
        <span id="rec-weekdays" style="display:none;gap:4px">${wk.map((w, i) => `<span class="rec-opt" data-wd="${i}">${w}</span>`).join('')}</span>
        <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer"><input type="checkbox" id="rec-skip" checked style="width:auto"> رد کردن تعطیلات</label>
      </div></div>`;
  }

  function wireRecur() {
    const opts = document.getElementById('rec-opts');
    if (!opts) return;
    const cfg = document.getElementById('rec-cfg');
    const units = { daily: 'روز', weekly: 'هفته', monthly: 'ماه' };
    opts.addEventListener('click', (e) => {
      const o = e.target.closest('.rec-opt'); if (!o) return;
      opts.querySelectorAll('.rec-opt').forEach((x) => x.classList.remove('on'));
      o.classList.add('on');
      const f = o.dataset.freq;
      cfg.style.display = f ? 'flex' : 'none';
      document.getElementById('rec-unit').textContent = units[f] || '';
      document.getElementById('rec-weekdays').style.display = (f === 'weekly') ? 'flex' : 'none';
    });
    document.getElementById('rec-weekdays').addEventListener('click', (e) => {
      const w = e.target.closest('.rec-opt'); if (w) w.classList.toggle('on');
    });
  }

  // ── نمایشِ فقط‌خواندنیِ KPIها در مودال (کارمند ببیند طبق چه سنجیده می‌شود) ──
  async function initKpis(id) {
    const box = document.getElementById('kpi-box'); if (!box) return;
    try {
      const d = await App.fetchJSON(`/tasks/api/${id}/kpis/`);
      if (!d.has) { box.style.display = 'none'; return; }
      box.style.display = '';
      box.innerHTML = `<label style="font-weight:700">شاخص‌های کیفیت (KPI)${d.cap ? ` — امتیاز: ${d.total}/${d.cap}` : ''}</label>` +
        d.kpis.map((k) => `<div class="kpi-item"><div class="kpi-head"><b>${esc(k.title)}</b>
          <span class="tag t-mute">سقف ${k.cap}</span>${k.given != null ? `<span class="tag t-ok">امتیاز: ${k.given}</span>` : ''}
          ${k.description ? `<span class="kpi-info" title="${esc(k.description)}">ℹ️</span>` : ''}</div>
          ${k.has_checklist ? `<div class="kpi-items">${k.items.map((it) => `<div class="kpi-ci"><span>${esc(it.title)} <b>(${it.score})</b></span></div>`).join('')}</div>` : ''}</div>`).join('');
    } catch (_) {}
  }

  // ── جعبه‌ی «موارد نیاز به اصلاح» بالای مودال + تاریخچه (جدیدترین باز، قبلی‌ها جمع) ──
  function reviewNotesHtml(t) {
    const ns = (t && t.review_notes) || [];
    if (!ns.length) return '';
    // note از سرور با clean_html پاکسازی شده؛ درج مستقیم HTML امن است
    const item = (n, i) => `<div class="fixnote-item" data-fix-item${i > 0 ? ' style="display:none"' : ''}>
        <div class="fixnote-meta">${esc(n.author)}${n.author ? ' · ' : ''}${esc(n.when)}${i === 0 ? ' <b>(آخرین)</b>' : ''}</div>
        <div class="rich">${n.note}</div></div>`;
    const more = ns.length > 1
      ? `<button type="button" class="mini" id="fix-hist-toggle" style="margin-top:6px">نمایش سوابق قبلی (${ns.length - 1})</button>` : '';
    return `<div class="fixnote-box"><div class="fixnote-h">⚠ موارد نیاز به اصلاح</div>${ns.map(item).join('')}${more}</div>`;
  }

  // ── رندر فیلدهای سفارشی یک نوع ──
  function renderCustom(t, values) {
    const box = document.getElementById('custom-fields');
    if (!t || !t.fields || !t.fields.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
    values = values || {};
    box.style.display = '';
    box.innerHTML = t.fields.map((f) => {
      const v = values[f.key] != null ? values[f.key] : '';
      let input;
      if (f.kind === 'textarea') input = `<textarea class="cf" data-key="${f.key}" rows="2" placeholder="${esc(f.placeholder)}">${esc(v)}</textarea>`;
      else if (f.kind === 'checkbox') input = `<label style="display:flex;align-items:center;gap:8px;margin:0"><input type="checkbox" class="cf" data-key="${f.key}" ${v ? 'checked' : ''} style="width:auto"> ${esc(f.label)}</label>`;
      else if (f.kind === 'select') input = `<select class="cf" data-key="${f.key}"><option value="">—</option>${f.options.map((o) => opt(o, o, v)).join('')}</select>`;
      else if (f.kind === 'number') input = `<input type="number" class="cf input" data-key="${f.key}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      else input = `<input type="text" class="cf input" data-key="${f.key}" dir="${f.kind === 'url' ? 'ltr' : 'rtl'}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      if (f.kind === 'checkbox') return `<div class="field" data-cf>${input}</div>`;
      return `<div class="field" data-cf><label>${esc(f.label)}${f.required ? ' *' : ''}</label>${input}</div>`;
    }).join('');
  }

  function applyVisibility(loadedCustom) {
    const ty = findType(document.getElementById('f-task_type').value);
    const bk = ty ? ty.builtin_key : '';
    const on = bk ? S.fieldsFor(bk) : new Set();
    document.querySelectorAll('#tform [data-f]').forEach((el) => {
      const f = el.dataset.f;
      if (ALWAYS.includes(f)) return;
      if (f === 'update_type') { el.style.display = (bk === 'update') ? '' : 'none'; return; }
      el.style.display = on.has(f) ? '' : 'none';
    });
    renderCustom(ty, loadedCustom);
  }

  function collect() {
    if (window.RichText) RichText.save();  // TinyMCE → textarea
    const g = (id) => { const e = document.getElementById(id); return e ? e.value : ''; };
    const ty = findType(g('f-task_type'));
    const bk = ty ? ty.builtin_key : '';
    const p = {
      project: g('f-project'), assignee: g('f-assignee'),
      task_type: bk || 'other',
      type_def: (ty && typeof ty.id === 'number') ? ty.id : null,
      update_type: g('f-update_type'), priority: g('f-priority'), title: g('f-title'),
      planned_date: g('f-planned_date'), status: g('f-status'), word_count: g('f-word_count'),
      seo_title: g('f-seo_title'), keywords: g('f-keywords'), lsi_keywords: g('f-lsi_keywords'),
      current_rank: g('f-current_rank'), published_url: g('f-published_url'), estimate_minutes: g('f-estimate_minutes'),
      source_url: g('f-source_url'), media_name: g('f-media_name'), media_cost: g('f-media_cost'),
      anchor_text: g('f-anchor_text'), target_url: g('f-target_url'), link_type: g('f-link_type'),
      link_count: g('f-link_count'), description: g('f-description'),
    };
    if (ty && ty.fields && ty.fields.length) {
      const custom = {};
      document.querySelectorAll('#custom-fields .cf').forEach((el) => {
        custom[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
      });
      p.custom = custom;
    }
    // تکرار (فقط تسک جدید)
    const recOpts = document.getElementById('rec-opts');
    if (recOpts) {
      const freq = recOpts.querySelector('.rec-opt.on').dataset.freq;
      if (freq) {
        p.recurrence = {
          freq, interval: +document.getElementById('rec-interval').value || 1,
          skip_holidays: document.getElementById('rec-skip').checked,
          weekdays: [...document.querySelectorAll('#rec-weekdays .rec-opt.on')].map((x) => +x.dataset.wd),
        };
      }
    }
    return p;
  }

  // ── بخش «گزارش» ته مودال تسک (ادیتور TinyMCE + لیست ساده + ویرایش/حذف) ──
  function reportItemHtml(r) {
    const tools = r.mine ? `<span class="report-tools">
        <i class="rep-edit" data-id="${r.id}" title="ویرایش">✏️</i>
        <i class="rep-del" data-id="${r.id}" title="حذف">🗑</i></span>` : '';
    return `<div class="report-item" data-id="${r.id}">
        <div class="report-meta">${esc(r.author)}${r.author ? ' · ' : ''}${esc(r.at)}${tools}</div>
        <div class="rich report-body">${r.body}</div></div>`;
  }

  function initReports(id) {
    if (window.RichText) RichText.init('#f-report');
    let editingId = null;
    const listEl = document.getElementById('report-list');
    const sendBtn = document.getElementById('report-send');
    const cancelBtn = document.getElementById('report-cancel');
    if (!listEl || !sendBtn) return;
    const getBody = () => { if (window.RichText) RichText.save(); const e = document.getElementById('f-report'); return e ? e.value : ''; };
    const setBody = (html) => {
      const e = document.getElementById('f-report'); if (!e) return;
      const ed = window.tinymce && window.tinymce.get(e.id);
      if (ed) ed.setContent(html || ''); else e.value = html || '';
    };
    function reset() { editingId = null; setBody(''); sendBtn.textContent = 'ارسال گزارش'; cancelBtn.style.display = 'none'; }
    async function load() {
      try {
        const d = await App.fetchJSON(`/tasks/api/${id}/comments/`);
        listEl.innerHTML = d.comments.length
          ? d.comments.map(reportItemHtml).join('')
          : '<div class="report-empty">هنوز گزارشی ثبت نشده</div>';
      } catch (_) {}
    }
    sendBtn.onclick = async () => {
      const body = getBody().trim();
      if (!body || body === '<p></p>') { App.toast('متن گزارش لازم است', 'warn'); return; }
      try {
        if (editingId) await App.fetchJSON(`/tasks/api/comment/${editingId}/`, { method: 'PATCH', body: { body } });
        else await App.fetchJSON(`/tasks/api/${id}/comments/`, { method: 'POST', body: { body } });
        reset(); App.toast('گزارش ثبت شد', 'ok'); load();
      } catch (_) {}
    };
    cancelBtn.onclick = reset;
    listEl.onclick = async (e) => {
      const ed = e.target.closest('.rep-edit');
      const del = e.target.closest('.rep-del');
      if (ed) {
        const item = ed.closest('.report-item');
        editingId = ed.dataset.id;
        setBody(item.querySelector('.report-body').innerHTML);
        sendBtn.textContent = 'ذخیره ویرایش'; cancelBtn.style.display = '';
        document.getElementById('f-report').scrollIntoView({ block: 'center' });
      }
      if (del && await App.confirm('این گزارش حذف شود؟')) {
        try { await App.fetchJSON(`/tasks/api/comment/${del.dataset.id}/`, { method: 'DELETE' }); if (editingId === del.dataset.id) reset(); load(); } catch (_) {}
      }
    };
    load();
  }

  async function openTask(id, prefill) {
    await ensureCfg();
    if (!id && (!cfg.projects || !cfg.projects.length)) {
      App.toast('ابتدا یک پروژه بساز؛ تسک بدون پروژه ثبت نمی‌شود.', 'warn');
      return;
    }
    let data = prefill || {};
    if (id) { try { data = await App.fetchJSON(`/tasks/api/${id}/`); } catch (_) { return; } }
    App.openModal(modalHtml(data));
    if (data.status) document.getElementById('f-status').value = data.status;
    if (data.priority) document.getElementById('f-priority').value = data.priority;
    else document.getElementById('f-priority').value = 'med';
    const loaded = data.custom || {};
    document.getElementById('f-task_type').addEventListener('change', () => applyVisibility(loaded));
    applyVisibility(loaded);
    if (window.RichText) RichText.init('#f-description');  // ادیتور غنی توضیحات
    const histBtn = document.getElementById('fix-hist-toggle');  // باز کردن سوابق قبلی نیاز به اصلاح
    if (histBtn) histBtn.onclick = () => {
      document.querySelectorAll('[data-fix-item]').forEach((el, i) => { if (i > 0) el.style.display = ''; });
      histBtn.style.display = 'none';
    };
    wireRecur();               // نوار تکرار (تسک جدید)
    if (id) { initReports(id); initKpis(id); }  // گزارش + نمایش KPI (تسک موجود)
    const recDel = document.getElementById('rec-del');
    if (recDel) recDel.onclick = async () => {
      if (await App.confirm('کلِ سریِ آینده‌ی این تکرار حذف شود؟ (تسک‌های انجام‌شده می‌مانند)')) {
        try { await App.fetchJSON(`/tasks/api/recurrence/${recDel.dataset.id}/`, { method: 'DELETE' }); App.closeModal(); location.reload(); } catch (_) {}
      }
    };

    let saving = false;  // جلوگیری از دوبار/سه‌بار کلیک که چند تسک می‌ساخت (#۲)
    const save = async (again) => {
      if (saving) return;
      const payload = collect();
      if (!payload.title || !payload.project) { App.toast('عنوان و پروژه لازم است', 'warn'); return; }
      saving = true;
      const btns = ['t-save', 't-save-next'].map((i) => document.getElementById(i)).filter(Boolean);
      btns.forEach((b) => { b.disabled = true; b.classList.add('loading'); });
      try {
        if (id) await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: payload });
        else await App.fetchJSON('/tasks/api/', { method: 'POST', body: payload });
        App.toast('ذخیره شد', 'ok');
        if (again) { openTask(null); }
        else { App.closeModal(); setTimeout(() => location.reload(), 250); }
      } catch (_) {
        saving = false;
        btns.forEach((b) => { b.disabled = false; b.classList.remove('loading'); });
      }
    };
    document.getElementById('t-save').onclick = () => save(false);
    const n = document.getElementById('t-save-next'); if (n) n.onclick = () => save(true);
    const d = document.getElementById('t-del');
    if (d) d.onclick = async () => { if (await App.confirm('این تسک حذف شود؟')) { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'DELETE' }); App.closeModal(); location.reload(); } };
  }
  window.openTask = openTask;

  // ── بازبینی: نوشتن موارد نیاز به اصلاح (TinyMCE) ──
  async function openFixModal(id) {
    App.openModal(
      `<div class="modal-h"><h3>موارد نیاز به اصلاح</h3><button class="x" onclick="App.closeModal()">×</button></div>
       <div class="modal-b"><p style="color:var(--text-dim);font-size:12px;margin-bottom:8px">توضیح بده چه چیزی باید اصلاح شود (بولد و عکس هم می‌توانی بگذاری). با ثبت، تسک از حالت انجام‌شده خارج و برای اصلاح برمی‌گردد.</p>
         <textarea id="fix-note" class="rich-editor" rows="5"></textarea></div>
       <div class="modal-f"><button class="btn btn-p" id="fix-save">ثبت و بازگرداندن برای اصلاح</button><button class="btn" onclick="App.closeModal()">انصراف</button></div>`);
    if (window.RichText) RichText.init('#fix-note');
    document.getElementById('fix-save').onclick = async () => {
      if (window.RichText) RichText.save();
      const note = document.getElementById('fix-note').value;
      try {
        await App.fetchJSON(`/tasks/api/${id}/review/`, { method: 'PATCH', body: { review_status: 'needs_fix', review_note: note } });
        App.toast('برای اصلاح علامت خورد', 'ok'); App.closeModal(); setTimeout(() => location.reload(), 300);
      } catch (_) {}
    };
  }
  window.openFixModal = openFixModal;

  // ── کلیک روی تگ «نیاز به اصلاح» → مودالِ تسک باز می‌شود؛ موارد و تاریخچه بالای همان مودال
  //    نمایش داده می‌شوند (دیگر مودال‌روی‌مودال نداریم). ──
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-fix-note]');
    if (t) { e.stopImmediatePropagation(); e.preventDefault(); openTask(t.dataset.fixNote); }
  });

  // ── ویرایشِ زندهٔ جدول تسک‌ها (بدون دکمهٔ ذخیره) ──
  document.addEventListener('change', async (e) => {
    const el = e.target.closest('.tx-inline'); if (!el) return;
    const tr = el.closest('tr'); if (!tr) return;
    try { await App.fetchJSON(`/tasks/api/${tr.dataset.id}/`, { method: 'PATCH', body: { [el.dataset.f]: el.value } }); App.toast('ذخیره شد', 'ok'); }
    catch (_) {}
  });

  // ── تغییر سریع وضعیت از دراپ‌داون ردیف ──
  document.addEventListener('change', async (e) => {
    if (e.target.matches('.row-status')) {
      const sel = e.target;
      try {
        await App.fetchJSON(`/tasks/api/${sel.dataset.id}/status/`, { method: 'PATCH', body: { status: sel.value } });
        sel.className = 'row-status st-' + sel.value;
        App.toast('وضعیت به‌روز شد', 'ok');
      } catch (_) {}
    }
  });

  // ── باز کردن مودال (دکمه‌ها و ردیف‌ها/چیپ‌ها) ──
  document.addEventListener('click', (e) => {
    if (e.target.closest('#new-task')) { e.preventDefault(); openTask(null); return; }
    const row = e.target.closest('[data-open-task]');
    if (row && !e.target.closest('a,select,input,button')) openTask(row.dataset.openTask);
  });

  // ── عملیات گروهی ──
  const selected = () => Array.from(document.querySelectorAll('.row-check:checked')).map((c) => c.dataset.id);
  document.addEventListener('change', (e) => {
    if (e.target.matches('.row-check, #check-all')) {
      if (e.target.id === 'check-all') document.querySelectorAll('.row-check').forEach((c) => (c.checked = e.target.checked));
      const bar = document.getElementById('bulkbar');
      if (bar) { const n = selected().length; bar.style.display = n ? 'flex' : 'none'; const c = document.getElementById('bulk-count'); if (c) c.textContent = n; }
    }
  });
  async function bulk(action, extra) {
    const ids = selected(); if (!ids.length) return;
    try { await App.fetchJSON('/tasks/api/bulk/', { method: 'POST', body: Object.assign({ ids, action }, extra) }); App.toast('انجام شد', 'ok'); setTimeout(() => location.reload(), 300); }
    catch (_) {}
  }
  window.TaskBulk = { shift: (d) => bulk('shift_date', { days: d, skip_holidays: true }), done: () => bulk('mark_done', {}) };

  // ── تایمر تسک (ستون «زمان» لیست) ──
  function fmtMin(m) { m = Math.max(0, Math.round(m)); const h = Math.floor(m / 60), mm = m % 60; return h ? `${h}:${String(mm).padStart(2, '0')}` : `${mm}د`; }
  document.querySelectorAll('.timer-cell').forEach((cell) => {
    const id = cell.dataset.id;
    const val = cell.querySelector('.tval');
    const btn = cell.querySelector('.tbtn');
    const edit = cell.querySelector('.tedit');
    let running = cell.dataset.running === '1';
    let started = cell.dataset.started ? new Date(cell.dataset.started) : null;
    let base = +cell.dataset.spent || 0;
    let ticker = null;
    function render() {
      if (running && started) {
        val.textContent = fmtMin(base + (Date.now() - started.getTime()) / 60000);
        btn.textContent = '⏸'; cell.classList.add('running');
      } else { val.textContent = fmtMin(base); btn.textContent = '▶'; cell.classList.remove('running'); }
    }
    function startTick() { if (!ticker) ticker = setInterval(render, 15000); }
    function stopTick() { if (ticker) { clearInterval(ticker); ticker = null; } }
    if (running) startTick();
    render();
    btn.onclick = async (e) => {
      e.stopPropagation();
      try {
        const d = await App.fetchJSON(`/tasks/api/${id}/timer/`, { method: 'POST', body: { action: running ? 'stop' : 'start' } });
        base = d.spent_minutes; running = d.timer_running; started = d.timer_started ? new Date(d.timer_started) : null;
        running ? startTick() : stopTick();
        render();
        window.dispatchEvent(new CustomEvent('timer-changed'));  // به‌روزرسانی ویجت سراسری
      } catch (_) {}
    };
    if (edit) edit.onclick = async (e) => {
      e.stopPropagation();
      const cur = prompt('زمان کارکرد (دقیقه):', base);
      if (cur === null) return;
      try { const d = await App.fetchJSON(`/tasks/api/${id}/timer/`, { method: 'PATCH', body: { minutes: cur } }); base = d.spent_minutes; render(); } catch (_) {}
    };
  });

})();
