/* personal.js — تعاملِ فضای شخصی (فقط /personal/).
   بالای صفحه = تقویمِ مشترک (calendar.js؛ اینباکس/برنامهٔ هفته حذف شدند و جایشان را
   تقویم + پنلِ «تسک‌های بدون تاریخ» گرفت). اینجا فقط عادت‌ها/اهداف/عمر مانده‌اند؛
   یادداشت‌ها اسکریپتِ inlineِ خودشان را در index.html دارند. */
(function () {
  const root = document.querySelector('.pers');
  if (!root) return;
  const esc = (v) => (v == null ? '' : String(v)).replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const toFa = (n) => String(n).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);
  const api = (url, method, body) => App.fetchJSON(url, { method: method || 'GET', body });

  // ── هبیت ترکر ──
  const WD = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
  const habitList = document.getElementById('habit-list');
  if (habitList) {
    habitList.addEventListener('click', async (e) => {
      const cell = e.target.closest('.habit-cell');
      if (cell && !cell.disabled) {
        try {
          const r = await api('/personal/api/habits/toggle/', 'POST', { habit: cell.dataset.habit, date: cell.dataset.date });
          cell.classList.toggle('done', r.done);
          cell.querySelector('.hc-mark').textContent = r.done ? '✓' : (cell.classList.contains('active') ? '•' : '');
          recomputeHabitPct(cell.closest('.habit-row'));
        } catch (_) {}
        return;
      }
      const title = e.target.closest('.habit-title');
      if (title) openHabitModal(title.closest('.habit-row'));
    });
  }
  function recomputeHabitPct(rowEl) {
    // شمارنده = هر روزِ انجام‌شده (هدف یا نه)؛ مخرج = روزهای هدفِ هفته (اگر هیچ = ۷). سقفِ ۱۰۰.
    const doneDays = rowEl.querySelectorAll('.habit-cell.done:not(.future)').length;
    const target = rowEl.querySelectorAll('.habit-cell.active').length || 7;
    rowEl.querySelector('.habit-pct').textContent = toFa(Math.min(100, Math.round(doneDays / target * 100))) + '٪';
  }
  function habitModalHtml(h) {
    const wset = h && h.weekdays ? h.weekdays.split(',') : [];
    const pol = h ? h.polarity : 'good';
    const chips = WD.map((w, i) => `<span class="wd-chip${wset.includes(String(i)) ? ' on' : ''}" data-wd="${i}">${w}</span>`).join('');
    return `<div class="modal-h"><h3>${h ? 'ویرایش عادت' : 'عادت جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <label>عنوان</label><input id="h-title" class="input" value="${h ? esc(h.title) : ''}">
        <label>روزهای هدف</label><div class="wd-row" id="h-days">${chips}</div>
        <label style="margin-top:10px">نوع</label>
        <div class="pol-row" id="h-pol">
          <span class="pol-opt good${pol === 'good' ? ' on' : ''}" data-pol="good">مثبت</span>
          <span class="pol-opt bad${pol === 'bad' ? ' on' : ''}" data-pol="bad">منفی</span>
        </div>
      </div>
      <div class="modal-f"><button class="btn btn-p" id="h-save">ذخیره</button>
        <button class="btn" onclick="App.closeModal()">انصراف</button>
        ${h ? '<button class="btn" id="h-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}</div>`;
  }
  function wireHabitModal(id) {
    document.getElementById('h-days').addEventListener('click', (e) => { const c = e.target.closest('.wd-chip'); if (c) c.classList.toggle('on'); });
    document.getElementById('h-pol').addEventListener('click', (e) => {
      const o = e.target.closest('.pol-opt'); if (!o) return;
      document.querySelectorAll('#h-pol .pol-opt').forEach((x) => x.classList.remove('on')); o.classList.add('on');
    });
    document.getElementById('h-save').onclick = async () => {
      const sel = document.querySelector('#h-pol .pol-opt.on');
      const body = {
        title: document.getElementById('h-title').value.trim(),
        weekdays: [...document.querySelectorAll('#h-days .wd-chip.on')].map((c) => +c.dataset.wd),
        polarity: sel ? sel.dataset.pol : 'good',
      };
      if (!body.title) { App.toast('عنوان لازم است', 'warn'); return; }
      try {
        if (id) await api(`/personal/api/habits/${id}/`, 'PATCH', body);
        else await api('/personal/api/habits/', 'POST', body);
        App.closeModal(); location.reload();
      } catch (_) {}
    };
    const del = document.getElementById('h-del');
    if (del) del.onclick = async () => {
      if (!await App.confirm('این عادت و سوابقش حذف شوند؟')) return;
      try { await api(`/personal/api/habits/${id}/`, 'DELETE'); App.closeModal(); location.reload(); } catch (_) {}
    };
  }
  function openHabitModal(rowEl) {
    App.openModal(habitModalHtml({ title: rowEl.dataset.title, weekdays: rowEl.dataset.weekdays, polarity: rowEl.dataset.polarity }));
    wireHabitModal(rowEl.dataset.id);
  }
  const habitNew = document.getElementById('habit-new');
  if (habitNew) habitNew.onclick = () => { App.openModal(habitModalHtml(null)); wireHabitModal(null); };

  // ── درگ‌ودراپِ قابلِ‌استفادهٔ مجدد (یک‌جا نوشته، همه‌جا استفاده) ──
  function makeSortable(list, sel, onDrop) {
    let dr = null;
    list.addEventListener('dragstart', (e) => { dr = e.target.closest(sel); if (dr) dr.classList.add('dragging'); });
    list.addEventListener('dragend', () => { if (!dr) return; dr.classList.remove('dragging'); const el = dr; dr = null; onDrop([...list.querySelectorAll(sel)].map((r) => +r.dataset.id), el); });
    list.addEventListener('dragover', (e) => {
      e.preventDefault(); if (!dr) return;
      const after = [...list.querySelectorAll(sel + ':not(.dragging)')].find((r) => { const b = r.getBoundingClientRect(); return e.clientY < b.top + b.height / 2; });
      if (after) list.insertBefore(dr, after); else list.appendChild(dr);
    });
  }
  window.makeSortable = makeSortable;

  // ── اهداف: مودالِ ویرایش (رنگ + TinyMCE) ──
  function goalEditHtml(g) {
    const color = (g && g.color) || '#6366F1';
    return `<div class="modal-h"><h3>${g ? 'ویرایش هدف' : 'هدف جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <div class="grid2"><div><label>عنوان</label><input id="g-title" class="input" value="${g ? esc(g.title) : ''}"></div>
        <div><label>رنگ</label><input id="g-color" type="color" class="input g-color" value="${color}"></div></div>
        <label>توضیحات</label><textarea id="g-desc" class="rich-editor" rows="4">${g ? esc(g.description || '') : ''}</textarea>
        <div class="grid2"><div><label>شروع</label><input id="g-start" class="input jdate" dir="ltr" readonly value="${g ? esc(g.start_num || '') : ''}"></div>
        <div><label>پایان</label><input id="g-end" class="input jdate" dir="ltr" readonly value="${g ? esc(g.end_num || '') : ''}"></div></div>
      </div>
      <div class="modal-f"><button class="btn btn-p" id="g-save">ذخیره</button>
        <button class="btn" onclick="App.closeModal()">انصراف</button>
        ${g ? '<button class="btn" id="g-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}</div>`;
  }
  function openGoalEdit(g) {
    App.openModal(goalEditHtml(g));
    if (window.RichText) RichText.init('#g-desc');
    const id = g && g.id;
    document.getElementById('g-save').onclick = async () => {
      if (window.RichText) RichText.save();
      const body = {
        title: document.getElementById('g-title').value.trim(),
        description: document.getElementById('g-desc').value,
        color: document.getElementById('g-color').value,
        start_date: document.getElementById('g-start').value.trim(),
        end_date: document.getElementById('g-end').value.trim(),
      };
      if (!body.title || !body.start_date || !body.end_date) { App.toast('عنوان، شروع و پایان لازم است', 'warn'); return; }
      try {
        if (id) await api(`/personal/api/goals/${id}/`, 'PATCH', body);
        else await api('/personal/api/goals/', 'POST', body);
        App.closeModal(); location.reload();
      } catch (_) {}
    };
    const del = document.getElementById('g-del');
    if (del) del.onclick = async () => {
      if (!await App.confirm('این هدف حذف شود؟')) return;
      try { await api(`/personal/api/goals/${id}/`, 'DELETE'); App.closeModal(); location.reload(); } catch (_) {}
    };
  }

  // ── اهداف: مودالِ جزئیات (متا + توضیحات + تسک‌های مرتبط + افزودن + جابه‌جایی) ──
  const gtRow = (t) => `<div class="gt-row" data-id="${t.id}" draggable="true"><span class="gt-grip">⋮⋮</span>` +
    `<span class="gt-title${t.done ? ' is-done' : ''}">${esc(t.title)}</span>${t.planned ? '<span class="gt-date" title="برنامه‌ریزی‌شده">📅</span>' : ''}` +
    `<button class="gt-x" title="جدا کردن از هدف">×</button></div>`;
  async function openGoalDetail(id) {
    let g; try { g = await api(`/personal/api/goals/${id}/`); } catch (_) { return; }
    App.openModal(`<div class="modal-h"><h3><i class="goal-dot" style="background:${g.color}"></i> ${esc(g.title)}</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <div class="gd-meta">${g.start_fa} – ${g.end_fa}</div>
        ${g.description ? `<div class="rich gd-desc">${g.description}</div>` : ''}
        <label style="font-weight:700;margin:12px 0 6px;display:block">تسک‌های مرتبط</label>
        <div class="gt-list" id="gt-list">${g.tasks.map(gtRow).join('') || '<div class="zero" id="gt-zero">تسکی وصل نشده</div>'}</div>
        <div class="pers-add" style="margin-top:8px"><input id="gt-new" class="input" placeholder="تسکِ جدید برای این هدف…"><button class="btn btn-p" id="gt-add">＋</button></div>
      </div>
      <div class="modal-f"><button class="btn" id="gd-edit">ویرایشِ هدف</button><button class="btn" onclick="App.closeModal()">بستن</button></div>`);
    const list = document.getElementById('gt-list'), inp = document.getElementById('gt-new');
    const add = async () => {
      const title = inp.value.trim(); if (!title) return;
      try {
        const t = await api(`/personal/api/goals/${id}/add-task/`, 'POST', { title });
        const z = document.getElementById('gt-zero'); if (z) z.remove();
        list.insertAdjacentHTML('beforeend', gtRow({ id: t.id, title: t.title, done: false, planned: null }));
        inp.value = ''; inp.focus();
      } catch (_) {}
    };
    document.getElementById('gt-add').onclick = add;
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } });
    list.addEventListener('click', async (e) => {
      if (!e.target.classList.contains('gt-x')) return;
      const row = e.target.closest('.gt-row');
      try { await api(`/personal/api/tasks/${row.dataset.id}/goal/`, 'PATCH', { goal: null }); row.remove(); } catch (_) {}
    });
    makeSortable(list, '.gt-row', (ids) => { api(`/personal/api/goals/${id}/reorder/`, 'POST', { ids }).catch(() => {}); });
    document.getElementById('gd-edit').onclick = () => openGoalEdit(g);
  }

  const goalList = document.getElementById('goal-list');
  if (goalList) goalList.addEventListener('click', (e) => {
    const row = e.target.closest('.goal-row'); if (row) openGoalDetail(row.dataset.id);
  });
  const goalNew = document.getElementById('goal-new');
  if (goalNew) goalNew.onclick = () => openGoalEdit(null);

  // ── عمر: شمارشِ باقی‌مانده به صورتِ «سال/روز/ساعت/دقیقه/ثانیه» ──
  const birth = new Date(root.dataset.birth + 'T00:00:00');
  const death = new Date(root.dataset.death + 'T00:00:00');
  const total = death - birth;
  const elCount = document.getElementById('life-count');
  const elFill = document.getElementById('life-fill');
  const elPct = document.getElementById('life-pct');
  const elLeftD = document.getElementById('life-left-days');
  function tickLife() {
    if (!elCount || !elFill || !elPct || !elLeftD) return;  // DOM ناقص → بی‌سروصدا رد شو
    const now = new Date();
    const lived = now - birth;
    const pct = Math.min(Math.max(lived / total * 100, 0), 100);
    let rem = Math.max(death - now, 0) / 1000;  // ثانیه
    const yr = Math.floor(rem / (365.25 * 86400)); rem -= yr * 365.25 * 86400;
    const dd = Math.floor(rem / 86400); rem -= dd * 86400;
    const hh = Math.floor(rem / 3600); rem -= hh * 3600;
    const mm = Math.floor(rem / 60); rem -= mm * 60;
    const ss = Math.floor(rem);
    elCount.textContent = `${toFa(yr)} سال و ${toFa(dd)} روز و ${toFa(hh)} ساعت و ${toFa(mm)} دقیقه و ${toFa(ss)} ثانیه`;
    elFill.style.width = pct.toFixed(3) + '%';
    elPct.textContent = toFa(pct.toFixed(1)) + '٪ گذشته';
    elLeftD.textContent = toFa(Math.floor(Math.max(death - now, 0) / 86400000).toLocaleString('en-US')) + ' روز';
  }
  if (elCount) { tickLife(); setInterval(tickLife, 1000); }
})();
