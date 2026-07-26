---
layout: page
icon: fas fa-comments
order: 7
title: 커뮤니티
description: AI 질문, 도구 후기, 논문과 기술 이야기를 함께 나누는 OPSOAI 커뮤니티입니다.
---

<link rel="stylesheet" href="{{ '/assets/css/community.css' | relative_url }}">

{%- assign community = site.data.community -%}
{%- assign feed = site.data.community_discussions.discussions -%}

<div class="community-page" markdown="0">
  <section class="community-hero" aria-labelledby="community-welcome">
    <div class="community-eyebrow">
      <i class="fas fa-circle" aria-hidden="true"></i>
      OPSOAI Community
    </div>
    <h2 id="community-welcome">AI를 혼자 읽지 않는 곳</h2>
    <p>
      논문에서 이해되지 않은 부분, 직접 써 본 AI 도구, 다음에 다뤘으면 하는 주제까지
      자유롭게 꺼내 주세요. 좋은 질문과 경험이 다음 사람의 출발점이 됩니다.
    </p>
    <div class="community-actions">
      <a class="community-button community-button--primary"
         href="{{ community.discussion_url }}/new"
         rel="noopener">
        <i class="fas fa-pen" aria-hidden="true"></i>
        새 토론 시작
      </a>
      <a class="community-button community-button--secondary"
         href="#latest-discussions">
        <i class="fas fa-stream" aria-hidden="true"></i>
        최근 토론 보기
      </a>
    </div>
    <p class="community-login-note">
      <i class="fab fa-github" aria-hidden="true"></i>
      읽기는 누구나, 작성은 GitHub 로그인 후 가능합니다.
    </p>
  </section>

  <section class="community-section" aria-labelledby="community-spaces">
    <div class="community-section-header">
      <div>
        <h2 id="community-spaces">어디에서 이야기할까요?</h2>
        <p>주제에 가장 가까운 공간을 선택하면 답을 더 빨리 받을 수 있어요.</p>
      </div>
      <a class="community-text-link"
         href="{{ community.discussion_url }}"
         rel="noopener">
        GitHub에서 전체 보기
        <i class="fas fa-arrow-right" aria-hidden="true"></i>
      </a>
    </div>

    <div class="community-category-grid">
      {% for category in community.categories %}
        <article class="community-category" style="--category-color: {{ category.color }};">
          <div class="community-category__top">
            <span class="community-category__icon">
              <i class="{{ category.icon }}" aria-hidden="true"></i>
            </span>
            <div>
              <h3>{{ category.title }}</h3>
              <span class="community-category__github-name">{{ category.github_name }}</span>
            </div>
          </div>
          <p>{{ category.description }}</p>
          <div class="community-category__links">
            <a href="{{ community.discussion_url }}/categories/{{ category.slug }}"
               rel="noopener">
              둘러보기
            </a>
            <a href="{{ community.discussion_url }}/new?category={{ category.slug }}"
               rel="noopener">
              글쓰기
              <i class="fas fa-arrow-right" aria-hidden="true"></i>
            </a>
          </div>
        </article>
      {% endfor %}
    </div>
  </section>

  <section class="community-section" id="latest-discussions" aria-labelledby="latest-title">
    <div class="community-section-header">
      <div>
        <h2 id="latest-title">최근 토론</h2>
        <p>새로 올라오거나 최근 답변이 달린 이야기입니다.</p>
      </div>
      <a class="community-text-link"
         href="{{ community.discussion_url }}"
         rel="noopener">
        모든 토론
        <i class="fas fa-external-link-alt" aria-hidden="true"></i>
      </a>
    </div>

    <form class="community-search"
          action="{{ community.discussion_url }}"
          method="get"
          role="search">
      <label>
        <span class="visually-hidden">커뮤니티 토론 검색</span>
        <input type="search"
               name="discussions_q"
               placeholder="궁금한 주제를 검색해 보세요"
               autocomplete="off">
      </label>
      <button type="submit" aria-label="검색">
        <i class="fas fa-search" aria-hidden="true"></i>
      </button>
    </form>

    {% if feed and feed.size > 0 %}
      <ul class="community-feed">
        {% for discussion in feed %}
          {%- assign category_meta = community.categories | where: "slug", discussion.category.slug | first -%}
          <li class="community-feed__item">
            <article class="community-discussion"
                     style="--category-color: {{ category_meta.color | default: '#6657d9' }};">
              <div>
                <span class="community-discussion__category">
                  <i class="{{ category_meta.icon | default: 'fas fa-comments' }}" aria-hidden="true"></i>
                  {{ category_meta.title | default: discussion.category.name | escape }}
                </span>
                <h3>
                  <a href="{{ discussion.url | escape }}" rel="noopener">
                    {{ discussion.title | escape }}
                  </a>
                </h3>
                <div class="community-discussion__meta">
                  <span>
                    <i class="far fa-user" aria-hidden="true"></i>
                    {{ discussion.author | default: "ghost" | escape }}
                  </span>
                  <time datetime="{{ discussion.updated_at | escape }}">
                    <i class="far fa-clock" aria-hidden="true"></i>
                    {{ discussion.updated_at | date: "%Y.%m.%d" }}
                  </time>
                  {% if discussion.answered %}
                    <span class="community-discussion__answered">
                      <i class="fas fa-check-circle" aria-hidden="true"></i>
                      답변 채택
                    </span>
                  {% endif %}
                </div>
              </div>
              <div class="community-discussion__counts" aria-label="토론 활동">
                <span title="추천">
                  <i class="far fa-thumbs-up" aria-hidden="true"></i>
                  {{ discussion.upvotes }}
                </span>
                <span title="답글">
                  <i class="far fa-comment" aria-hidden="true"></i>
                  {{ discussion.comments }}
                </span>
              </div>
            </article>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <div class="community-empty">
        <i class="far fa-comments" aria-hidden="true"></i>
        <h3>첫 이야기를 기다리고 있어요</h3>
        <p>궁금했던 AI 주제나 오늘 써 본 도구 이야기로 시작해 보세요.</p>
        <a class="community-button community-button--primary"
           href="{{ community.discussion_url }}/new"
           rel="noopener">
          첫 토론 시작하기
        </a>
      </div>
    {% endif %}
  </section>

  <section class="community-section" aria-labelledby="community-rules">
    <div class="community-section-header">
      <div>
        <h2 id="community-rules">함께 지키는 세 가지</h2>
        <p>편하게 이야기하되 서로의 시간과 경험을 존중해 주세요.</p>
      </div>
    </div>
    <div class="community-guide">
      <article class="community-guide__item">
        <i class="fas fa-heart" aria-hidden="true"></i>
        <h3>사람을 존중해요</h3>
        <p>생각은 반박할 수 있지만 사람을 공격하거나 비하하지 않습니다.</p>
      </article>
      <article class="community-guide__item">
        <i class="fas fa-search" aria-hidden="true"></i>
        <h3>맥락을 함께 적어요</h3>
        <p>무엇을 시도했고 어디에서 막혔는지 적으면 더 좋은 답을 얻을 수 있어요.</p>
      </article>
      <article class="community-guide__item">
        <i class="fas fa-shield-alt" aria-hidden="true"></i>
        <h3>광고와 개인정보는 조심해요</h3>
        <p>반복 홍보, 무관한 광고, 타인의 개인정보 공유는 허용하지 않습니다.</p>
      </article>
    </div>
    <p class="community-guide-footer">
      글을 작성하면
      <a href="{{ '/community-guidelines/' | relative_url }}">커뮤니티 운영 원칙</a>에 동의한 것으로 봅니다.
    </p>
  </section>
</div>
