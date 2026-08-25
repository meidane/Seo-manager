/* sticky-thead.js — هدرِ چسبانِ جدول‌ها هنگام اسکرولِ کلِ صفحه.
   چون اجدادِ overflow (کارت + رَپِ افقی) `position:sticky`ِ بومی را می‌شکنند، هدرِ هر
   جدول را کلون و `position:fixed` می‌کنیم. چند جدول در صفحه پشتیبانی می‌شود؛ اسکرولِ
   افقیِ رَپ هم آینه می‌شود. فقط جدول‌های `table.tsheet`. */
(function () {
  'use strict';
  const floats = new Map();  // table -> floatEl

  function scrollParent(el) {   // نزدیک‌ترین جدِ اسکرولِ افقی (رَپ)
    let p = el.parentElement;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll') return p;
      p = p.parentElement;
    }
    return el.parentElement;
  }

  function ensureFloat(table) {
    let f = floats.get(table);
    if (f && f.isConnected) return f;
    f = document.createElement('div');
    f.className = 'thead-float';
    const tbl = document.createElement('table');
    tbl.className = table.className;
    tbl.appendChild(table.tHead.cloneNode(true));
    f.appendChild(tbl);
    document.body.appendChild(f);
    floats.set(table, f);
    return f;
  }

  function update() {
    document.querySelectorAll('table.tsheet').forEach((table) => {
      if (!table.tHead || !table.offsetParent) { const g = floats.get(table); if (g) g.style.display = 'none'; return; }
      const rect = table.getBoundingClientRect();
      const headH = table.tHead.offsetHeight;
      if (rect.top < 0 && rect.bottom > headH + 6) {
        const wrap = scrollParent(table);
        const wrect = wrap.getBoundingClientRect();
        const f = ensureFloat(table);
        const tbl = f.firstChild;
        f.style.display = '';
        f.style.left = wrect.left + 'px';
        f.style.width = wrap.clientWidth + 'px';
        tbl.style.width = table.offsetWidth + 'px';
        tbl.style.transform = 'translateX(' + (-(wrap.scrollLeft || 0)) + 'px)';
        const src = table.tHead.rows[0].cells, dst = tbl.tHead.rows[0].cells;
        for (let i = 0; i < src.length; i++) { if (dst[i]) dst[i].style.width = src[i].getBoundingClientRect().width + 'px'; }
      } else {
        const f = floats.get(table); if (f) f.style.display = 'none';
      }
    });
  }

  let raf = null;
  function onScroll() { if (raf) return; raf = requestAnimationFrame(() => { raf = null; update(); }); }
  window.addEventListener('scroll', onScroll, true);   // capture: هم صفحه هم رَپ
  window.addEventListener('resize', onScroll);
  window.addEventListener('load', update);
  document.addEventListener('DOMContentLoaded', update);
})();
