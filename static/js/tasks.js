/* tasks.js — مودال تسک (built-in + انواع سفارشی)، لیست/کانبان، عملیات گروهی.
   از هر صفحه‌ای کار می‌کند: داده‌ی فرم را یک‌بار از /tasks/api/formdata/ می‌گیرد.
   به App (app.js) و TASK_SCHEMA (task-schema.js) وابسته است. */
(function () {
  'use strict';
  let cfg = null;
  async function ensureCfg() {
    if (!cfg) cfg = await App.fetchJSON('/tasks/api/formdata/');
    return cfg;
  }

  const opt = (v, l, sel) => `<option value="${v}"${String(v) === String(sel) ? ' selected' : ''}>${l}</option>`;
  // گزینه با رنگ/تصویر برای دراپ‌داونِ غنی (پروژه/مسئول)
  const optRich = (v, l, sel, color, img) => `<option value="${v}"${String(v) === String(sel) ? ' selected' : ''}` +
    `${color ? ` data-color="${color}"` : ''}${img ? ` data-img="${img}"` : ''}>${l}</option>`;
  function field(id, label, inner) {
    return `<div class="field" data-f="${id}"><label>${label}</label>${inner}</div>`;
  }

  // ── آیکن‌های SVG (هم‌سبکِ بقیهٔ سایت: فونت‌اوسام، fill=currentColor) برای چیپ‌های تولبارِ مودال ──
  const svg = (p, vb) => `<svg class="topt-ic" viewBox="${vb || '0 0 512 512'}" aria-hidden="true"><path fill="currentColor" d="${p}"/></svg>`;
  const ICON = {
    description: svg('M16 64C16 46.3 30.3 32 48 32l416 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L48 96C30.3 96 16 81.7 16 64zm0 128c0-17.7 14.3-32 32-32l288 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L48 224c-17.7 0-32-14.3-32-32zM16 320c0-17.7 14.3-32 32-32l416 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L48 352c-17.7 0-32-14.3-32-32zm0 128c0-17.7 14.3-32 32-32l288 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L48 480c-17.7 0-32-14.3-32-32z'),
    checklist: svg('M152.1 38.2c9.9 8.9 10.7 24 1.8 33.9l-72 80c-4.4 4.9-10.6 7.8-17.2 7.9s-12.9-2.4-17.6-7L7 113C-2.3 103.6-2.3 88.4 7 79s24.6-9.4 33.9 0l22.1 22.1 55.1-61.2c8.9-9.9 24-10.7 33.9-1.8zm0 160c9.9 8.9 10.7 24 1.8 33.9l-72 80c-4.4 4.9-10.6 7.8-17.2 7.9s-12.9-2.4-17.6-7L7 273c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l22.1 22.1 55.1-61.2c8.9-9.9 24-10.7 33.9-1.8zM224 96c0-17.7 14.3-32 32-32l224 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-224 0c-17.7 0-32-14.3-32-32zm0 160c0-17.7 14.3-32 32-32l224 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-224 0c-17.7 0-32-14.3-32-32zM160 416c0-17.7 14.3-32 32-32l288 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-288 0c-17.7 0-32-14.3-32-32zM48 384a48 48 0 1 1 0 96 48 48 0 1 1 0-96z'),
    recur: svg('M0 224c0 17.7 14.3 32 32 32s32-14.3 32-32c0-53 43-96 96-96l160 0 0 32c0 12.9 7.8 24.6 19.8 29.6s25.7 2.2 34.9-6.9l64-64c12.5-12.5 12.5-32.8 0-45.3l-64-64c-9.2-9.2-22.9-11.9-34.9-6.9S320 19.1 320 32l0 32L160 64C71.6 64 0 135.6 0 224zm512 64c0-17.7-14.3-32-32-32s-32 14.3-32 32c0 53-43 96-96 96l-160 0 0-32c0-12.9-7.8-24.6-19.8-29.6s-25.7-2.2-34.9 6.9l-64 64c-12.5 12.5-12.5 32.8 0 45.3l64 64c9.2 9.2 22.9 11.9 34.9 6.9s19.8-16.6 19.8-29.6l0-32 160 0c88.4 0 160-71.6 160-160z'),
    report: svg('M512 240c0 114.9-114.6 208-256 208-37.1 0-72.3-6.4-104.1-17.9-11.9 8.7-31.3 20.6-54.3 30.6C73.6 471.1 44.7 480 16 480c-6.5 0-12.3-3.9-14.8-9.9s-1.1-12.8 3.4-17.4l.3-.3c.3-.3 .7-.7 1.3-1.4 1.1-1.2 2.8-3.1 4.9-5.7 4.1-5 9.6-12.4 15.2-21.6 10-16.6 19.5-38.4 21.4-62.9C17.7 326.8 0 285.1 0 240 0 125.1 114.6 32 256 32s256 93.1 256 208z'),
    review: svg('M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM369 209L241 337c-9.4 9.4-24.6 9.4-33.9 0l-64-64c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l47 47L335 175c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9z'),
    history: svg('M75 75L41 41C25.9 25.9 0 36.6 0 57.9L0 168c0 13.3 10.7 24 24 24l110.1 0c21.4 0 32.1-25.9 17-41l-30.8-30.8C155 85.5 203 64 256 64c106 0 192 86 192 192s-86 192-192 192c-40.8 0-78.6-12.7-109.7-34.4-14.5-10.1-34.4-6.6-44.6 7.9s-6.6 34.4 7.9 44.6C158.6 496.9 205.5 512 256 512c141.4 0 256-114.6 256-256S397.4 0 256 0C185.3 0 121.3 28.7 75 75zm181 53c-13.3 0-24 10.7-24 24l0 104c0 6.4 2.5 12.5 7 17l72 72c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-65-65 0-94.1c0-13.3-10.7-24-24-24z'),
  };

  // دراپ‌داونِ «ماه گزارش» — از ماه‌های تعریف‌شده در تنظیمات (cfg.reportPeriods، value='سال-ماه').
  // مقدارِ فعلیِ تسک اگر در فهرست نبود (دادهٔ قدیمی) خودش هم اضافه می‌شود تا گم نشود.
  function reportPeriodSelect(t) {
    const cur = (t.report_month && t.report_year) ? `${t.report_year}-${t.report_month}` : '';
    const periods = cfg.reportPeriods || [];
    const vals = new Set(periods.map((p) => p[0]));
    const mName = Object.fromEntries((cfg.reportMonths || []).map(([n, l]) => [n, l]));
    let opts = '<option value="">— بدون ماه —</option>';
    if (cur && !vals.has(cur)) opts += `<option value="${cur}" selected>${(mName[t.report_month] || '') + ' ' + t.report_year}</option>`;
    opts += periods.map(([v, l]) => `<option value="${v}"${v === cur ? ' selected' : ''}>${l}</option>`).join('');
    const hint = periods.length ? '' : ' <span style="font-size:10px;color:var(--text-faint)">— در تنظیمات ← ماه‌های گزارش تعریف کن</span>';
    return `<select id="f-report_period">${opts}</select>${hint}`;
  }

  // بعد از ذخیرهٔ مودال، ردیفِ جدولِ لیستِ تسک‌ها (.tsheet) را بدونِ رفرش به‌روز/درج می‌کند.
  // اگر روی صفحه‌ای هستیم که این جدول را ندارد (برد/تقویم)، false می‌دهد تا رفرشِ نرم شود.
  async function refreshTaskRow(id, isNew) {
    if (!id) return false;
    const existing = document.querySelector(`.tsheet tr[data-id="${id}"]`);
    if (!existing && !isNew) return false;
    const tbody = existing ? existing.closest('tbody') : document.querySelector('.tsheet tbody');
    if (!tbody) return false;
    try {
      const d = await App.fetchJSON(`/tasks/api/${id}/row/`);
      if (existing) existing.outerHTML = d.html;
      else tbody.insertAdjacentHTML('afterbegin', d.html);
      const nw = tbody.querySelector(`tr[data-id="${id}"]`);
      if (window.RichSelect && nw) RichSelect.init(nw);
      if (nw) { kwHighlightAll(nw); initAllGutters(nw); }   // کلمهٔ کلیدی + شماره‌گذاریِ خطوط
      if (nw && typeof renderAllTimerCells === 'function') renderAllTimerCells();
      return true;
    } catch (_) { return false; }
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

  // آیا این همکار به‌طورِ پیش‌فرض نیاز به بازبینی دارد؟ (cfg.colleagues: [id, name, needsReview])
  function colleagueNeedsReview(id) {
    const c = (cfg.colleagues || []).find((x) => String(x[0]) === String(id));
    return !!(c && c[2]);
  }

  // گزینه‌های وضعیت — تسکِ needs_review هرگز «انجام‌شده» ندارد (فقط «تکمیل»)، برعکسش هم همین‌طور
  const STATUS_LABELS = [['todo', 'در انتظار'], ['doing', 'در حال انجام'], ['pending', 'تکمیل — در انتظار بازبینی'], ['done', 'انجام شده']];
  function statusOptions(sel, needsReview) {
    return STATUS_LABELS
      .filter(([v]) => (needsReview ? v !== 'done' : v !== 'pending'))
      .map(([v, l]) => opt(v, l, sel)).join('');
  }

  function modalHtml(t) {
    t = t || {};
    const isNew = !t.id;
    // اگر own_tasks_only داشت، فقط روی تسکِ خودش ویرایش/حذف مجاز است (بقیه‌ی تسک‌ها را
    // اصلاً نمی‌بیند تا اینجا برسد، ولی این چک برای بازکردنِ مستقیم/لینکِ قدیمی هم درست کار کند).
    const ownMatch = !cfg.ownTasksOnly || t.assignee_id === cfg.myColleagueId;
    // تسکِ جدید: هرکسی با createTask (پروفایلِ همکار) می‌تواند برای خودش بسازد، حتی
    // بدونِ edit_task؛ تسکِ موجود: فقط edit_task واقعی (+ own_tasks_only اگر داشت).
    const canEditThis = isNew ? (cfg.editTask || cfg.createTask) : (cfg.editTask && ownMatch);
    const canDeleteThis = t.id && cfg.deleteTask && ownMatch;
    const _bt = typeList().find((x) => x.builtin_key === (t.type || 'other'));
    const typeSel = t.type_def || (_bt ? _bt.id : (typeList()[0] || {}).id);
    // مسئول: پیش‌فرض خودِ کاربر (فقط برای تسکِ جدید)؛ اگر own_tasks_only داشت، یا
    // تسکِ جدیدی که بدونِ edit_task فقط برای خودش مجاز است، دراپ‌داون قفل می‌شود.
    const lockAssignee = cfg.ownTasksOnly || (isNew && !cfg.editTask);
    const assigneeSel = t.id ? t.assignee_id : (t.assignee_id || cfg.myColleagueId || '');
    const assigneeSelect = lockAssignee
      ? `<select id="f-assignee" disabled>${opt(cfg.myColleagueId || '', 'خودم', assigneeSel)}</select>`
      : `<select id="f-assignee" class="rich-select"><option value="">—</option>${cfg.colleagues.map(([v, l, , color, img]) => optRich(v, l, assigneeSel, color, img)).join('')}</select>`;
    // نیاز به بازبینی: پیش‌فرض از تسکِ موجود (t.needs_review)، وگرنه از تنظیمِ خودِ
    // مسئولِ فعلاً انتخاب‌شده (Colleague.needs_review) — هربار قابلِ‌تغییرِ دستی است.
    const needsReviewDefault = t.id ? !!t.needs_review : colleagueNeedsReview(assigneeSel);
    return `
    <div class="modal-h"><h3>${t.id ? 'ویرایش تسک' : 'تسک جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
    <div class="modal-b tmodal" id="tform">
      ${reviewNotesHtml(t)}
      <div class="tmodal-col">
        <!-- عنوان (فیلدِ اصلی، بزرگ‌تر) -->
        ${field('title', 'عنوان', `<input id="f-title" class="input tm-title" value="${esc(t.title)}" placeholder="عنوان تسک…">`)}
        <div class="grid2">
          ${field('project', 'پروژه', `<select id="f-project" class="rich-select"><option value="">— انتخاب —</option>${cfg.projects.map(([v, l, color, img]) => optRich(v, l, t.project_id, color, img)).join('')}</select>`)}
          ${field('assignee', 'مسئول', assigneeSelect)}
        </div>
        <div class="grid2">
          ${field('task_type', 'نوع تسک', `<select id="f-task_type">${typeOptions(typeSel)}</select>`)}
          ${field('status', 'وضعیت', `<select id="f-status">${statusOptions(t.status, needsReviewDefault)}</select>`)}
        </div>
        <div class="grid3">
          ${field('planned_date', 'تاریخ برنامه <span id="rel-planned" class="rel-hint"></span>', `<input id="f-planned_date" class="input jdate" dir="ltr" readonly value="${t.planned_date_fa || ''}">`)}
          ${field('estimate_minutes', 'تخمین (H:MM)', `<input id="f-estimate_minutes" class="input" dir="ltr" placeholder="0:00" value="${t.estimate_minutes ? fmtMin(t.estimate_minutes) : ''}">`)}
          ${field('report_month', 'ماه گزارش', reportPeriodSelect(t))}
        </div>
        <!-- چک‌باکسِ مخفیِ «نیاز به بازبینی» (وضعیت را کنترل می‌کند)؛ UI آن چیپِ تولبار است -->
        <input type="checkbox" id="f-needs-review" ${needsReviewDefault ? 'checked' : ''} hidden>
        <!-- فیلدهای سفارشیِ نوع (داینامیک، فقط اگر نوع داشته باشد) -->
        <div id="custom-fields" style="display:none"></div>
        ${recurBannerHtml(t)}
        <!-- تولبارِ بخش‌های اختیاری + کلیدهای بازبینی/تاریخچه (آیکنِ SVG، مثلِ گوگل‌کلندر) -->
        <div class="topt-bar" id="topt-bar">
          <button type="button" class="topt" data-sec="description">${ICON.description} توضیحات</button>
          <button type="button" class="topt" data-sec="checklist">${ICON.checklist} چک‌لیست</button>
          ${isNew ? `<button type="button" class="topt" data-sec="recur">${ICON.recur} تکرار</button>` : ''}
          ${t.id ? `<button type="button" class="topt" data-sec="report">${ICON.report} گزارش کار</button>` : ''}
          <button type="button" class="topt topt-rev" data-rev>${ICON.review} نیاز به بازبینی</button>
          ${t.id ? `<button type="button" class="topt" data-sec="history">${ICON.history} تاریخچه <span class="topt-count">${String((t.history || []).length)}</span></button>` : ''}
        </div>
        <div id="sec-description" class="topt-sec" style="display:none">
          <textarea id="f-description" class="rich-editor" rows="4">${esc(t.description)}</textarea>
        </div>
        <div id="sec-checklist" class="topt-sec" style="display:none">${checklistHtml(t)}</div>
        ${isNew ? `<div id="sec-recur" class="topt-sec" style="display:none">${recurPickerHtml()}</div>` : ''}
        ${t.id ? `<div id="sec-report" class="topt-sec" style="display:none">
          <div class="report-sec">
            <textarea id="f-report" class="rich-editor" rows="3"></textarea>
            <div style="margin-top:6px;display:flex;gap:8px;align-items:center">
              <button type="button" class="btn btn-sm btn-p" id="report-send">ارسال گزارش</button>
              <button type="button" class="btn btn-sm" id="report-cancel" style="display:none">لغو ویرایش</button>
            </div>
            <div id="report-list" class="report-list"></div>
          </div>
        </div>` : ''}
        ${t.id ? `<div id="sec-history" class="topt-sec" style="display:none"><div class="hist-list">${historyListHtml(t)}</div></div>` : ''}
        ${t.id ? '<div id="kpi-box" style="display:none;margin-top:12px"></div>' : ''}
      </div>
    </div>
    <div class="modal-f">
      ${canEditThis ? '<button class="btn btn-p" id="t-save">ذخیره</button>' : ''}
      ${canEditThis && !t.id ? '<button class="btn" id="t-save-next">ذخیره و ایجاد بعدی</button>' : ''}
      <button class="btn" onclick="App.closeModal()">انصراف</button>
      ${canDeleteThis ? '<button class="btn" id="t-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}
    </div>`;
  }

  function esc(v) { return (v == null ? '' : String(v)).replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  // ── چک‌لیستِ عمومی — هر ردیف: چک‌باکس + متن + دکمه‌های + و × داخلِ همان اینپوت.
  //    Enter یا + ردیفِ جدید می‌سازد؛ × حذف می‌کند (بدونِ دکمه‌ی جدای «افزودن»).
  function ckRow(it) {
    it = it || {};
    return `<div class="ck-row"><input type="checkbox" class="ck-done"${it.done ? ' checked' : ''}>` +
      `<div class="ck-field"><input type="text" class="ck-text" value="${esc(it.text)}" placeholder="یک مورد بنویس و Enter بزن…">` +
      `<button type="button" class="ck-plus" title="افزودن">＋</button>` +
      `<button type="button" class="ck-x" title="حذف">×</button></div></div>`;
  }
  function checklistHtml(t) {
    const items = (t && t.checklist) || [];
    const body = items.map(ckRow).join('') + ckRow();  // همیشه یک ردیفِ خالیِ آماده ته لیست
    return `<div class="ck-wrap"><label style="font-weight:700">چک‌لیست</label>
      <div class="ck-list" id="ck-list">${body}</div></div>`;
  }
  function ckAddAfter(row, focus) {
    const html = ckRow();
    if (row && row.parentElement) row.insertAdjacentHTML('afterend', html);
    else { const list = document.getElementById('ck-list'); if (list) list.insertAdjacentHTML('beforeend', html); }
    const nw = row ? row.nextElementSibling : document.getElementById('ck-list').lastElementChild;
    if (focus && nw) nw.querySelector('.ck-text').focus();
  }
  function wireChecklist() {
    const list = document.getElementById('ck-list'); if (!list) return;
    list.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.classList.contains('ck-text')) {
        e.preventDefault();
        const row = e.target.closest('.ck-row');
        if (row.nextElementSibling) row.nextElementSibling.querySelector('.ck-text').focus();
        else if (e.target.value.trim()) ckAddAfter(row, true);
      }
    });
    list.addEventListener('click', (e) => {
      if (e.target.classList.contains('ck-plus')) { ckAddAfter(e.target.closest('.ck-row'), true); return; }
      if (e.target.classList.contains('ck-x')) {
        const rows = list.querySelectorAll('.ck-row');
        if (rows.length > 1) e.target.closest('.ck-row').remove();
        else e.target.closest('.ck-row').querySelector('.ck-text').value = '';
      }
    });
  }
  function readChecklist() {
    const list = document.getElementById('ck-list'); if (!list) return [];
    return [...list.querySelectorAll('.ck-row')].map((r) => ({
      text: r.querySelector('.ck-text').value.trim(),
      done: r.querySelector('.ck-done').checked,
    })).filter((x) => x.text);
  }

  // ── تکرار: بنرِ «بخشی از سری» (تسکِ موجودِ تکرارشونده) + پیکرِ نوعِ تکرار (تسک جدید،
  //    داخلِ بخشِ جمع‌شونده‌ی «تکرار»؛ فقط با کلیک روی تولبار باز می‌شود). ──
  function recurBannerHtml(t) {
    if (!(t.id && t.recurrence)) return '';
    return `<div class="rec-bar" style="color:var(--text-dim);margin-top:8px">🔁 این تسک بخشی از یک سری تکرار است.
      <button type="button" class="btn btn-sm" id="rec-del" data-id="${t.recurrence}" style="color:var(--danger)">حذف کل سریِ آینده</button></div>`;
  }
  function recurPickerHtml() {
    const wk = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];  // شنبه=۰ .. جمعه=۶
    return `<div class="rec-wrap">
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
        <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer"><input type="checkbox" id="rec-skip" checked> رد کردن تعطیلات</label>
      </div></div>`;
  }

  // ── تولبارِ بخش‌های اختیاری (توضیحات/چک‌لیست/تکرار/گزارش) ──
  //    هر بخش پیش‌فرض بسته است؛ با کلیک روی چیپ باز/بسته می‌شود. بخشی که از قبل محتوا
  //    دارد (توضیحاتِ پر، چک‌لیستِ غیرخالی، گزارشِ ثبت‌شده) خودکار باز می‌شود. ادیتورهای
  //    سنگین (TinyMCE توضیحات/گزارش) فقط هنگامِ اولین بازشدن init می‌شوند (لودِ تنبل).
  function wireOptToolbar(t, id) {
    const bar = document.getElementById('topt-bar'); if (!bar) return;
    const inited = {};
    const reveal = (name) => {
      if (name === 'description' && !inited.description) { if (window.RichText) RichText.init('#f-description'); inited.description = true; }
      if (name === 'report' && !inited.report) { initReports(id); inited.report = true; }
    };
    const setSec = (name, show) => {
      const sec = document.getElementById('sec-' + name);
      const chip = bar.querySelector(`.topt[data-sec="${name}"]`);
      if (!sec) return;
      sec.style.display = show ? '' : 'none';
      if (chip) chip.classList.toggle('on', show);
      if (show) reveal(name);
    };
    bar.addEventListener('click', (e) => {
      const chip = e.target.closest('.topt'); if (!chip) return;
      const name = chip.dataset.sec;
      const sec = document.getElementById('sec-' + name); if (!sec) return;
      setSec(name, sec.style.display === 'none');
    });
    // بازکردنِ خودکارِ بخش‌های دارای محتوا
    if (t.description && t.description.replace(/<[^>]*>/g, '').trim()) setSec('description', true);
    if (t.checklist && t.checklist.length) setSec('checklist', true);
    if (id) {
      App.fetchJSON(`/tasks/api/${id}/comments/`)
        .then((d) => { if (d && d.comments && d.comments.length) setSec('report', true); })
        .catch(() => {});
    }
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

  // ── KPI در مودال: کارمند طبق چه سنجیده می‌شود + خوداظهاریِ چک‌لیست (نمایشی) ──
  // آیتم‌های چک‌لیستِ KPI را خودِ مسئولِ تسک می‌تواند تیک بزند (خوداظهاری، ذخیره‌ی زنده).
  // امتیازدهیِ نهایی همچنان با مدیر است (review.html: scoreKpis) — این فقط نمایشی است.
  async function initKpis(id) {
    const box = document.getElementById('kpi-box'); if (!box) return;
    try {
      const d = await App.fetchJSON(`/tasks/api/${id}/kpis/`);
      if (!d.has) { box.style.display = 'none'; return; }
      box.style.display = '';
      const canCheck = !!d.can_self_check;
      const selfScore = (k) => (k.self_checked || []).reduce((a, id2) => {
        const it = (k.items || []).find((x) => x.id === id2); return a + (it ? it.score : 0);
      }, 0);
      box.innerHTML = `<label style="font-weight:700">شاخص‌های کیفیت (KPI)${d.cap ? ` — امتیاز: ${d.total}/${d.cap}` : ''}</label>` +
        d.kpis.map((k) => {
          const sc = (k.self_checked || []);
          const items = k.has_checklist ? `<div class="kpi-items">${k.items.map((it) => `<label class="kpi-ci${canCheck ? ' kpi-ci-check' : ''}">
            <input type="checkbox" class="kci-self" data-kpi="${k.id}" data-score="${it.score}" value="${it.id}" ${sc.includes(it.id) ? 'checked' : ''}${canCheck ? '' : ' disabled'}>
            <span>${esc(it.title)} <b>(${it.score})</b>${it.description ? ` <span class="kpi-info" title="${esc(it.description)}">ℹ️</span>` : ''}</span></label>`).join('')}</div>` : '';
          const selfTag = k.has_checklist ? `<span class="tag t-mute kpi-self-tag" data-kpi="${k.id}" data-cap="${k.cap}">خوداظهاری: ${selfScore(k)}/${k.cap}</span>` : '';
          return `<div class="kpi-item" data-kpi="${k.id}"><div class="kpi-head"><b>${esc(k.title)}</b>
          <span class="tag t-mute">سقف ${k.cap}</span>${selfTag}${k.given != null ? `<span class="tag t-ok">امتیازِ مدیر: ${k.given}</span>` : ''}
          ${k.description ? `<span class="kpi-info" title="${esc(k.description)}">ℹ️</span>` : ''}</div>${items}</div>`;
        }).join('');
      if (canCheck) wireKpiSelfCheck(box, id);
    } catch (_) {}
  }

  // تیک‌های خوداظهاریِ KPI را زنده ذخیره کن (delegated؛ فقط مسئولِ تسک آن را می‌بیند)
  function wireKpiSelfCheck(box, id) {
    box.addEventListener('change', async (e) => {
      const cb = e.target.closest('.kci-self'); if (!cb) return;
      const kpiId = cb.dataset.kpi;
      const item = box.querySelector(`.kpi-item[data-kpi="${kpiId}"]`);
      const boxes = [...item.querySelectorAll('.kci-self:checked')];
      const checked = boxes.map((c) => +c.value);
      const sum = boxes.reduce((a, c) => a + (+c.dataset.score || 0), 0);
      const tag = item.querySelector('.kpi-self-tag');
      if (tag) tag.textContent = `خوداظهاری: ${sum}/${tag.dataset.cap}`;
      try { await App.fetchJSON(`/tasks/api/${id}/kpi-self-check/`, { method: 'POST', body: { kpi: +kpiId, checked_items: checked } }); }
      catch (_) {}
    });
  }

  // ── جعبه‌ی «موارد نیاز به اصلاح» بالای مودال + تاریخچه (جدیدترین باز، قبلی‌ها جمع) ──
  function reviewNotesHtml(t) {
    const ns = (t && t.review_notes) || [];
    if (!ns.length) return '';
    const canEdit = !!(t && t.review_can_edit);
    // note از سرور با clean_html پاکسازی شده؛ درج مستقیم HTML امن است
    const item = (n, i) => `<div class="fixnote-item" data-fix-item${i > 0 ? ' style="display:none"' : ''} data-note-id="${n.id}">
        <div class="fixnote-meta">${esc(n.author)}${n.author ? ' · ' : ''}${esc(n.when)}${i === 0 ? ' <b>(آخرین)</b>' : ''}${canEdit ? ` <i class="fixnote-edit" data-note-edit="${n.id}" title="ویرایشِ یادداشت">✏️</i>` : ''}</div>
        <div class="rich" data-note-body="${n.id}">${n.note}</div></div>`;
    const more = ns.length > 1
      ? `<button type="button" class="mini" id="fix-hist-toggle" style="margin-top:6px">نمایش سوابق قبلی (${ns.length - 1})</button>` : '';
    return `<div class="fixnote-box"><div class="fixnote-h">⚠ موارد نیاز به اصلاح</div>${ns.map(item).join('')}${more}</div>`;
  }

  // ── تاریخچهٔ تسک (داخلِ بخشِ جمع‌شونده‌ی تولبار؛ تعداد در چیپ) ──
  function historyListHtml(t) {
    const hs = (t && t.history) || [];
    const item = (h) => {
      const ch = Object.keys(h.changes || {}).map((k) =>
        `<div class="hist-ch"><b>${esc(k)}</b>: <span class="hist-old">${esc(h.changes[k][0])}</span> ← <span class="hist-new">${esc(h.changes[k][1])}</span></div>`).join('');
      return `<div class="hist-item"><div class="hist-meta"><span class="hist-badge hist-${h.action}">${esc(h.action_label)}</span> · ${esc(h.user)} · ${esc(h.when)}</div>${ch}</div>`;
    };
    return hs.length ? hs.map(item).join('') : '<div class="zero" style="padding:8px">تاریخچه‌ای نیست</div>';
  }

  // ── فیلدِ کلمهٔ کلیدی/مترادف: تک‌فیلدِ ساده، جدا با «-»، جداکننده رنگی ──
  //   (به‌جای چیپِ دونه‌دونه؛ خواستِ کاربر). مقدار = رشته؛ بک‌اند با «-» به لیست می‌شکند.
  const KW_SEP = '-';
  function kwCaretOffset(el) {
    const sel = window.getSelection(); if (!sel || !sel.rangeCount) return null;
    const r = sel.getRangeAt(0); if (!el.contains(r.endContainer)) return null;
    const pre = r.cloneRange(); pre.selectNodeContents(el); pre.setEnd(r.endContainer, r.endOffset);
    return pre.toString().length;
  }
  function kwSetCaret(el, off) {
    if (off == null) return;
    const sel = window.getSelection(); const range = document.createRange(); let cur = 0, done = false;
    (function walk(n) {
      if (done) return;
      if (n.nodeType === 3) { if (cur + n.length >= off) { range.setStart(n, off - cur); range.collapse(true); done = true; } else cur += n.length; }
      else n.childNodes.forEach(walk);
    })(el);
    if (done) { sel.removeAllRanges(); sel.addRange(range); }
  }
  // متنِ خام را با هایلایتِ جداکننده («-») دوباره می‌سازد، بدونِ پریدنِ نشانگر
  function kwHighlight(el) {
    const text = el.textContent;
    const off = document.activeElement === el ? kwCaretOffset(el) : null;
    const frag = document.createDocumentFragment(); let buf = '';
    const flush = () => { if (buf) { frag.appendChild(document.createTextNode(buf)); buf = ''; } };
    for (const ch of text) {
      if (ch === KW_SEP) { flush(); const s = document.createElement('span'); s.className = 'kw-sep'; s.textContent = KW_SEP; frag.appendChild(s); }
      else buf += ch;
    }
    flush();
    el.innerHTML = ''; el.appendChild(frag);
    el.dataset.kwinit = '1';
    if (off != null) kwSetCaret(el, off);
  }
  function kwHighlightAll(root) {
    (root || document).querySelectorAll('.kwfield:not([data-kwinit])').forEach(kwHighlight);
  }
  window.kwHighlightAll = kwHighlightAll;
  // مقدارِ اولیه = لیست را با « - » به هم می‌چسباند (نمایشِ خوانا)
  function kwFieldHtml(key, words, placeholder, inline) {
    const attr = inline ? `data-cf="${key}"` : `data-key="${key}" data-kind="tags"`;
    const cls = inline ? 'kwfield cf-kw' : 'kwfield cf';
    const text = (Array.isArray(words) ? words : (words ? [words] : [])).join(' ' + KW_SEP + ' ');
    return `<div class="${cls}" ${attr} contenteditable="true" dir="rtl" spellcheck="false" data-ph="${esc(placeholder || 'کلمه‌ها را با «-» جدا کن')}">${esc(text)}</div>`;
  }
  // هایلایتِ زندهٔ همهٔ فیلدهای کلمهٔ کلیدی (مودال + اینلاین) هنگامِ تایپ
  document.addEventListener('input', (e) => {
    const kw = e.target.closest && e.target.closest('.kwfield');
    if (kw) kwHighlight(kw);
  });
  // ذخیرهٔ اینلاین (فقط فیلدِ کلمهٔ کلیدیِ درون‌جدولی، با data-cf) هنگامِ خروجِ فوکوس
  document.addEventListener('focusout', async (e) => {
    const kw = e.target.closest && e.target.closest('.kwfield.cf-kw'); if (!kw) return;
    const tr = kw.closest('tr'); if (!tr) return;
    try {
      const r = await App.fetchJSON(`/tasks/api/${tr.dataset.id}/`, { method: 'PATCH', body: { custom_patch: { [kw.dataset.cf]: kw.textContent } } });
      App.toast('ذخیره شد', 'ok');
      updateMissReq(tr, r && r.warnings);
    } catch (_) {}
  });
  // ── شماره‌گذاریِ خودکارِ خطوط (۱-۲-۳) کنارِ textareaهای «هر مورد در یک خط» (لینک/انکرِ رپورتاژ) ──
  function initLineGutter(ta) {
    if (ta.dataset.gut) return; ta.dataset.gut = '1';
    const wrap = document.createElement('div'); wrap.className = 'ta-wrap';
    ta.parentNode.insertBefore(wrap, ta); wrap.appendChild(ta);
    const gut = document.createElement('div'); gut.className = 'ta-gut'; wrap.insertBefore(gut, ta);
    const upd = () => {
      const n = Math.max(1, (ta.value.match(/\n/g) || []).length + 1);
      let s = ''; for (let i = 1; i <= n; i++) s += i + '\n';
      gut.textContent = s; gut.scrollTop = ta.scrollTop;
    };
    ta.addEventListener('input', upd);
    ta.addEventListener('scroll', () => { gut.scrollTop = ta.scrollTop; });
    upd();
  }
  function initAllGutters(root) { (root || document).querySelectorAll('textarea.cf-ta:not([data-gut])').forEach(initLineGutter); }
  window.initAllGutters = initAllGutters;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { kwHighlightAll(); initAllGutters(); });
  else { kwHighlightAll(); initAllGutters(); }

  // عرضِ فیلدِ سفارشی در گریدِ ۱۲ستونه (از تنظیماتِ نوعِ تسک)
  const CF_SPAN = { full: 12, half: 6, third: 4, quarter: 3 };

  // ── رندر فیلدهای سفارشی یک نوع ──
  function renderCustom(t, values) {
    const box = document.getElementById('custom-fields');
    if (!t || !t.fields || !t.fields.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
    values = values || {};
    box.style.display = 'grid';
    box.innerHTML = t.fields.map((f) => {
      const span = CF_SPAN[f.width] || 12;
      const v = values[f.key] != null ? values[f.key] : '';
      let input;
      if (f.kind === 'tags') input = kwFieldHtml(f.key, v, f.placeholder, false);
      else if (f.kind === 'textarea') input = `<textarea class="cf cf-ta" data-key="${f.key}" rows="3" placeholder="${esc(f.placeholder)}">${esc(v)}</textarea>`;
      else if (f.kind === 'checkbox') input = `<label style="display:flex;align-items:center;gap:8px;margin:0"><input type="checkbox" class="cf" data-key="${f.key}" ${v ? 'checked' : ''}> ${esc(f.label)}</label>`;
      else if (f.kind === 'select') input = `<select class="cf" data-key="${f.key}"><option value="">—</option>${f.options.map((o) => opt(o, o, v)).join('')}</select>`;
      else if (f.kind === 'number') input = `<input type="number" class="cf input" data-key="${f.key}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      else input = `<input type="text" class="cf input" data-key="${f.key}" dir="${f.kind === 'url' ? 'ltr' : 'rtl'}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      if (f.kind === 'checkbox') return `<div class="field" data-cf style="grid-column:span ${span}">${input}</div>`;
      const req = f.required ? ' *' : (f.required_on_done ? ' (برای تکمیل الزامی)' : '');
      return `<div class="field" data-cf style="grid-column:span ${span}"><label>${esc(f.label)}${req}</label>${input}</div>`;
    }).join('');
    kwHighlightAll(box);   // جداکنندهٔ رنگیِ فیلدهای کلمهٔ کلیدی
    initAllGutters(box);    // شماره‌گذاریِ خطوطِ textareaها
  }

  // مقادیرِ فعلیِ فیلدهای سفارشی را از DOM می‌خواند (منبعِ واحد؛ collect و تعویضِ نوع
  // هر دو از این می‌خوانند تا با عوض‌کردنِ نوع، فیلدهای هم‌کلید حفظ شوند).
  function readCustomValues() {
    const custom = {};
    document.querySelectorAll('#custom-fields .cf').forEach((el) => {
      if (el.dataset.kind === 'tags') {
        // تک‌فیلدِ کلمهٔ کلیدی → رشتهٔ خام (بک‌اند با «-» به لیست می‌شکند)
        custom[el.dataset.key] = el.textContent.trim();
      } else {
        custom[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
      }
    });
    return custom;
  }

  // نمایش فیلدها دیگر برحسبِ نوعِ built-in نیست: فیلدهای عمومی همیشه دیده می‌شوند،
  // فقط فیلدهای سفارشیِ همان نوع (renderCustom) داینامیک اضافه/عوض می‌شوند.
  function applyVisibility(loadedCustom) {
    const ty = findType(document.getElementById('f-task_type').value);
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
      title: g('f-title'),
      planned_date: g('f-planned_date'), status: g('f-status'),
      needs_review: document.getElementById('f-needs-review').checked,
      estimate_minutes: parseHM(g('f-estimate_minutes')), description: g('f-description'),
      checklist: readChecklist(),
    };
    // ماه گزارش: تک‌دراپ‌داونِ «سال-ماه» → به report_month + report_year تفکیک می‌شود
    const rp = g('f-report_period');
    if (rp) { const [y, m] = rp.split('-'); p.report_year = +y; p.report_month = +m; }
    else { p.report_year = null; p.report_month = null; }
    if (ty && ty.fields && ty.fields.length) {
      p.custom = readCustomValues();
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
    if (window.RichSelect) RichSelect.init();  // دراپ‌داونِ غنیِ پروژه/مسئول در مودال
    if (data.status) document.getElementById('f-status').value = data.status;
    // نیاز به بازبینی: با عوضِ مسئول، پیش‌فرضِ خودش را می‌گیرد؛ با تیک‌زدن/برداشتنِ
    // دستی، گزینه‌های وضعیت (انجام‌شده ⇄ تکمیل) دوباره ساخته می‌شوند.
    const needsReviewBox = document.getElementById('f-needs-review');
    const statusSel = document.getElementById('f-status');
    const revChip = document.querySelector('.topt-rev');
    const syncRevChip = () => { if (revChip) revChip.classList.toggle('on', needsReviewBox.checked); };
    const rebuildStatus = () => {
      const cur = statusSel.value;
      statusSel.innerHTML = statusOptions(cur, needsReviewBox.checked);
      if (!statusSel.value) statusSel.selectedIndex = 0;  // مقدارِ ازدست‌رفته → اولین گزینه
    };
    document.getElementById('f-assignee').addEventListener('change', (e) => {
      needsReviewBox.checked = colleagueNeedsReview(e.target.value);
      rebuildStatus(); syncRevChip();
    });
    // چیپِ «نیاز به بازبینی» در تولبار = تاگلِ همان چک‌باکسِ مخفی
    if (revChip) revChip.onclick = () => { needsReviewBox.checked = !needsReviewBox.checked; rebuildStatus(); syncRevChip(); };
    syncRevChip();
    const loaded = data.custom || {};
    // با عوض‌کردنِ نوع، مقادیرِ فعلیِ فیلدها را نگه دار و روی مقادیرِ اولیه merge کن؛
    // فیلدهایی که کلیدِ یکسان در نوعِ جدید دارند (مثلاً «کلمات کلیدی» در انتشار↔آپدیت)
    // حفظ می‌شوند، نه اینکه همه‌چیز بپرد (درخواستِ کاربر).
    document.getElementById('f-task_type').addEventListener('change', () => {
      Object.assign(loaded, readCustomValues());
      applyVisibility(loaded);
    });
    applyVisibility(loaded);
    // برچسبِ تاریخِ نسبی کنارِ «تاریخ برنامه» (امروز/فردا/۳ روز بعد) — اولیه + با انتخابِ تاریخ
    const relInit = () => {
      const inp = document.getElementById('f-planned_date'), h = document.getElementById('rel-planned');
      if (inp && h) h.textContent = inp.value ? '(' + (window.App && App.relDate(inp.value) || '') + ')' : '';
    };
    relInit();
    const pd = document.getElementById('f-planned_date');
    if (pd) pd.addEventListener('change', relInit);
    wireOptToolbar(data, id);  // تولبارِ بخش‌های اختیاری (توضیحات/چک‌لیست/تکرار/گزارش) + لود تنبلِ ادیتورها
    const histBtn = document.getElementById('fix-hist-toggle');  // باز کردن سوابق قبلی نیاز به اصلاح
    if (histBtn) histBtn.onclick = () => {
      document.querySelectorAll('[data-fix-item]').forEach((el, i) => { if (i > 0) el.style.display = ''; });
      histBtn.style.display = 'none';
    };
    wireRecur();               // نوار تکرار (تسک جدید)
    wireChecklist();           // چک‌لیستِ عمومی
    if (id) initKpis(id);      // نمایش KPI (تسک موجود)؛ گزارش تنبل در wireOptToolbar
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
        let savedId = id, resp;
        if (id) resp = await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: payload });
        else { resp = await App.fetchJSON('/tasks/api/', { method: 'POST', body: payload }); savedId = resp.id; }
        App.toast('ذخیره شد', 'ok');
        // اخطارِ نرمِ فیلدهای الزامیِ خالی (ذخیره انجام شد، فقط هشدار)
        if (resp && resp.warnings && resp.warnings.length) {
          App.toast('⚠ فیلدهای الزامیِ خالی: ' + resp.warnings.join('، '), 'warn', 6000);
        }
        if (again) { openTask(null); return; }
        App.closeModal();
        // بدونِ رفرش: ردیفِ لیستِ تسک‌ها را درجا به‌روز/درج می‌کنیم؛ اگر تقویمی روی صفحه بود
        // آن را اجاکسی نو می‌کنیم (حفظِ فیلتر)؛ وگرنه رفرشِ نرمِ صفحه.
        const done = await refreshTaskRow(savedId, !id);
        if (!done) {
          if (window.Calendar && Calendar.any()) Calendar.refreshAll();
          else setTimeout(() => location.reload(), 200);
        }
      } catch (_) {
        saving = false;
        btns.forEach((b) => { b.disabled = false; b.classList.remove('loading'); });
      }
    };
    const s = document.getElementById('t-save'); if (s) s.onclick = () => save(false);
    const n = document.getElementById('t-save-next'); if (n) n.onclick = () => save(true);
    const d = document.getElementById('t-del');
    if (d) d.onclick = async () => { if (await App.confirm('این تسک حذف شود؟')) { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'DELETE' }); App.closeModal();
      if (window.Calendar && Calendar.any()) Calendar.refreshAll(); else location.reload(); } };
  }
  window.openTask = openTask;

  // ── لینکِ عمیق: /tasks/?task=<id> مودالِ همان تسک را باز می‌کند (از اعلان‌ها) ──
  (function () {
    try {
      const id = new URLSearchParams(location.search).get('task');
      if (id) setTimeout(() => openTask(id), 60);
    } catch (_) {}
  })();

  // ── بازبینی: نوشتن موارد نیاز به اصلاح (TinyMCE) ──
  //   هر بار «نیاز به اصلاح» یک اصلاحِ *جدید* است → مودال همیشه خالی باز می‌شود (اصلاحاتِ
  //   قبلی در تاریخچهٔ TaskReviewNote می‌مانند و از آنجا قابلِ ویرایش‌اند).
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

  // ── ویرایشِ یک یادداشتِ بازبینیِ موجود (مدیر/نویسنده) ──
  function openReviewNoteEdit(noteId, curHtml) {
    App.openModal(
      `<div class="modal-h"><h3>ویرایشِ یادداشتِ بازبینی</h3><button class="x" onclick="App.closeModal()">×</button></div>
       <div class="modal-b"><textarea id="rn-edit" class="rich-editor" rows="5">${curHtml || ''}</textarea></div>
       <div class="modal-f"><button class="btn btn-p" id="rn-save">ذخیره</button><button class="btn" onclick="App.closeModal()">انصراف</button></div>`);
    if (window.RichText) RichText.init('#rn-edit');
    document.getElementById('rn-save').onclick = async () => {
      if (window.RichText) RichText.save();
      const note = document.getElementById('rn-edit').value;
      try {
        await App.fetchJSON(`/tasks/api/review-note/${noteId}/`, { method: 'PATCH', body: { note } });
        App.toast('ذخیره شد', 'ok'); App.closeModal();
        const body = document.querySelector(`[data-note-body="${noteId}"]`);
        if (body) body.innerHTML = note;
      } catch (_) {}
    };
  }
  document.addEventListener('click', (e) => {
    const ed = e.target.closest('[data-note-edit]'); if (!ed) return;
    e.stopPropagation(); e.preventDefault();
    const body = document.querySelector(`[data-note-body="${ed.dataset.noteEdit}"]`);
    openReviewNoteEdit(ed.dataset.noteEdit, body ? body.innerHTML : '');
  });

  // ── کلیک روی تگ «نیاز به اصلاح» → مودالِ تسک باز می‌شود؛ موارد و تاریخچه بالای همان مودال
  //    نمایش داده می‌شوند (دیگر مودال‌روی‌مودال نداریم). ──
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-fix-note]');
    if (t) { e.stopImmediatePropagation(); e.preventDefault(); openTask(t.dataset.fixNote); }
  });

  // ── به‌روزرسانیِ برچسبِ تاریخِ نسبی بعد از انتخابِ تاریخ (بدونِ رفرش) ──
  document.addEventListener('change', (e) => {
    const inp = e.target.closest('.reldate-input'); if (!inp) return;
    const lbl = inp.closest('.reldate-cell') && inp.closest('.reldate-cell').querySelector('.reldate-label');
    if (lbl) { lbl.textContent = (window.App && App.relDate(inp.value)) || inp.value; lbl.title = inp.value; }
  });

  // ── ویرایشِ زندهٔ جدول تسک‌ها (بدون دکمهٔ ذخیره) ──
  //    فیلدِ اصلی → {data-f: value}؛ فیلدِ سفارشی (data-cf) → {custom_patch:{key:value}}
  document.addEventListener('change', async (e) => {
    const el = e.target.closest('.tx-inline, .cf-inline'); if (!el) return;
    const tr = el.closest('tr'); if (!tr) return;
    let body;
    if (el.dataset.cf) {
      const v = el.type === 'checkbox' ? el.checked : el.value;
      body = { custom_patch: { [el.dataset.cf]: v } };
    } else if (el.dataset.f) {
      body = { [el.dataset.f]: el.value };
    } else { return; }
    try {
      const r = await App.fetchJSON(`/tasks/api/${tr.dataset.id}/`, { method: 'PATCH', body });
      App.toast('ذخیره شد', 'ok');
      updateMissReq(tr, r && r.warnings);   // بَجِ «⚠ ناقص» را زنده به‌روز کن
    } catch (_) {}
  });

  // بَجِ اخطارِ «فیلدهای الزامیِ خالی» را روی ردیف زنده می‌سازد/به‌روز می‌کند (بدونِ رفرش)
  function updateMissReq(tr, warnings) {
    if (!tr) return;
    const cell = tr.querySelector('.tcell'); if (!cell) return;
    let badge = cell.querySelector('.miss-req');
    if (warnings && warnings.length) {
      if (!badge) { badge = document.createElement('span'); badge.className = 'tag miss-req'; badge.textContent = '⚠ ناقص'; cell.appendChild(badge); }
      badge.title = 'فیلدهای الزامیِ خالی: ' + warnings.join('، ');
    } else if (badge) { badge.remove(); }
  }

  // ── تگ‌باکسِ درون‌جدولی (کلمات کلیدی/مترادف): + برای افزودن، × برای حذف ──
  function ctagPatch(box) {
    const tr = box.closest('tr'); if (!tr) return;
    const words = [...box.querySelectorAll('.ctag')].map((c) => c.dataset.w).filter(Boolean);
    App.fetchJSON(`/tasks/api/${tr.dataset.id}/`, { method: 'PATCH', body: { custom_patch: { [box.dataset.cf]: words } } })
      .then(() => App.toast('ذخیره شد', 'ok')).catch(() => {});
  }
  function ctagChip(w) {
    const s = document.createElement('span'); s.className = 'ctag'; s.dataset.w = w;
    s.textContent = w; const x = document.createElement('i'); x.className = 'ctag-x'; x.title = 'حذف'; x.textContent = '×';
    s.appendChild(x); return s;
  }
  document.addEventListener('click', async (e) => {
    const x = e.target.closest('.ctag-x');
    if (x) {
      e.stopPropagation();
      const chip = x.closest('.ctag'), box = x.closest('.cf-tags');
      const w = chip.dataset.w || '';
      if (!await App.confirm(`«${w}» حذف شود؟`)) return;   // تأیید قبلِ حذف
      chip.remove(); ctagPatch(box); return;
    }
    const add = e.target.closest('.ctag-add');
    if (add) {
      e.stopPropagation();
      const box = add.closest('.cf-tags');
      if (box.querySelector('.ctag-pop')) { box.querySelector('.ctag-pop').remove(); return; }
      const pop = document.createElement('div'); pop.className = 'ctag-pop';
      pop.innerHTML = '<input type="text" placeholder="کلمه… (Enter)"><button type="button">افزودن</button>';
      box.appendChild(pop);
      const inp = pop.querySelector('input'); inp.focus();
      const list = box.querySelector('.ctag-list');
      const commit = () => {
        const raw = inp.value.trim(); if (!raw) { pop.remove(); return; }
        // فقط ویرگولِ لاتین «,» جدا می‌کند؛ ویرگولِ فارسی «،» بخشی از کلمه می‌ماند (خواستِ کاربر)
        raw.split(',').map((w) => w.trim()).filter(Boolean).forEach((w) => {
          if (![...box.querySelectorAll('.ctag')].some((c) => c.dataset.w === w))
            list.appendChild(ctagChip(w));
        });
        pop.remove(); ctagPatch(box);
      };
      pop.querySelector('button').onclick = commit;
      inp.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); commit(); } if (ev.key === 'Escape') pop.remove(); });
    }
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
    if (row && !e.target.closest('a,select,input,button,.seo-drag,.cf-tags,.ctag-x,.ctag-add,.tedit')) openTask(row.dataset.openTask);
  });

  // ── عملیات گروهی ──
  const selected = () => Array.from(document.querySelectorAll('.row-check:checked')).map((c) => c.dataset.id);
  document.addEventListener('change', (e) => {
    if (e.target.matches('.row-check, .check-all')) {
      if (e.target.matches('.check-all')) document.querySelectorAll('.row-check').forEach((c) => (c.checked = e.target.checked));
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

  // ── تایمر تسک (ستون «زمان» لیست) — با delegation تا ردیف‌های بعداً اضافه‌شده
  //    (جدولِ تسک‌های آینده، لودِ تنبل) هم بدونِ سیم‌کشیِ دوباره کار کنند. ──
  // فرمتِ واحدِ زمان «H:MM» (هماهنگ با فیلترِ hm سرور و ویجتِ تایمر)
  function fmtMin(m) { m = Math.max(0, Math.round(m)); return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`; }
  function parseHM(s) {  // «1:30»→۹۰ ، «۹۰»→۹۰ ، خالی→null
    s = String(s == null ? '' : s).trim().replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
    if (!s) return null;
    if (s.includes(':')) { const [h, mm] = s.split(':'); return (parseInt(h, 10) || 0) * 60 + (parseInt(mm, 10) || 0); }
    return parseInt(s, 10) || 0;
  }
  window.fmtMin = fmtMin; window.parseHM = parseHM;
  function renderTimerCell(cell) {
    const val = cell.querySelector('.tval');
    const btn = cell.querySelector('.tbtn');
    if (!val) return;
    const running = cell.dataset.running === '1';
    const started = cell.dataset.started ? new Date(cell.dataset.started) : null;
    const base = +cell.dataset.spent || 0;
    if (running && started) {
      val.textContent = fmtMin(base + (Date.now() - started.getTime()) / 60000);
      if (btn) btn.textContent = '⏸'; cell.classList.add('running');
    } else { val.textContent = fmtMin(base); if (btn) btn.textContent = '▶'; cell.classList.remove('running'); }
  }
  function renderAllTimerCells() { document.querySelectorAll('.timer-cell').forEach(renderTimerCell); }
  renderAllTimerCells();
  setInterval(renderAllTimerCells, 15000);

  // وقتی تایمری از **ویجتِ سراسری** (یا جای دیگر) متوقف شد، سلولِ همان تسک در جدول هم
  // بدونِ رفرش استاپ شود (باگِ «بعد از استوپ در ویجت، جدول رفرش می‌خواست»).
  window.addEventListener('timer-changed', (e) => {
    const id = e.detail && e.detail.id; if (!id) return;
    const cell = document.querySelector(`.timer-cell[data-id="${id}"]`); if (!cell) return;
    cell.dataset.running = '0'; cell.dataset.started = '';
    if (e.detail.spent != null) cell.dataset.spent = e.detail.spent;
    renderTimerCell(cell);
  });

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.timer-cell .tbtn'); if (!btn) return;
    e.stopPropagation();
    const cell = btn.closest('.timer-cell');
    const id = cell.dataset.id;
    const running = cell.dataset.running === '1';
    try {
      const d = await App.fetchJSON(`/tasks/api/${id}/timer/`, { method: 'POST', body: { action: running ? 'stop' : 'start' } });
      cell.dataset.spent = d.spent_minutes; cell.dataset.running = d.timer_running ? '1' : '0';
      cell.dataset.started = d.timer_started || '';
      renderTimerCell(cell);
      // اگر با استارتِ این یکی تایمرِ دیگری از همین مسئول خودکار استاپ شد، آن سلول را هم به‌روز کن
      if (d.stopped_id) {
        const other = document.querySelector(`.timer-cell[data-id="${d.stopped_id}"]`);
        if (other) { other.dataset.spent = d.stopped_spent; other.dataset.running = '0'; other.dataset.started = ''; renderTimerCell(other); }
      }
      window.dispatchEvent(new CustomEvent('timer-changed'));  // به‌روزرسانی ویجت سراسری
    } catch (_) {}
  });
  document.addEventListener('click', async (e) => {
    const edit = e.target.closest('.timer-cell .tedit'); if (!edit) return;
    e.stopPropagation();
    const cell = edit.closest('.timer-cell');
    const id = cell.dataset.id;
    const cur = prompt('زمان کارکرد (H:MM):', fmtMin(+cell.dataset.spent || 0));
    if (cur === null) return;
    try { const d = await App.fetchJSON(`/tasks/api/${id}/timer/`, { method: 'PATCH', body: { minutes: parseHM(cur) } }); cell.dataset.spent = d.spent_minutes; renderTimerCell(cell); } catch (_) {}
  });

  // ── تعیینِ «تخمینِ زمان» با کلیک روی بخشِ تخمین (فقط جدولِ ویرایشی) ──
  document.addEventListener('click', async (e) => {
    const est = e.target.closest('.timer-cell .t-est.est-edit'); if (!est) return;
    e.stopPropagation();
    const cell = est.closest('.timer-cell'); const id = cell.dataset.id;
    const cur = prompt('تخمینِ زمان (H:MM):', '');
    if (cur === null) return;
    const mn = parseHM(cur);
    try {
      await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: { estimate_minutes: mn } });
      est.textContent = ' / ' + (mn ? fmtMin(mn) : '—');
      App.toast('تخمین ذخیره شد', 'ok');
    } catch (_) {}
  });

  // ── لودِ تنبل: اسکرول برای صفحه‌بندیِ جعبه‌ی «انجام‌شده‌ها» (بیش از ۵۰ ردیف) ──
  (function () {
    const lz = window.TASKS_LAZY;
    if (!lz) return;
    const tbody = document.querySelector('#done-tsheet tbody');
    if (!tbody) return;
    let loading = false;
    async function loadMore() {
      if (loading || !lz.hasMore) return;
      loading = true;
      const params = new URLSearchParams(location.search);
      params.set('page', lz.page + 1);
      try {
        const d = await App.fetchJSON(`/tasks/api/rows/?${params.toString()}`);
        tbody.insertAdjacentHTML('beforeend', d.html);
        if (window.RichSelect) RichSelect.init(tbody);  // دراپ‌داونِ غنیِ ردیف‌های تازه‌لودشده
        lz.page = d.page; lz.hasMore = d.has_more;
        renderAllTimerCells();
      } catch (_) { lz.hasMore = false; } finally { loading = false; }
    }
    window.addEventListener('scroll', () => {
      if (!lz.hasMore || loading) return;
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 400) loadMore();
    });
  })();

})();
