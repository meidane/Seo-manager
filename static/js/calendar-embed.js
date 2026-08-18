/* calendar-embed.js — تقویم فیلترشده‌ی قابل‌جاسازی در تب‌ها (سینگل پروژه/همکار).
   استفاده: <div data-cal-embed data-project="3"></div>  یا  data-assignee="5"
   به App.fetchJSON وابسته است. ماه جاری را می‌گیرد و prev/next دارد. */
(function () {
  'use strict';

  function chip(t) {
    return `<span class="tk${t.done ? ' done' : ''}" ` +
      `style="background:rgba(${t.color},.15);border-right:3px solid rgb(${t.color});color:rgb(${t.color})">` +
      `${t.type_label}: ${t.title}</span>`;
  }
  function cell(c) {
    let h = `<div class="cell${c.is_holiday && !c.dim ? ' off' : ''}${c.dim ? ' dim' : ''}${c.is_today ? ' today' : ''}">` +
      `<div class="cell-h"><span class="dnum">${c.jday_fa}</span>` +
      `${c.holiday_title && !c.dim ? `<span class="hol">${c.holiday_title}</span>` : ''}` +
      `${c.tasks.length ? `<span class="cnt">${c.tasks.length.toLocaleString('en-US')}</span>` : ''}</div>`;
    c.tasks.slice(0, 4).forEach((t) => (h += chip(t)));
    if (c.tasks.length > 4) h += `<span class="more">+${(c.tasks.length - 4).toLocaleString('en-US')} مورد دیگر</span>`;
    return h + '</div>';
  }

  const DOW = '<div class="grid7"><div class="dow">شنبه</div><div class="dow">یکشنبه</div><div class="dow">دوشنبه</div><div class="dow">سه‌شنبه</div><div class="dow">چهارشنبه</div><div class="dow">پنجشنبه</div><div class="dow off">جمعه</div></div>';

  function mount(el) {
    const fixed = {};
    if (el.dataset.project) fixed.project = el.dataset.project;
    if (el.dataset.assignee) fixed.assignee = el.dataset.assignee;
    let year, month; // با اولین لود از پاسخ پر می‌شوند

    el.innerHTML =
      `<div class="cal-bar"><button class="nav-b" data-nav="next">›</button><h3 data-title>—</h3><button class="nav-b" data-nav="prev">‹</button></div>` +
      DOW + `<div class="grid7" data-grid></div>`;
    const grid = el.querySelector('[data-grid]');
    const title = el.querySelector('[data-title]');

    async function load(y, m) {
      const p = new URLSearchParams(fixed);
      if (y) { p.set('year', y); p.set('month', m); }
      try {
        const d = await App.fetchJSON('/calendar/api/?' + p.toString());
        year = d.year; month = d.month; title.textContent = d.title;
        grid.innerHTML = d.days.map(cell).join('');
      } catch (_) {}
    }
    el.querySelector('[data-nav="prev"]').onclick = () => { month--; if (month < 1) { month = 12; year--; } load(year, month); };
    el.querySelector('[data-nav="next"]').onclick = () => { month++; if (month > 12) { month = 1; year++; } load(year, month); };
    load();
  }

  window.CalendarEmbed = {
    mountAll() { document.querySelectorAll('[data-cal-embed]').forEach((el) => { if (!el.dataset.mounted) { el.dataset.mounted = '1'; mount(el); } }); },
  };
  document.addEventListener('DOMContentLoaded', () => window.CalendarEmbed.mountAll());
})();
