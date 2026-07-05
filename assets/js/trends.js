/* AI 트렌드 대시보드. Reads #trends-data (Liquid-generated post list) and renders
   Chart.js charts: monthly publishing, category distribution, most-featured orgs.
   External file (not HTML-minified), so comments are safe. */
(function () {
  var el = document.getElementById('trends-data');
  if (!el) { return; }
  var POSTS = [];
  try { POSTS = JSON.parse(el.textContent); } catch (e) { return; }

  var LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];
  var DARK = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926'];
  var CLOUD = '#F0EEE9';

  function isDark() {
    var m = document.documentElement.getAttribute('data-mode');
    if (m) { return m === 'dark'; }
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function catOf(t) {
    var s = (t.name + ' ' + t.title).toLowerCase();
    if (/design|디자인|figma|canvas/.test(s)) { return '디자인'; }
    if (/video|영상|비디오|image|이미지|diffus|render|montage|clip|photo|사진/.test(s)) { return '영상/이미지'; }
    if (/voice|음성|speech|audio|music|음악|\btts\b|sound|오디오/.test(s)) { return '음성/음악'; }
    if (/\brag\b|search|검색|graph|그래프|memory|메모리|데이터|vector|벡터|\bdb\b|index|knowledge/.test(s)) { return '데이터/검색'; }
    if (/cod|코딩|\bide\b|\bcli\b|agent|에이전트|\bdev\b|compil|컴파일|plugin|terminal|mcp|debug/.test(s)) { return '코딩'; }
    return '기타';
  }

  function setText(id, v) { var e = document.getElementById(id); if (e) { e.textContent = v; } }

  function fillStats() {
    var orgs = {};
    POSTS.forEach(function (p) { if (p.owner) { orgs[p.owner] = 1; } });
    var nowYm = new Date().toISOString().slice(0, 7);
    var thisMonth = POSTS.filter(function (p) { return (p.date || '').slice(0, 7) === nowYm; }).length;
    setText('st-total', POSTS.length);
    setText('st-orgs', Object.keys(orgs).length);
    setText('st-month', thisMonth);
  }

  function start() {
    fillStats();
    if (typeof Chart === 'undefined') { return setTimeout(start, 200); }
    var dark = isDark();
    var palette = dark ? DARK : LIGHT;
    var ink = dark ? '#c3c2b7' : '#2b2926';
    var grid = dark ? 'rgba(240,238,233,.12)' : 'rgba(43,41,38,.12)';
    Chart.defaults.color = ink;
    Chart.defaults.borderColor = grid;
    if (Chart.defaults.font) { Chart.defaults.font.family = 'Pretendard, sans-serif'; }

    /* monthly counts (last 12 months present in data) */
    var mMap = {};
    POSTS.forEach(function (p) { var k = (p.date || '').slice(0, 7); if (k) { mMap[k] = (mMap[k] || 0) + 1; } });
    var months = Object.keys(mMap).sort().slice(-12);
    mkChart('trends-monthly', {
      type: 'bar',
      data: { labels: months, datasets: [{ label: '글 수', data: months.map(function (m) { return mMap[m]; }), backgroundColor: palette[0], borderRadius: 4 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });

    /* category distribution */
    var cMap = {};
    POSTS.forEach(function (p) { var c = catOf(p); cMap[c] = (cMap[c] || 0) + 1; });
    var cats = Object.keys(cMap).sort(function (a, b) { return cMap[b] - cMap[a]; });
    mkChart('trends-cats', {
      type: 'doughnut',
      data: { labels: cats, datasets: [{ data: cats.map(function (c) { return cMap[c]; }), backgroundColor: cats.map(function (_, i) { return palette[i % palette.length]; }), borderColor: dark ? '#201f1d' : CLOUD, borderWidth: 2 }] },
      options: { plugins: { legend: { position: 'right', labels: { boxWidth: 12 } } }, cutout: '58%' }
    });

    /* top orgs */
    var oMap = {};
    POSTS.forEach(function (p) { if (p.owner) { oMap[p.owner] = (oMap[p.owner] || 0) + 1; } });
    var owners = Object.keys(oMap).sort(function (a, b) { return oMap[b] - oMap[a]; }).slice(0, 10);
    mkChart('trends-orgs', {
      type: 'bar',
      data: { labels: owners, datasets: [{ label: '글 수', data: owners.map(function (o) { return oMap[o]; }), backgroundColor: palette[4], borderRadius: 4 }] },
      options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }

  function mkChart(id, cfg) {
    var c = document.getElementById(id);
    if (!c) { return; }
    cfg.options = cfg.options || {};
    cfg.options.responsive = true;
    cfg.options.maintainAspectRatio = false;
    try { new Chart(c, cfg); } catch (e) { if (window.console) { console.error('trends chart failed', id, e); } }
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', start); } else { start(); }
  window.addEventListener('load', start);
})();
