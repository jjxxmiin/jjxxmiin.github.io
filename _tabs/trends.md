---
layout: page
icon: fas fa-chart-line
order: 5
title: TRENDS
---

{%- assign tools = site.posts | where_exp: "p", "p.github_url" -%}

<style>
.trd { max-width: 880px; }
.trd-head { margin-bottom: 1.1rem; }
.trd-head .tag { display:inline-block; font-size:.72rem; font-weight:800; letter-spacing:.14em; color:#2a78d6; }
.trd-head .h { font-size:1.5rem; font-weight:800; margin:.25rem 0 .2rem; color:var(--text-color); }
.trd-head .sub { font-size:.9rem; color:var(--text-muted-color); }
.trd-stats { display:flex; gap:.75rem; margin-bottom:1.4rem; flex-wrap:wrap; }
.trd-stats .s { flex:1; min-width:96px; text-align:center; padding:.85rem .5rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.trd-stats .s .n { display:block; font-size:1.7rem; font-weight:800; color:#2a78d6; line-height:1.1; }
.trd-stats .s .l { display:block; font-size:.75rem; color:var(--text-muted-color); margin-top:.25rem; }
.trd-card { border-radius:12px; border:1px solid var(--main-border-color); background:var(--card-bg); padding:1.1rem 1.2rem; margin-bottom:1.3rem; }
.trd-card h2 { font-size:1.05rem; font-weight:800; margin:0 0 .9rem; color:var(--text-color); }
.trd-chart { position:relative; height:300px; }
.trd-grid2 { display:grid; grid-template-columns:1fr 1fr; gap:1.3rem; } @media (max-width:640px){ .trd-grid2 { grid-template-columns:1fr; } }
.trd-hl { display:flex; gap:.6rem; align-items:baseline; padding:.5rem 0; font-size:.88rem; border-top:1px solid var(--main-border-color); }
.trd-hl:first-child { border-top:none; }
.trd-hl .c { font-weight:700; color:#2a78d6; width:6.2rem; flex-shrink:0; }
.trd-hl .d { color:var(--text-muted-color); width:2.6rem; flex-shrink:0; font-size:.78rem; font-variant-numeric:tabular-nums; }
.trd-hl .t { color:var(--text-color); word-break:keep-all; }
.trd-more { display:inline-block; margin-top:.8rem; font-size:.85rem; font-weight:700; color:#2a78d6; }
</style>

<div class="trd" markdown="0">

  <div class="trd-head">
    <div class="h">AI 트렌드 대시보드</div>
    <div class="sub">이 블로그가 다룬 AI 툴 데이터로 보는 흐름</div>
  </div>

  <div class="trd-stats">
    <div class="s"><span class="n" id="st-total">–</span><span class="l">총 다룬 툴</span></div>
    <div class="s"><span class="n" id="st-orgs">–</span><span class="l">기업/조직</span></div>
    <div class="s"><span class="n" id="st-month">–</span><span class="l">이번 달 글</span></div>
  </div>

  <div class="trd-card">
    <h2>월별 발행 추이</h2>
    <div class="trd-chart"><canvas id="trends-monthly"></canvas></div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h2>분야별 분포</h2>
      <div class="trd-chart"><canvas id="trends-cats"></canvas></div>
    </div>
    <div class="trd-card">
      <h2>최다 등장 조직 TOP 10</h2>
      <div class="trd-chart"><canvas id="trends-orgs"></canvas></div>
    </div>
  </div>

  <div class="trd-grid2">
    <div class="trd-card">
      <h2>누적 글 수</h2>
      <div class="trd-chart"><canvas id="trends-cumulative"></canvas></div>
    </div>
    <div class="trd-card">
      <h2>요일별 발행</h2>
      <div class="trd-chart"><canvas id="trends-dow"></canvas></div>
    </div>
  </div>

  <div class="trd-card">
    <h2>많이 다룬 키워드</h2>
    <div class="trd-chart" style="height:360px;"><canvas id="trends-keywords"></canvas></div>
  </div>

  {%- assign news = site.data.ai_news -%}
  {%- if news -%}
  <div class="trd-card">
    <h2>이번 주 하이라이트</h2>
    {%- for cat in news.categories -%}
    <div class="trd-hl"><span class="c">{{ cat.name }}</span><span class="d">{{ cat.items[0].date }}</span><span class="t">{{ cat.items[0].text }}</span></div>
    {%- endfor -%}
    <a class="trd-more" href="{{ '/updates/' | relative_url }}">전체 업데이트 보기 →</a>
  </div>
  {%- endif -%}

</div>

<script type="application/json" id="trends-data">
[{% for post in tools %}{% assign gp = post.github_url | split: 'github.com/' | last | split: '/' %}{% assign trepo = gp[1] | split: '?' | first | split: '#' | first %}{"owner":{{ gp[0] | jsonify }},"name":{{ trepo | default: gp[0] | jsonify }},"title":{{ post.title | strip_newlines | jsonify }},"date":{{ post.date | date: "%Y-%m-%d" | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}]
</script>
<script src="{{ '/assets/lib/chartjs/chart.umd.min.js' | relative_url }}"></script>
<script src="{{ '/assets/js/trends.js' | relative_url }}" defer></script>

<!-- v1 -->
