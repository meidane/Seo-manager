/* گزارشِ مالیِ پروژه (گردشِ حساب) — ویجتِ مشترکِ صفحه‌ی فاکتور و صفحه‌ی گزارش.
   ظاهر **دقیقاً مثلِ تبِ گزارشِ حسابداری** (`finance/ledger.html`): جدولِ `sheet ledger`،
   تگ‌های فاکتور/تفکیک، ستون‌های dep/wd، ماندهٔ رنگی. **مانده همیشه کلی است** (نه بازه‌ای)
   = `project_balance` (همان ماندهٔ فاکتور/گزارش). داده از `/finance/api/project-ledger/`.
   منبعِ ردیف: `finance/ledger_data.py`. */
(function () {
  'use strict';
  var money = function (n) { return (Number(n) || 0).toLocaleString('fa-IR'); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };

  function rowHtml(r, i) {
    var tag = '';
    if (r.kind === 'invoice') tag = '<span class="tag t-warn" style="margin-inline-end:4px">فاکتور</span>';
    else if (r.split) tag = '<span class="tag t-mute" style="margin-inline-end:4px">تفکیک</span>';
    var caret = (r.lines && r.lines.length) ? '<span class="lg-caret">▸</span> ' : '';
    var bal = '<td class="num-c" style="font-weight:700;' + (r.balance < 0 ? 'color:var(--danger)' : '') + '">' + money(r.balance) + '</td>';
    var main = '<tr' + (r.lines && r.lines.length ? ' class="lg-inv-row" data-inv="' + r.ref_id + '" style="cursor:pointer" title="کلیک برای دیدنِ ریزِ فاکتور"' : '') + '>' +
      '<td class="num-c">' + money(i + 1) + '</td>' +
      '<td class="num-c">' + esc(r.date) + '</td>' +
      '<td style="text-align:right">' + tag + caret + esc(r.title) + '</td>' +
      '<td>' + (r.cat ? '<span style="color:var(--text-dim);font-size:12px">' + esc(r.cat) + '</span>' : '—') + '</td>' +
      '<td>' + (r.bank ? '<span class="tag t-mute" style="white-space:nowrap">' + esc(r.bank) + '</span>' : '—') + '</td>' +
      '<td class="num ' + (r.deposit ? 'dep' : '') + '">' + (r.deposit ? money(r.deposit) : '—') + '</td>' +
      '<td class="num ' + (r.withdrawal ? 'wd' : '') + '">' + (r.withdrawal ? money(r.withdrawal) : '—') + '</td>' +
      bal + '</tr>';
    if (r.lines && r.lines.length) {
      main += r.lines.map(function (li) {
        return '<tr class="split-child lg-inv-line lg-inv-line-' + r.ref_id + '" hidden>' +
          '<td></td><td></td>' +
          '<td style="text-align:right;color:var(--text-dim)"><span class="split-mark">└</span> ' + esc(li.desc || '—') + ' <span style="opacity:.7">× ' + money(li.qty) + '</span></td>' +
          '<td style="color:var(--text-dim);font-size:12px">' + esc(li.cat) + '</td><td></td><td></td>' +
          '<td class="num wd" style="opacity:.75">' + money(li.total) + '</td><td></td></tr>';
      }).join('');
    }
    return main;
  }

  function render(box, d) {
    var body = box.querySelector('.pl-body');
    var rangeLbl = box.querySelector('.pl-range');
    if (rangeLbl) rangeLbl.textContent = d.from + ' تا ' + d.to;
    var balEl = box.querySelector('.pl-globalbal');
    if (balEl) {
      balEl.textContent = 'مانده‌ی کل: ' + money(d.project_balance);
      balEl.className = 'tag pl-globalbal ' + (d.project_balance < 0 ? 't-bad' : (d.project_balance > 0 ? 't-ok' : 't-mute'));
    }
    if (!d.rows.length) {
      body.innerHTML = '<div class="empty" style="padding:22px 16px"><div class="ico">▪</div><h4>در این بازه گردشی نیست</h4></div>';
      return;
    }
    var rows = d.rows.map(rowHtml).join('');
    body.innerHTML =
      '<div class="sheet-wrap"><table class="sheet ledger"><thead><tr>' +
      '<th style="width:38px"></th><th style="width:104px">تاریخ</th><th>شرح</th>' +
      '<th style="width:130px">بابت</th><th style="width:110px">بانک</th>' +
      '<th style="width:120px">واریز</th><th style="width:120px">برداشت</th><th style="width:130px">مانده</th>' +
      '</tr></thead><tbody>' + rows + '</tbody>' +
      '<tfoot><tr style="border-top:2px solid var(--stroke);font-weight:700">' +
      '<td></td><td></td><td style="text-align:right">جمع (بازهٔ نمایش)</td><td></td><td></td>' +
      '<td class="num dep">' + money(d.total_deposit) + '</td>' +
      '<td class="num wd">' + money(d.total_withdrawal) + '</td>' +
      '<td class="num-c" style="' + (d.project_balance < 0 ? 'color:var(--danger)' : 'color:var(--info)') + '">' + money(d.project_balance) + '</td>' +
      '</tr></tfoot></table></div>';
    // بازکردنِ ریزِ فاکتور (مثلِ ledger.html)
    body.querySelectorAll('.lg-inv-row').forEach(function (tr) {
      tr.addEventListener('click', function () {
        var id = tr.dataset.inv, open = tr.querySelector('.lg-caret');
        var lines = body.querySelectorAll('.lg-inv-line-' + id);
        var willOpen = lines.length && lines[0].hidden;
        lines.forEach(function (li) { li.hidden = !willOpen; });
        if (open) open.textContent = willOpen ? '▾' : '▸';
      });
    });
  }

  function load(box, showAll) {
    var pid = box.dataset.project;
    if (!pid) return;
    var from = (box.querySelector('.pl-from') || {}).value || '';
    var to = (box.querySelector('.pl-to') || {}).value || '';
    var qs = 'project=' + encodeURIComponent(pid);
    if (from && to) qs += '&from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to);
    else if (showAll) qs += '&all=1';
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
    if (apply) apply.addEventListener('click', function () { load(box, false); });
    if (reset) reset.addEventListener('click', function () {
      var f = box.querySelector('.pl-from'), t = box.querySelector('.pl-to');
      if (f) f.value = ''; if (t) t.value = ''; load(box, true);  // «همه» = کلِ تاریخ
    });
    load(box, false);  // پیش‌فرض: ۳ ماهِ اخیر
  }

  window.ProjectLedger = {
    init: init,
    load: load,
    initAll: function (root) {
      (root || document).querySelectorAll('.pledger').forEach(function (box) {
        if (box.dataset.lazy) return;
        init(box);
      });
    }
  };
  document.addEventListener('DOMContentLoaded', function () { window.ProjectLedger.initAll(); });
})();
