/* calendar.js — رندر تقویم شمسی نمایشی (داده‌ی ساختگی) — برگرفته از designpreview */
(function () {
  const el = document.getElementById('cal');
  if (!el) return;

  const P = { info: '56,189,248', warn: '251,191,36', org: '249,115,22',
    vio: '167,139,250', pink: '244,114,182', ok: '45,212,167' };
  const chip = (c, label, title, time, done) =>
    `<span class="tk${done ? ' done' : ''}" style="background:rgba(${P[c]},.15);border-right:3px solid rgb(${P[c]});color:rgb(${P[c]})">` +
    `${label}: ${title}<span class="tk-t">${time}</span></span>`;

  const HOL = { 13: 'شهادت امام جعفر صادق', 21: 'عید سعید غدیر', 22: 'تعطیل رسمی' };
  const DATA = {
    3: [['ok', 'لینک‌سازی', 'جراحی یار و کلینیک', '۰۸:۰۰', 1]],
    15: [['info', 'انتشار', '۴۰ عکس پروفایل حرفه‌ای', '۰۸:۰۰', 0],
      ['warn', 'آپدیت سطحی', 'تولیدی و نمایندگی', '۰۹:۳۰', 0],
      ['org', 'آپدیت اساسی', 'خط تولید نوین', '۱۱:۰۰', 0]],
    17: [['warn', 'آپدیت سطحی', 'وکیل اوقاف و امور خیریه', '۰۸:۰۰', 1],
      ['vio', 'فنی', 'اصلاح تصاویر شاخص', '۰۸:۳۰', 1],
      ['pink', 'رپورتاژ', 'تفاوت اسکراب زنانه', '۱۰:۰۰', 1],
      ['org', 'آپدیت اساسی', 'دیوایدر شیشه‌ای', '۱۱:۰۰', 0],
      ['info', 'انتشار', 'دندانپزشکی طرف قرارداد', '۱۳:۰۰', 0]],
    18: [['info', 'انتشار', 'تشخیص ساعت اورجینال', '۰۸:۰۰', 1],
      ['info', 'انتشار', 'راهنمای انتخاب درب', '۰۹:۰۰', 0],
      ['org', 'آپدیت اساسی', 'پارتیشن متحرک', '۱۰:۳۰', 0],
      ['pink', 'رپورتاژ', 'ماسک پزشکی یا N95', '۱۲:۰۰', 0]],
    19: [['org', 'آپدیت اساسی', 'وی پی ان و امنیت', '۰۸:۰۰', 0],
      ['info', 'انتشار', 'تشخیص ساعت کارتیر', '۰۹:۰۰', 0],
      ['ok', 'لینک‌سازی', 'ساعت مچی هدیه', '۱۰:۰۰', 0]],
    20: [['org', 'آپدیت اساسی', 'لوپتو و ابزار دقیق', '۰۸:۰۰', 0],
      ['info', 'انتشار', 'ساعت ادیفایس یا کاسیو', '۰۹:۰۰', 0],
      ['pink', 'رپورتاژ', 'تفاوت اسکراب پزشکی', '۱۱:۰۰', 0]],
    24: [['org', 'آپدیت اساسی', 'پارتیشن تک جداره', '۰۸:۰۰', 0],
      ['org', 'آپدیت اساسی', 'پارتیشن کناف اداری', '۰۹:۰۰', 0],
      ['warn', 'آپدیت سطحی', 'ایمپلنت دندان', '۱۰:۳۰', 0]],
    25: [['info', 'انتشار', 'طول عمر سگ چقدر است', '۰۸:۰۰', 0],
      ['org', 'آپدیت اساسی', 'عصب کشی دندان', '۰۹:۰۰', 0]],
    28: [['vio', 'فنی', 'بهینه‌سازی سرعت سایت', '۰۸:۰۰', 0]],
  };

  let html = '';
  for (let i = 0; i < 35; i++) {
    const d = i - 1;
    const prev = d < 1, next = d > 31;
    const num = prev ? 30 + d : (next ? d - 31 : d);
    const col = i % 7;
    const off = col === 6 || HOL[d];
    const today = d === 15;
    const tasks = DATA[d] || [];

    let cls = 'cell';
    if (off && !prev && !next) cls += ' off';
    if (prev || next) cls += ' dim';
    if (today) cls += ' today';

    html += `<div class="${cls}"><div class="cell-h">
      <span class="dnum">${num.toLocaleString('fa-IR')}${next ? ' شهریور' : ''}</span>
      ${HOL[d] && !prev && !next ? `<span class="hol">${HOL[d]}</span>` : ''}
      ${tasks.length ? `<span class="cnt">${tasks.length.toLocaleString('fa-IR')}</span>` : ''}
    </div>`;
    tasks.slice(0, 4).forEach((t) => (html += chip(t[0], t[1], t[2], t[3], t[4])));
    if (tasks.length > 4) html += `<span class="more">+${(tasks.length - 4).toLocaleString('fa-IR')} مورد دیگر</span>`;
    html += '</div>';
  }
  el.innerHTML = html;
})();
