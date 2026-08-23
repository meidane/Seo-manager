/* personal.js — تعاملِ فضای شخصی (فقط صفحه‌ی /personal/).
   از App.fetchJSON/openModal/closeModal/toast/confirm (app.js) و openTask (tasks.js) استفاده می‌کند.
   ساده و کم‌کد نگه داشته شده؛ عملیاتِ ساختاری (ویرایش/برنامه‌ریزی/افزودنِ عادت‌وهدف) صفحه را
   رفرش می‌کنند، عملیاتِ سبک (تیک/پلی/حذف/جابه‌جایی) درجا. */
(function () {
  const root = document.querySelector('.pers');
  if (!root) return;
  const WEEK = root.dataset.week, TODAY = root.dataset.today;
  const WD = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];  // شنبه=۰ .. جمعه=۶
  const esc = (v) => (v == null ? '' : String(v)).replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const api = (url, method, body) => App.fetchJSON(url, { method: method || 'GET', body });

  // ── تسک‌های شخصی: تیک/پلی/حذف/ویرایش (delegated روی هر دو لیست) ──
  function taskRowHtml(t, daily) {
    const grip = daily ? '<span class="pt-grip" title="جابه‌جایی">⋮⋮</span>' : '';
    const play = daily ? `<button class="pt-play${t.playing ? ' on' : ''}" title="پلی">${t.playing ? '⏸' : '▶'}</button>` : '';
    const plan = (!daily && t.planned_date) ? `<span class="pt-plan" title="برنامه‌ریزی‌شده">📅</span>` : '';
    return `<div class="pers-row${daily ? ' pers-drag' : ''}" data-id="${t.id}"${daily ? ' draggable="true"' : ''}>
      ${grip}${play}<input type="checkbox" class="pt-done"${t.done ? ' checked' : ''}>
      <span class="pt-title${t.done ? ' is-done' : ''}" data-edit>${esc(t.title)}</span>${plan}
      <button class="pt-x" title="حذف">×</button></div>`;
  }

  function wireTaskList(list, daily) {
    if (!list) return;
    list.addEventListener('click', async (e) => {
      const row = e.target.closest('.pers-row'); if (!row) return;
      const id = row.dataset.id;
      // تسکِ سیستمی → مودالِ تسکِ اصلی
      if (row.classList.contains('pers-sys')) {
        if (window.openTask) window.openTask(row.dataset.task);
        return;
      }
      if (e.target.classList.contains('pt-x')) {
        if (!await App.confirm('این کار حذف شود؟')) return;
        try { await api(`/personal/api/tasks/${id}/`, 'DELETE'); row.remove(); } catch (_) {}
        return;
      }
      if (e.target.classList.contains('pt-play')) {
        const on = !row.querySelector('.pt-play').classList.contains('on');
        try {
          await api(`/personal/api/tasks/${id}/`, 'PATCH', { playing: on });
          list.querySelectorAll('.pt-play.on').forEach((b) => { b.classList.remove('on'); b.textContent = '▶'; });
          const btn = row.querySelector('.pt-play');
          if (on) { btn.classList.add('on'); btn.textContent = '⏸'; }
        } catch (_) {}
        return;
      }
      if (e.target.classList.contains('pt-title')) openTaskModal(id, row);
    });
    list.addEventListener('change', async (e) => {
      if (!e.target.classList.contains('pt-done')) return;
      const row = e.target.closest('.pers-row');
      const done = e.target.checked;
      try {
        await api(`/personal/api/tasks/${row.dataset.id}/`, 'PATCH', { done });
        row.querySelector('.pt-title').classList.toggle('is-done', done);
      } catch (_) { e.target.checked = !done; }
    });
    if (daily) wireDrag(list);
  }

  // ── درگ‌ودراپِ باکسِ روزانه ──
  function wireDrag(list) {
    let dragged = null;
    list.addEventListener('dragstart', (e) => { dragged = e.target.closest('.pers-drag'); if (dragged) dragged.classList.add('dragging'); });
    list.addEventListener('dragend', async () => {
      if (!dragged) return;
      dragged.classList.remove('dragging'); dragged = null;
      const ids = [...list.querySelectorAll('.pers-drag')].map((r) => +r.dataset.id);
      try { await api('/personal/api/tasks/reorder/', 'POST', { ids }); } catch (_) {}
    });
    list.addEventListener('dragover', (e) => {
      e.preventDefault();
      const after = [...list.querySelectorAll('.pers-drag:not(.dragging)')].find((r) => {
        const box = r.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      if (!dragged) return;
      if (after) list.insertBefore(dragged, after); else list.appendChild(dragged);
    });
  }

  // ── افزودن به اینباکس ──
  const addInput = document.getElementById('inbox-title');
  const planInput = document.getElementById('inbox-plan');
  async function addInbox() {
    const title = addInput.value.trim();
    if (!title) return;
    const planned = (planInput.value || '').trim();
    try {
      const t = await api('/personal/api/tasks/', 'POST', { title, week: WEEK, planned_date: planned });
      // اگر برای امروز برنامه‌ریزی شد، رفرش تا در باکسِ امروز هم بیاید
      if (t.planned_date === TODAY) { location.reload(); return; }
      const list = document.getElementById('inbox-list');
      const empty = document.getElementById('inbox-empty'); if (empty) empty.remove();
      list.insertAdjacentHTML('beforeend', taskRowHtml(t, false));
      addInput.value = ''; planInput.value = ''; addInput.focus();
    } catch (_) {}
  }
  if (addInput) addInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addInbox(); } });
  const plus = document.getElementById('inbox-plus');
  if (plus) plus.onclick = addInbox;

  // ── مودالِ ویرایشِ تسکِ شخصی ──
  function openTaskModal(id, row) {
    const title = row.querySelector('.pt-title').textContent;
    App.openModal(`<div class="modal-h"><h3>ویرایش کار</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <label>عنوان</label><input id="p-title" class="input" value="${esc(title)}">
        <label>نوع</label><input id="p-kind" class="input" placeholder="اختیاری">
        <label>توضیحات</label><textarea id="p-note" class="input" rows="3"></textarea>
        <label>تاریخِ برنامه</label><input id="p-plan" class="input jdate" dir="ltr" readonly placeholder="۱۴۰۵/۰۵/۱۵">
        <div style="margin-top:8px"><button type="button" class="btn btn-sm" id="p-clear-plan">حذفِ تاریخ (بازگشت به اینباکس)</button></div>
      </div>
      <div class="modal-f"><button class="btn btn-p" id="p-save">ذخیره</button>
        <button class="btn" onclick="App.closeModal()">انصراف</button>
        <button class="btn" id="p-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button></div>`);
    let clearPlan = false;
    document.getElementById('p-clear-plan').onclick = () => { document.getElementById('p-plan').value = ''; clearPlan = true; };
    document.getElementById('p-plan').addEventListener('change', () => { clearPlan = false; });
    document.getElementById('p-save').onclick = async () => {
      const body = {
        title: document.getElementById('p-title').value.trim(),
        kind: document.getElementById('p-kind').value.trim(),
        note: document.getElementById('p-note').value,
      };
      const pv = document.getElementById('p-plan').value.trim();
      if (pv) body.planned_date = pv; else if (clearPlan) body.planned_date = '';
      if (!body.title) { App.toast('عنوان لازم است', 'warn'); return; }
      try { await api(`/personal/api/tasks/${id}/`, 'PATCH', body); App.closeModal(); location.reload(); } catch (_) {}
    };
    document.getElementById('p-del').onclick = async () => {
      if (!await App.confirm('این کار حذف شود؟')) return;
      try { await api(`/personal/api/tasks/${id}/`, 'DELETE'); App.closeModal(); location.reload(); } catch (_) {}
    };
  }

  wireTaskList(document.getElementById('inbox-list'), false);
  wireTaskList(document.getElementById('daily-list'), true);

  // ── هبیت ترکر: تیکِ سلول ──
  const habitList = document.getElementById('habit-list');
  if (habitList) {
    habitList.addEventListener('click', async (e) => {
      const cell = e.target.closest('.habit-cell');
      if (cell && !cell.disabled) {
        const habit = cell.dataset.habit, d = cell.dataset.date;
        try {
          const r = await api('/personal/api/habits/toggle/', 'POST', { habit, date: d });
          cell.classList.toggle('done', r.done);
          cell.querySelector('.hc-mark').textContent = r.done ? '✓' : '·';
          recomputePct(cell.closest('.habit-row'));
        } catch (_) {}
        return;
      }
      const title = e.target.closest('.habit-title');
      if (title) openHabitModal(title.closest('.habit-row'));
    });
  }
  function recomputePct(rowEl) {
    const cells = [...rowEl.querySelectorAll('.habit-cell.active:not(.future)')];
    const done = cells.filter((c) => c.classList.contains('done')).length;
    const pct = cells.length ? Math.round(done / cells.length * 100) : 0;
    rowEl.querySelector('.habit-pct').textContent = toFa(pct) + '٪';
  }
  const toFa = (n) => String(n).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);

  // ── مودالِ عادت (افزودن/ویرایش) ──
  function habitModalHtml(h) {
    const wset = h ? (h.weekdays ? h.weekdays.split(',') : []) : [];
    const pol = h ? h.polarity : 'good';
    const chips = WD.map((w, i) => `<span class="wd-chip${wset.includes(String(i)) ? ' on' : ''}" data-wd="${i}">${w}</span>`).join('');
    return `<div class="modal-h"><h3>${h ? 'ویرایش عادت' : 'عادت جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <label>عنوان</label><input id="h-title" class="input" value="${h ? esc(h.title) : ''}">
        <label>روزهای هفته</label><div class="wd-row" id="h-days">${chips}</div>
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
      const body = {
        title: document.getElementById('h-title').value.trim(),
        weekdays: [...document.querySelectorAll('#h-days .wd-chip.on')].map((c) => +c.dataset.wd),
        polarity: (document.querySelector('#h-pol .pol-opt.on') || {}).dataset ? document.querySelector('#h-pol .pol-opt.on').dataset.pol : 'good',
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
    const h = { title: rowEl.dataset.title, weekdays: rowEl.dataset.weekdays, polarity: rowEl.dataset.polarity };
    App.openModal(habitModalHtml(h)); wireHabitModal(rowEl.dataset.id);
  }
  const habitNew = document.getElementById('habit-new');
  if (habitNew) habitNew.onclick = () => { App.openModal(habitModalHtml(null)); wireHabitModal(null); };

  // ── اهداف (افزودن/ویرایش) ──
  function goalModalHtml(g) {
    return `<div class="modal-h"><h3>${g ? 'ویرایش هدف' : 'هدف جدید'}</h3><button class="x" onclick="App.closeModal()">×</button></div>
      <div class="modal-b">
        <label>عنوان</label><input id="g-title" class="input" value="${g ? esc(g.title) : ''}">
        <label>توضیحات</label><textarea id="g-desc" class="input" rows="3">${g ? esc(g.desc) : ''}</textarea>
        <div class="grid2"><div><label>شروع</label><input id="g-start" class="input jdate" dir="ltr" readonly value="${g ? esc(g.start) : ''}"></div>
        <div><label>پایان</label><input id="g-end" class="input jdate" dir="ltr" readonly value="${g ? esc(g.end) : ''}"></div></div>
      </div>
      <div class="modal-f"><button class="btn btn-p" id="g-save">ذخیره</button>
        <button class="btn" onclick="App.closeModal()">انصراف</button>
        ${g ? '<button class="btn" id="g-del" style="margin-inline-start:auto;color:var(--danger)">حذف</button>' : ''}</div>`;
  }
  function wireGoalModal(id) {
    document.getElementById('g-save').onclick = async () => {
      const body = {
        title: document.getElementById('g-title').value.trim(),
        description: document.getElementById('g-desc').value,
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
  const goalList = document.getElementById('goal-list');
  if (goalList) goalList.addEventListener('click', (e) => {
    const t = e.target.closest('.goal-title'); if (!t) return;
    const row = t.closest('.goal-row');
    App.openModal(goalModalHtml({ title: row.dataset.title, desc: row.dataset.desc, start: row.dataset.start, end: row.dataset.end }));
    wireGoalModal(row.dataset.id);
  });
  const goalNew = document.getElementById('goal-new');
  if (goalNew) goalNew.onclick = () => { App.openModal(goalModalHtml(null)); wireGoalModal(null); };

  // ── ثانیه‌شمارِ عمر ──
  const birth = new Date(root.dataset.birth + 'T00:00:00');
  const death = new Date(root.dataset.death + 'T00:00:00');
  const total = death - birth;
  const elLived = document.getElementById('life-lived');
  const elFill = document.getElementById('life-fill');
  const elPct = document.getElementById('life-pct');
  const elLeft = document.getElementById('life-left');
  const elTick = document.getElementById('life-tick');
  function tickLife() {
    const now = new Date();
    const lived = now - birth, left = Math.max(death - now, 0);
    const pct = Math.min(lived / total * 100, 100);
    const days = Math.floor(lived / 86400000);
    const yrs = (lived / (365.25 * 86400000));
    elLived.textContent = toFa(yrs.toFixed(4)) + ' سال';
    elFill.style.width = pct.toFixed(2) + '%';
    elPct.textContent = toFa(pct.toFixed(1)) + '٪ گذشته';
    const leftDays = Math.floor(left / 86400000);
    elLeft.textContent = toFa(leftDays.toLocaleString('en-US')) + ' روز مانده';
    const leftSec = Math.floor(left / 1000);
    elTick.textContent = toFa(leftSec.toLocaleString('en-US')) + ' ثانیه';
  }
  tickLife();
  setInterval(tickLife, 1000);
})();
