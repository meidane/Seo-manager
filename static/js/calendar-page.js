/* calendar-page.js — تقویم گوگل‌کلندری: ناوبری AJAX، آواتار نویسنده، انجام‌شده‌ی
   طوسی ته سلول، دکمه‌ی + با hover، درگ‌ودراپ تسک بین روزها. */
(function () {
  'use strict';
  let { year, month } = window.CAL_INIT;

  const grid = document.getElementById('cal-grid');
  const title = document.getElementById('cal-title');
  const q = () => {
    const p = new URLSearchParams({ year, month });
    ['project', 'assignee', 'type'].forEach((k) => {
      const el = document.getElementById('f-' + k);
      if (el && el.value) p.set(k, el.value);
    });
    return p.toString();
  };

  function av(t) {
    return t.avatar
      ? `<img class="tk-av" src="${t.avatar}" alt="">`
      : `<span class="tk-av" style="background:${t.a_color}">${t.initials || ''}</span>`;
  }
  function chip(t) {
    const style = t.done ? '' : `style="background:rgba(${t.color},.15);border-right:3px solid rgb(${t.color});color:rgb(${t.color})"`;
    return `<span class="tk${t.done ? ' done' : ''}${t.is_placeholder ? ' placeholder' : ''}" draggable="true" data-id="${t.id}" data-open-task="${t.id}" ${style}>` +
      `${av(t)}<span class="tk-tx">${t.type_label}: ${t.title}</span>${t.done ? '' : `<span class="tk-t">${t.time}</span>`}</span>`;
  }
  function cellHtml(c) {
    let h = `<div class="cell${c.is_holiday && !c.dim ? ' off' : ''}${c.dim ? ' dim' : ''}${c.is_today ? ' today' : ''}" data-date="${c.gdate}" data-jdate="${c.jdate}">` +
      `<div class="cell-h"><span class="dnum">${c.jday_fa}</span>` +
      `${c.holiday_title && !c.dim ? `<span class="hol">${c.holiday_title}</span>` : ''}` +
      `${c.tasks.length ? `<span class="cnt">${c.tasks.length.toLocaleString('fa-IR')}</span>` : ''}</div>`;
    if (!c.dim) h += `<button class="cell-add" data-jdate="${c.jdate}" title="تسک جدید در این روز">＋</button>`;
    c.tasks.slice(0, 5).forEach((t) => (h += chip(t)));
    if (c.tasks.length > 5) h += `<span class="more">+${(c.tasks.length - 5).toLocaleString('fa-IR')} مورد دیگر</span>`;
    return h + '</div>';
  }

  async function load() {
    try {
      const d = await App.fetchJSON('/calendar/api/?' + q());
      title.textContent = d.title;
      grid.innerHTML = d.days.map(cellHtml).join('');
      bindDnd();
    } catch (_) {}
  }

  function prev() { month--; if (month < 1) { month = 12; year--; } load(); }
  function next() { month++; if (month > 12) { month = 1; year++; } load(); }
  document.getElementById('cal-prev').onclick = prev;
  document.getElementById('cal-next').onclick = next;
  document.getElementById('cal-today').onclick = () => { year = window.CAL_INIT.year; month = window.CAL_INIT.month; load(); };
  ['f-project', 'f-assignee', 'f-type'].forEach((id) => { const el = document.getElementById(id); if (el) el.onchange = load; });

  // ── دکمه‌ی + هر روز → مودال تسک با تاریخ پرشده ──
  grid.addEventListener('click', (e) => {
    const add = e.target.closest('.cell-add');
    if (add && window.openTask) { e.stopPropagation(); window.openTask(null, { planned_date_fa: add.dataset.jdate }); }
  });

  // ── درگ‌ودراپ: چیپ روی سلول → PATCH تاریخ برنامه ──
  function bindDnd() {
    grid.querySelectorAll('.tk[draggable]').forEach((tk) => {
      tk.addEventListener('dragstart', (e) => { e.dataTransfer.setData('id', tk.dataset.id); tk.style.opacity = '.4'; });
      tk.addEventListener('dragend', () => { tk.style.opacity = ''; });
    });
    grid.querySelectorAll('.cell[data-date]').forEach((cell) => {
      cell.addEventListener('dragover', (e) => { e.preventDefault(); cell.classList.add('drop-hover'); });
      cell.addEventListener('dragleave', () => cell.classList.remove('drop-hover'));
      cell.addEventListener('drop', async (e) => {
        e.preventDefault(); cell.classList.remove('drop-hover');
        const id = e.dataTransfer.getData('id');
        if (!id) return;
        try { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: { planned_date_iso: cell.dataset.date } }); load(); }
        catch (_) {}
      });
    });
  }
  bindDnd();
})();
