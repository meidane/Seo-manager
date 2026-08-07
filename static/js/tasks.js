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

  function typeOptions(sel) {
    let h = cfg.typeChoices.map(([v, l]) => opt(v, l, sel)).join('');
    if (cfg.customTypes.length) {
      h += '<optgroup label="انواع سفارشی">' +
        cfg.customTypes.map((t) => opt('custom:' + t.id, t.name, sel)).join('') + '</optgroup>';
    }
    return h;
  }

  function modalHtml(t) {
    t = t || {};
    const typeSel = t.type_def ? 'custom:' + t.type_def : (t.type || 'publish');
    return `
    <div class="modal-h"><h3>${t.id ? 'ویرایش تسک' : 'تسک جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
    <div class="modal-b" id="tform">
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
        ${field('status', 'وضعیت', `<select id="f-status"><option value="todo">در انتظار</option><option value="doing">در حال انجام</option><option value="done">انجام شده</option><option value="cancelled">لغو شده</option></select>`)}
        ${field('estimate_minutes', 'تخمین زمان (دقیقه)', `<input id="f-estimate_minutes" class="input" type="number" dir="ltr" placeholder="۶۰" value="${t.estimate_minutes || ''}">`)}
      </div>

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
      ${field('description', 'توضیحات', `<textarea id="f-description" rows="3">${esc(t.description)}</textarea>`)}
    </div>
    <div class="modal-f">
      <button class="btn btn-p" id="t-save">ذخیره</button>
      ${t.id ? '' : '<button class="btn" id="t-save-next">ذخیره و ایجاد بعدی</button>'}
      <button class="btn" onclick="App.closeModal()">انصراف</button>
      ${t.id ? '<button class="btn" id="t-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}
    </div>`;
  }

  function esc(v) { return (v == null ? '' : String(v)).replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  // ── رندر فیلدهای سفارشی یک نوع ──
  function renderCustom(typeId, values) {
    const t = cfg.customTypes.find((x) => String(x.id) === String(typeId));
    const box = document.getElementById('custom-fields');
    if (!t) { box.style.display = 'none'; box.innerHTML = ''; return; }
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
    const val = document.getElementById('f-task_type').value;
    const isCustom = val.startsWith('custom:');
    const on = isCustom ? new Set() : S.fieldsFor(val);
    document.querySelectorAll('#tform [data-f]').forEach((el) => {
      const f = el.dataset.f;
      if (ALWAYS.includes(f)) return;
      if (f === 'update_type') { el.style.display = (!isCustom && val === 'update') ? '' : 'none'; return; }
      el.style.display = on.has(f) ? '' : 'none';
    });
    if (isCustom) renderCustom(val.split(':')[1], loadedCustom);
    else { const b = document.getElementById('custom-fields'); b.style.display = 'none'; b.innerHTML = ''; }
  }

  function collect() {
    const g = (id) => { const e = document.getElementById(id); return e ? e.value : ''; };
    const typeVal = g('f-task_type');
    const isCustom = typeVal.startsWith('custom:');
    const p = {
      project: g('f-project'), assignee: g('f-assignee'),
      task_type: isCustom ? 'other' : typeVal,
      type_def: isCustom ? +typeVal.split(':')[1] : null,
      update_type: g('f-update_type'), priority: g('f-priority'), title: g('f-title'),
      planned_date: g('f-planned_date'), status: g('f-status'), word_count: g('f-word_count'),
      seo_title: g('f-seo_title'), keywords: g('f-keywords'), lsi_keywords: g('f-lsi_keywords'),
      current_rank: g('f-current_rank'), published_url: g('f-published_url'), estimate_minutes: g('f-estimate_minutes'),
      source_url: g('f-source_url'), media_name: g('f-media_name'), media_cost: g('f-media_cost'),
      anchor_text: g('f-anchor_text'), target_url: g('f-target_url'), link_type: g('f-link_type'),
      link_count: g('f-link_count'), description: g('f-description'),
    };
    if (isCustom) {
      const custom = {};
      document.querySelectorAll('#custom-fields .cf').forEach((el) => {
        custom[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
      });
      p.custom = custom;
    }
    return p;
  }

  async function openTask(id, prefill) {
    await ensureCfg();
    let data = prefill || {};
    if (id) { try { data = await App.fetchJSON(`/tasks/api/${id}/`); } catch (_) { return; } }
    App.openModal(modalHtml(data));
    if (data.status) document.getElementById('f-status').value = data.status;
    if (data.priority) document.getElementById('f-priority').value = data.priority;
    else document.getElementById('f-priority').value = 'med';
    const loaded = data.custom || {};
    document.getElementById('f-task_type').addEventListener('change', () => applyVisibility(loaded));
    applyVisibility(loaded);

    const save = async (again) => {
      const payload = collect();
      if (!payload.title || !payload.project) { App.toast('عنوان و پروژه لازم است', 'warn'); return; }
      try {
        if (id) await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: payload });
        else await App.fetchJSON('/tasks/api/', { method: 'POST', body: payload });
        App.toast('ذخیره شد', 'ok');
        if (again) { openTask(null); }
        else { App.closeModal(); setTimeout(() => location.reload(), 250); }
      } catch (_) {}
    };
    document.getElementById('t-save').onclick = () => save(false);
    const n = document.getElementById('t-save-next'); if (n) n.onclick = () => save(true);
    const d = document.getElementById('t-del');
    if (d) d.onclick = async () => { if (await App.confirm('این تسک حذف شود؟')) { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'DELETE' }); App.closeModal(); location.reload(); } };
  }
  window.openTask = openTask;

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

  // ── کانبان drag & drop ──
  document.querySelectorAll('.kcard[draggable]').forEach((c) => c.addEventListener('dragstart', (e) => e.dataTransfer.setData('id', c.dataset.id)));
  document.querySelectorAll('.kcol-b[data-status]').forEach((col) => {
    col.addEventListener('dragover', (e) => e.preventDefault());
    col.addEventListener('drop', async (e) => {
      e.preventDefault();
      const id = e.dataTransfer.getData('id');
      try { await App.fetchJSON(`/tasks/api/${id}/status/`, { method: 'PATCH', body: { status: col.dataset.status } }); location.reload(); }
      catch (_) {}
    });
  });
})();
