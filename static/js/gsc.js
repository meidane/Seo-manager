/* gsc.js — نمایشِ دادهٔ سرچ کنسول (منبعِ واحدِ فرانت): نمودارِ روند + جدولِ کلمات + کارتِ زیرِ تسک + تبِ تحلیلِ پروژه.
   داده از `/gsc/api/task/<id>/` و `/gsc/api/project/<id>/` (gsc/analysis.py). رنگ‌ها فقط از متغیرهای CSS.
   نمودار: یک سری، یک محور (کلیک | ایمپرشن | جایگاه با محورِ وارونه)، خطِ ۲px + ناحیهٔ کم‌رنگ، تولتیپ با هاور. */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const fa = n => (n == null ? '—' : Number(n).toLocaleString('fa-IR'));
  const jd = iso => new Date(iso + 'T12:00:00').toLocaleDateString('fa-IR-u-ca-persian', {month: 'short', day: 'numeric'});
  const M = {clicks: 'کلیک', impressions: 'ایمپرشن', ctr: 'CTR', position: 'جایگاه'};
  const decode = u => { try { return decodeURI(u); } catch (_) { return u; } };
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
      tip.innerHTML = `<b>${jd(s.date)}</b><span>کلیک ${fa(s.clicks)}</span><span>ایمپرشن ${fa(s.impressions)}</span><span>CTR ${fa(s.ctr)}٪</span><span>جایگاه ${fa(s.position)}</span>`;
      const left = x(i) * r.width / W;
      tip.style.left = Math.min(Math.max(left - tip.offsetWidth / 2, 0), r.width - tip.offsetWidth) + 'px';
    };
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerleave', () => { tip.hidden = true; cr.style.display = 'none'; dot.style.display = 'none'; });
  }

  // نمودار + تب‌های متریک + جمعِ بازه
  function chartBlock(el, series, compact) {
    const tot = series.reduce((o, d) => { o.c += d.clicks; o.i += d.impressions; o.pw += (d.position || 0) * d.impressions; return o; }, {c: 0, i: 0, pw: 0});
    const sum = {clicks: fa(tot.c), impressions: fa(tot.i), ctr: tot.i ? fa(Math.round(tot.c * 1000 / tot.i) / 10) + '٪' : '—', position: tot.i ? fa(Math.round(tot.pw * 10 / tot.i) / 10) : '—'};
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
        <tbody>${vis.map(r => `<tr><td dir="auto">${esc(r.query)}</td><td>${fa(r.clicks)}</td><td>${fa(r.impressions)}</td><td>${fa(r.ctr)}٪</td><td>${fa(r.position)}</td></tr>`).join('')}</tbody></table></div>
        ${rows.length > vis.length ? `<button type="button" class="btn btn-sm gsc-more">نمایشِ همه (${fa(rows.length)})</button>` : ''}`;
      el.querySelectorAll('th').forEach(th => th.onclick = () => { const k = th.dataset.k; dir = k === key ? -dir : (k === 'position' || k === 'query' ? 1 : -1); key = k; render(); });
      const m = el.querySelector('.gsc-more'); if (m) m.onclick = () => { all = true; render(); };
    };
    render();
  }

  function impactHtml(im) {
    if (!im) return '';
    const b = im.before, a = im.after, cd = im.clicks_delta, pd = im.position_delta;
    const sign = v => `<bdi dir="ltr">${v > 0 ? '+' : ''}${fa(v)}</bdi>`;
    return `<div class="gsc-imp"><b>اثرِ این تسک</b> <span class="zero">${im.full ? '۲۸ روز قبل و بعد از انجام' : fa(im.days) + ' روز قبل و بعد (هنوز ۲۸ روز نگذشته)'}</span>
      <div class="gsc-imp-r"><span>کلیک ${fa(b.clicks)} ← ${fa(a.clicks)} <em class="${cd > 0 ? 'up' : cd < 0 ? 'down' : ''}">${sign(cd)}</em></span>
      <span>ایمپرشن ${fa(b.impressions)} ← ${fa(a.impressions)}</span>
      <span>جایگاه ${fa(b.position)} ← ${fa(a.position)}${pd ? ` <em class="${pd > 0 ? 'up' : pd < 0 ? 'down' : ''}">${pd > 0 ? 'بهتر ' : pd < 0 ? 'بدتر ' : ''}${fa(Math.abs(pd))}</em>` : ''}</span></div></div>`;
  }

  // ── کارتِ زیرِ تسک (خودکار؛ فقط اگر صفحهٔ تسک در سرچ کنسول باشد) ──
  async function taskCard(taskId, box) {
    if (!box) return;
    let d;
    try { const r = await fetch(`/gsc/api/task/${taskId}/`); if (!r.ok) return; d = await r.json(); } catch (_) { return; }
    const pages = (d.pages || []);
    if (!pages.length) return;
    box.style.display = '';
    const tabs = pages.length > 1 ? `<div class="gsc-pages">${pages.map((p, i) => `<button type="button" class="chip${i ? '' : ' on'}" data-i="${i}" title="${esc(decode(p.url))}">${p.role === 'target' ? 'هدف: ' : ''}${esc(short(p.url))}</button>`).join('')}</div>` : '';
    box.innerHTML = `<div class="gsc-card"><div class="gsc-card-h">${App.icon('chart')} سرچ کنسول <span class="zero">۳ ماهِ اخیر${pages[0].until ? ' تا ' + jd(pages[0].until) : ''}</span></div>${tabs}<div class="gsc-body"></div></div>`;
    const body = box.querySelector('.gsc-body');
    const show = i => {
      const p = pages[i];
      body.innerHTML = `<a class="gsc-url" href="${esc(p.url)}" target="_blank" rel="noopener" dir="ltr">${esc(decode(p.url))}</a>${impactHtml(p.impact)}<div class="gsc-chart"></div>
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
      return `<em class="${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲' : '▼'} ${pct != null && !inv ? fa(pct) + '٪' : fa(Math.round(Math.abs(a - b) * 10) / 10)}</em>`; };
    const link = u => `<a href="https://${esc(u)}" target="_blank" rel="noopener" dir="ltr" class="gsc-pg" title="${esc(u)}">${esc(short('https://' + u))}</a>`;
    const sec = (id, icon, title, hint, n, inner) => `<details class="gsc-sec" ${n ? 'open' : ''}><summary>${App.icon(icon)} <b>${title}</b> <span class="gsc-n">${fa(n)}</span><span class="zero">${hint}</span></summary><div class="gsc-sec-b">${n ? inner : '<div class="gsc-nodata">موردی نیست</div>'}</div></details>`;
    const tbl = (head, rows) => `<div class="tscroll"><table class="gsc-tbl"><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;

    el.innerHTML = `<div class="gsc-proj">
      <div class="gsc-kpis">
        <div><span>کلیک (۲۸ روز)</span><b>${fa(c.clicks)}</b>${delta(c.clicks, p.clicks)}</div>
        <div><span>ایمپرشن</span><b>${fa(c.impressions)}</b>${delta(c.impressions, p.impressions)}</div>
        <div><span>CTR</span><b>${fa(c.ctr)}٪</b></div>
        <div><span>میانگینِ جایگاه</span><b>${fa(c.position)}</b>${delta(c.position, p.position, true)}</div>
      </div>
      <p class="zero" style="margin:4px 2px 8px;font-size:11.5px">مقایسه با ۲۸ روزِ قبل از آن · داده تا ${jd(d.until)} · ${d.sites.map(esc).join('، ')}</p>
      <div class="gsc-chart"></div>
      <div class="gsc-group-h">پیشنهادها</div>
      ${sec('decline', 'warning', 'صفحه‌های در حالِ افت', 'کلیکِ ۲۸ روزِ اخیر ۳۰٪+ کمتر — نامزدِ آپدیت', d.decline.length,
        tbl(['صفحه', 'کلیکِ قبل', 'کلیکِ اخیر', 'افت', 'جایگاه'], d.decline.map(x => `<tr><td>${link(x.page)}</td><td>${fa(x.before.clicks)}</td><td>${fa(x.after.clicks)}</td><td><em class="down">${fa(x.drop)}٪</em></td><td>${fa(x.before.position)} ← ${fa(x.after.position)}</td></tr>`)))}
      ${sec('striking', 'star', 'نزدیکِ صفحهٔ اول', 'جایگاه ۸ تا ۲۰ با نمایشِ زیاد — کمترین کار، بیشترین بازده', d.striking.length,
        tbl(['کلمه', 'صفحه', 'ایمپرشن', 'کلیک', 'جایگاه'], d.striking.map(x => `<tr><td dir="auto">${esc(x.query)}</td><td>${link(x.page)}</td><td>${fa(x.impressions)}</td><td>${fa(x.clicks)}</td><td>${fa(x.position)}</td></tr>`)))}
      ${sec('ctr', 'eye', 'CTR پایین', 'جایگاهِ خوب ولی کلیکِ کم — عنوان و متا را بهتر کن', d.low_ctr.length,
        tbl(['کلمه', 'صفحه', 'جایگاه', 'ایمپرشن', 'CTR'], d.low_ctr.map(x => `<tr><td dir="auto">${esc(x.query)}</td><td>${link(x.page)}</td><td>${fa(x.position)}</td><td>${fa(x.impressions)}</td><td>${fa(x.ctr)}٪</td></tr>`)))}
      ${sec('cannibal', 'layers', 'رقابتِ صفحه‌ها روی یک کلمه', 'چند صفحه برای یک کلمه با هم رقابت می‌کنند — ادغام یا تفکیکِ هدف', d.cannibal.length,
        tbl(['کلمه', 'صفحه‌ها (ایمپرشن · جایگاه)'], d.cannibal.map(x => `<tr><td dir="auto">${esc(x.query)}</td><td>${x.pages.map(pg => `<div>${link(pg.page)} <span class="zero">${fa(pg.impressions)} · ${fa(pg.position)}</span></div>`).join('')}</td></tr>`)))}
      <div class="gsc-group-h">اثرِ کارها</div>
      ${sec('types', 'chart', 'مقایسهٔ انواعِ کار', 'میانگینِ تغییرِ کلیکِ صفحه ۲۸ روز بعد از انجام (فقط کارهای با ۲۸ روزِ کامل)', d.by_type.length,
        tbl(['نوع', 'تعداد', 'میانگینِ کلیکِ اضافه', 'میانگینِ بهبودِ جایگاه', 'هزینه به‌ازای هر کلیک'], d.by_type.map(g => `<tr><td>${esc(g.type)}</td><td>${fa(g.n)}</td><td>${fa(g.avg_clicks)}</td><td>${fa(g.avg_position)}</td><td>${g.cost_per_click ? fa(g.cost_per_click) + ' ریال' : '—'}</td></tr>`)))}
      ${sec('work', 'check-circle', 'قبل و بعدِ هر تسک', 'تسک‌های انجام‌شدهٔ ۶ ماهِ اخیر که صفحه یا هدفشان در سرچ کنسول است', d.work.length,
        tbl(['تسک', 'نوع', 'تاریخ', 'کلیک قبل ← بعد', 'جایگاه', 'هزینه/کلیک'], d.work.map(w => `<tr><td><a class="lnk" href="#" data-open-task="${w.id}">${esc(w.title)}</a>${w.full ? '' : ` <span class="zero">(${fa(w.days)} روز)</span>`}</td><td>${esc(w.type)}</td><td>${jd(w.done)}</td>
          <td>${fa(w.clicks_before)} ← ${fa(w.clicks_after)} <em class="${w.clicks_delta > 0 ? 'up' : w.clicks_delta < 0 ? 'down' : ''}"><bdi dir="ltr">${w.clicks_delta > 0 ? '+' : ''}${fa(w.clicks_delta)}</bdi></em></td>
          <td>${w.position_delta == null ? '—' : !w.position_delta ? 'بدونِ تغییر' : `<em class="${w.position_delta > 0 ? 'up' : w.position_delta < 0 ? 'down' : ''}">${w.position_delta > 0 ? 'بهتر ' : 'بدتر '}${fa(Math.abs(w.position_delta))}</em>`}</td>
          <td>${w.cost_per_click ? fa(w.cost_per_click) : '—'}</td></tr>`)))}
    </div>`;
    chartBlock(el.querySelector('.gsc-chart'), d.series, true);
  }

  window.GSC = {chart, chartBlock, queryTable, taskCard, projectTab};
})();
