/* گزارشِ مالیِ پروژه (گردشِ حساب) — ویجتِ مشترکِ صفحه‌ی فاکتور و صفحه‌ی گزارش.
   هر `.pledger[data-project]` را خودکار مقداردهی می‌کند: کنترلِ بازه (پیش‌فرض ۳ ماهِ اخیر)
   + جدولِ فاکتور/تراکنش با مانده‌ی تجمعی. داده از `/finance/api/project-ledger/`.
   بابتِ «منبعِ واحد» — منطقِ ردیف در `finance/ledger_data.py`. */
(function () {
  'use strict';
  var money = function (n) { return (Number(n) || 0).toLocaleString('fa-IR'); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };

  function rowHtml(r) {
    var tag = '';
    if (r.kind === 'invoice') tag = '<span class="tag t-warn">فاکتور</span> ';
    else if (r.split) tag = '<span class="tag t-mute">تفکیک</span> ';
    var linesBtn = (r.lines && r.lines.length) ? '<span class="pl-caret">▸</span> ' : '';
    var main = '<tr class="pl-r' + (r.lines && r.lines.length ? ' pl-inv' : '') + '">' +
      '<td class="pl-date" dir="ltr">' + esc(r.date) + '</td>' +
      '<td>' + tag + linesBtn + esc(r.title) + '</td>' +
      '<td class="pl-cat">' + esc(r.cat || '—') + '</td>' +
      '<td class="num-c pl-dep">' + (r.deposit ? money(r.deposit) : '—') + '</td>' +
      '<td class="num-c pl-wd">' + (r.withdrawal ? money(r.withdrawal) : '—') + '</td>' +
      '<td class="num-c pl-bal">' + money(r.balance) + '</td></tr>';
    if (r.lines && r.lines.length) {
      var sub = r.lines.map(function (li) {
        return '<div class="pl-line"><span>' + esc(li.cat) + '</span><span>' + esc(li.desc || '—') +
          '</span><span class="num-c">' + money(li.total) + '</span></div>';
      }).join('');
      main += '<tr class="pl-sub" hidden><td colspan="6">' + sub + '</td></tr>';
    }
    return main;
  }

  function render(box, d) {
    var body = box.querySelector('.pl-body');
    var rangeLbl = box.querySelector('.pl-range');
    if (rangeLbl) rangeLbl.textContent = d.from + ' تا ' + d.to + (d.default_range ? ' (۳ ماهِ اخیر)' : '');
    if (!d.rows.length) {
      body.innerHTML = '<div class="zero" style="padding:16px;text-align:center">در این بازه گردشی نیست.</div>';
      return;
    }
    var rows = d.rows.map(rowHtml).join('');
    body.innerHTML =
      '<div class="tscroll"><table class="tsheet"><thead><tr>' +
      '<th>تاریخ</th><th>شرح</th><th>بابت</th><th>واریز</th><th>برداشت</th><th>مانده</th>' +
      '</tr></thead><tbody>' + rows + '</tbody>' +
      '<tfoot><tr><td colspan="3" style="text-align:left"><b>جمع</b></td>' +
      '<td class="num-c"><b>' + money(d.total_deposit) + '</b></td>' +
      '<td class="num-c"><b>' + money(d.total_withdrawal) + '</b></td>' +
      '<td class="num-c"><b>' + money(d.final_balance) + '</b></td></tr></tfoot></table></div>';
    // بازکردنِ ریزِ فاکتور
    body.querySelectorAll('.pl-inv').forEach(function (tr) {
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', function () {
        var sub = tr.nextElementSibling;
        if (sub && sub.classList.contains('pl-sub')) {
          sub.hidden = !sub.hidden;
          var c = tr.querySelector('.pl-caret'); if (c) c.textContent = sub.hidden ? '▸' : '▾';
        }
      });
    });
  }

  function load(box) {
    var pid = box.dataset.project;
    if (!pid) return;
    var from = (box.querySelector('.pl-from') || {}).value || '';
    var to = (box.querySelector('.pl-to') || {}).value || '';
    var qs = 'project=' + encodeURIComponent(pid);
    if (from && to) qs += '&from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to);
    var body = box.querySelector('.pl-body');
    body.innerHTML = '<div class="zero" style="padding:16px;text-align:center">در حالِ بارگذاری…</div>';
    fetch('/finance/api/project-ledger/?' + qs, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { render(box, d); })
      .catch(function () { body.innerHTML = '<div class="zero" style="padding:16px;text-align:center;color:var(--danger)">خطا در بارگذاریِ گزارش.</div>'; });
  }

  function init(box) {
    if (box.dataset.plInit) return;
    box.dataset.plInit = '1';
    var apply = box.querySelector('.pl-apply');
    var reset = box.querySelector('.pl-reset');
    if (apply) apply.addEventListener('click', function () { load(box); });
    if (reset) reset.addEventListener('click', function () {
      var f = box.querySelector('.pl-from'), t = box.querySelector('.pl-to');
      if (f) f.value = ''; if (t) t.value = ''; load(box);
    });
    load(box);
  }

  window.ProjectLedger = {
    init: init,
    load: load,
    initAll: function (root) {
      (root || document).querySelectorAll('.pledger').forEach(function (box) {
        if (box.dataset.lazy) return;  // تنبل: فقط با فراخوانیِ صریح (دکمه)
        init(box);
      });
    }
  };
  document.addEventListener('DOMContentLoaded', function () { window.ProjectLedger.initAll(); });
})();
