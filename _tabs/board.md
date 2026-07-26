---
layout: page
icon: fas fa-comments
order: 7
title: Community
description: Ask questions and share useful experience about AI news, models, tools, research, and real-world deployment.
keywords: [AI community, artificial intelligence questions, AI news discussion]
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

  <p class="comm-lead"><b>Let’s make AI coverage more useful together.</b><br>
  <span class="muted">Share a question, a tool you tested, a paper worth explaining, or a story we should investigate. Reader requests help shape future coverage.</span></p>

  <div class="comm-rules">
    <span class="r"><i class="fas fa-lightbulb"></i>Pitch a topic</span>
    <span class="r"><i class="fas fa-comments"></i>Ask or review</span>
    <span class="r"><i class="fas fa-heart"></i>Respect each other</span>
    <span class="r"><i class="fab fa-github"></i>Sign in with GitHub</span>
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
    data-lang="{{ g.lang | default: 'en' }}"
    data-loading="lazy"
    crossorigin="anonymous"
    async>
  </script>
  {% else %}
  <div class="comm-setup">
    The community is <b>being prepared</b>. Comments will open soon.
  </div>
  {% endif %}

</div>
