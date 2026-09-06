/* datepicker.js — دیت‌پیکر شمسی برای هر <input class="jdate">.
   پاپ‌آور ماهانه از /calendar/api/picker/ می‌گیرد؛ تعطیلات قرمز، امروز مشخص.
   کلیک روی روز → فیلد پر می‌شود (شمسی). به App.fetchJSON وابسته است. */
(function () {
  'use strict';
  const FA = '۰۱۲۳۴۵۶۷۸۹';
  // اعداد لاتین (طبق درخواست: نمایشِ همه‌ی اعداد انگلیسی) — تاریخِ ورودی هم لاتین می‌شود
  const toFa = (s) => String(s).replace(/[۰-۹]/g, (d) => FA.indexOf(d));
  const toEn = (s) => String(s).replace(/[۰-۹]/g, (d) => FA.indexOf(d));

  let pop = null, target = null, y = 0, m = 0;
  let preview = null, hoverTimer = null;
  const dayCache = {};   // کشِ تسک‌های هر روز (به‌ازای jdate) تا هاورِ مکرر دوباره فچ نکند

  function killPreview() {
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
    if (preview) { preview.remove(); preview = null; }
  }
  function close() { killPreview(); if (pop) { pop.remove(); pop = null; target = null; } }

  async function render() {
    const params = new URLSearchParams();
    if (y && m) { params.set('year', y); params.set('month', m); }
    let d;
    try { d = await App.fetchJSON('/calendar/api/picker/?' + params.toString()); } catch (_) { return; }
    y = d.year; m = d.month;
    const cur = toEn((target.value || '').trim());
    const dow = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
    pop.innerHTML =
      `<div class="dp-head"><button class="dp-nav" data-nav="next">›</button><h4>${d.title}</h4><button class="dp-nav" data-nav="prev">‹</button></div>` +
      `<div class="dp-grid">${dow.map((x, i) => `<div class="dp-dow"${i === 6 ? ' style="color:#FF9AAB"' : ''}>${x}</div>`).join('')}` +
      d.days.map((c) => {
        const cls = ['dp-day', c.dim ? 'dim' : '', c.is_today ? 'today' : '', c.is_holiday ? 'hol' : '', cur === c.jdate ? 'sel' : ''].filter(Boolean).join(' ');
        return `<div class="${cls}" data-jdate="${c.jdate}" title="${c.holiday_title || ''}">${c.jday_fa}</div>`;
      }).join('') + '</div>';
  }

  function open(input) {
    close();
    target = input;
    // ماه اولیه از مقدار فعلی فیلد
    const v = toEn((input.value || '').trim()).split('/');
    if (v.length === 3 && +v[0] > 1300) { y = +v[0]; m = +v[1]; } else { y = 0; m = 0; }
    pop = document.createElement('div');
    pop.className = 'dp-pop';
    pop.addEventListener('mouseleave', killPreview);   // خروجِ موس از تقویم → بستنِ پیش‌نمایش
    document.body.appendChild(pop);
    const r = input.getBoundingClientRect();
    pop.style.top = (window.scrollY + r.bottom + 4) + 'px';
    // مختصاتِ سندی با left (نه inset-inline-start که در RTL به right نگاشت می‌شود و پاپ‌آور
    // را دور از فیلد می‌بُرد)؛ با کلمپ تا از لبهٔ صفحه بیرون نزند.
    const vw = document.documentElement.clientWidth;
    let left = window.scrollX + r.left;
    left = Math.max(6 + window.scrollX, Math.min(left, window.scrollX + vw - 268));  // عرضِ تقریبیِ پاپ‌آور
    pop.style.left = left + 'px';
    pop.style.insetInlineStart = 'auto';
    pop.style.right = 'auto';
    render();
  }

  // باز کردن روی فوکوس/کلیک فیلدهای jdate
  document.addEventListener('focusin', (e) => { if (e.target.matches('input.jdate')) open(e.target); });
  document.addEventListener('click', (e) => {
    if (e.target.matches('input.jdate')) { if (!pop || target !== e.target) open(e.target); return; }
    if (pop && !e.target.closest('.dp-pop')) close();
  });

  // تعامل داخل پاپ‌آور
  document.addEventListener('click', (e) => {
    if (!pop) return;
    const nav = e.target.closest('.dp-nav');
    if (nav) {
      if (nav.dataset.nav === 'prev') { m--; if (m < 1) { m = 12; y--; } } else { m++; if (m > 12) { m = 1; y++; } }
      render(); return;
    }
    const day = e.target.closest('.dp-day');
    if (day && target) { target.value = toFa(day.dataset.jdate); target.dispatchEvent(new Event('change', { bubbles: true })); close(); }
  });
  window.addEventListener('resize', close);

  // ── پیش‌نمایشِ سلولِ تقویمِ همان روز روی هاورِ یک روز (کنارِ پاپ‌آور) ──
  const FA2 = (s) => String(s).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);
  function renderPreview(jdate, data) {
    if (!pop) return;
    if (!preview) { preview = document.createElement('div'); preview.className = 'dp-preview glass'; document.body.appendChild(preview); }
    const tasks = (data && data.tasks) || [];
    const chips = tasks.slice(0, 8).map((t) => {
      const pc = t.project_color || t.color || '143,160,184';
      const av = t.avatar
        ? `<img class="dpp-av" src="${t.avatar}">`
        : `<span class="dpp-av" style="background:${t.a_color || '#8FA0B8'}">${(t.initials || '').replace(/"/g, '')}</span>`;
      const tl = `${t.type_label ? t.type_label + ': ' : ''}${t.title || ''}`.replace(/</g, '&lt;');
      return `<div class="dpp-tk${t.done ? ' done' : ''}" style="border-right:3px solid rgb(${pc})" title="${tl.replace(/"/g, '&quot;')}">${av}<span class="dpp-tx">${tl}</span>${t.time ? `<span class="dpp-t">${t.time}</span>` : ''}</div>`;
    }).join('');
    const more = tasks.length > 8 ? `<div class="dpp-more">+${FA2(tasks.length - 8)} مورد دیگر</div>` : '';
    preview.innerHTML = `<div class="dpp-h">${FA2(jdate)}${tasks.length ? ` · ${FA2(tasks.length)} تسک` : ''}</div>` +
      (tasks.length ? chips + more : '<div class="dpp-empty">تسکی برای این روز نیست</div>');
    // کنارِ پاپ‌آور (سمتِ چپش)، هم‌ترازِ بالای پاپ‌آور
    const r = pop.getBoundingClientRect();
    let left = window.scrollX + r.left - 246;                 // ۲۳۰px عرض + کمی فاصله
    if (left < window.scrollX + 6) left = window.scrollX + r.right + 8;  // اگر جا نبود، سمتِ راست
    preview.style.top = (window.scrollY + r.top) + 'px';
    preview.style.left = left + 'px';
  }
  document.addEventListener('mouseover', (e) => {
    const day = e.target.closest && e.target.closest('.dp-day');
    if (!day || !pop || !pop.contains(day) || day.classList.contains('dim')) { return; }
    const jdate = day.dataset.jdate;
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(async () => {
      if (jdate in dayCache) { renderPreview(jdate, dayCache[jdate]); return; }
      try { const d = await App.fetchJSON('/calendar/api/day/?date=' + encodeURIComponent(jdate)); dayCache[jdate] = d; renderPreview(jdate, d); } catch (_) {}
    }, 220);
  });
  document.addEventListener('mouseout', (e) => {
    const day = e.target.closest && e.target.closest('.dp-day');
    if (day) { if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; } }
  });
})();
