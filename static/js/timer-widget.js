/* timer-widget.js — ویجت سراسریِ «در حال انجام» گوشهٔ پایین-راست (RTL).
   هرکس فقط تسکِ در حالِ اجرای خودش را (با دکمهٔ توقف) می‌بیند؛ اگر مدیرِ کسی باشد،
   تسکِ در حالِ اجرای زیرمجموعه‌هایش را هم می‌بیند، فقط‌خواندنی (بدونِ دکمهٔ توقف). */
(function () {
  'use strict';
  const box = document.getElementById('timer-widget');
  if (!box) return;
  let items = [];
  try { items = JSON.parse(document.getElementById('running-timers-data').textContent || '[]'); } catch (_) {}

  const esc = (v) => (v || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  function fmt(mins) {
    const m = Math.max(0, Math.round(mins)), h = Math.floor(m / 60), mm = m % 60;
    return h ? `${h}:${String(mm).padStart(2, '0')}` : `${mm}:00`;
  }
  function elapsed(it) {
    return (it.spent || 0) + (it.started ? (Date.now() - new Date(it.started).getTime()) / 60000 : 0);
  }
  function render() {
    if (!items.length) { box.classList.remove('on'); box.innerHTML = ''; return; }
    box.classList.add('on');
    const mine = items.filter((it) => it.mine);
    const subs = items.filter((it) => !it.mine);
    let html = '';
    if (mine.length) {
      html += `<div class="tw-h">در حال انجام (${mine.length})</div>` +
        mine.map((it) => `<div class="tw-row" data-id="${it.id}">
          <span class="tw-dot"></span>
          <span class="tw-tt" title="${esc(it.title)}">${it.title || 'تسک'}</span>
          <span class="tw-time">${fmt(elapsed(it))}</span>
          <button class="tw-stop" data-id="${it.id}" title="توقف">■</button></div>`).join('');
    }
    if (subs.length) {
      html += `<div class="tw-h"${mine.length ? ' style="margin-top:8px"' : ''}>زیرمجموعه‌ها</div>` +
        subs.map((it) => `<div class="tw-row tw-sub">
          <span class="tw-dot"></span>
          <span class="tw-tt" title="${esc(it.title)}"><b>${esc(it.assignee)}</b> — ${it.title || 'تسک'}</span>
          <span class="tw-time">${fmt(elapsed(it))}</span></div>`).join('');
    }
    box.innerHTML = html;
  }
  async function refresh() {
    try { const d = await App.fetchJSON('/tasks/api/running/'); items = d.running || []; render(); } catch (_) {}
  }
  box.addEventListener('click', async (e) => {
    const s = e.target.closest('.tw-stop'); if (!s) return;
    try { await App.fetchJSON(`/tasks/api/${s.dataset.id}/timer/`, { method: 'POST', body: { action: 'stop' } });
      items = items.filter((x) => String(x.id) !== String(s.dataset.id)); render();
      window.dispatchEvent(new CustomEvent('timer-changed'));
    } catch (_) {}
  });
  window.addEventListener('timer-changed', refresh);
  setInterval(render, 15000);   // شمارندهٔ زنده
  setInterval(refresh, 30000);  // هماهنگی با سرور
  render();
})();
