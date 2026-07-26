/* AI 주식 연관도. For each stock card (data-kw keywords), find blog-covered AI tools whose
   name/title/owner match; show count + related tool chips; fill summary tiles; and render a
   "blog correlation" bar chart (Chart.js). External file (not HTML-minified). */
(function () {
  var el = document.getElementById('stocks-tools');
  if (!el) { return; }
  var TOOLS = [];
  try { TOOLS = JSON.parse(el.textContent); } catch (e) { return; }
  var LC = TOOLS.map(function (t) { return { t: t, s: (t.name + ' ' + t.title + ' ' + t.owner).toLowerCase() }; });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function relatedOf(kws) {
    var out = [];
    for (var i = 0; i < LC.length; i++) {
      for (var j = 0; j < kws.length; j++) {
        if (kws[j] && LC[i].s.indexOf(kws[j]) !== -1) { out.push(LC[i].t); break; }
      }
    }
    out.sort(function (a, b) { return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0); });
    return out;
  }

  var rows = [];
  Array.prototype.forEach.call(document.querySelectorAll('.stk'), function (card) {
    var kws = (card.getAttribute('data-kw') || '').toLowerCase().split('|')
      .map(function (x) { return x.trim(); }).filter(Boolean);
    var rel = relatedOf(kws);
    card.setAttribute('data-count', rel.length);
    var relEl = card.querySelector('.stk-rel');
    if (relEl) { relEl.textContent = rel.length; }
    var wrap = card.querySelector('.stk-tools');
    if (wrap) {
      wrap.innerHTML = rel.length
        ? rel.slice(0, 4).map(function (t) { return '<a class="stk-tool" href="' + t.url + '">' + esc(t.name) + '</a>'; }).join('')
          + (rel.length > 4 ? '<span class="stk-more">+' + (rel.length - 4) + '</span>' : '')
        : '<span class="stk-none">직접 다룬 글 없음</span>';
    }
    var nameEl = card.querySelector('.stk-name');
    rows.push({ name: nameEl ? nameEl.textContent : '', count: rel.length, market: card.getAttribute('data-market') || 'US' });
  });

  /* summary tiles */
  function setText(id, v) { var e = document.getElementById(id); if (e) { e.textContent = v; } }
  setText('stk-total', rows.length);
  setText('stk-us', rows.filter(function (r) { return r.market === 'US'; }).length);
  setText('stk-kr', rows.filter(function (r) { return r.market === 'KR'; }).length);

  /* sort cards within each market group by correlation (most connected first) */
  Array.prototype.forEach.call(document.querySelectorAll('.stk-grid'), function (grid) {
    Array.prototype.slice.call(grid.querySelectorAll('.stk'))
      .sort(function (a, b) { return (+b.getAttribute('data-count') || 0) - (+a.getAttribute('data-count') || 0); })
      .forEach(function (c) { grid.appendChild(c); });
  });

  /* correlation bar chart */
  function isDark() {
    var m = document.documentElement.getAttribute('data-mode');
    if (m) { return m === 'dark'; }
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }
  function drawChart() {
    var canvas = document.getElementById('stk-corr-chart');
    if (!canvas) { return; }
    if (typeof Chart === 'undefined') { return setTimeout(drawChart, 200); }
    var dark = isDark();
    Chart.defaults.color = dark ? '#c3c2b7' : '#2b2926';
    Chart.defaults.borderColor = dark ? 'rgba(240,238,233,.12)' : 'rgba(43,41,38,.12)';
    if (Chart.defaults.font) { Chart.defaults.font.family = 'Pretendard, sans-serif'; }
    var top = rows.slice().sort(function (a, b) { return b.count - a.count; });
    var us = dark ? '#3987e5' : '#2a78d6';
    var kr = dark ? '#199e70' : '#1baf7a';
    var prev = Chart.getChart ? Chart.getChart(canvas) : null;
    if (prev) { prev.destroy(); } // idempotent: safe if drawChart() runs more than once
    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: top.map(function (r) { return r.name; }),
        datasets: [{
          label: '블로그 관련 글 수',
          data: top.map(function (r) { return r.count; }),
          backgroundColor: top.map(function (r) { return r.market === 'KR' ? kr : us; }),
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', drawChart); } else { drawChart(); }
})();
