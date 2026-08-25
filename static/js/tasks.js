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
      <div class="tmodal-grid">
        <!-- ستونِ راست (اصلی): اطلاعاتِ تسک -->
        <div class="tmodal-left">
          <!-- ردیفِ ۴ستونه: پروژه / مسئول / نوع / وضعیت -->
          <div class="grid4">
            ${field('project', 'پروژه', `<select id="f-project" class="rich-select"><option value="">— انتخاب —</option>${cfg.projects.map(([v, l, color, img]) => optRich(v, l, t.project_id, color, img)).join('')}</select>`)}
            ${field('assignee', 'مسئول', assigneeSelect)}
            ${field('task_type', 'نوع تسک', `<select id="f-task_type">${typeOptions(typeSel)}</select>`)}
            ${field('status', 'وضعیت', `<select id="f-status">${statusOptions(t.status, needsReviewDefault)}</select>`)}
          </div>
          ${field('title', 'عنوان', `<input id="f-title" class="input" value="${esc(t.title)}">`)}
          <!-- ردیفِ ۴ستونه: تاریخ / تخمین / ماه گزارش -->
          <div class="grid4">
            ${field('planned_date', 'تاریخ برنامه', `<div style="display:flex;align-items:center"><input id="f-planned_date" class="input jdate" dir="ltr" readonly value="${t.planned_date_fa || ''}"><span id="rel-planned" class="rel-hint"></span></div>`)}
            ${field('estimate_minutes', 'تخمین (H:MM)', `<input id="f-estimate_minutes" class="input" dir="ltr" placeholder="0:00" value="${t.estimate_minutes ? fmtMin(t.estimate_minutes) : ''}">`)}
            ${field('report_month', 'ماه گزارش', reportPeriodSelect(t))}
          </div>
          ${recurBarHtml(t)}
          <label style="display:flex;align-items:center;gap:8px;margin:0 0 14px;cursor:pointer">
            <input type="checkbox" id="f-needs-review" ${needsReviewDefault ? 'checked' : ''}>
            بازبینی
          </label>
          <!-- فیلدهای سفارشی نوع (کلمه کلیدی/مترادف/... هرکدام یک ردیفِ کامل) -->
          <div id="custom-fields" style="display:none"></div>
        </div>
        <!-- ستونِ چپ: چک‌لیست (بالا) + توضیحات + گزارش + تاریخچه -->
        <div class="tmodal-right">
          ${checklistHtml(t)}
          ${t.id ? '<div id="kpi-box" style="display:none;margin-bottom:12px"></div>' : ''}
          ${field('description', 'توضیحات', `<textarea id="f-description" class="rich-editor" rows="4">${esc(t.description)}</textarea>`)}
          ${t.id ? `<div class="report-sec">
            <label style="font-weight:700">گزارش</label>
            <textarea id="f-report" class="rich-editor" rows="3"></textarea>
            <div style="margin-top:6px;display:flex;gap:8px;align-items:center">
              <button type="button" class="btn btn-sm btn-p" id="report-send">ارسال گزارش</button>
              <button type="button" class="btn btn-sm" id="report-cancel" style="display:none">لغو ویرایش</button>
            </div>
            <div id="report-list" class="report-list"></div>
          </div>` : ''}
          ${historyHtml(t)}
        </div>
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
        <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer"><input type="checkbox" id="rec-skip" checked> رد کردن تعطیلات</label>
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

  // ── تاریخچهٔ تسک (آیکنِ کوچک پایینِ مودال، جمع‌شونده) ──
  function historyHtml(t) {
    if (!t || !t.id) return '';
    const hs = t.history || [];
    const item = (h) => {
      const ch = Object.keys(h.changes || {}).map((k) =>
        `<div class="hist-ch"><b>${esc(k)}</b>: <span class="hist-old">${esc(h.changes[k][0])}</span> ← <span class="hist-new">${esc(h.changes[k][1])}</span></div>`).join('');
      return `<div class="hist-item"><div class="hist-meta"><span class="hist-badge hist-${h.action}">${esc(h.action_label)}</span> · ${esc(h.user)} · ${esc(h.when)}</div>${ch}</div>`;
    };
    const body = hs.length ? hs.map(item).join('') : '<div class="zero" style="padding:8px">تاریخچه‌ای نیست</div>';
    const faNum = String(hs.length);
    return `<div class="hist-box"><button type="button" class="hist-toggle" id="hist-toggle">🕐 تاریخچهٔ تسک (${faNum})</button><div class="hist-list" id="hist-list" style="display:none">${body}</div></div>`;
  }

  // ── چیپ‌های کلمه/برچسب (Enter یا دکمه‌ی + اضافه می‌کند؛ ویرگول خودکار جدا می‌شود) ──
  function tagChip(word) {
    // data-w روی خودِ چیپ (span) — چون collect()/dedup از `.tagbox-chip`.dataset.w می‌خوانند،
    // نه از آیکنِ ×. (باگِ قبلی: data-w روی <i> بود → collect همیشه undefined→[None] ذخیره می‌کرد
    // و بعدِ ذخیره چیپِ خالی فقط با × می‌ماند.)
    return `<span class="tag t-mute tagbox-chip" data-w="${esc(word)}">${esc(word)}<i class="tagbox-x">×</i></span>`;
  }
  function tagboxHtml(key, words, placeholder) {
    const chips = (words || []).map(tagChip).join('');
    return `<div class="tagbox cf" data-key="${key}" data-kind="tags">
      <div class="tagbox-chips">${chips}</div>
      <div class="tagbox-field"><input type="text" class="tagbox-input" placeholder="${esc(placeholder || 'بنویس و Enter بزن…')}"><button type="button" class="tagbox-add" title="افزودن">＋</button></div>
    </div>`;
  }
  function tagboxAddWords(box, raw) {
    const chipsWrap = box.querySelector('.tagbox-chips');
    const existing = new Set([...box.querySelectorAll('.tagbox-chip')].map((c) => c.dataset.w));
    raw.split(',').map((w) => w.trim()).filter((w) => w && !existing.has(w)).forEach((w) => {
      existing.add(w);
      chipsWrap.insertAdjacentHTML('beforeend', tagChip(w));
    });
  }
  // یک‌بار روی #custom-fields سیم‌کشی می‌شود (نه هر renderCustom، چون innerHTML عوض می‌شود
  // ولی خودِ نودِ box ثابت می‌ماند — الگوی delegation مثل بقیه‌ی مودال).
  function wireTagboxes(box) {
    if (box.dataset.tagWired) return;
    box.dataset.tagWired = '1';
    box.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || !e.target.matches('.tagbox-input')) return;
      e.preventDefault();
      const tb = e.target.closest('.tagbox');
      if (e.target.value.trim()) { tagboxAddWords(tb, e.target.value); e.target.value = ''; }
    });
    box.addEventListener('click', (e) => {
      const add = e.target.closest('.tagbox-add');
      if (add) { const tb = add.closest('.tagbox'); const inp = tb.querySelector('.tagbox-input');
        if (inp.value.trim()) { tagboxAddWords(tb, inp.value); inp.value = ''; } return; }
      const x = e.target.closest('.tagbox-x');
      if (x) x.closest('.tagbox-chip').remove();
    });
  }

  // عرضِ فیلدِ سفارشی در گریدِ ۱۲ستونه (از تنظیماتِ نوعِ تسک)
  const CF_SPAN = { full: 12, half: 6, third: 4, quarter: 3 };

  // ── رندر فیلدهای سفارشی یک نوع ──
  function renderCustom(t, values) {
    const box = document.getElementById('custom-fields');
    if (!t || !t.fields || !t.fields.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
    values = values || {};
    box.style.display = 'grid';
    wireTagboxes(box);
    box.innerHTML = t.fields.map((f) => {
      const span = CF_SPAN[f.width] || 12;
      const v = values[f.key] != null ? values[f.key] : '';
      let input;
      if (f.kind === 'tags') input = tagboxHtml(f.key, Array.isArray(v) ? v : [], f.placeholder);
      else if (f.kind === 'textarea') input = `<textarea class="cf" data-key="${f.key}" rows="2" placeholder="${esc(f.placeholder)}">${esc(v)}</textarea>`;
      else if (f.kind === 'checkbox') input = `<label style="display:flex;align-items:center;gap:8px;margin:0"><input type="checkbox" class="cf" data-key="${f.key}" ${v ? 'checked' : ''}> ${esc(f.label)}</label>`;
      else if (f.kind === 'select') input = `<select class="cf" data-key="${f.key}"><option value="">—</option>${f.options.map((o) => opt(o, o, v)).join('')}</select>`;
      else if (f.kind === 'number') input = `<input type="number" class="cf input" data-key="${f.key}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      else input = `<input type="text" class="cf input" data-key="${f.key}" dir="${f.kind === 'url' ? 'ltr' : 'rtl'}" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
      if (f.kind === 'checkbox') return `<div class="field" data-cf style="grid-column:span ${span}">${input}</div>`;
      const req = f.required ? ' *' : (f.required_on_done ? ' (برای تکمیل الزامی)' : '');
      return `<div class="field" data-cf style="grid-column:span ${span}"><label>${esc(f.label)}${req}</label>${input}</div>`;
    }).join('');
  }

  // مقادیرِ فعلیِ فیلدهای سفارشی را از DOM می‌خواند (منبعِ واحد؛ collect و تعویضِ نوع
  // هر دو از این می‌خوانند تا با عوض‌کردنِ نوع، فیلدهای هم‌کلید حفظ شوند).
  function readCustomValues() {
    const custom = {};
    document.querySelectorAll('#custom-fields .cf').forEach((el) => {
      if (el.dataset.kind === 'tags') {
        const pend = el.querySelector('.tagbox-input');
        if (pend && pend.value.trim()) { tagboxAddWords(el, pend.value); pend.value = ''; }
        custom[el.dataset.key] = [...el.querySelectorAll('.tagbox-chip')]
          .map((c) => c.dataset.w).filter((w) => w && w.trim());
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
    const rebuildStatus = () => {
      const cur = statusSel.value;
      statusSel.innerHTML = statusOptions(cur, needsReviewBox.checked);
      if (!statusSel.value) statusSel.selectedIndex = 0;  // مقدارِ ازدست‌رفته → اولین گزینه
    };
    document.getElementById('f-assignee').addEventListener('change', (e) => {
      needsReviewBox.checked = colleagueNeedsReview(e.target.value);
      rebuildStatus();
    });
    needsReviewBox.addEventListener('change', rebuildStatus);
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
    if (window.RichText) RichText.init('#f-description');  // ادیتور غنی توضیحات
    const histBtn = document.getElementById('fix-hist-toggle');  // باز کردن سوابق قبلی نیاز به اصلاح
    if (histBtn) histBtn.onclick = () => {
      document.querySelectorAll('[data-fix-item]').forEach((el, i) => { if (i > 0) el.style.display = ''; });
      histBtn.style.display = 'none';
    };
    const histToggle = document.getElementById('hist-toggle');  // تاریخچهٔ تسک
    if (histToggle) histToggle.onclick = () => {
      const l = document.getElementById('hist-list');
      l.style.display = l.style.display === 'none' ? '' : 'none';
    };
    wireRecur();               // نوار تکرار (تسک جدید)
    wireChecklist();           // چک‌لیستِ عمومی
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
        let savedId = id;
        if (id) await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: payload });
        else { const r = await App.fetchJSON('/tasks/api/', { method: 'POST', body: payload }); savedId = r.id; }
        App.toast('ذخیره شد', 'ok');
        if (again) { openTask(null); return; }
        App.closeModal();
        // بدونِ رفرش: ردیفِ لیستِ تسک‌ها را درجا به‌روز/درج می‌کنیم؛ اگر نشد، رفرشِ نرم
        const done = await refreshTaskRow(savedId, !id);
        if (!done) setTimeout(() => location.reload(), 200);
      } catch (_) {
        saving = false;
        btns.forEach((b) => { b.disabled = false; b.classList.remove('loading'); });
      }
    };
    const s = document.getElementById('t-save'); if (s) s.onclick = () => save(false);
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
    try { await App.fetchJSON(`/tasks/api/${tr.dataset.id}/`, { method: 'PATCH', body }); App.toast('ذخیره شد', 'ok'); }
    catch (_) {}
  });

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
        // ویرگول → چند کلمه
        raw.replace(/،/g, ',').split(',').map((w) => w.trim()).filter(Boolean).forEach((w) => {
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
