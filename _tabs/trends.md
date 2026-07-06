---
layout: page
icon: fas fa-chart-line
order: 5
title: 트렌드
---

{%- assign tools = site.posts | where_exp: "p", "p.github_url" -%}
{%- assign toolposts = tools -%}
{%- assign stocks = site.data.ai_stocks.stocks -%}

<style>
/* ===== shared shell ===== */
.mkt { max-width: 900px; }
.mkt-hero { border-radius:16px; padding:1.7rem 1.5rem; margin-bottom:1.1rem;
  background:linear-gradient(135deg, rgba(42,120,214,.14), rgba(42,120,214,.03));
  border:1px solid var(--main-border-color); }
.mkt-hero .tag { display:inline-block; font-size:.72rem; font-weight:800; letter-spacing:.14em; color:#2a78d6; margin-bottom:.5rem; }
.mkt-hero .h { font-size:1.5rem; font-weight:800; margin:0 0 .4rem; color:var(--text-color); word-break:keep-all; }
.mkt-hero .sub { font-size:.92rem; color:var(--text-muted-color); line-height:1.6; margin:0; word-break:keep-all; }
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

  <div class="mkt-hero">
    <div class="tag">AI 트렌드 &amp; 마켓</div>
    <div class="h">데이터로 보는 AI 흐름과 관련 주식</div>
    <p class="sub">이 블로그가 매일 다룬 AI 툴 데이터로 개발 트렌드를 시각화하고, 그 흐름이 어떤 기업·주식과 연결되는지까지 한눈에 봅니다.</p>
  </div>

  <div class="mkt-jump">
    <a href="#trend"><i class="fas fa-chart-line"></i> 트렌드 대시보드</a>
    <a href="#market"><i class="fas fa-arrow-trend-up"></i> 관련 주식</a>
  </div>

  <!-- ============ 트렌드 대시보드 ============ -->
  <h2 class="mkt-sec" id="trend"><i class="fas fa-chart-line"></i>트렌드 대시보드<span class="lead">블로그가 다룬 AI 툴 기준</span></h2>

  <div class="trd-stats">
    <div class="s"><span class="n" id="st-total">–</span><span class="l">총 다룬 툴</span></div>
    <div class="s"><span class="n" id="st-orgs">–</span><span class="l">기업/조직</span></div>
    <div class="s"><span class="n" id="st-month">–</span><span class="l">이번 달 글</span></div>
  </div>

  <div class="trd-card">
    <h3>월별 발행 추이</h3>
    <div class="trd-chart"><canvas id="trends-monthly"></canvas></div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h3>분야별 분포</h3>
      <div class="trd-chart"><canvas id="trends-cats"></canvas></div>
    </div>
    <div class="trd-card">
      <h3>최다 등장 조직 TOP 10</h3>
      <div class="trd-chart"><canvas id="trends-orgs"></canvas></div>
    </div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h3>누적 글 수</h3>
      <div class="trd-chart"><canvas id="trends-cumulative"></canvas></div>
    </div>
    <div class="trd-card">
      <h3>요일별 발행</h3>
      <div class="trd-chart"><canvas id="trends-dow"></canvas></div>
    </div>
  </div>

  <div class="trd-card">
    <h3>많이 다룬 키워드</h3>
    <div class="trd-chart" style="height:360px;"><canvas id="trends-keywords"></canvas></div>
  </div>

  <!-- ============ AI 주식 연관도 ============ -->
  <h2 class="mkt-sec" id="market"><i class="fas fa-arrow-trend-up"></i>AI 주식 연관도<span class="lead">트렌드가 향하는 종목</span></h2>

  <div class="stocks-note">
    각 종목의 <b>블로그 관련도</b>는 그 회사의 제품/키워드가 등장한 블로그 글(AI 툴) 수입니다.
    많이 엮일수록 그 회사의 AI가 실제 개발 현장에서 자주 언급된다는 신호예요.
    <b>투자 조언이 아니며</b>, 가격은 각 종목의 "차트 보기"에서 확인하세요.
  </div>

  <div class="stk-stats">
    <div class="s"><span class="n" id="stk-total">–</span><span class="l">종목</span></div>
    <div class="s"><span class="n" id="stk-us">–</span><span class="l">미국</span></div>
    <div class="s"><span class="n" id="stk-kr">–</span><span class="l">한국</span></div>
  </div>

  <div class="stk-viz">
    <h3>블로그 연관도 (많이 다룬 순)</h3>
    <div class="cwrap"><canvas id="stk-corr-chart"></canvas></div>
  </div>

  {%- assign markets = "US,KR" | split: "," -%}
  {%- for mk in markets -%}
  <div class="stk-mkt">{% if mk == "US" %}미국{% else %}한국{% endif %}</div>
  <div class="stk-grid">
    {%- assign ms = stocks | where: "market", mk -%}
    {%- for s in ms -%}
    <div class="stk" data-kw="{{ s.keywords | join: '|' }}" data-market="{{ s.market }}">
      <div class="stk-h"><span class="stk-name">{{ s.name }}</span><span class="stk-tk">{{ s.ticker }}</span></div>
      <div class="stk-focus">{{ s.focus }}</div>
      <div class="stk-rel-line">블로그 관련도 <b class="stk-rel">–</b>개</div>
      <div class="stk-tools"></div>
      <a class="stk-chart" href="https://www.google.com/finance/quote/{{ s.gf }}" target="_blank" rel="noopener">차트 보기 →</a>
    </div>
    {%- endfor -%}
  </div>
  {%- endfor -%}

  <!-- ============ 이번 주 하이라이트 ============ -->
  {%- assign news = site.data.ai_news -%}
  {%- if news -%}
  <h2 class="mkt-sec"><i class="fas fa-bolt"></i>이번 주 하이라이트</h2>
  <div class="trd-card">
    {%- for cat in news.categories -%}
    <div class="trd-hl"><span class="c">{{ cat.name }}</span><span class="d">{{ cat.items[0].date }}</span><span class="t">{{ cat.items[0].text }}</span></div>
    {%- endfor -%}
    <a class="trd-more" href="{{ '/updates/' | relative_url }}">전체 뉴스 보기 →</a>
  </div>
  {%- endif -%}

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
