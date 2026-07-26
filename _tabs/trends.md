---
layout: page
icon: fas fa-chart-line
order: 5
title: AI Data
description: Explore patterns in the OPSOAI technology archive and see how frequently major AI companies and topics appear in our coverage.
keywords: [AI trends, artificial intelligence data, AI companies, AI coverage analysis]
---

{%- assign tools = site.posts | where_exp: "p", "p.github_url" -%}
{%- assign toolposts = tools -%}
{%- assign stocks = site.data.ai_stocks.stocks -%}

<style>
/* ===== shared shell ===== */
.mkt { max-width: 900px; }
.mkt-lead { font-size:1.02rem; color:var(--text-color); line-height:1.75; word-break:keep-all; margin:.1rem 0 1.2rem; }
.mkt-lead b { font-weight:800; }
.mkt-lead .muted { color:var(--text-muted-color); }
.mkt-jump { display:flex; gap:.5rem; margin-bottom:1.4rem; flex-wrap:wrap; }
.mkt-jump a { font-size:.82rem; font-weight:700; color:#2a78d6; background:rgba(42,120,214,.11); border:1px solid rgba(42,120,214,.25); border-radius:999px; padding:.4rem .95rem; text-decoration:none; }
.mkt-jump a:hover { background:#2a78d6; color:#fff; }
.mkt-sec { display:flex; align-items:center; gap:.6rem; font-size:1.22rem; font-weight:800; margin:2.4rem 0 1rem; padding-bottom:.5rem; border-bottom:2px solid var(--main-border-color); color:var(--text-color); scroll-margin-top:5rem; }
.mkt-sec i { color:#2a78d6; }
.mkt-sec .lead { margin-left:auto; font-size:.8rem; font-weight:600; color:var(--text-muted-color); }

/* ===== trends ===== */
.trd-stats { display:flex; gap:.75rem; margin-bottom:1.4rem; flex-wrap:wrap; }
.trd-stats .s { flex:1; min-width:96px; text-align:center; padding:.85rem .5rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.trd-stats .s .n { display:block; font-size:1.7rem; font-weight:800; color:#2a78d6; line-height:1.1; }
.trd-stats .s .l { display:block; font-size:.75rem; color:var(--text-muted-color); margin-top:.25rem; }
.trd-card { border-radius:12px; border:1px solid var(--main-border-color); background:var(--card-bg); padding:1.1rem 1.2rem; margin-bottom:1.3rem; }
.trd-card h3 { font-size:1.05rem; font-weight:800; margin:0 0 .9rem; color:var(--text-color); }
.trd-chart { position:relative; height:300px; }
.trd-grid2 { display:grid; grid-template-columns:1fr 1fr; gap:1.3rem; } @media (max-width:640px){ .trd-grid2 { grid-template-columns:1fr; } }
.trd-hl { display:flex; gap:.6rem; align-items:baseline; padding:.5rem 0; font-size:.88rem; border-top:1px solid var(--main-border-color); }
.trd-hl:first-child { border-top:none; }
.trd-hl .c { font-weight:700; color:#2a78d6; width:6.2rem; flex-shrink:0; }
.trd-hl .d { color:var(--text-muted-color); width:2.6rem; flex-shrink:0; font-size:.78rem; font-variant-numeric:tabular-nums; }
.trd-hl .t { color:var(--text-color); word-break:keep-all; }
.trd-more { display:inline-block; margin-top:.8rem; font-size:.85rem; font-weight:700; color:#2a78d6; }

/* ===== stocks ===== */
.stocks-note { font-size:.82rem; color:var(--text-muted-color); background:var(--card-bg); border:1px solid var(--main-border-color); border-radius:10px; padding:.7rem .95rem; margin:0 0 1.3rem; line-height:1.6; }
.stk-mkt { font-size:1.02rem; font-weight:800; margin:1.5rem 0 .8rem; color:var(--text-color); border-bottom:2px solid var(--main-border-color); padding-bottom:.42rem; }
.stk-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(262px,1fr)); gap:.8rem; }
.stk { border-radius:12px; border:1px solid var(--main-border-color); background:var(--card-bg); padding:.95rem 1rem; display:flex; flex-direction:column; transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
.stk:hover { transform:translateY(-2px); box-shadow:var(--card-shadow); border-color:rgba(42,120,214,.4); }
.stk-h { display:flex; align-items:center; gap:.5rem; margin-bottom:.45rem; }
.stk-name { font-weight:800; font-size:1rem; color:var(--text-color); }
.stk-tk { margin-left:auto; font-size:.72rem; font-weight:800; color:#2a78d6; background:rgba(42,120,214,.11); border-radius:6px; padding:.15rem .48rem; font-variant-numeric:tabular-nums; }
.stk-focus { font-size:.82rem; color:var(--text-muted-color); line-height:1.5; word-break:keep-all; margin-bottom:.6rem; flex:1; }
.stk-rel-line { font-size:.8rem; color:var(--text-color); margin-bottom:.35rem; }
.stk-rel-line .stk-rel { color:#2a78d6; font-weight:800; }
.stk-tools { display:flex; flex-wrap:wrap; gap:.3rem; margin-bottom:.65rem; }
.stk-tool { font-size:.72rem; padding:.16rem .5rem; border-radius:999px; background:rgba(128,128,128,.12); color:var(--text-color); }
.stk-tool:hover { background:#2a78d6; color:#fff; text-decoration:none; }
.stk-none { font-size:.75rem; color:var(--text-muted-color); }
.stk-chart { font-size:.78rem; font-weight:700; color:#2a78d6; margin-top:auto; }
.stk-chart:hover { text-decoration:underline; }
.stk-stats { display:flex; gap:.75rem; margin-bottom:1.3rem; flex-wrap:wrap; }
.stk-stats .s { flex:1; min-width:88px; text-align:center; padding:.8rem .4rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.stk-stats .s .n { display:block; font-size:1.55rem; font-weight:800; color:#2a78d6; line-height:1.1; }
.stk-stats .s .l { display:block; font-size:.74rem; color:var(--text-muted-color); margin-top:.2rem; }
.stk-viz { border:1px solid var(--main-border-color); background:var(--card-bg); border-radius:12px; padding:1rem 1.1rem; margin-bottom:1.4rem; }
.stk-viz h3 { font-size:1.02rem; font-weight:800; margin:0 0 .8rem; color:var(--text-color); }
.stk-viz .cwrap { position:relative; height:360px; }
</style>

<div class="mkt" markdown="0">

  <p class="mkt-lead"><b>Patterns in the OPSOAI technology archive.</b><br>
  <span class="muted">These charts visualize the projects, organizations, and topics covered in our historical open-source archive. They are editorial coverage signals, not market forecasts.</span></p>

  <div class="mkt-jump">
    <a href="#trend"><i class="fas fa-chart-line"></i> Archive dashboard</a>
    <a href="#market"><i class="fas fa-arrow-trend-up"></i> Company map</a>
  </div>

  <!-- ============ 트렌드 대시보드 ============ -->
  <h2 class="mkt-sec" id="trend"><i class="fas fa-chart-line"></i>Archive dashboard<span class="lead">Based on covered AI tools</span></h2>

  <div class="trd-stats">
    <div class="s"><span class="n" id="st-total">–</span><span class="l">Covered tools</span></div>
    <div class="s"><span class="n" id="st-orgs">–</span><span class="l">Organizations</span></div>
    <div class="s"><span class="n" id="st-month">–</span><span class="l">This month</span></div>
  </div>

  <div class="trd-card">
    <h3>Monthly coverage</h3>
    <div class="trd-chart"><canvas id="trends-monthly"></canvas></div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h3>Topic distribution</h3>
      <div class="trd-chart"><canvas id="trends-cats"></canvas></div>
    </div>
    <div class="trd-card">
      <h3>Top 10 organizations</h3>
      <div class="trd-chart"><canvas id="trends-orgs"></canvas></div>
    </div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h3>Cumulative articles</h3>
      <div class="trd-chart"><canvas id="trends-cumulative"></canvas></div>
    </div>
    <div class="trd-card">
      <h3>Publishing by weekday</h3>
      <div class="trd-chart"><canvas id="trends-dow"></canvas></div>
    </div>
  </div>

  <div class="trd-card">
    <h3>Most-covered keywords</h3>
    <div class="trd-chart" style="height:360px;"><canvas id="trends-keywords"></canvas></div>
  </div>

  <!-- ============ AI 주식 연관도 ============ -->
  <h2 class="mkt-sec" id="market"><i class="fas fa-arrow-trend-up"></i>Company coverage map<span class="lead">Archive mentions by company</span></h2>

  <div class="stocks-note">
    <b>Coverage count</b> is the number of archived AI-tool articles that mention a
    company’s products or keywords. It measures our historical coverage only.
    <b>This is not investment advice</b>; use the external chart for current market data.
  </div>

  <div class="stk-stats">
    <div class="s"><span class="n" id="stk-total">–</span><span class="l">Companies</span></div>
    <div class="s"><span class="n" id="stk-us">–</span><span class="l">United States</span></div>
    <div class="s"><span class="n" id="stk-kr">–</span><span class="l">South Korea</span></div>
  </div>

  <div class="stk-viz">
    <h3>Archive coverage count</h3>
    <div class="cwrap"><canvas id="stk-corr-chart"></canvas></div>
  </div>

  {%- assign markets = "US,KR" | split: "," -%}
  {%- for mk in markets -%}
  <div class="stk-mkt">{% if mk == "US" %}United States{% else %}South Korea{% endif %}</div>
  <div class="stk-grid">
    {%- assign ms = stocks | where: "market", mk -%}
    {%- for s in ms -%}
    <div class="stk" data-kw="{{ s.keywords | join: '|' }}" data-market="{{ s.market }}">
      <div class="stk-h"><span class="stk-name">{{ s.name }}</span><span class="stk-tk">{{ s.ticker }}</span></div>
      <div class="stk-focus">{{ s.focus }}</div>
      <div class="stk-rel-line">Coverage <b class="stk-rel">–</b> articles</div>
      <div class="stk-tools"></div>
      <a class="stk-chart" href="https://www.google.com/finance/quote/{{ s.gf }}" target="_blank" rel="noopener">View market chart →</a>
    </div>
    {%- endfor -%}
  </div>
  {%- endfor -%}

</div>

<script type="application/json" id="trends-data">
[{% for post in tools %}{% assign gp = post.github_url | split: 'github.com/' | last | split: '/' %}{% assign trepo = gp[1] | split: '?' | first | split: '#' | first %}{"owner":{{ gp[0] | jsonify }},"name":{{ trepo | default: gp[0] | jsonify }},"title":{{ post.title | strip_newlines | jsonify }},"date":{{ post.date | date: "%Y-%m-%d" | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}]
</script>
<script type="application/json" id="stocks-tools">
[{% for post in toolposts %}{% assign gp = post.github_url | split: 'github.com/' | last | split: '/' %}{% assign trepo = gp[1] | split: '?' | first | split: '#' | first %}{"name":{{ trepo | default: gp[0] | jsonify }},"owner":{{ gp[0] | jsonify }},"title":{{ post.title | strip_newlines | jsonify }},"url":{{ post.url | relative_url | jsonify }},"date":{{ post.date | date: "%Y-%m-%d" | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}]
</script>
<script src="{{ '/assets/lib/chartjs/chart.umd.min.js' | relative_url }}"></script>
<script src="{{ '/assets/js/trends.js' | relative_url }}" defer></script>
<script src="{{ '/assets/js/stocks.js' | relative_url }}" defer></script>

<!-- merged trends + stocks -->
