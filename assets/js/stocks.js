/* AI 주식 연관도. For each stock card (with data-kw keywords), find blog-covered AI tools
   whose name/title/owner match, and show the count + related tool chips. External file. */
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

  Array.prototype.forEach.call(document.querySelectorAll('.stk'), function (card) {
    var kws = (card.getAttribute('data-kw') || '').toLowerCase().split('|')
      .map(function (x) { return x.trim(); }).filter(Boolean);
    var rel = relatedOf(kws);
    card.setAttribute('data-count', rel.length);
    var relEl = card.querySelector('.stk-rel');
    if (relEl) { relEl.textContent = rel.length; }
    var wrap = card.querySelector('.stk-tools');
    if (wrap) {
      if (!rel.length) {
        wrap.innerHTML = '<span class="stk-none">직접 다룬 글 없음</span>';
      } else {
        wrap.innerHTML = rel.slice(0, 4).map(function (t) {
          return '<a class="stk-tool" href="' + t.url + '">' + esc(t.name) + '</a>';
        }).join('') + (rel.length > 4 ? '<span class="stk-more">+' + (rel.length - 4) + '</span>' : '');
      }
    }
  });

  /* within each market group, show the most-connected stocks first */
  Array.prototype.forEach.call(document.querySelectorAll('.stk-grid'), function (grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.stk'));
    cards.sort(function (a, b) {
      return (parseInt(b.getAttribute('data-count'), 10) || 0) - (parseInt(a.getAttribute('data-count'), 10) || 0);
    });
    cards.forEach(function (c) { grid.appendChild(c); });
  });
})();
