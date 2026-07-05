---
layout: page
icon: fas fa-arrow-trend-up
order: 6
title: STOCKS
---

{%- assign stocks = site.data.ai_stocks.stocks -%}
{%- assign toolposts = site.posts | where_exp: "p", "p.github_url" -%}

<style>
.stocks { max-width: 880px; }
.stocks-head .h { font-size:1.5rem; font-weight:800; margin:.25rem 0 .2rem; color:var(--text-color); }
.stocks-head .sub { font-size:.9rem; color:var(--text-muted-color); }
.stocks-note { font-size:.82rem; color:var(--text-muted-color); background:var(--card-bg); border:1px solid var(--main-border-color); border-radius:10px; padding:.7rem .95rem; margin:.9rem 0 1.4rem; line-height:1.6; }
.stk-mkt { font-size:1.08rem; font-weight:800; margin:1.6rem 0 .8rem; color:var(--text-color); border-bottom:2px solid var(--main-border-color); padding-bottom:.42rem; }
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
.stk-more { font-size:.72rem; color:var(--text-muted-color); align-self:center; }
.stk-none { font-size:.75rem; color:var(--text-muted-color); }
.stk-chart { font-size:.78rem; font-weight:700; color:#2a78d6; margin-top:auto; }
.stk-chart:hover { text-decoration:underline; }
.stk-stats { display:flex; gap:.75rem; margin-bottom:1.3rem; flex-wrap:wrap; }
.stk-stats .s { flex:1; min-width:88px; text-align:center; padding:.8rem .4rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.stk-stats .s .n { display:block; font-size:1.55rem; font-weight:800; color:#2a78d6; line-height:1.1; }
.stk-stats .s .l { display:block; font-size:.74rem; color:var(--text-muted-color); margin-top:.2rem; }
.stk-viz { border:1px solid var(--main-border-color); background:var(--card-bg); border-radius:12px; padding:1rem 1.1rem; margin-bottom:1.6rem; }
.stk-viz h2 { font-size:1.02rem; font-weight:800; margin:0 0 .8rem; color:var(--text-color); }
.stk-viz .cwrap { position:relative; height:360px; }
</style>

<div class="stocks" markdown="0">

  <div class="stocks-head">
    <div class="h">AI 주식 연관도</div>
    <div class="sub">AI 관련 주식과, 이 블로그가 다룬 AI 툴/회사의 연관도를 기록합니다</div>
  </div>

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
    <h2>블로그 연관도 (많이 다룬 순)</h2>
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

</div>

<script type="application/json" id="stocks-tools">
[{% for post in toolposts %}{% assign gp = post.github_url | split: 'github.com/' | last | split: '/' %}{% assign trepo = gp[1] | split: '?' | first | split: '#' | first %}{"name":{{ trepo | default: gp[0] | jsonify }},"owner":{{ gp[0] | jsonify }},"title":{{ post.title | strip_newlines | jsonify }},"url":{{ post.url | relative_url | jsonify }},"date":{{ post.date | date: "%Y-%m-%d" | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}]
</script>
<script src="{{ '/assets/lib/chartjs/chart.umd.min.js' | relative_url }}"></script>
<script src="{{ '/assets/js/stocks.js' | relative_url }}" defer></script>
