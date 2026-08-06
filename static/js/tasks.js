/* tasks.js — رفتار صفحه‌ی تسک‌ها: مودال چندحالته، لیست/کانبان، عملیات گروهی.
   به App (app.js) و TASK_SCHEMA (task-schema.js) وابسته است. */
(function () {
  'use strict';
  const S = window.TASK_SCHEMA;
  const cfg = window.TASK_CFG || {}; // {projects:[], colleagues:[], typeChoices:[]}

  // ── ساخت مارک‌آپ فیلدهای مودال ──
  function opts(list, sel) {
    return list.map((o) => `<option value="${o[0]}"${o[0] == sel ? ' selected' : ''}>${o[1]}</option>`).join('');
  }
  function field(id, label, inner) {
    return `<div class="field" data-f="${id}"><label>${label}</label>${inner}</div>`;
  }

  function modalHtml(t) {
    t = t || {};
    return `
    <div class="modal-h"><h3>${t.id ? 'ویرایش تسک' : 'تسک جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
    <div class="modal-b" id="tform">
      <div class="grid3">
        ${field('project', 'پروژه', `<select id="f-project">${opts(cfg.projects, t.project_id)}</select>`)}
        ${field('assignee', 'مسئول', `<select id="f-assignee"><option value="">—</option>${opts(cfg.colleagues, t.assignee_id)}</select>`)}
        ${field('task_type', 'نوع تسک', `<select id="f-task_type">${opts(cfg.typeChoices, t.type)}</select>`)}
      </div>
      <div class="grid2">
        ${field('update_type', 'زیرنوع', `<select id="f-update_type"><option value="">—</option><option value="minor"${t.update_type === 'minor' ? ' selected' : ''}>سطحی</option><option value="major"${t.update_type === 'major' ? ' selected' : ''}>اساسی</option></select>`)}
        ${field('priority', 'اولویت', `<select id="f-priority"><option value="low">کم</option><option value="med" selected>متوسط</option><option value="high">زیاد</option></select>`)}
      </div>
      ${field('title', 'عنوان', `<input id="f-title" class="input" value="${t.title || ''}">`)}
      <div class="grid2">
        ${field('planned_date', 'تاریخ برنامه (شمسی)', `<input id="f-planned_date" class="input" dir="ltr" placeholder="۱۴۰۵/۰۵/۱۵" value="${t.planned_date_fa || ''}">`)}
        ${field('status', 'وضعیت', `<select id="f-status"><option value="todo">در انتظار</option><option value="doing">در حال انجام</option><option value="done">انجام شده</option><option value="cancelled">لغو شده</option></select>`)}
      </div>
      <div class="grid2">
        ${field('word_count', 'تعداد کلمه', `<input id="f-word_count" class="input" type="number" value="${t.word_count || ''}">`)}
        ${field('seo_title', 'عنوان سئو', `<input id="f-seo_title" class="input" value="${t.seo_title || ''}">`)}
      </div>
      ${field('keywords', 'کلمات کلیدی', `<input id="f-keywords" class="input" value="${t.keywords || ''}">`)}
      ${field('lsi_keywords', 'کلمات LSI', `<input id="f-lsi_keywords" class="input" value="${t.lsi_keywords || ''}">`)}
      <div class="grid2">
        ${field('current_rank', 'جایگاه فعلی', `<input id="f-current_rank" class="input" type="number" value="${t.current_rank || ''}">`)}
        ${field('target_rank', 'جایگاه هدف', `<input id="f-target_rank" class="input" type="number" value="${t.target_rank || ''}">`)}
      </div>
      ${field('published_url', 'لینک انتشار', `<input id="f-published_url" class="input" dir="ltr" value="${t.published_url || ''}">`)}
      ${field('source_url', 'آدرس مطلب فعلی', `<input id="f-source_url" class="input" dir="ltr" value="${t.source_url || ''}">`)}
      <div class="grid2">
        ${field('media_name', 'نام رسانه', `<input id="f-media_name" class="input" value="${t.media_name || ''}">`)}
        ${field('media_cost', 'هزینه رپورتاژ', `<input id="f-media_cost" class="input" type="number" value="${t.media_cost || ''}">`)}
      </div>
      <div class="grid2">
        ${field('anchor_text', 'انکر تکست', `<input id="f-anchor_text" class="input" value="${t.anchor_text || ''}">`)}
        ${field('target_url', 'لینک مقصد', `<input id="f-target_url" class="input" dir="ltr" value="${t.target_url || ''}">`)}
      </div>
      <div class="grid2">
        ${field('link_type', 'نوع لینک', `<select id="f-link_type"><option value="">—</option><option value="comment">کامنت</option><option value="profile">پروفایل</option><option value="forum">فروم</option><option value="directory">دایرکتوری</option><option value="social">سوشال</option><option value="other">سایر</option></select>`)}
        ${field('link_count', 'تعداد لینک', `<input id="f-link_count" class="input" type="number" value="${t.link_count || ''}">`)}
      </div>
      ${field('description', 'توضیحات', `<textarea id="f-description" rows="3">${t.description || ''}</textarea>`)}
    </div>
    <div class="modal-f">
      <button class="btn btn-p" id="t-save">ذخیره</button>
      ${t.id ? '' : '<button class="btn" id="t-save-next">ذخیره و ایجاد بعدی</button>'}
      <button class="btn" onclick="App.closeModal()">انصراف</button>
      ${t.id ? '<button class="btn" id="t-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}
    </div>`;
  }

  function applyVisibility() {
    const type = document.getElementById('f-task_type').value;
    const on = S.fieldsFor(type);
    document.querySelectorAll('#tform [data-f]').forEach((el) => {
      const f = el.dataset.f;
      // فیلدهای همیشگی
      if (['project', 'assignee', 'task_type', 'title', 'planned_date', 'status', 'priority', 'description'].includes(f)) return;
      if (f === 'update_type') { el.style.display = type === 'update' ? '' : 'none'; return; }
      el.style.display = on.has(f) ? '' : 'none';
    });
  }

  function collect() {
    const g = (id) => { const e = document.getElementById(id); return e ? e.value : ''; };
    return {
      project: g('f-project'), assignee: g('f-assignee'), task_type: g('f-task_type'),
      update_type: g('f-update_type'), priority: g('f-priority'), title: g('f-title'),
      planned_date: g('f-planned_date'), status: g('f-status'), word_count: g('f-word_count'),
      seo_title: g('f-seo_title'), keywords: g('f-keywords'), lsi_keywords: g('f-lsi_keywords'),
      current_rank: g('f-current_rank'), target_rank: g('f-target_rank'), published_url: g('f-published_url'),
      source_url: g('f-source_url'), media_name: g('f-media_name'), media_cost: g('f-media_cost'),
      anchor_text: g('f-anchor_text'), target_url: g('f-target_url'), link_type: g('f-link_type'),
      link_count: g('f-link_count'), description: g('f-description'),
    };
  }

  async function openTask(id) {
    let data = {};
    if (id) { try { data = await App.fetchJSON(`/tasks/api/${id}/`); } catch (_) { return; } }
    App.openModal(modalHtml(data));
    const tt = document.getElementById('f-task_type');
    tt.addEventListener('change', applyVisibility);
    if (data.status) document.getElementById('f-status').value = data.status;
    if (data.priority) document.getElementById('f-priority').value = data.priority;
    applyVisibility();

    const save = async (again) => {
      const payload = collect();
      if (!payload.title || !payload.project) { App.toast('عنوان و پروژه لازم است', 'warn'); return; }
      try {
        if (id) await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: payload });
        else await App.fetchJSON('/tasks/api/', { method: 'POST', body: payload });
        App.toast('ذخیره شد', 'ok');
        if (again) { App.openModal(modalHtml({ project_id: payload.project, type: payload.task_type })); bind(null); }
        else { App.closeModal(); setTimeout(() => location.reload(), 300); }
      } catch (_) {}
    };
    function bind() {
      document.getElementById('f-task_type').addEventListener('change', applyVisibility);
      applyVisibility();
      document.getElementById('t-save').onclick = () => save(false);
      const n = document.getElementById('t-save-next'); if (n) n.onclick = () => save(true);
      const d = document.getElementById('t-del');
      if (d) d.onclick = async () => { if (await App.confirm('این تسک حذف شود؟')) { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'DELETE' }); App.closeModal(); location.reload(); } };
    }
    bind();
  }

  // ── تغییر سریع وضعیت از دراپ‌داون ردیف ──
  document.addEventListener('change', async (e) => {
    if (e.target.matches('.row-status')) {
      const id = e.target.dataset.id;
      try { await App.fetchJSON(`/tasks/api/${id}/status/`, { method: 'PATCH', body: { status: e.target.value } }); App.toast('وضعیت به‌روز شد', 'ok'); }
      catch (_) {}
    }
  });

  // ── باز کردن مودال (دکمه‌ها و ردیف‌ها) ──
  document.addEventListener('click', (e) => {
    if (e.target.closest('#new-task')) { e.preventDefault(); openTask(null); }
    const row = e.target.closest('[data-open-task]');
    if (row && !e.target.closest('a,select,input,button')) openTask(row.dataset.openTask);
  });

  // ── عملیات گروهی ──
  const selected = () => Array.from(document.querySelectorAll('.row-check:checked')).map((c) => c.dataset.id);
  document.addEventListener('change', (e) => {
    if (e.target.matches('.row-check, #check-all')) {
      if (e.target.id === 'check-all') document.querySelectorAll('.row-check').forEach((c) => (c.checked = e.target.checked));
      const n = selected().length;
      const bar = document.getElementById('bulkbar');
      if (bar) { bar.style.display = n ? 'flex' : 'none'; const c = document.getElementById('bulk-count'); if (c) c.textContent = n; }
    }
  });
  async function bulk(action, extra) {
    const ids = selected(); if (!ids.length) return;
    try { await App.fetchJSON('/tasks/api/bulk/', { method: 'POST', body: Object.assign({ ids, action }, extra) }); App.toast('انجام شد', 'ok'); setTimeout(() => location.reload(), 300); }
    catch (_) {}
  }
  window.TaskBulk = { shift: (d) => bulk('shift_date', { days: d, skip_holidays: true }), done: () => bulk('mark_done', {}), open: openTask };

  // ── کانبان drag & drop ──
  document.querySelectorAll('.kcard[draggable]').forEach((c) => {
    c.addEventListener('dragstart', (e) => e.dataTransfer.setData('id', c.dataset.id));
  });
  document.querySelectorAll('.kcol-b[data-status]').forEach((col) => {
    col.addEventListener('dragover', (e) => e.preventDefault());
    col.addEventListener('drop', async (e) => {
      e.preventDefault();
      const id = e.dataTransfer.getData('id');
      const status = col.dataset.status;
      try { await App.fetchJSON(`/tasks/api/${id}/status/`, { method: 'PATCH', body: { status } }); location.reload(); }
      catch (_) {}
    });
  });
})();
