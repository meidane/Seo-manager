/* shell.js — تزریق سایدبار و هدر مشترک در همه‌ی صفحات ماک‌آپ (استاتیک).
   هر صفحه فقط محتوای خودش را دارد؛ چیدمان مشترک اینجا ساخته می‌شود.
   صفحه‌ی فعال با data-page روی <body> مشخص می‌شود. */
(function () {
  const NAV = [
    { key: 'dashboard', href: 'dashboard.html', ico: '◈', label: 'داشبورد' },
    { key: 'projects', href: 'projects.html', ico: '▤', label: 'پروژه‌ها' },
    { key: 'tasks', href: 'tasks.html', ico: '☰', label: 'تسک‌ها', tail: '۷' },
    { key: 'calendar', href: 'calendar.html', ico: '▦', label: 'تقویم' },
    { key: 'review', href: 'tasks-review.html', ico: '◎', label: 'بازبینی محتوا', tail: '۹' },
    { sep: 'تیم و مالی' },
    { key: 'colleagues', href: 'colleagues.html', ico: '◉', label: 'همکاران' },
    { key: 'reports', href: 'reports.html', ico: '▪', label: 'گزارش‌ها' },
    { key: 'finance', href: 'finance.html', ico: '₮', label: 'حسابداری' },
    { sep: 'تنظیمات' },
    { key: 'holidays', href: 'holidays.html', ico: '✦', label: 'تعطیلات' },
  ];

  const active = document.body.dataset.page || '';
  const showHeader = document.body.dataset.header !== 'off';

  // ── سایدبار ──
  let navHtml = '';
  NAV.forEach((n) => {
    if (n.sep) { navHtml += `<div class="nav-label">${n.sep}</div>`; return; }
    const on = n.key === active ? ' class="on"' : '';
    const tail = n.tail ? ` <span class="tail">${n.tail}</span>` : '';
    navHtml += `<a href="${n.href}"${on}><span class="ico">${n.ico}</span> ${n.label}${tail}</a>`;
  });

  const side = document.createElement('aside');
  side.className = 'side';
  side.innerHTML = `
    <div class="brand">
      <div class="brand-mark">س</div>
      <div><b>سئوپنل</b><span>مدیریت پروژه‌های سئو</span></div>
    </div>
    <nav class="nav">${navHtml}
      <a href="login.html"><span class="ico">⏻</span> خروج</a>
    </nav>`;

  const shell = document.querySelector('.shell');
  if (shell) shell.insertBefore(side, shell.firstChild);

  // ── هدر ──
  if (showHeader) {
    const main = document.querySelector('.main');
    if (main) {
      const bar = document.createElement('div');
      bar.className = 'topbar glass';
      bar.innerHTML = `
        <div class="search"><span>⌕</span> جستجو در پروژه‌ها، تسک‌ها، همکاران<span class="kbd">Ctrl K</span></div>
        <div class="range">
          <button>امروز</button><button>۷ روز</button>
          <button class="on">۳۰ روز</button><button>۹۰ روز</button><button>دلخواه</button>
        </div>
        <span class="range-note">۱۴۰۵/۰۴/۱۶ تا ۱۴۰۵/۰۵/۱۵</span>
        <button class="btn btn-p" style="margin-inline-start:auto">＋ تسک جدید</button>
        <img class="avatar" src="https://i.pravatar.cc/64?img=13" alt="">`;
      main.insertBefore(bar, main.firstChild);
    }
  }
})();
