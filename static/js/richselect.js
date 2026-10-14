/* richselect.js — تبدیلِ <select class="rich-select"> به دراپ‌داونِ سفارشی که
   لوگو/آواتار و رنگِ هر گزینه را نشان می‌دهد. مقدار و رویدادِ change روی همان
   <select> بومی می‌مانند (سازگار با فرم/هندلرهای موجود). هر <option> با
   data-img (آدرس تصویر) و/یا data-color (رنگ) توصیف می‌شود. */
(function () {
  function esc(s) { return (s == null ? '' : String(s)); }

  function media(o) {
    var img = o.getAttribute('data-img'), color = o.getAttribute('data-color') || '';
    var initial = (o.textContent || '').trim().slice(0, 1);
    if (img) return '<span class="rs-av"><img src="' + esc(img) + '" alt=""></span>';
    if (color) return '<span class="rs-av" style="background:color-mix(in srgb,' + color + ' 24%,transparent);color:' + color + '">' + esc(initial) + '</span>';
    return '<span class="rs-av rs-empty"></span>';
  }

  function build(sel) {
    if (sel.dataset.rsInit) return;
    sel.dataset.rsInit = '1';
    var wrap = document.createElement('div');
    wrap.className = 'rs';
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    sel.classList.add('rs-native');

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rs-btn';
    var menu = document.createElement('div');
    menu.className = 'rs-menu';
    wrap.appendChild(btn);
    wrap.appendChild(menu);

    function renderBtn() {
      var o = sel.options[sel.selectedIndex];
      btn.innerHTML = o ? (media(o) + '<span class="rs-lb">' + esc(o.textContent) + '</span><span class="rs-caret">▾</span>') : '';
    }
    // فقط آیتم‌ها را می‌سازد (نه اینپوتِ جستجو) — تا موقعِ تایپ فوکوس/متن از دست نرود
    function itemsHTML(q) {
      q = (q || '').trim().toLowerCase();
      var items = '';
      for (var i = 0; i < sel.options.length; i++) {
        var o = sel.options[i];
        if (q && o.textContent.toLowerCase().indexOf(q) < 0) continue;
        items += '<div class="rs-item' + (i === sel.selectedIndex ? ' on' : '') + '" data-i="' + i + '">' +
          media(o) + '<span class="rs-lb">' + esc(o.textContent) + '</span></div>';
      }
      return items || '<div class="rs-nomatch">موردی یافت نشد</div>';
    }
    function bindItems() {
      menu.querySelectorAll('.rs-item').forEach(function (it) {
        it.onclick = function () {
          sel.selectedIndex = +it.getAttribute('data-i');
          renderBtn(); close();
          sel.dispatchEvent(new Event('change', { bubbles: true }));
        };
      });
    }
    // منو را با position:fixed نسبت به دکمه جای می‌دهد تا از هر کانتینرِ overflow:hidden
    // (کارتِ کوتاه، ردیفِ فلکس) و هر جدِّ transform/backdrop-filter (glass) فرار کند.
    function place() {
      var r = btn.getBoundingClientRect();
      var rtl = getComputedStyle(document.documentElement).direction === 'rtl';
      menu.style.position = 'fixed';
      menu.style.zIndex = '2000';   // بالاتر از مودال/نوارِ چسبانِ فرم
      menu.style.minWidth = r.width + 'px';
      menu.style.top = (r.bottom + 4) + 'px';
      menu.style.left = 'auto'; menu.style.right = 'auto';
      if (rtl) menu.style.right = (window.innerWidth - r.right) + 'px';
      else menu.style.left = r.left + 'px';
      // اگر پایین جا نشد و بالا جا هست، رو به بالا باز کن
      var mh = menu.offsetHeight;
      if (r.bottom + 4 + mh > window.innerHeight && r.top - 4 - mh > 0) {
        menu.style.top = (r.top - 4 - mh) + 'px';
      }
    }
    function open() {
      var withSearch = sel.options.length > 8;
      menu.innerHTML = (withSearch ? '<input class="rs-search" placeholder="جستجو…" autocomplete="off">' : '') +
        '<div class="rs-items">' + itemsHTML('') + '</div>';
      var box = menu.querySelector('.rs-items');
      bindItems();
      var si = menu.querySelector('.rs-search');
      if (si) {
        // فقط لیست را به‌روز کن؛ خودِ اینپوت دست‌نخورده می‌ماند (فوکوس و متن حفظ می‌شود)
        si.oninput = function () { box.innerHTML = itemsHTML(si.value); bindItems(); };
        setTimeout(function () { si.focus(); }, 0);
      }
      document.body.appendChild(menu);   // خروج از کانتینرِ کلیپ‌کننده
      menu.classList.add('open');
      wrap.classList.add('rs-open');
      place();
      window.addEventListener('scroll', place, true);
      window.addEventListener('resize', place);
    }
    function close() {
      menu.classList.remove('open'); wrap.classList.remove('rs-open');
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
      if (menu.parentNode === document.body) wrap.appendChild(menu);  // بازگشت به wrap
      menu.style.position = menu.style.top = menu.style.left = menu.style.right = menu.style.minWidth = menu.style.zIndex = '';
    }
    btn.onclick = function (e) { e.preventDefault(); menu.classList.contains('open') ? close() : open(); };
    document.addEventListener('click', function (e) { if (!wrap.contains(e.target) && !menu.contains(e.target)) close(); });
    // اگر مقدارِ select با کدِ دیگری عوض شد، دکمه هم به‌روز شود
    sel.addEventListener('rs-refresh', renderBtn);
    renderBtn();
  }

  function initAll(root) {
    (root || document).querySelectorAll('select.rich-select').forEach(build);
  }
  window.RichSelect = { init: initAll };
  if (document.readyState !== 'loading') initAll();
  else document.addEventListener('DOMContentLoaded', function () { initAll(); });
})();
