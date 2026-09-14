/* timer-widget.js — ویجت سراسریِ «در حال انجام» گوشهٔ پایین-راست (RTL).
   هرکس فقط تسکِ در حالِ اجرای خودش را (با دکمهٔ توقف) می‌بیند؛ اگر مدیرِ کسی باشد،
   تسکِ در حالِ اجرای زیرمجموعه‌هایش را هم می‌بیند، فقط‌خواندنی (بدونِ دکمهٔ توقف).
   جعبه چسبیده به پایینِ صفحه است و یک دکمهٔ فلشِ باز/بسته دارد — پیش‌فرض باز، ولی
   تصمیمِ کاربر (بسته) در localStorage می‌ماند. */
(function () {
  'use strict';
  const box = document.getElementById('timer-widget');
  if (!box) return;
  let items = [];
  try { items = JSON.parse(document.getElementById('running-timers-data').textContent || '[]'); } catch (_) {}

  const LS_KEY = 'timerWidgetCollapsed';   // تصمیمِ باز/بستهٔ کاربر (پیش‌فرض باز)
  let collapsed = false;
  try { collapsed = localStorage.getItem(LS_KEY) === '1'; } catch (_) {}
  function saveCollapsed() { try { localStorage.setItem(LS_KEY, collapsed ? '1' : '0'); } catch (_) {} }

  const esc = (v) => (v || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  function fmt(mins) {  // همیشه «H:MM» (۶ دقیقه = 0:06، نه 6:00)
    const m = Math.max(0, Math.round(mins));
    return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`;
  }
  function elapsed(it) {
    return (it.spent || 0) + (it.started ? (Date.now() - new Date(it.started).getTime()) / 60000 : 0);
  }
  function render() {
    if (!items.length) { box.classList.remove('on'); box.innerHTML = ''; return; }
    box.classList.add('on');
    box.classList.toggle('collapsed', collapsed);
    const mine = items.filter((it) => it.mine);
    const subs = items.filter((it) => !it.mine);
    // هدرِ همیشه‌دیده: عنوان + شمارش + دکمهٔ فلشِ باز/بسته (وقتی بسته است فقط همین می‌ماند)
    let html = `<div class="tw-head">
        <span class="tw-head-t">در حال انجام<span class="tw-count">${items.length}</span></span>
        <button class="tw-toggle" type="button" aria-expanded="${collapsed ? 'false' : 'true'}"
          title="${collapsed ? 'باز کردن' : 'بستن'}">▾</button>
      </div>`;
    let body = '';
    if (mine.length) {
      body += mine.map((it) => `<div class="tw-row" data-id="${it.id}">
          <span class="tw-dot"></span>
          <span class="tw-tt" title="${esc(it.title)}">${it.title || 'تسک'}</span>
          <span class="tw-time">${fmt(elapsed(it))}</span>
          <button class="tw-stop" data-id="${it.id}" title="توقف">■</button></div>`).join('');
    }
    if (subs.length) {
      body += `<div class="tw-h"${mine.length ? ' style="margin-top:8px"' : ''}>زیرمجموعه‌ها</div>` +
        subs.map((it) => `<div class="tw-row tw-sub">
          <span class="tw-dot"></span>
          <span class="tw-tt" title="${esc(it.title)}"><b>${esc(it.assignee)}</b> — ${it.title || 'تسک'}</span>
          <span class="tw-time">${fmt(elapsed(it))}</span></div>`).join('');
    }
    box.innerHTML = html + `<div class="tw-body">${body}</div>`;
  }
  async function refresh() {
    try { const d = await App.fetchJSON('/tasks/api/running/'); items = d.running || []; render(); } catch (_) {}
  }
  box.addEventListener('click', async (e) => {
    const tg = e.target.closest('.tw-toggle');
    if (tg) { collapsed = !collapsed; saveCollapsed(); render(); return; }
    const s = e.target.closest('.tw-stop'); if (!s) return;
    try { const d = await App.fetchJSON(`/tasks/api/${s.dataset.id}/timer/`, { method: 'POST', body: { action: 'stop' } });
      items = items.filter((x) => String(x.id) !== String(s.dataset.id)); render();
      // idِ متوقف‌شده + زمانِ نهایی را می‌فرستیم تا سلولِ همین تسک در جدول هم بدونِ رفرش استاپ شود
      window.dispatchEvent(new CustomEvent('timer-changed', { detail: { id: s.dataset.id, spent: d.spent_minutes } }));
    } catch (_) {}
  });
  window.addEventListener('timer-changed', refresh);
  setInterval(render, 15000);   // شمارندهٔ زنده
  setInterval(refresh, 30000);  // هماهنگی با سرور
  render();
})();
