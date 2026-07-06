---
layout: page
icon: fas fa-comments
order: 7
title: 커뮤니티
---

{%- assign g = site.comments.giscus -%}

<style>
.comm { max-width: 860px; }
.comm-hero { border-radius:16px; padding:1.7rem 1.5rem; margin-bottom:1.3rem;
  background:linear-gradient(135deg, rgba(42,120,214,.14), rgba(42,120,214,.03));
  border:1px solid var(--main-border-color); }
.comm-hero .tag { display:inline-block; font-size:.72rem; font-weight:800; letter-spacing:.14em; color:#2a78d6; margin-bottom:.55rem; }
.comm-hero .h { font-size:1.4rem; font-weight:800; margin:0 0 .5rem; color:var(--text-color); word-break:keep-all; }
.comm-hero .sub { font-size:.92rem; color:var(--text-muted-color); line-height:1.65; word-break:keep-all; margin:0; }
.comm-rules { display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 1.6rem; }
.comm-rules .r { font-size:.8rem; color:var(--text-color); background:var(--card-bg); border:1px solid var(--main-border-color); border-radius:999px; padding:.35rem .8rem; }
.comm-rules .r i { color:#2a78d6; margin-right:.35rem; }
.comm-setup { font-size:.88rem; color:var(--text-muted-color); background:var(--card-bg); border:1px dashed var(--main-border-color); border-radius:12px; padding:1.2rem 1.3rem; line-height:1.7; text-align:center; }
.comm-setup b { color:var(--text-color); }
.giscus { margin-top:.4rem; }
</style>

<div class="comm" markdown="0">

  <div class="comm-hero">
    <div class="tag">커뮤니티</div>
    <div class="h">AI, 같이 이야기해요</div>
    <p class="sub">궁금한 논문, 써 본 툴 후기, 다뤄줬으면 하는 주제까지 자유롭게 남겨주세요. 남겨주신 질문과 요청은 다음 글의 소재가 됩니다.</p>
  </div>

  <div class="comm-rules">
    <span class="r"><i class="fas fa-lightbulb"></i>주제 요청 환영</span>
    <span class="r"><i class="fas fa-comments"></i>편하게 질문/후기</span>
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
    <!--
      [운영자 설정 — 아래 3단계를 마치면 게시판이 자동으로 열립니다. repo / repo_id 는 이미 채워져 있어요]
      1) GitHub 저장소(jjxxmiin/jjxxmiin.github.io) → Settings → General → Features 에서 "Discussions" 체크
      2) https://github.com/apps/giscus 에서 이 저장소에 giscus 앱 설치(Only select repositories → 저장소 선택)
      3) https://giscus.app 접속 → Repository 에 jjxxmiin/jjxxmiin.github.io 입력
         → Discussion Category 선택(예: Announcements, 또는 Discussions에서 "커뮤니티" 카테고리 새로 생성)
         → 아래로 스크롤해 생성된 <script> 코드에서 data-category 와 data-category-id 값을 복사
         → _config.yml 의 comments.giscus.category / category_id 에 붙여넣고 커밋 → 끝
    -->
  </div>
  {% endif %}

</div>
