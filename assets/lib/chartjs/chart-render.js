/* Renders ```chartjs code blocks (a JSON Chart.js config) as charts, themed with the
   2026 Pantone Color of the Year "Cloud Dancer" (#F0EEE9) as the surface and a validated
   colorblind-safe accent palette. External file (not HTML-minified), so // comments are safe. */
(function () {
  var CLOUD = '#F0EEE9';                       // Color of the Year — chart surface
  var LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];
  var DARK  = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926'];

  function isDark() {
    var m = document.documentElement.getAttribute('data-bs-theme')
      || document.documentElement.getAttribute('data-mode');
    if (m) { return m === 'dark'; }
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function themeValues() {
    var dark = isDark();
    return {
      dark: dark,
      palette: dark ? DARK : LIGHT,
      ink: dark ? '#d8dbe6' : '#2b2926',
      grid: dark ? 'rgba(240,238,233,0.12)' : 'rgba(43,41,38,0.12)',
      surface: dark ? '#201f27' : CLOUD
    };
  }

  function applyDefaults(theme) {
    Chart.defaults.color = theme.ink;
    Chart.defaults.borderColor = theme.grid;
    if (Chart.defaults.font) { Chart.defaults.font.family = 'SUIT, sans-serif'; }
  }

  function applyDatasetColors(cfg, theme) {
    var arc = ['pie', 'doughnut', 'polarArea'].indexOf(cfg.type) !== -1;
    (cfg.data && cfg.data.datasets || []).forEach(function (ds, i) {
      if (ds.backgroundColor === undefined || ds._opsoaiAutoBackground) {
        ds._opsoaiAutoBackground = true;
        ds.backgroundColor = arc
          ? (ds.data || []).map(function (_, j) { return theme.palette[j % theme.palette.length]; })
          : theme.palette[i % theme.palette.length];
      }
      if (ds.borderColor === undefined || ds._opsoaiAutoBorder) {
        ds._opsoaiAutoBorder = true;
        ds.borderColor = arc ? theme.surface : theme.palette[i % theme.palette.length];
      }
      if (ds.borderWidth === undefined) { ds.borderWidth = arc ? 2 : 1.5; }
    });
  }

  function updateChartTheme() {
    if (typeof Chart === 'undefined') { return; }
    var theme = themeValues();
    applyDefaults(theme);

    document.querySelectorAll('.chartjs-wrap canvas').forEach(function (canvas) {
      var chart = typeof Chart.getChart === 'function' ? Chart.getChart(canvas) : null;
      if (!chart) { return; }

      applyDatasetColors(chart.config, theme);
      chart.options.color = theme.ink;
      Object.keys(chart.scales || {}).forEach(function (key) {
        var scale = chart.scales[key];
        scale.options.ticks = scale.options.ticks || {};
        scale.options.grid = scale.options.grid || {};
        scale.options.ticks.color = theme.ink;
        scale.options.grid.color = theme.grid;
      });
      if (chart.options.plugins && chart.options.plugins.title) {
        chart.options.plugins.title.color = theme.ink;
      }

      var wrap = canvas.closest('.chartjs-wrap');
      if (wrap) {
        wrap.style.background = theme.surface;
        wrap.style.borderColor = theme.dark ? 'rgba(240,238,233,0.10)' : 'rgba(43,41,38,0.08)';
      }
      chart.update('none');
      chart.resize();
    });
  }

  function render() {
    if (typeof Chart === 'undefined') { return setTimeout(render, 200); }
    var theme = themeValues();
    applyDefaults(theme);

    var blocks = document.querySelectorAll('pre code.language-chartjs, code.language-chartjs, .language-chartjs');
    blocks.forEach(function (code) {
      if (code.getAttribute('data-chart-done')) { return; }
      var pre = code.closest('pre') || code;
      try {
        var cfg = JSON.parse(code.textContent);
        cfg.options = cfg.options || {};
        cfg.options.responsive = true;
        cfg.options.maintainAspectRatio = false;
        applyDatasetColors(cfg, theme);
        var wrap = document.createElement('div');
        wrap.className = 'chartjs-wrap';
        wrap.style.cssText = 'position:relative;max-width:760px;height:380px;margin:1.5rem auto;'
          + 'padding:16px 18px;border-radius:12px;background:' + theme.surface + ';'
          + 'border:1px solid ' + (theme.dark ? 'rgba(240,238,233,0.10)' : 'rgba(43,41,38,0.08)') + ';';
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
  window.addEventListener('message', function (event) {
    if (event.source === window && event.data && event.data.id === 'theme-updated') {
      window.setTimeout(updateChartTheme, 30);
    }
  });
})();
