/* calendar.js — ماژولِ واحدِ تقویم (صفحهٔ /calendar/ + فضای شخصی + امبدِ تب‌ها).
   روی هر `[data-cal]` سوار می‌شود. فیلتر/ناوبریِ اجاکسی، دکمهٔ +، درگ بین روزها،
   پنلِ «تسک‌های بدون تاریخ» + فیلدِ سریع + درگ از پنل روی روز.
   بعدِ ذخیرهٔ تسک در مودال، `Calendar.refreshAll()` همهٔ تقویم‌ها را بدونِ رفرشِ صفحه نو می‌کند. */
(function () {
  'use strict';
  const instances = [];
  const esc = (v) => (v == null ? '' : String(v)).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const faNum = (n) => String(n).replace(/[0-9]/g, (x) => '۰۱۲۳۴۵۶۷۸۹'[x]);
  const hrs = (mn) => Math.round(mn / 60 * 10) / 10;

  function av(t) {
    return t.avatar
      ? `<img class="tk-av" src="${t.avatar}" alt="">`
      : `<span class="tk-av" style="background:${t.a_color}">${esc(t.initials || '')}</span>`;
  }
  function chip(t, extra) {
    const pc = t.project_color || t.color;
    const style = `style="${t.done ? '' : `background:rgba(${pc},.20);`}border-right:4px solid rgb(${pc})"`;
    const attrs = t.virtual ? '' : ` draggable="true" data-id="${t.id}" data-open-task="${t.id}"`;
    const title = `${t.type_label}: ${t.title}${t.project ? ' — ' + t.project : ''}`;
    return `<span class="tk${extra ? ' tk-extra' : ''}${t.done ? ' done' : ''}${t.is_placeholder ? ' placeholder' : ''}${t.virtual ? ' virtual' : ''}"${attrs} title="${esc(title)}" ${style}>` +
      `${av(t)}<span class="tk-tx">${esc(t.type_label)}: ${esc(t.title)}</span></span>`;
  }
  function peopleRow(c) {
    if (!c.people || !c.people.length) return '';
    const one = (p) => {
      const a = p.avatar ? `<img class="cp-av" src="${p.avatar}" alt="">`
        : `<span class="cp-av" style="background:${p.a_color}">${esc(p.initials || '')}</span>`;
      const tt = `${esc(p.name)} — ${p.count} تسک${p.minutes ? ' · ' + hrs(p.minutes) + ' ساعت' : ''}`;
      return `<span class="cp" title="${tt}">${a}${p.minutes ? `<b class="cp-h">${hrs(p.minutes)}h</b>` : ''}</span>`;
    };
    return `<div class="cell-people">${c.people.map(one).join('')}</div>`;
  }
  function cellHtml(c, canCreate) {
    let h = `<div class="cell${c.is_holiday && !c.dim ? ' off' : ''}${c.dim ? ' dim' : ''}${c.is_today ? ' today' : ''}" data-date="${c.gdate}" data-jdate="${c.jdate}">` +
      `<div class="cell-h"><span class="dnum">${c.jday_fa}</span>` +
      `${c.holiday_title && !c.dim ? `<span class="hol">${esc(c.holiday_title)}</span>` : ''}` +
      `${c.tasks.length ? `<span class="cnt">${c.tasks.length.toLocaleString('en-US')}</span>` : ''}` +
      (() => { const mn = c.tasks.reduce((s, t) => s + (t.estimate_minutes || 0), 0); return mn ? `<span class="cnt-h" title="جمعِ زمانِ تخمینیِ این روز">${hrs(mn)}h</span>` : ''; })() + '</div>';
    h += peopleRow(c);
    if (!c.dim && canCreate) h += `<button type="button" class="cell-add" data-jdate="${c.jdate}" title="تسک جدید در این روز">＋</button>`;
    c.tasks.forEach((t, i) => (h += chip(t, i >= 5)));
    if (c.tasks.length > 5) h += `<button type="button" class="more" data-more>+${(c.tasks.length - 5).toLocaleString('en-US')} مورد دیگر</button>`;
    return h + '</div>';
  }
  function undatedItem(t) {
    const pc = t.project_color || t.color;
    return `<div class="calx-uitem" draggable="true" data-id="${t.id}" data-open-task="${t.id}" title="${esc(t.type_label)}: ${esc(t.title)}${t.project ? ' — ' + esc(t.project) : ''}" style="border-right:4px solid rgb(${pc})">` +
      `${av(t)}<span class="calx-uitem-tx">${esc(t.title)}</span>` +
      `${t.project ? `<span class="calx-uitem-pj" style="color:rgb(${pc})">${esc(t.project)}</span>` : ''}</div>`;
  }

  function mount(root) {
    const grid = root.querySelector('[data-cal-grid]');
    if (!grid) return;
    const canCreate = root.dataset.canCreate === '1';
    const fixedAssignee = root.dataset.fixedAssignee || '';
    const panel = root.querySelector('[data-undated-panel]');
    const undatedList = root.querySelector('[data-undated-list]');
    const uBadge = root.querySelector('[data-undated-count]');
    let year = +root.dataset.year, month = +root.dataset.month;
    let showUndated = root.dataset.undated === '1';

    const monthSel = root.querySelector('.calx-month');
    const yearSel = root.querySelector('.calx-year');

    function q() {
      const p = new URLSearchParams({ year, month });
      if (fixedAssignee) p.set('assignee', fixedAssignee);
      root.querySelectorAll('[data-cf]').forEach((el) => { if (el.value) p.set(el.dataset.cf, el.value); });
      if (showUndated) p.set('undated', '1');
      return p.toString();
    }
    function syncNav() {
      if (monthSel) monthSel.value = String(month);
      if (yearSel) {
        if (![...yearSel.options].some((o) => +o.value === year)) {
          const o = document.createElement('option'); o.value = year; o.textContent = faNum(year); yearSel.appendChild(o);
          [...yearSel.options].sort((a, b) => +a.value - +b.value).forEach((op) => yearSel.appendChild(op));
        }
        yearSel.value = String(year);
      }
    }
    function renderUndated(list) {
      if (!panel) return;
      panel.hidden = !showUndated;
      const btn = root.querySelector('[data-cal-undated-toggle]');
      if (btn) btn.classList.toggle('on', showUndated);
      if (!showUndated) return;
      list = list || [];
      if (uBadge) { uBadge.hidden = !list.length; uBadge.textContent = faNum(list.length); }
      undatedList.innerHTML = list.length ? list.map(undatedItem).join('')
        : '<div class="calx-undated-empty">تسکِ بدون تاریخی نیست</div>';
      bindUndatedDnd();
    }

    // موبایل: در اولین باز شدن، اسکرولِ افقیِ گرید را روی «امروز» ببر تا روزهای جاری دیده شوند
    let didScroll = false;
    function maybeScrollToToday() {
      if (didScroll) return;
      const wrap = root.querySelector('.calx-grid-wrap');
      const today = grid.querySelector('.cell.today');
      if (!wrap || !today) return;
      didScroll = true;
      if (wrap.scrollWidth <= wrap.clientWidth + 4) return;  // بدونِ اسکرولِ افقی (دسکتاپ)
      const wr = wrap.getBoundingClientRect(), tr = today.getBoundingClientRect();
      wrap.scrollLeft += (tr.left + tr.width / 2) - (wr.left + wr.width / 2);
    }

    let seq = 0;
    async function load() {
      const s = ++seq;
      try {
        const d = await App.fetchJSON('/calendar/api/?' + q());
        if (s !== seq) return;
        year = d.year; month = d.month;
        grid.innerHTML = d.days.map((c) => cellHtml(c, canCreate)).join('');
        syncNav(); bindGridDnd();
        if (showUndated) renderUndated(d.undated);
        maybeScrollToToday();
      } catch (_) {}
    }

    // ── ناوبری + فیلترها ──
    root.querySelector('[data-cal-prev]').onclick = () => { month--; if (month < 1) { month = 12; year--; } load(); };
    root.querySelector('[data-cal-next]').onclick = () => { month++; if (month > 12) { month = 1; year++; } load(); };
    root.querySelector('[data-cal-today]').onclick = () => { year = +root.dataset.year; month = +root.dataset.month; load(); };
    if (monthSel) monthSel.onchange = () => { month = +monthSel.value; load(); };
    if (yearSel) yearSel.onchange = () => { year = +yearSel.value; load(); };
    root.querySelectorAll('[data-cf]').forEach((el) => el.addEventListener('change', load));
    const uToggle = root.querySelector('[data-cal-undated-toggle]');
    if (uToggle) uToggle.onclick = () => {
      showUndated = !showUndated;
      uToggle.classList.toggle('on', showUndated);
      if (panel) panel.hidden = !showUndated;   // CSS: .calx-undated[hidden]{display:none}
      load();
    };

    // ── کلیکِ سلول: دکمهٔ + / باز-بستِ «N مورد دیگر» ──
    grid.addEventListener('click', (e) => {
      const add = e.target.closest('.cell-add');
      if (add && window.openTask) { e.stopPropagation(); window.openTask(null, { planned_date_fa: add.dataset.jdate }); return; }
      const more = e.target.closest('[data-more]');
      if (more) {
        e.stopPropagation();
        const cell = more.closest('.cell');
        if (!more.dataset.label) more.dataset.label = more.textContent;
        const open = cell.classList.toggle('expanded');
        more.textContent = open ? 'بستن' : more.dataset.label;
      }
    });

    // ── درگِ چیپِ روز / آیتمِ بدون‌تاریخ → سلولِ روز = تعیینِ تاریخ ──
    function bindGridDnd() {
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
          try { await App.fetchJSON(`/tasks/api/${id}/`, { method: 'PATCH', body: { planned_date_iso: cell.dataset.date } }); load(); } catch (_) {}
        });
      });
    }
    function bindUndatedDnd() {
      if (!undatedList) return;
      undatedList.querySelectorAll('.calx-uitem[draggable]').forEach((it) => {
        it.addEventListener('dragstart', (e) => { e.dataTransfer.setData('id', it.dataset.id); it.style.opacity = '.4'; });
        it.addEventListener('dragend', () => { it.style.opacity = ''; });
      });
    }

    // ── کلیکِ آیتمِ بدون‌تاریخ → مودالِ تسک ──
    if (undatedList) undatedList.addEventListener('click', (e) => {
      const it = e.target.closest('[data-open-task]');
      if (it && window.openTask) window.openTask(+it.dataset.openTask);
    });

    // ── فیلدِ سریعِ افزودن (بدون تاریخ) ──
    const qaddForm = root.querySelector('[data-qadd-form]');
    if (qaddForm) qaddForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const inp = qaddForm.querySelector('[data-qadd]');
      const title = inp.value.trim(); if (!title) return;
      const body = { title };
      if (root.dataset.personal) body.personal = 1;
      else {
        const pf = root.querySelector('[data-cf="project"]');
        body.project = (pf && pf.value) || root.dataset.quickProject || '';
        const af = root.querySelector('[data-cf="assignee"]');
        if (fixedAssignee) body.assignee = fixedAssignee; else if (af && af.value) body.assignee = af.value;
      }
      try {
        await App.fetchJSON('/calendar/api/quick-add/', { method: 'POST', body });
        inp.value = ''; inp.focus(); load();
      } catch (err) {
        // اگر پروژه لازم بود → مودالِ کامل با عنوانِ پرشده
        if (window.openTask) { window.openTask(null, { title }); inp.value = ''; }
      }
    });

    load();
    instances.push({ load });
  }

  window.Calendar = {
    mountAll() { document.querySelectorAll('[data-cal]').forEach((el) => { if (!el.dataset.mounted) { el.dataset.mounted = '1'; mount(el); } }); },
    refreshAll() { instances.forEach((i) => i.load()); },
    any() { return instances.length > 0; },
  };
  document.addEventListener('DOMContentLoaded', () => window.Calendar.mountAll());
})();
