/* finance.js — تعاملات ماک‌آپ حسابداری (داده‌ی ساختگی):
   ساب‌نویگیشن، جدول اکسل‌مانند با حرکت کیبوردی، عملیات گروهی، ویزارد ورود اکسل. */
(function () {
  // ── ساب‌نویگیشن مالی ──
  const NAV = [
    ['finance.html', 'داشبورد'],
    ['finance-transactions.html', 'تراکنش‌ها'],
    ['finance-import.html', 'ورود اکسل'],
    ['finance-banks.html', 'بانک‌ها'],
    ['finance-payroll.html', 'حقوق'],
  ];
  const holder = document.getElementById('fin-nav');
  if (holder) {
    const cur = document.body.dataset.fin || '';
    holder.className = 'fin-nav';
    holder.innerHTML = NAV.map(([h, l]) =>
      `<a href="${h}" class="${h === cur ? 'on' : ''}">${l}</a>`).join('');
  }

  // ── جدول اکسل‌مانند: حرکت با کیبورد + انتخاب + عملیات گروهی ──
  const sheet = document.querySelector('table.sheet');
  if (sheet) {
    const editable = ['proj', 'cat', 'note']; // ستون‌های قابل‌ویرایش
    let active = null; // {r,c}

    function cells() { return Array.from(sheet.querySelectorAll('tbody td[data-c]')); }
    function at(r, c) { return sheet.querySelector(`tbody tr[data-r="${r}"] td[data-c="${c}"]`); }

    function focusCell(r, c) {
      sheet.querySelectorAll('td.active').forEach((x) => x.classList.remove('active'));
      const td = at(r, c);
      if (!td) return;
      td.classList.add('active');
      active = { r, c };
      td.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }

    function edit(td) {
      if (!editable.includes(td.dataset.c)) return;
      const cur = td.querySelector('.cv').textContent.trim();
      td.innerHTML = `<input class="cell-input" value="${cur === '—' ? '' : cur}">`;
      const inp = td.querySelector('input');
      inp.focus(); inp.select();
      const done = () => {
        const v = inp.value.trim();
        td.innerHTML = `<span class="cv">${v || '—'}</span>`;
        td.classList.add('active');
      };
      inp.addEventListener('blur', done);
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { done(); const r = +td.closest('tr').dataset.r; focusCell(r + 1, td.dataset.c); e.preventDefault(); }
        if (e.key === 'Escape') { td.innerHTML = `<span class="cv">${cur}</span>`; td.classList.add('active'); }
      });
    }

    sheet.addEventListener('click', (e) => {
      const td = e.target.closest('td[data-c]'); if (!td) return;
      focusCell(+td.closest('tr').dataset.r, td.dataset.c);
    });
    sheet.addEventListener('dblclick', (e) => {
      const td = e.target.closest('td[data-c]'); if (td) edit(td);
    });

    const COLS = ['date', 'desc', 'dep', 'wd', 'bal', 'proj', 'cat', 'note'];
    document.addEventListener('keydown', (e) => {
      if (!active || /input/i.test(e.target.tagName)) return;
      const ci = COLS.indexOf(active.c);
      if (e.key === 'ArrowDown' || e.key === 'Enter') { focusCell(active.r + 1, active.c); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { focusCell(active.r - 1, active.c); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { focusCell(active.r, COLS[Math.min(ci + 1, COLS.length - 1)]); e.preventDefault(); }
      else if (e.key === 'ArrowRight') { focusCell(active.r, COLS[Math.max(ci - 1, 0)]); e.preventDefault(); }
      else if (e.key === 'F2' || (e.key.length === 1 && !e.ctrlKey && !e.metaKey)) { const td = at(active.r, active.c); if (td) edit(td); }
    });

    // انتخاب و نوار عملیات گروهی
    const bar = document.getElementById('bulkbar');
    function refresh() {
      const n = sheet.querySelectorAll('.row-check:checked').length;
      if (bar) { bar.style.display = n ? 'flex' : 'none'; const c = document.getElementById('bulk-count'); if (c) c.textContent = n.toLocaleString('fa-IR'); }
    }
    sheet.addEventListener('change', (e) => {
      if (e.target.matches('.row-check')) { e.target.closest('tr').classList.toggle('sel-row', e.target.checked); refresh(); }
      if (e.target.id === 'check-all') { sheet.querySelectorAll('.row-check').forEach((c) => { c.checked = e.target.checked; c.closest('tr').classList.toggle('sel-row', e.target.checked); }); refresh(); }
    });
    focusCell(0, 'proj');
  }

  // ── ویزارد ورود اکسل ──
  window.finStep = function (n) {
    document.querySelectorAll('[data-step]').forEach((el) => { el.style.display = +el.dataset.step === n ? '' : 'none'; });
    document.querySelectorAll('.stepper .st').forEach((el, i) => {
      el.classList.toggle('on', i === n - 1);
      el.classList.toggle('done', i < n - 1);
    });
  };
})();
