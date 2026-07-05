---
layout: page
icon: fas fa-bolt
order: 3
title: UPDATES
---

{%- assign news = site.data.ai_news -%}
{%- assign total = 0 -%}{%- assign maxc = 1 -%}
{%- for cat in news.categories -%}
  {%- assign total = total | plus: cat.items.size -%}
  {%- if cat.items.size > maxc -%}{%- assign maxc = cat.items.size -%}{%- endif -%}
{%- endfor -%}

<style>
.upd { max-width: 860px; }
.upd-hero { border-radius: 16px; padding: 1.7rem 1.5rem; margin-bottom: 1.3rem;
  background: linear-gradient(135deg, rgba(42,120,214,.12), rgba(240,238,233,.55));
  border: 1px solid var(--main-border-color); }
.upd-hero .tag { display:inline-block; font-size:.72rem; font-weight:800; letter-spacing:.14em; color:#2a78d6; margin-bottom:.55rem; }
.upd-hero .txt { font-size:1.3rem; font-weight:800; line-height:1.5; margin:0; color:var(--text-color); word-break:keep-all; }
.upd-hero .meta { font-size:.82rem; color:var(--text-muted-color); margin-top:.65rem; }
.upd-stats { display:flex; gap:.75rem; margin-bottom:1.5rem; flex-wrap:wrap; }
.upd-stats .s { flex:1; min-width:92px; text-align:center; padding:.85rem .5rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.upd-stats .s .n { display:block; font-size:1.6rem; font-weight:800; color:#2a78d6; line-height:1.1; }
.upd-stats .s .l { display:block; font-size:.75rem; color:var(--text-muted-color); margin-top:.25rem; }
.upd-dist { margin-bottom:2rem; padding:1.05rem 1.15rem; border-radius:12px; background:var(--card-bg); border:1px solid var(--main-border-color); }
.upd-dist .row { display:flex; align-items:center; gap:.7rem; margin:.42rem 0; font-size:.86rem; }
.upd-dist .row .dn { width:6.8rem; flex-shrink:0; color:var(--text-color); font-weight:600; }
.upd-dist .row .db { flex:1; height:9px; border-radius:6px; background:rgba(128,128,128,.16); overflow:hidden; }
.upd-dist .row .db i { display:block; height:100%; border-radius:6px; background:linear-gradient(90deg,#2a78d6,#7bb0f2); }
.upd-dist .row .dc { width:1.5rem; text-align:right; color:var(--text-muted-color); font-variant-numeric:tabular-nums; }
.upd-cat { margin-bottom:1.7rem; }
.upd-cat .h { display:flex; align-items:center; gap:.55rem; font-size:1.18rem; font-weight:800; margin:0 0 .75rem; padding-bottom:.42rem; border-bottom:2px solid var(--main-border-color); color:var(--text-color); }
.upd-cat .h i.ci { color:#2a78d6; }
.upd-cat .h .pill { margin-left:auto; font-size:.76rem; font-weight:700; color:var(--text-muted-color); background:rgba(128,128,128,.14); border-radius:999px; padding:.12rem .62rem; }
.upd-list { display:flex; flex-direction:column; gap:.5rem; }
.upd-item { display:flex; gap:.85rem; align-items:baseline; padding:.72rem .95rem; border-radius:10px; background:var(--card-bg); border:1px solid var(--main-border-color); transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
.upd-item:hover { transform:translateY(-2px); box-shadow:var(--card-shadow); border-color:rgba(42,120,214,.4); }
.upd-item .date { flex-shrink:0; font-size:.75rem; font-weight:800; color:#2a78d6; background:rgba(42,120,214,.11); border-radius:6px; padding:.2rem .52rem; font-variant-numeric:tabular-nums; white-space:nowrap; }
.upd-item .t { font-size:.94rem; line-height:1.55; color:var(--text-color); word-break:keep-all; }
@media (max-width:560px){ .upd-item{ flex-direction:column; gap:.4rem; } .upd-dist .row .dn{ width:5.2rem; } }
</style>

<div class="upd" markdown="0">

  <div class="upd-hero">
    <div class="tag">THIS WEEK IN AI</div>
    <p class="txt">{{ news.big_picture | replace: '·', '/' }}</p>
    <div class="meta">{{ news.title_note | replace: '·', '/' }}</div>
  </div>

  <div class="upd-stats">
    <div class="s"><span class="n">{{ total }}</span><span class="l">건의 업데이트</span></div>
    <div class="s"><span class="n">{{ news.categories.size }}</span><span class="l">개 분야</span></div>
    <div class="s"><span class="n">{{ news.updated }}</span><span class="l">기준</span></div>
  </div>

  <div class="upd-dist">
    {%- for cat in news.categories -%}
    <div class="row"><span class="dn">{{ cat.name }}</span><span class="db"><i style="width:{{ cat.items.size | times: 100 | divided_by: maxc }}%"></i></span><span class="dc">{{ cat.items.size }}</span></div>
    {%- endfor -%}
  </div>

  {% for cat in news.categories %}
  {%- case cat.name -%}
    {%- when '프론티어 모델' -%}{%- assign ci = 'fa-rocket' -%}
    {%- when '코딩 툴' -%}{%- assign ci = 'fa-code' -%}
    {%- when '영상/이미지' -%}{%- assign ci = 'fa-film' -%}
    {%- when '음성/음악' -%}{%- assign ci = 'fa-music' -%}
    {%- when '오픈소스/중국계' -%}{%- assign ci = 'fa-cube' -%}
    {%- when '국내' -%}{%- assign ci = 'fa-flag' -%}
    {%- else -%}{%- assign ci = 'fa-angle-right' -%}
  {%- endcase -%}
  <section class="upd-cat">
    <div class="h"><i class="fas {{ ci }} ci"></i>{{ cat.name }}<span class="pill">{{ cat.items.size }}건</span></div>
    <div class="upd-list">
      {%- for item in cat.items -%}
      <div class="upd-item"><span class="date">{{ item.date }}</span><span class="t">{{ item.text | replace: '·', '/' }}</span></div>
      {%- endfor -%}
    </div>
  </section>
  {% endfor %}

</div>
