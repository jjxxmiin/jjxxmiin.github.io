/* Renders ```chartjs code blocks (a JSON Chart.js config) as charts, themed with the
   2026 Pantone Color of the Year "Cloud Dancer" (#F0EEE9) as the surface and a validated
   colorblind-safe accent palette. External file (not HTML-minified), so // comments are safe. */
(function () {
  var CLOUD = '#F0EEE9';                       // Color of the Year — chart surface
  var LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];
  var DARK  = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926'];

  function isDark() {
    var m = document.documentElement.getAttribute('data-mode');
    if (m) { return m === 'dark'; }
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function render() {
    if (typeof Chart === 'undefined') { return setTimeout(render, 200); }
    var dark = isDark();
    var palette = dark ? DARK : LIGHT;
    var ink = dark ? '#c3c2b7' : '#2b2926';
    var grid = dark ? 'rgba(240,238,233,0.12)' : 'rgba(43,41,38,0.12)';
    var surface = dark ? '#201f1d' : CLOUD;
    Chart.defaults.color = ink;
    Chart.defaults.borderColor = grid;
    if (Chart.defaults.font) { Chart.defaults.font.family = 'Pretendard, sans-serif'; }

    var blocks = document.querySelectorAll('pre code.language-chartjs, code.language-chartjs, .language-chartjs');
    blocks.forEach(function (code) {
      if (code.getAttribute('data-chart-done')) { return; }
      var pre = code.closest('pre') || code;
      try {
        var cfg = JSON.parse(code.textContent);
        cfg.options = cfg.options || {};
        cfg.options.responsive = true;
        cfg.options.maintainAspectRatio = false;
        var arc = ['pie', 'doughnut', 'polarArea'].indexOf(cfg.type) !== -1;
        (cfg.data && cfg.data.datasets || []).forEach(function (ds, i) {
          if (ds.backgroundColor === undefined) {
            ds.backgroundColor = arc
              ? (ds.data || []).map(function (_, j) { return palette[j % palette.length]; })
              : palette[i % palette.length];
          }
          if (ds.borderColor === undefined) { ds.borderColor = arc ? surface : palette[i % palette.length]; }
          if (ds.borderWidth === undefined) { ds.borderWidth = arc ? 2 : 1.5; }
        });
        var wrap = document.createElement('div');
        wrap.className = 'chartjs-wrap';
        wrap.style.cssText = 'position:relative;max-width:760px;height:380px;margin:1.5rem auto;'
          + 'padding:16px 18px;border-radius:12px;background:' + surface + ';'
          + 'border:1px solid ' + (dark ? 'rgba(240,238,233,0.10)' : 'rgba(43,41,38,0.08)') + ';';
        var canvas = document.createElement('canvas');
        wrap.appendChild(canvas);
        code.setAttribute('data-chart-done', '1');
        pre.parentNode.replaceChild(wrap, pre);
        new Chart(canvas, cfg);
      } catch (e) {
        if (window.console) { console.error('chartjs render failed:', e); }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
  window.addEventListener('load', render);
})();
