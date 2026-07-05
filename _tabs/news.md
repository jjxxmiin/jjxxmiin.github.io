---
layout: page
icon: fas fa-newspaper
order: 3
title: AI 소식
---

{%- assign news = site.data.ai_news -%}

> **이번 주 큰 그림 —** {{ news.big_picture }}
{: .prompt-tip }

<p style="color: var(--text-muted-color); font-size: 0.88rem; margin-top: -0.4rem;">
  {{ news.title_note }} · 업데이트 {{ news.updated }}
</p>

{% for cat in news.categories %}
<h2 style="border-bottom:1px solid var(--main-border-color); padding-bottom:.3rem; margin-top:2rem;">{{ cat.name }}</h2>
<table>
  <thead><tr><th style="white-space:nowrap;width:4.5rem;">날짜</th><th>소식</th></tr></thead>
  <tbody>
    {%- for item in cat.items %}
    <tr><td style="white-space:nowrap;font-variant-numeric:tabular-nums;">{{ item.date }}</td><td>{{ item.text }}</td></tr>
    {%- endfor %}
  </tbody>
</table>
{% endfor %}

<h2 style="border-bottom:1px solid var(--main-border-color); padding-bottom:.3rem; margin-top:2.5rem;">매일 심층 해설 — 최근 글</h2>

매일 아침 자동으로 올라오는 최신 AI 오픈소스·도구 심층 해설입니다.

{% for post in site.posts limit:15 %}
- **{{ post.date | date: "%-m/%-d" }}** · [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}
