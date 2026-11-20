/* gsc.js — نمایشِ دادهٔ سرچ کنسول (منبعِ واحدِ فرانت): نمودارِ روند + جدولِ کلمات + کارتِ زیرِ تسک + تبِ تحلیلِ پروژه.
   داده از `/gsc/api/task/<id>/` و `/gsc/api/project/<id>/` (gsc/analysis.py). رنگ‌ها فقط از متغیرهای CSS.
   نمودار: یک سری، یک محور (کلیک | ایمپرشن | جایگاه با محورِ وارونه)، خطِ ۲px + ناحیهٔ کم‌رنگ، تولتیپ با هاور. */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const fa = n => (n == null ? '—' : Number(n).toLocaleString('en-US'));   // اعدادِ لاتین (خواناتر کنارِ لینک)
  const jd = iso => new Date(iso + 'T12:00:00').toLocaleDateString('fa-IR-u-ca-persian-nu-latn', {month: 'short', day: 'numeric'});
  // نشانِ رنگیِ جایگاه: ۱–۳ سبز، ۴–۱۰ آبی، ۱۱–۲۰ کهربایی، بیشتر خاکستری (راهنما زیرِ «پیشنهادها»)
  const pos = v => v == null ? '<span class="zero">—</span>' : `<span class="posb ${v <= 3.5 ? 'p1' : v <= 10.5 ? 'p2' : v <= 20.5 ? 'p3' : 'p4'}">${fa(v)}</span>`;
  const M = {clicks: 'کلیک', impressions: 'ایمپرشن', ctr: 'CTR', position: 'جایگاه'};
  const decode = u => { try { return decodeURI(u); } catch (_) { return u; } };
  const nice = u => {   // {title, dir}: آخرین بخشِ نشانی با فاصله به‌جای خط‌تیره + پوشهٔ والد
    const p = decode(String(u || '').replace(/^https?:\/\/(www\.)?/, '')).replace(/^[^/]+/, '') || '/';
    const segs = p.split('/').filter(Boolean);
    return {title: segs.length ? segs[segs.length - 1].replace(/[-_]+/g, ' ').trim() : 'صفحهٔ اصلی',
            dir: segs.length > 1 ? '/' + segs.slice(0, -1).join('/') + '/' : '/'};
  };
  const short = u => decode(String(u || '').replace(/^https?:\/\/(www\.)?/, '')).replace(/^[^/]+/, '') || '/';

  // ── نمودار ──
  function chart(el, series, metric) {
    const W = Math.max(el.clientWidth || 600, 280), H = 150, P = {l: 38, r: 8, t: 10, b: 22};
    const vals = series.map(d => metric === 'position' ? d.position : d[metric]);
    const real = vals.filter(v => v != null);
    if (!real.length) { el.innerHTML = '<div class="gsc-nodata">دادهٔ کافی نیست</div>'; return; }
    let lo = 0, hi = Math.max(...real, 1);
    if (metric === 'position') { lo = Math.max(1, Math.floor(Math.min(...real))); hi = Math.ceil(Math.max(...real)); if (hi === lo) hi = lo + 1; }
    const x = i => P.l + (W - P.l - P.r) * (series.length < 2 ? .5 : i / (series.length - 1));
    const y = v => metric === 'position' ? P.t + (H - P.t - P.b) * (v - lo) / (hi - lo) : H - P.b - (H - P.t - P.b) * (v - lo) / (hi - lo);
    let d = '', a = '', started = false;
    vals.forEach((v, i) => { if (v == null) { started = false; return; } d += (started ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); started = true; });
    if (metric !== 'position') a = d + `L${x(vals.length - 1)} ${H - P.b}L${x(0)} ${H - P.b}Z`;
    const ticks = [lo, lo + (hi - lo) / 2, hi].map(t => metric === 'position' ? Math.round(t) : Math.round(t));
    const xt = [0, Math.floor(series.length / 3), Math.floor(2 * series.length / 3), series.length - 1];
    el.innerHTML = `<div class="gsc-ch"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none">
      ${ticks.map(t => `<line class="g-grid" x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}"/><text class="g-ax" x="${P.l - 6}" y="${y(t) + 4}" text-anchor="end">${fa(t)}</text>`).join('')}
      ${xt.map(i => `<text class="g-ax" x="${x(i)}" y="${H - 6}" text-anchor="middle">${jd(series[i].date)}</text>`).join('')}
      ${a ? `<path class="g-area" d="${a}"/>` : ''}<path class="g-line" d="${d}"/>
      <line class="g-cross" y1="${P.t}" y2="${H - P.b}" x1="0" x2="0" style="display:none"/><circle class="g-dot" r="4" style="display:none"/>
      <rect class="g-hit" x="${P.l}" y="0" width="${W - P.l - P.r}" height="${H}"/></svg><div class="g-tip" hidden></div></div>`;
    const svg = el.querySelector('svg'), tip = el.querySelector('.g-tip'), cr = el.querySelector('.g-cross'), dot = el.querySelector('.g-dot');
    const move = e => {
      const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * W / r.width;
      const i = Math.max(0, Math.min(series.length - 1, Math.round((px - P.l) / (W - P.l - P.r) * (series.length - 1))));
      const s = series[i], v = vals[i];
      cr.setAttribute('x1', x(i)); cr.setAttribute('x2', x(i)); cr.style.display = '';
      if (v != null) { dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(v)); dot.style.display = ''; } else dot.style.display = 'none';
      tip.hidden = false;
      tip.innerHTML = `<b>${jd(s.date)}</b><span>کلیک ${fa(s.clicks)}</span><span>ایمپرشن ${fa(s.impressions)}</span><span>CTR ${fa(s.ctr)}%</span><span>جایگاه ${fa(s.position)}</span>`;
      const left = x(i) * r.width / W;
      tip.style.left = Math.min(Math.max(left - tip.offsetWidth / 2, 0), r.width - tip.offsetWidth) + 'px';
    };
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerleave', () => { tip.hidden = true; cr.style.display = 'none'; dot.style.display = 'none'; });
  }

  // نمودار + تب‌های متریک + جمعِ بازه
  function chartBlock(el, series, compact) {
    const tot = series.reduce((o, d) => { o.c += d.clicks; o.i += d.impressions; o.pw += (d.position || 0) * d.impressions; return o; }, {c: 0, i: 0, pw: 0});
    const sum = {clicks: fa(tot.c), impressions: fa(tot.i), ctr: tot.i ? fa(Math.round(tot.c * 1000 / tot.i) / 10) + '%' : '—', position: tot.i ? fa(Math.round(tot.pw * 10 / tot.i) / 10) : '—'};
    // compact: فقط تب‌های کوچکِ متریک (جمع‌ها جای دیگری نمایش داده شده‌اند — تبِ پروژه)
    el.innerHTML = `<div class="gsc-mt${compact ? ' compact' : ''}">${['clicks', 'impressions', 'ctr', 'position'].map((k, i) => `<button type="button" class="gsc-m${i ? '' : ' on'}" data-m="${k}"><span>${M[k]}</span>${compact ? '' : `<b>${sum[k]}</b>`}</button>`).join('')}</div><div class="gsc-plot"></div>`;
    const plot = el.querySelector('.gsc-plot');
    const draw = m => chart(plot, series, m);
    el.querySelector('.gsc-mt').onclick = e => { const b = e.target.closest('.gsc-m'); if (!b) return;
      el.querySelectorAll('.gsc-m').forEach(x => x.classList.toggle('on', x === b)); draw(b.dataset.m); };
    requestAnimationFrame(() => draw('clicks'));
  }

  // جدولِ کلمات (مرتب‌سازی با کلیک روی سرستون)
  function queryTable(el, rows, opts) {
    opts = opts || {};
    let key = 'clicks', dir = -1, all = false;
    const cols = [['query', 'کلمه'], ['clicks', 'کلیک'], ['impressions', 'ایمپرشن'], ['ctr', 'CTR'], ['position', 'جایگاه']];
    const render = () => {
      const sorted = rows.slice().sort((a, b) => key === 'query' ? dir * a.query.localeCompare(b.query, 'fa')
        : dir * (((a[key] ?? 999) - (b[key] ?? 999)) || (b.impressions - a.impressions)));
      const vis = all ? sorted : sorted.slice(0, opts.limit || 25);
      el.innerHTML = `<div class="tscroll"><table class="gsc-tbl"><thead><tr>${cols.map(([k, l]) => `<th data-k="${k}" class="${k === key ? 'on' : ''}">${l}${k === key ? (dir < 0 ? ' ▾' : ' ▴') : ''}</th>`).join('')}</tr></thead>
        <tbody>${vis.map(r => `<tr><td dir="auto">${esc(r.query)}</td><td class="n">${fa(r.clicks)}</td><td class="n">${fa(r.impressions)}</td><td class="n">${fa(r.ctr)}%</td><td class="n">${pos(r.position)}</td></tr>`).join('')}</tbody></table></div>
        ${rows.length > vis.length ? `<button type="button" class="btn btn-sm gsc-more">نمایشِ همه (${fa(rows.length)})</button>` : ''}`;
      el.querySelectorAll('th').forEach(th => th.onclick = () => { const k = th.dataset.k; dir = k === key ? -dir : (k === 'position' || k === 'query' ? 1 : -1); key = k; render(); });
      const m = el.querySelector('.gsc-more'); if (m) m.onclick = () => { all = true; render(); };
    };
    render();
  }

  function impactHtml(im) {
    if (!im) return '';
    const b = im.before, a = im.after, cd = im.clicks_delta, pd = im.position_delta;
    // ▲ سبز = بهتر، ▼ قرمز = بدتر (برای جایگاه، position_delta = قبل − بعد؛ مثبت یعنی بهتر شده)
    const chg = v => !v ? '<span class="zero">—</span>' : `<em class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲' : '▼'} <span dir="ltr">${fa(Math.abs(v))}</span></em>`;
    const di = a.impressions - b.impressions;
    return `<div class="gsc-imp"><b>اثرِ این تسک</b> <span class="zero">${im.full ? '۲۸ روز قبل و بعد از انجام' : im.days + ' روز قبل و بعد (هنوز ۲۸ روز نگذشته)'}</span>
      <table class="gsc-tbl gsc-imp-t"><thead><tr><th></th><th>قبل</th><th>بعد</th><th>تغییر</th></tr></thead><tbody>
        <tr><td>کلیک</td><td class="n">${fa(b.clicks)}</td><td class="n">${fa(a.clicks)}</td><td class="n">${chg(cd)}</td></tr>
        <tr><td>ایمپرشن</td><td class="n">${fa(b.impressions)}</td><td class="n">${fa(a.impressions)}</td><td class="n">${chg(di)}</td></tr>
        <tr><td>جایگاه</td><td class="n">${pos(b.position)}</td><td class="n">${pos(a.position)}</td><td class="n">${chg(pd)}</td></tr>
      </tbody></table></div>`;
  }

  function indexLine(ix) {
    if (!ix) return '';
    if (ix.error && !ix.verdict) return `<div class="ix-line"><span class="ix">${App.icon('warning')} بررسیِ ایندکس ناموفق</span></div>`;
    return `<div class="ix-line">${ix.indexed ? `<span class="ix ok">${App.icon('check-circle')} ایندکس شده</span>` : `<span class="ix bad">${App.icon('warning')} ایندکس نشده — ${esc(ix.coverage || '')}</span>`}
      ${ix.last_crawl ? `<span class="zero">آخرین کراول ${jd(ix.last_crawl)}</span>` : ''}<span class="zero">بررسی ${jd(ix.checked)}</span>
      ${ix.canonical_mismatch ? `<span class="ix warn" title="${esc(ix.google_canonical)}">${App.icon('warning')} گوگل canonicalِ دیگری انتخاب کرده</span>` : ''}</div>`;
  }

  // کلمه‌های هدفِ تسک: جایگاهِ همین صفحه (سرچ کنسول، ۲۸ روز) + اگر صفحهٔ دیگری از سایت برای آن کلمه بهتر دیده می‌شود + آخرین رتبهٔ افزونه
  function kwHtml(list) {
    if (!list || !list.length) return '';
    return `<div class="gsc-q-h">${App.icon('star')} کلماتِ هدفِ تسک <span class="zero">۲۸ روزِ اخیر</span></div>
      <div class="tscroll"><table class="gsc-tbl"><thead><tr><th>کلمه</th><th class="n">جایگاهِ این صفحه</th><th class="n">کلیک</th><th class="n">ایمپرشن</th><th>صفحهٔ دیگرِ سایت</th><th class="n">افزونه</th></tr></thead><tbody>
      ${list.map(k => { const pg = k.page, b = k.best;
        const other = b && !b.same ? `<span title="${esc(decode(b.url))}">${esc(nice(b.url).title)} ${pos(b.position)}</span>` : '<span class="zero">—</span>';
        return `<tr><td dir="auto"><b>${esc(k.keyword)}</b></td><td class="n">${pg ? pos(pg.position) : '<span class="zero" title="این صفحه برای این کلمه در ۲۸ روزِ اخیر نمایشی نداشته">دیده نشده</span>'}</td>
          <td class="n">${pg ? fa(pg.clicks) : '—'}</td><td class="n">${pg ? fa(pg.impressions) : '—'}</td><td>${other}</td>
          <td class="n">${k.ext ? `${pos(k.ext.position)} <span class="zero">${jd(k.ext.date)}</span>` : '<span class="zero">—</span>'}</td></tr>`; }).join('')}
      </tbody></table></div>`;
  }

  // ── کارتِ زیرِ تسک (خودکار؛ فقط اگر صفحهٔ تسک در سرچ کنسول باشد) ──
  async function taskCard(taskId, box) {
    if (!box) return;
    let d;
    try { const r = await fetch(`/gsc/api/task/${taskId}/`); if (!r.ok) return; d = await r.json(); } catch (_) { return; }
    const pages = (d.pages || []);
    if (!pages.length) return;
    box.style.display = '';
    const tabs = pages.length > 1 ? `<div class="gsc-pages">${pages.map((p, i) => `<button type="button" class="chip${i ? '' : ' on'}" data-i="${i}" title="${esc(decode(p.url))}">${p.role === 'target' ? 'هدف: ' : ''}${esc(nice(p.url).title)}</button>`).join('')}</div>` : '';
    box.innerHTML = `<div class="gsc-card"><div class="gsc-card-h">${App.icon('chart')} سرچ کنسول <span class="zero">۳ ماهِ اخیر${pages[0].until ? ' تا ' + jd(pages[0].until) : ''}</span>
      <a class="btn btn-sm" style="margin-inline-start:auto" href="/gsc/api/task/${taskId}/export/" title="خروجیِ اکسل">${App.icon('file-excel')} اکسل</a></div>${tabs}<div class="gsc-body"></div></div>`;
    const body = box.querySelector('.gsc-body');
    const show = i => {
      const p = pages[i];
      const nm = nice(p.url);
      body.innerHTML = `<a class="gsc-url gsc-pg" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(decode(p.url))}"><span class="t" dir="auto">${esc(nm.title)}</span><span class="p" dir="ltr">${esc(nm.dir)}</span></a>${indexLine(p.index)}${kwHtml(p.keywords)}${impactHtml(p.impact)}<div class="gsc-chart"></div>
        <div class="gsc-q-h">کلماتی که این صفحه با آن‌ها دیده شده <span class="zero">${fa(p.queries.length)}</span></div><div class="gsc-q"></div>`;
      chartBlock(body.querySelector('.gsc-chart'), p.series);
      if (p.queries.length) queryTable(body.querySelector('.gsc-q'), p.queries);
      else body.querySelector('.gsc-q').innerHTML = '<div class="gsc-nodata">در ۳ ماهِ اخیر کلمه‌ای ثبت نشده</div>';
    };
    const pt = box.querySelector('.gsc-pages');
    if (pt) pt.onclick = e => { const b = e.target.closest('.chip'); if (!b) return; pt.querySelectorAll('.chip').forEach(x => x.classList.toggle('on', x === b)); show(+b.dataset.i); };
    show(0);
  }

  // ── تبِ «تحلیلِ سرچ کنسول»ِ پروژه ──
  async function projectTab(pid, el) {
    if (!el || el.dataset.loaded) return;
    el.dataset.loaded = '1';
    el.innerHTML = '<div class="gsc-nodata">در حالِ بارگذاری…</div>';
    let r;
    try { r = await App.fetchJSON(`/gsc/api/project/${pid}/`); } catch (_) { el.innerHTML = '<div class="gsc-nodata">خطا در بارگذاری</div>'; delete el.dataset.loaded; return; }
    const d = r.data;
    if (!d) {
      el.innerHTML = `<div class="empty"><div class="ico">${App.icon('chart')}</div><h4>${r.connected ? 'هنوز داده‌ای همگام نشده' : 'این پروژه به سرچ کنسول وصل نیست'}</h4>
        <p style="color:var(--text-faint);font-size:12px;margin-top:6px">از تنظیمات ← سرچ کنسول، property این سایت را به پروژه جفت و همگام‌سازی کن.</p></div>`;
      return;
    }
    const c = d.total.current, p = d.total.previous;
    const delta = (a, b, inv) => { if (a == null || b == null) return ''; const v = inv ? b - a : a - b; if (!v) return ''; const pct = b ? Math.round(Math.abs(a - b) * 100 / b) : null;
      if (!inv && pct === 0) return ''; if (inv && Math.round(Math.abs(a - b) * 10) === 0) return '';
      return `<em class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲' : '▼'} ${pct != null && !inv ? fa(pct) + '%' : fa(Math.round(Math.abs(a - b) * 10) / 10)}</em>`; };
    const link = u => {
      if (!/^https?:\/\//.test(u)) u = 'https://' + u;
      const p = short(u), segs = p.split('/').filter(Boolean), last = segs[segs.length - 1] || '';
      const title = !segs.length ? 'صفحهٔ اصلی' : last.replace(/[-_]+/g, ' ').trim();
      const dir = segs.length > 1 ? '/' + segs.slice(0, -1).join('/') + '/' : '/';   // فقط پوشه (عنوان خودش آخرین بخش است)
      return `<a href="${esc(u)}" target="_blank" rel="noopener" class="gsc-pg" title="${esc(p)}"><span class="t" dir="auto">${esc(title)}</span><span class="p" dir="ltr">${esc(dir)}</span></a>`;
    };
    const U = u => `<td class="u">${link(u)}</td>`, N = v => `<td class="n">${v}</td>`;
    const arrow = (v, unit) => !v ? '<span class="zero">—</span>' : `<em class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲' : '▼'} <span dir="ltr">${fa(Math.abs(v))}${unit || ''}</span></em>`;
    const sec = (id, icon, title, hint, n, inner) => `<details class="gsc-sec s-${id}" ${n ? 'open' : ''}><summary>${App.icon(icon)} <b>${title}</b> <span class="gsc-n">${fa(n)}</span><span class="zero">${hint}</span></summary><div class="gsc-sec-b">${n ? inner : '<div class="gsc-nodata">موردی نیست</div>'}</div></details>`;
    // urlCols: اندیسِ ستون‌های لینک (سرستونشان هم چپ‌چین)؛ بقیهٔ ستون‌های عددی وسط‌چین (td.n)
    const tbl = (head, rows, urlCols) => `<div class="tscroll"><table class="gsc-tbl"><thead><tr>${head.map((h, i) => `<th class="${(urlCols || []).includes(i) ? 'u' : i ? 'n' : ''}">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;

    el.innerHTML = `<div class="gsc-proj">
      <div class="gsc-kpis">
        <div class="k-c"><span>${App.icon('pointer')} کلیک (۲۸ روز)</span><b>${fa(c.clicks)}</b>${delta(c.clicks, p.clicks)}</div>
        <div class="k-i"><span>${App.icon('eye')} ایمپرشن</span><b>${fa(c.impressions)}</b>${delta(c.impressions, p.impressions)}</div>
        <div class="k-r"><span>${App.icon('percent')} CTR</span><b>${fa(c.ctr)}%</b>${delta(c.ctr, p.ctr)}</div>
        <div class="k-p"><span>${App.icon('trophy')} میانگینِ جایگاه</span><b>${fa(c.position)}</b>${delta(c.position, p.position, true)}</div>
      </div>
      <p class="zero" style="margin:4px 2px 8px;font-size:11.5px">مقایسه با ۲۸ روزِ قبل از آن · داده تا ${jd(d.until)} · ${d.sites.map(esc).join('، ')}</p>
      <div class="gsc-chart"></div>
      ${devicesHtml(d.devices)}
      <div class="gsc-group-h">پیشنهادها</div>
      <div class="gsc-legend"><span><em class="up">▲</em> بهتر</span><span><em class="down">▼</em> بدتر</span>
        <span class="sep"></span><span>جایگاه:</span><span class="posb p1" dir="ltr">1–3</span><span class="posb p2" dir="ltr">4–10</span><span class="posb p3" dir="ltr">11–20</span><span class="posb p4" dir="ltr">20+</span></div>
      ${sec('decline', 'trend-down', 'صفحه‌های در حالِ افت', 'کلیکِ ۲۸ روزِ اخیر نسبت به ۲۸ روزِ قبلش ۳۰٪ یا بیشتر کم شده — نامزدِ آپدیت', d.decline.length,
        tbl(['صفحه', 'کلیکِ قبل', 'کلیکِ اخیر', 'افت', 'جایگاهِ قبل', 'جایگاهِ اخیر'], d.decline.map(x => `<tr>${U(x.page)}${N(fa(x.before.clicks))}${N(fa(x.after.clicks))}${N(arrow(-x.drop, '%'))}${N(pos(x.before.position))}${N(pos(x.after.position))}</tr>`), [0]))}
      ${sec('striking', 'star', 'نزدیکِ صفحهٔ اول', '۲۸ روزِ اخیر · جایگاه ۸ تا ۲۰ با نمایشِ زیاد — کمترین کار، بیشترین بازده', d.striking.length,
        tbl(['کلمه', 'صفحه', 'ایمپرشن', 'کلیک', 'جایگاه'], d.striking.map(x => `<tr><td dir="auto">${esc(x.query)}</td>${U(x.page)}${N(fa(x.impressions))}${N(fa(x.clicks))}${N(pos(x.position))}</tr>`), [1]))}
      ${sec('ctr', 'eye', 'CTR پایین', '۲۸ روزِ اخیر · جایگاهِ خوب ولی کلیکِ کم — عنوان و متا را بهتر کن', d.low_ctr.length,
        tbl(['کلمه', 'صفحه', 'جایگاه', 'ایمپرشن', 'CTR'], d.low_ctr.map(x => `<tr><td dir="auto">${esc(x.query)}</td>${U(x.page)}${N(pos(x.position))}${N(fa(x.impressions))}${N(`<span class="ctr-low">${fa(x.ctr)}%</span>`)}</tr>`), [1]))}
      ${sec('cannibal', 'layers', 'رقابتِ صفحه‌ها روی یک کلمه', '۲۸ روزِ اخیر · چند صفحه برای یک کلمه با هم رقابت می‌کنند — ادغام یا تفکیکِ هدف', d.cannibal.length,
        tbl(['کلمه', 'صفحه', 'ایمپرشن', 'کلیک', 'جایگاه'], d.cannibal.map(x => x.pages.map((pg, i) => `<tr class="${i ? 'cont' : 'grp'}">${i ? '' : `<td dir="auto" rowspan="${x.pages.length}" class="q">${esc(x.query)}</td>`}${U(pg.page)}${N(fa(pg.impressions))}${N(fa(pg.clicks))}${N(pos(pg.position))}</tr>`).join('')), [1]))}
      <div class="gsc-group-h">تغییراتِ کلمات <span class="zero">۲۸ روزِ اخیر در برابرِ ۲۸ روزِ قبل</span></div>
      ${sec('new', 'plus', 'کلماتِ تازه', 'حالا نمایش دارند و قبلاً نداشتند (حداقل ۱۰ نمایش)', d.changes.new_n,
        tbl(['کلمه', 'ایمپرشن', 'کلیک', 'جایگاه'], d.changes.new.map(x => `<tr><td dir="auto">${esc(x.query)}</td>${N(fa(x.impressions))}${N(fa(x.clicks))}${N(pos(x.position))}</tr>`)))}
      ${sec('lost', 'trend-down', 'کلماتِ ازدست‌رفته', 'قبلاً نمایش داشتند (حداقل ۲۰) و حالا ندارند', d.changes.lost_n,
        tbl(['کلمه', 'ایمپرشنِ قبل', 'کلیکِ قبل', 'جایگاهِ قبل'], d.changes.lost.map(x => `<tr><td dir="auto">${esc(x.query)}</td>${N(fa(x.impressions))}${N(fa(x.clicks))}${N(pos(x.position))}</tr>`)))}
      ${sec('moves', 'sync', 'بیشترین جابه‌جاییِ جایگاه', 'کلماتی با حداقل ۲۰ نمایش در هر دو بازه', d.changes.up.length + d.changes.down.length,
        tbl(['کلمه', 'جایگاهِ قبل', 'جایگاهِ اخیر', 'تغییر', 'ایمپرشن'], d.changes.up.concat(d.changes.down).map(x => `<tr><td dir="auto">${esc(x.query)}</td>${N(pos(x.before))}${N(pos(x.after))}${N(arrow(x.delta))}${N(fa(x.impressions))}</tr>`)))}
      <div class="gsc-group-h">بخش‌های سایت</div>
      ${sec('sections', 'folder', 'مقایسهٔ بخش‌ها', 'بر اساسِ اولین پوشهٔ نشانی (/blog/، /product/، …) — «/» یعنی صفحه‌های سطحِ اول', d.sections.length,
        tbl(['بخش', 'صفحه', 'کلیکِ قبل', 'کلیکِ اخیر', 'تغییرِ کلیک', 'ایمپرشنِ اخیر', 'جایگاهِ اخیر', 'تغییرِ جایگاه'], d.sections.map(x => `<tr><td dir="ltr" class="u"><b>${esc(x.section)}</b></td>${N(fa(x.pages))}${N(fa(x.previous.clicks))}${N(fa(x.current.clicks))}${N(arrow(x.clicks_delta))}${N(fa(x.current.impressions))}${N(pos(x.current.position))}${N(arrow(x.position_delta))}</tr>`), [0]))}
      ${indexHtml(d.index, sec, tbl, U, N)}
      <div class="gsc-group-h">صفحه‌های بی‌نمایش <span class="zero">منتشرشده در وردپرس ولی بدونِ هیچ نمایشی در گوگل در ۹۰ روزِ اخیر</span></div>
      <div class="gsc-unseen" id="gsc-unseen"></div>
      <div class="gsc-group-h">اثرِ کارها</div>
      ${sec('types', 'chart', 'مقایسهٔ انواعِ کار', 'میانگینِ تغییرِ کلیکِ صفحه ۲۸ روز بعد از انجام (فقط کارهای با ۲۸ روزِ کامل)', d.by_type.length,
        tbl(['نوع', 'تعداد', 'میانگینِ تغییرِ کلیک', 'میانگینِ تغییرِ جایگاه', 'هزینه به‌ازای هر کلیک'], d.by_type.map(g => `<tr><td>${esc(g.type)}</td>${N(fa(g.n))}${N(arrow(g.avg_clicks))}${N(arrow(g.avg_position))}${N(g.cost_per_click ? fa(g.cost_per_click) + ' ریال' : '—')}</tr>`)))}
      ${sec('work', 'check-circle', 'قبل و بعدِ هر تسک', 'تسک‌های انجام‌شدهٔ ۶ ماهِ اخیر که صفحه یا هدفشان در سرچ کنسول است', d.work.length,
        tbl(['تسک', 'نوع', 'تاریخ', 'کلیکِ قبل', 'کلیکِ بعد', 'تغییرِ کلیک', 'تغییرِ جایگاه', 'هزینه/کلیک'], d.work.map(w => `<tr><td><a class="lnk" href="#" data-open-task="${w.id}">${esc(w.title)}</a>${w.full ? '' : ` <span class="zero">(${w.days} روز)</span>`}</td><td>${esc(w.type)}</td>${N(jd(w.done))}
          ${N(fa(w.clicks_before))}${N(fa(w.clicks_after))}${N(arrow(w.clicks_delta))}
          ${N(arrow(w.position_delta))}
          ${N(w.cost_per_click ? fa(w.cost_per_click) : '—')}</tr>`)))}
    </div>`;
    chartBlock(el.querySelector('.gsc-chart'), d.series, true);
    el.querySelector('.gsc-proj').insertAdjacentHTML('afterbegin', `<div class="gsc-top"><a class="btn btn-sm" href="/gsc/api/project/${pid}/export/">${App.icon('file-excel')} خروجیِ اکسل</a></div>`);
    unseenBlock(pid, el.querySelector('#gsc-unseen'), d.unseen, link, N);
  }

  const KIND = {post: 'مقاله', page: 'برگه', product: 'محصول', category: 'دستهٔ مقاله', product_cat: 'دستهٔ محصول'};
  const kindName = k => KIND[k] || k;

  function devicesHtml(list) {
    if (!list || !list.length) return '';
    const tot = list.reduce((a, x) => a + x.current.clicks, 0) || 1;
    const ch = (a, b, inv) => { const v = inv ? (b && a ? b - a : 0) : a - b; if (!v || Math.abs(v) < (inv ? .1 : 1)) return ''; const pct = !inv && b ? Math.round(Math.abs(v) * 100 / b) : null;
      return `<em class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲' : '▼'}<span dir="ltr">${pct != null ? pct + '%' : fa(Math.round(Math.abs(v) * 10) / 10)}</span></em>`; };
    return `<div class="gsc-dev">${list.map(x => `<div><b>${esc(x.device)}</b><span class="zero" dir="ltr">${Math.round(x.current.clicks * 100 / tot)}%</span>
      <span>کلیک ${fa(x.current.clicks)} ${ch(x.current.clicks, x.previous.clicks)}</span>
      <span>ایمپرشن ${fa(x.current.impressions)} ${ch(x.current.impressions, x.previous.impressions)}</span>
      <span>جایگاه ${pos(x.current.position)} ${ch(x.current.position, x.previous.position, true)}</span></div>`).join('')}</div>`;
  }

  function indexHtml(ix, sec, tbl, U, N) {
    if (!ix) return `<div class="gsc-group-h">ایندکس و کراول</div><div class="gsc-nodata">هنوز بررسی نشده — بعد از همگام‌سازیِ بعدی، صفحهٔ تسک‌ها و صفحه‌های پربازدید خودکار بررسی می‌شوند.</div>`;
    const crawl = x => x.last_crawl ? jd(x.last_crawl) : '—';
    return `<div class="gsc-group-h">ایندکس و کراول <span class="zero">${fa(ix.checked)} صفحه بررسی شده · ${fa(ix.indexed)} ایندکس</span></div>
      ${sec('noindex', 'warning', 'بررسی‌شده و ایندکس‌نشده', 'صفحهٔ تسک‌ها، صفحه‌های تازه و پربازدید که گوگل ایندکس نکرده — علت در ستونِ وضعیت', ix.not_indexed.length,
        tbl(['صفحه', 'وضعیت', 'آخرین کراول', 'بررسی'], ix.not_indexed.map(x => `<tr>${U(x.url)}<td class="cov">${esc(x.coverage)}</td>${N(crawl(x))}${N(jd(x.checked))}</tr>`), [0]))}
      ${sec('stale', 'hourglass', 'کراولِ قدیمی', 'ایندکس است ولی گوگل بیش از ۳۰ روز است سراغش نیامده', ix.stale.length,
        tbl(['صفحه', 'آخرین کراول', 'بررسی'], ix.stale.map(x => `<tr>${U(x.url)}${N(crawl(x))}${N(jd(x.checked))}</tr>`), [0]))}
      ${sec('sitemaps', 'layers', 'سایت‌مپ‌ها', 'از سرچ کنسول', ix.sitemaps.length,
        tbl(['سایت‌مپ', 'نشانی‌ها', 'خطا', 'هشدار', 'آخرین خواندن'], ix.sitemaps.map(m => `<tr><td dir="ltr" class="u">${esc(m.path)}</td>${N(fa(m.submitted))}${N(m.errors ? `<span class="ctr-low">${fa(m.errors)}</span>` : '0')}${N(fa(m.warnings))}${N(m.last_downloaded ? jd(m.last_downloaded.slice(0, 10)) : (m.pending ? 'در انتظار' : '—'))}</tr>`), [0]))}`;
  }

  // صفحه‌های بی‌نمایش: خلاصه به تفکیکِ نوع + فهرستِ فیلترشونده (نوع/جستجو/تازه‌ها) + «بررسیِ ایندکس» برای انتخاب‌شده‌ها
  function unseenBlock(pid, box, sum, link, N) {
    if (!box) return;
    if (!sum.kinds.length) {
      box.innerHTML = `<div class="gsc-nodata">${sum.error ? esc(sum.error) : sum.pending ? 'فهرستِ صفحه‌ها هنوز از وردپرس گرفته نشده (با همگام‌سازیِ بعدی، یا همین الان:)' : 'صفحه‌ای پیدا نشد'}
        <div style="margin-top:8px"><button type="button" class="btn btn-sm" id="un-inv">${App.icon('refresh')} دریافتِ فهرست از وردپرس</button></div></div>`;
    } else {
      box.innerHTML = `<div class="tscroll"><table class="gsc-tbl un-sum"><thead><tr><th>نوع</th><th class="n">کل</th><th class="n">با نمایش</th><th class="n">بی‌نمایش</th><th class="n">تازه (کمتر از ۳ هفته)</th><th class="n">سهمِ بی‌نمایش</th></tr></thead><tbody>
        ${sum.kinds.map(k => `<tr data-kind="${esc(k.kind)}" class="pick"><td><b>${esc(kindName(k.kind))}</b></td>${N(fa(k.total))}${N(fa(k.seen))}${N(k.unseen ? `<span class="ctr-low">${fa(k.unseen)}</span>` : '0')}${N(fa(k.new))}
          ${N(`<span class="bar"><i style="width:${Math.round(k.unseen * 100 / (k.total || 1))}%"></i></span> <span dir="ltr">${Math.round(k.unseen * 100 / (k.total || 1))}%</span>`)}</tr>`).join('')}</tbody></table></div>
        <div class="un-bar">
          <select id="un-kind"><option value="">همهٔ نوع‌ها</option>${sum.kinds.map(k => `<option value="${esc(k.kind)}">${esc(kindName(k.kind))} (${fa(k.unseen)})</option>`).join('')}</select>
          <input class="input" id="un-q" placeholder="جستجو در عنوان یا نشانی…">
          <label class="mcp-switch"><input type="checkbox" id="un-new"> با صفحه‌های تازه</label>
          <span class="zero" id="un-count"></span>
          <span style="margin-inline-start:auto;display:inline-flex;gap:6px">
            <button type="button" class="btn btn-sm" id="un-check" disabled>${App.icon('search')} بررسیِ ایندکسِ انتخاب‌شده‌ها</button>
            <button type="button" class="btn btn-sm" id="un-inv" title="فهرست هفته‌ای یک بار خودکار تازه می‌شود">${App.icon('refresh')} تازه‌کردنِ فهرست</button></span>
        </div>
        <div id="un-list"></div>`;
    }
    const inv = box.querySelector('#un-inv');
    if (inv) inv.onclick = async () => { await App.fetchJSON(`/gsc/api/project/${pid}/inventory/`, {method: 'POST'}); App.toast('در حالِ دریافت از وردپرس — برای سایتِ بزرگ چند دقیقه؛ بعد صفحه را رفرش کن', 'ok', 6000); };
    if (!sum.kinds.length) return;
    let rows = [], total = 0, t;
    const list = box.querySelector('#un-list'), cnt = box.querySelector('#un-count'), chk = box.querySelector('#un-check');
    const idx = x => !x.index ? '<span class="zero">—</span>' : x.index.indexed ? `<span class="ix ok">${App.icon('check')} ایندکس</span>` : `<span class="ix bad" title="${esc(x.index.coverage)}">${App.icon('warning')} ${esc(x.index.coverage || 'ایندکس نشده')}</span>`;
    const render = () => {
      list.innerHTML = `<div class="tscroll un-scroll"><table class="gsc-tbl"><thead><tr><th class="n"><input type="checkbox" id="un-all"></th><th class="u">صفحه</th><th>نوع</th><th class="n">انتشار</th><th>ایندکس</th></tr></thead><tbody>
        ${rows.map((x, i) => `<tr><td class="n"><input type="checkbox" class="un-c" data-i="${i}"></td><td class="u">${link(x.url).replace('class="t" dir="auto">' + esc(nice(x.url).title), 'class="t" dir="auto">' + esc(x.title || nice(x.url).title))}</td><td>${esc(kindName(x.kind))}</td>${N(x.published ? jd(x.published) : '—')}<td>${idx(x)}</td></tr>`).join('') || '<tr><td colspan="5" class="gsc-nodata">موردی نیست</td></tr>'}</tbody></table></div>
        ${rows.length < total ? `<button type="button" class="btn btn-sm gsc-more" id="un-more">نمایشِ بیشتر (${fa(total - rows.length)})</button>` : ''}`;
      cnt.textContent = `${fa(total)} صفحه`;
      const all = list.querySelector('#un-all');
      const sync = () => { chk.disabled = !list.querySelector('.un-c:checked'); };
      if (all) all.onchange = () => { list.querySelectorAll('.un-c').forEach((c, i) => c.checked = all.checked && i < 20); sync(); };
      list.querySelectorAll('.un-c').forEach(c => c.onchange = sync);
      const more = list.querySelector('#un-more'); if (more) more.onclick = () => load(rows.length);
      sync();
    };
    const load = async (offset) => {
      const q = new URLSearchParams({kind: box.querySelector('#un-kind').value, q: box.querySelector('#un-q').value, new: box.querySelector('#un-new').checked ? '1' : '', offset: offset || 0, limit: offset ? 100 : 30});
      const r = await (await fetch(`/gsc/api/project/${pid}/unseen/?${q}`)).json();
      rows = offset ? rows.concat(r.rows) : r.rows; total = r.total; render();
    };
    box.querySelector('#un-kind').onchange = () => load(0);
    box.querySelector('#un-new').onchange = () => load(0);
    box.querySelector('#un-q').oninput = () => { clearTimeout(t); t = setTimeout(() => load(0), 350); };
    box.querySelectorAll('.un-sum tr.pick').forEach(tr => tr.onclick = () => { box.querySelector('#un-kind').value = tr.dataset.kind; load(0); });
    chk.onclick = async () => {
      const picked = [...list.querySelectorAll('.un-c:checked')].map(c => rows[+c.dataset.i]).slice(0, 20);
      if (!picked.length) return;
      const r = await App.fetchJSON(`/gsc/api/project/${pid}/inspect/`, {method: 'POST', body: {urls: picked.map(x => x.url)}});
      picked.forEach(x => { if (r.results[x.url]) x.index = r.results[x.url]; });
      render(); App.toast(`${fa(Object.keys(r.results).length)} صفحه بررسی شد`, 'ok');
    };
    load(0);
  }

  window.GSC = {chart, chartBlock, queryTable, taskCard, projectTab};
})();
