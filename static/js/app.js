/* ═══════════════════════════════════════════════════════════
   app.js — ابزارهای پایه‌ی فرانت: CSRF، fetchJSON، مودال، توست، تأیید
   بدون هیچ کتابخانه‌ای؛ Vanilla JS.
   ═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── CSRF ── یک‌بار خوانده می‌شود و به همه‌ی درخواست‌های AJAX می‌چسبد ── */
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }
  const CSRF = getCookie('csrftoken');

  /* ── جلوگیری از دابل‌کلیک ── دکمه‌ای که fetchJSON را آغاز می‌کند تا پایانِ درخواست
     غیرفعال + لودینگ می‌شود. چون disable هم‌زمان (sync) در ابتدای fetchJSON انجام
     می‌شود (پیش از اولین await، درونِ همان onclick)، کلیک‌های سریعِ بعدی روی همان دکمه
     اصلاً شلیک نمی‌شوند و رکوردِ تکراری ساخته نمی‌شود. ── */
  let _lastBtn = null, _lastBtnAt = 0;
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('button, .btn');
    if (b) { _lastBtn = b; _lastBtnAt = Date.now(); }
  }, true);
  function claimButton() {
    const b = _lastBtn;
    _lastBtn = null;
    return (b && !b.disabled && Date.now() - _lastBtnAt < 2500) ? b : null;
  }

  /* ── fetchJSON ── لایه‌ی نازک روی fetch با مدیریت خطا و CSRF ── */
  async function fetchJSON(url, options = {}) {
    const btn = claimButton();
    if (btn) { btn.disabled = true; btn.classList.add('is-loading'); }
    try {
      const opts = Object.assign(
        {
          method: 'GET',
          headers: {},
          credentials: 'same-origin',
        },
        options
      );
      opts.headers = Object.assign(
        {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': CSRF,
        },
        opts.headers
      );

      // بدنه‌ی آبجکت را به JSON تبدیل کن مگر FormData باشد
      if (opts.body && !(opts.body instanceof FormData) && typeof opts.body === 'object') {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
      }

      const res = await fetch(url, opts);
      const ct = res.headers.get('content-type') || '';
      const data = ct.includes('application/json') ? await res.json() : await res.text();

      if (!res.ok) {
        const msg = (data && data.detail) || 'خطا در ارتباط با سرور';
        toast(msg, 'err');
        throw { status: res.status, data };
      }
      return data;
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove('is-loading'); }
    }
  }

  /* ── توست ── اعلان گوشه‌ی پایین-چپ ── */
  function ensureToastWrap() {
    let wrap = document.querySelector('.toast-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'toast-wrap';
      document.body.appendChild(wrap);
    }
    return wrap;
  }
  function toast(message, type = '', timeout = 3200) {
    const wrap = ensureToastWrap();
    const el = document.createElement('div');
    el.className = 'toast glass ' + type;
    el.textContent = message;
    wrap.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(12px)';
      setTimeout(() => el.remove(), 200);
    }, timeout);
  }

  /* ── مودال ── باز/بسته کردن مودال عمومی ── */
  function ensureModalRoot() {
    let root = document.getElementById('modal-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'modal-root';
      root.className = 'modal-backdrop';
      root.innerHTML = '<div class="modal glass"></div>';
      document.body.appendChild(root);
      // کلیکِ بیرونِ مودال فقط وقتی می‌بندد که چیزی توی مودال تغییر نکرده باشد
      // (`data-dirty`، با اولین input/change ست می‌شود)؛ اگر داده دستکاری شده، فقط
      // دکمه‌ی × یا انصراف می‌بندد تا چیزی یک‌دفعه از دست نرود.
      root.addEventListener('click', (e) => {
        if (e.target === root && root.dataset.dirty !== '1') closeModal();
      });
      root.addEventListener('input', () => { root.dataset.dirty = '1'; });
      root.addEventListener('change', () => { root.dataset.dirty = '1'; });
    }
    return root;
  }
  function openModal(html) {
    const root = ensureModalRoot();
    root.querySelector('.modal').innerHTML = html;
    root.dataset.dirty = '';
    root.classList.add('open');
    initMoney(root);  // ویرگول‌دارکردنِ مقادیرِ اولیه‌ی اینپوت‌های مبلغ درونِ مودال
    return root;
  }
  function closeModal() {
    const root = document.getElementById('modal-root');
    if (root) root.classList.remove('open');
  }

  /* ── تأیید ── جایگزین confirm بومی با ظاهر شیشه‌ای ── */
  function confirmDialog(message, { okText = 'تأیید', cancelText = 'انصراف' } = {}) {
    return new Promise((resolve) => {
      const root = openModal(
        `<div class="modal-b" style="text-align:center">
           <p style="font-size:14px;margin:8px 0 18px">${message}</p>
           <div style="display:flex;gap:8px;justify-content:center">
             <button class="btn" data-act="cancel">${cancelText}</button>
             <button class="btn btn-p" data-act="ok">${okText}</button>
           </div>
         </div>`
      );
      root.querySelector('[data-act="ok"]').onclick = () => {
        closeModal();
        resolve(true);
      };
      root.querySelector('[data-act="cancel"]').onclick = () => {
        closeModal();
        resolve(false);
      };
    });
  }

  /* ── اینپوت مبالغ ── نمایشِ سه‌تاسه‌تا با ویرگول موقعِ تایپ (کلاسِ `money`) ──
     گروه‌بندی مستقل از خط (لاتین/فارسی). بک‌اند (`parse_amount`) و فرمِ فاکتور
     (`toNum`) ویرگول را پاک می‌کنند؛ برای فرمِ نیتیوِ Django هم روی submit پاک می‌شود. */
  function groupDigits(s) {
    const d = (String(s).match(/[\d۰-۹]/g) || []).join('');
    let out = '';
    for (let i = 0; i < d.length; i++) {
      if (i > 0 && (d.length - i) % 3 === 0) out += ',';
      out += d[i];
    }
    return out;
  }
  function formatMoneyInput(el) {
    const before = (el.value.slice(0, el.selectionStart).match(/[\d۰-۹]/g) || []).length;
    el.value = groupDigits(el.value);
    let pos = 0, seen = 0;
    while (pos < el.value.length && seen < before) {
      if (/[\d۰-۹]/.test(el.value[pos])) seen++;
      pos++;
    }
    try { el.setSelectionRange(pos, pos); } catch (_) { /* اینپوت‌های بدونِ selection */ }
  }
  function initMoney(root) {
    (root || document).querySelectorAll('input.money').forEach((el) => {
      if (el.value) el.value = groupDigits(el.value);
    });
  }
  document.addEventListener('input', (e) => {
    if (e.target.matches && e.target.matches('input.money')) formatMoneyInput(e.target);
  });
  // فرمِ نیتیو (submit واقعی مثلِ فرمِ پروژه): ویرگول پاک و ارقام لاتین شود تا Django بخواند
  document.addEventListener('submit', (e) => {
    if (!e.target || !e.target.querySelectorAll) return;
    e.target.querySelectorAll('input.money').forEach((el) => {
      el.value = el.value.replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[^\d]/g, '');
    });
  }, true);
  document.addEventListener('DOMContentLoaded', () => initMoney(document));

  /* ── دعوت‌نامه‌ها ── بنرِ سراسری + صفحه‌ی /invites/ هر دو از این دلیگیت استفاده می‌کنند ── */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.invite-accept, .invite-reject');
    if (!btn) return;
    fetchJSON(btn.dataset.url, { method: 'POST' })
      .then(() => window.location.reload())
      .catch(() => {});
  });

  /* ── تاریخِ نسبی (امروز/فردا/۳ روز بعد) — همسان با فیلترِ reldate در پایتون ── */
  // jalaali-js toGregorian (فشرده، آزموده) — jy/jm/jd یک‌مبنا → {gy,gm,gd}
  function jToG(jy, jm, jd) {
    jy += 1595;
    let days = -355668 + 365 * jy + ~~(jy / 33) * 8 + ~~(((jy % 33) + 3) / 4) + jd +
      (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
    let gy = 400 * ~~(days / 146097); days %= 146097;
    if (days > 36524) { gy += 100 * ~~(--days / 36524); days %= 36524; if (days >= 365) days++; }
    gy += 4 * ~~(days / 1461); days %= 1461;
    if (days > 365) { gy += ~~((days - 1) / 365); days = (days - 1) % 365; }
    let gd = days + 1;
    const leap = (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0;
    const sal = [0, 31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let gm = 0;
    for (gm = 1; gm <= 12 && gd > sal[gm]; gm++) gd -= sal[gm];
    return { gy, gm, gd };
  }
  function relDate(jalaliStr) {
    const s = String(jalaliStr || '').replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
    const m = s.match(/(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
    if (!m) return '';
    const g = jToG(+m[1], +m[2], +m[3]);
    const d = new Date(g.gy, g.gm - 1, g.gd); d.setHours(0, 0, 0, 0);
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diff = Math.round((d - today) / 86400000);
    if (diff === 0) return 'امروز';
    if (diff === 1) return 'فردا';
    if (diff === -1) return 'دیروز';
    if (diff > 0) return diff + ' روز بعد';       // همیشه نسبی، هر چقدر هم دور
    return (-diff) + ' روز قبل';                    // تاریخِ اصلی در هاور (title) است
  }

  /* ── نمای عمومی ── */
  window.App = {
    csrf: CSRF,
    fetchJSON,
    toast,
    openModal,
    closeModal,
    confirm: confirmDialog,
    relDate,
  };
})();
