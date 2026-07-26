/* AI tool archive renderer. Reads the Liquid-generated JSON in #tools-data and renders a
   searchable / filterable card grid. External file (not HTML-minified), so comments are safe. */
(function () {
  var dataEl = document.getElementById('tools-data');
  var grid = document.getElementById('tools-grid');
  if (!dataEl || !grid) { return; }

  var TOOLS = [];
  try { TOOLS = JSON.parse(dataEl.textContent); } catch (e) { return; }
  TOOLS.sort(function (a, b) { return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0); });

  function catOf(t) {
    var s = (t.name + ' ' + t.title).toLowerCase();
    if (/design|디자인|figma|canvas|ui\/ux|ux\/ui/.test(s)) { return 'Design'; }
    if (/video|영상|비디오|image|이미지|diffus|render|montage|clip|photo|사진|frame/.test(s)) { return 'Video & image'; }
    if (/voice|음성|speech|audio|music|음악|\btts\b|sound|오디오/.test(s)) { return 'Voice & audio'; }
    if (/\brag\b|search|검색|graph|그래프|memory|메모리|데이터|vector|벡터|\bdb\b|index|색인|knowledge/.test(s)) { return 'Data & search'; }
    if (/cod|코딩|\bide\b|\bcli\b|agent|에이전트|\bdev\b|compil|컴파일|plugin|플러그인|terminal|터미널|mcp|debug/.test(s)) { return 'Coding'; }
    return 'Other';
  }

  var CATS = ['All', 'Coding', 'Video & image', 'Design', 'Voice & audio', 'Data & search', 'Other'];
  var counts = { 'All': TOOLS.length };
  TOOLS.forEach(function (t) { t.cat = catOf(t); counts[t.cat] = (counts[t.cat] || 0) + 1; });

  var state = { cat: 'All', q: '' };

  var chipsWrap = document.getElementById('tools-chips');
  CATS.forEach(function (c) {
    if (c !== 'All' && !counts[c]) { return; }
    var b = document.createElement('button');
    b.className = 'tchip' + (c === 'All' ? ' on' : '');
    b.textContent = c + ' ' + (counts[c] || 0);
    b.setAttribute('data-cat', c);
    b.addEventListener('click', function () {
      state.cat = c;
      Array.prototype.forEach.call(chipsWrap.children, function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      renderGrid();
    });
    chipsWrap.appendChild(b);
  });

  var search = document.getElementById('tools-search');
  if (search) {
    search.addEventListener('input', function () { state.q = search.value.trim().toLowerCase(); renderGrid(); });
  }

  function ghAvatar(owner) { return 'https://github.com/' + encodeURIComponent(owner) + '.png?size=96'; }

  function renderGrid() {
    var list = TOOLS.filter(function (t) {
      if (state.cat !== 'All' && t.cat !== state.cat) { return false; }
      if (state.q && (t.name + ' ' + t.title).toLowerCase().indexOf(state.q) === -1) { return false; }
      return true;
    });
    var count = document.getElementById('tools-count');
    if (count) { count.textContent = list.length; }
    if (!list.length) { grid.innerHTML = '<p class="tools-empty">No matching tools found.</p>'; return; }

    grid.innerHTML = list.map(function (t) {
      var logo = ghAvatar(t.owner);
      return '<article class="tcard">'
        + '<a class="tcard-main" href="' + t.url + '">'
        + '<img class="tlogo" src="' + logo + '" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'">'
        + '<div class="tbody"><div class="tname">' + esc(t.name) + '</div>'
        + '<div class="ttitle">' + esc(t.title) + '</div></div>'
        + '</a>'
        + '<div class="tfoot"><span class="tcat">' + t.cat + '</span>'
        + '<span class="tdate">' + t.date + '</span>'
        + '<a class="tgh" href="' + t.gh + '" target="_blank" rel="noopener" aria-label="GitHub"><i class="fab fa-github"></i></a>'
        + '</div></article>';
    }).join('');
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  renderGrid();
})();
