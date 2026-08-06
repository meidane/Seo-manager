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

  /* ── fetchJSON ── لایه‌ی نازک روی fetch با مدیریت خطا و CSRF ── */
  async function fetchJSON(url, options = {}) {
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
      root.addEventListener('click', (e) => {
        if (e.target === root) closeModal();
      });
    }
    return root;
  }
  function openModal(html) {
    const root = ensureModalRoot();
    root.querySelector('.modal').innerHTML = html;
    root.classList.add('open');
    document.addEventListener('keydown', escToClose);
    return root;
  }
  function closeModal() {
    const root = document.getElementById('modal-root');
    if (root) root.classList.remove('open');
    document.removeEventListener('keydown', escToClose);
  }
  function escToClose(e) {
    if (e.key === 'Escape') closeModal();
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

  /* ── نمای عمومی ── */
  window.App = {
    csrf: CSRF,
    fetchJSON,
    toast,
    openModal,
    closeModal,
    confirm: confirmDialog,
  };
})();
