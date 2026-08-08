/* richtext.js — ادیتور غنی TinyMCE (self-host) برای textareaهای .rich-editor.
   TinyMCE فقط هنگام نیاز lazy-load می‌شود. آپلود عکس با CSRF به /api/editor/upload/. */
(function () {
  'use strict';
  const BASE = '/static/vendor/tinymce';

  function ensureTiny(cb) {
    if (window.tinymce) { cb(); return; }
    if (window._tinyLoading) { window._tinyLoading.push(cb); return; }
    window._tinyLoading = [cb];
    const s = document.createElement('script');
    s.src = BASE + '/tinymce.min.js';
    s.onload = () => { window._tinyLoading.forEach((f) => f()); window._tinyLoading = null; };
    document.head.appendChild(s);
  }

  function uploadHandler(blobInfo) {
    return new Promise((resolve, reject) => {
      const fd = new FormData();
      fd.append('file', blobInfo.blob(), blobInfo.filename());
      fetch('/api/editor/upload/', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'X-CSRFToken': window.App ? App.csrf : '' }, body: fd,
      }).then((r) => r.json()).then((d) => (d.location ? resolve(d.location) : reject('خطا')))
        .catch(() => reject('آپلود ناموفق'));
    });
  }

  function init(selector) {
    ensureTiny(() => {
      window.tinymce.remove(selector);
      window.tinymce.init({
        selector, base_url: BASE, suffix: '.min',
        directionality: 'rtl', skin: 'oxide-dark', content_css: 'dark',
        menubar: false, statusbar: false, height: 240, branding: false,
        plugins: 'lists link image table autoresize code',
        toolbar: 'bold italic | h2 h3 | bullist numlist | link image table | code',
        autoresize_bottom_margin: 12,
        content_style: 'body{font-family:Vazirmatn,system-ui,sans-serif;font-size:14px;line-height:1.9}',
        automatic_uploads: true,
        images_upload_handler: uploadHandler,
        setup: (ed) => { ed.on('change', () => ed.save()); },
      });
    });
  }

  function save() { if (window.tinymce) window.tinymce.triggerSave(); }
  function remove(selector) { if (window.tinymce) window.tinymce.remove(selector); }

  window.RichText = { init, save, remove };

  // آغاز خودکار روی textareaهای فرم‌های استاتیک
  document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('textarea.rich-editor')) init('textarea.rich-editor');
  });
})();
