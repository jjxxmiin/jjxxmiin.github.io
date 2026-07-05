---
layout: page
icon: fas fa-toolbox
order: 4
title: TOOLS
---

{%- assign tools = site.posts | where_exp: "p", "p.github_url" -%}

<style>
.tools-head { margin-bottom: 1rem; }
.tools-head .tag { display:inline-block; font-size:.72rem; font-weight:800; letter-spacing:.14em; color:#2a78d6; }
.tools-head .h { font-size:1.5rem; font-weight:800; margin:.25rem 0 .2rem; color:var(--text-color); }
.tools-head .sub { font-size:.9rem; color:var(--text-muted-color); }
.tools-controls { padding:.2rem 0 .5rem; }
#tools-search { width:100%; padding:.7rem 1rem; border-radius:10px; border:1px solid var(--main-border-color); background:var(--card-bg); color:var(--text-color); font-size:.95rem; }
#tools-search:focus { outline:none; border-color:#2a78d6; }
#tools-chips { display:flex; flex-wrap:wrap; gap:.4rem; margin:.65rem 0 .2rem; }
.tchip { font-size:.79rem; font-weight:600; padding:.32rem .72rem; border-radius:999px; border:1px solid var(--main-border-color); background:var(--card-bg); color:var(--text-muted-color); cursor:pointer; transition:background .12s ease, color .12s ease, border-color .12s ease; }
.tchip:hover { border-color:#2a78d6; }
.tchip.on { background:#2a78d6; color:#fff; border-color:#2a78d6; }
#tools-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(212px,1fr)); gap:.8rem; margin-top:.7rem; }
.tcard { display:flex; flex-direction:column; border-radius:12px; border:1px solid var(--main-border-color); background:var(--card-bg); overflow:hidden; transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
.tcard:hover { transform:translateY(-3px); box-shadow:var(--card-shadow); border-color:rgba(42,120,214,.45); }
.tcard-main { display:flex; gap:.7rem; align-items:center; padding:.85rem .9rem; color:inherit; }
.tcard-main:hover { text-decoration:none; }
.tlogo { width:44px; height:44px; border-radius:10px; flex-shrink:0; background:rgba(128,128,128,.15); object-fit:cover; }
.tbody { min-width:0; }
.tname { font-weight:800; font-size:.95rem; color:var(--text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ttitle { font-size:.8rem; color:var(--text-muted-color); line-height:1.4; margin-top:.15rem; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; word-break:keep-all; }
.tfoot { display:flex; align-items:center; gap:.5rem; padding:.5rem .9rem; border-top:1px solid var(--main-border-color); font-size:.72rem; color:var(--text-muted-color); }
.tcat { font-weight:700; color:#2a78d6; }
.tdate { margin-left:auto; font-variant-numeric:tabular-nums; }
.tgh { color:var(--text-muted-color); font-size:.95rem; }
.tgh:hover { color:#2a78d6; }
.tools-empty { color:var(--text-muted-color); padding:2rem 0; text-align:center; grid-column:1/-1; }
</style>

<div class="tools-head" markdown="0">
  <div class="h">AI 툴 도감</div>
  <div class="sub">블로그가 다룬 <b id="tools-count">{{ tools | size }}</b>개의 AI 툴, 매일 새 글마다 자동으로 추가됩니다</div>
</div>

<div class="tools-controls" markdown="0">
  <input id="tools-search" type="search" placeholder="툴 이름/설명 검색 (예: cursor, 에이전트, rag)" autocomplete="off">
  <div id="tools-chips"></div>
</div>

<div id="tools-grid" markdown="0"></div>

<script type="application/json" id="tools-data">
[{% for post in tools %}{% assign gp = post.github_url | split: 'github.com/' | last | split: '/' %}{% assign trepo = gp[1] | split: '?' | first | split: '#' | first %}{"name":{{ trepo | default: gp[0] | jsonify }},"owner":{{ gp[0] | jsonify }},"title":{{ post.title | strip_newlines | jsonify }},"url":{{ post.url | relative_url | jsonify }},"gh":{{ post.github_url | jsonify }},"date":{{ post.date | date: "%Y-%m-%d" | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}]
</script>
<script src="{{ '/assets/js/tools.js' | relative_url }}" defer></script>
