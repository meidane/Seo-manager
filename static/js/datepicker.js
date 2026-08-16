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

  function close() { if (pop) { pop.remove(); pop = null; target = null; } }

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
    document.body.appendChild(pop);
    const r = input.getBoundingClientRect();
    pop.style.top = (window.scrollY + r.bottom + 4) + 'px';
    pop.style.insetInlineStart = (window.scrollX + r.left) + 'px';
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
})();
