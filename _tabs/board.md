---
layout: page
icon: fas fa-comments
order: 7
title: 커뮤니티
---

{%- assign g = site.comments.giscus -%}

<style>
.comm { max-width: 860px; }
.comm-lead { font-size: 1.02rem; color: var(--text-color); line-height: 1.75; word-break: keep-all; margin: .1rem 0 1.3rem; }
.comm-lead b { font-weight: 800; }
.comm-lead .muted { color: var(--text-muted-color); }
.comm-rules { display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 2rem; }
.comm-rules .r { font-size:.8rem; color:var(--text-muted-color); background:var(--card-bg); border:1px solid var(--main-border-color); border-radius:999px; padding:.35rem .8rem; }
.comm-rules .r i { color:#2a78d6; margin-right:.35rem; }
.comm-setup { font-size:.9rem; color:var(--text-muted-color); background:var(--card-bg); border:1px dashed var(--main-border-color); border-radius:12px; padding:1.4rem 1.3rem; text-align:center; line-height:1.7; }
.comm-setup b { color:var(--text-color); }
</style>

<div class="comm" markdown="0">

  <p class="comm-lead"><b>AI, 같이 이야기해요.</b><br>
  <span class="muted">궁금한 논문, 써 본 툴 후기, 다뤄줬으면 하는 주제까지 자유롭게 남겨주세요. 남겨주신 질문과 요청은 다음 글의 소재가 됩니다.</span></p>

  <div class="comm-rules">
    <span class="r"><i class="fas fa-lightbulb"></i>주제 요청 환영</span>
    <span class="r"><i class="fas fa-comments"></i>편하게 질문·후기</span>
    <span class="r"><i class="fas fa-heart"></i>서로 존중</span>
    <span class="r"><i class="fab fa-github"></i>GitHub 로그인으로 작성</span>
  </div>

  {% if g.repo and g.repo_id and g.category_id %}
  <script src="https://giscus.app/client.js"
    data-repo="{{ g.repo }}"
    data-repo-id="{{ g.repo_id }}"
    data-category="{{ g.category }}"
    data-category-id="{{ g.category_id }}"
    data-mapping="{{ g.mapping | default: 'pathname' }}"
    data-strict="{{ g.strict | default: '0' }}"
    data-reactions-enabled="{{ g.reactions_enabled | default: '1' }}"
    data-emit-metadata="0"
    data-input-position="{{ g.input_position | default: 'top' }}"
    data-theme="preferred_color_scheme"
    data-lang="{{ g.lang | default: 'ko' }}"
    data-loading="lazy"
    crossorigin="anonymous"
    async>
  </script>
  {% else %}
  <div class="comm-setup">
    게시판을 <b>준비 중</b>입니다. 곧 자유롭게 글을 남기실 수 있어요.
  </div>
  {% endif %}

</div>
