---
layout: page
title: About
icon: fas fa-circle-info
order: 1
permalink: /about/
description: OPSOAI는 쏟아지는 AI 기술을 오늘 쓸 수 있는 형태로 옮겨 적는 한국어 AI 활용 미디어입니다. 운영자 정재민(캐모릭스 대표) 소개와 강연 이력, 콘텐츠 제작 원칙.
---

<style>
/* 색은 전부 Chirpy 테마 변수로만 쓴다. 하드코딩하면 다크모드에서 글자가 사라진다. */

/* ── 히어로 ── */
.ab-hero{display:flex;flex-direction:column;gap:.9rem;padding:.2rem 0 1.7rem;border-bottom:2px solid var(--heading-color);margin-bottom:.4rem}
.ab-kicker{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--text-muted-color)}
.ab-hero h2{margin:0;font-size:1.9rem;line-height:1.35;border:0;padding:0;text-wrap:balance}
.ab-hero p{margin:0;color:var(--text-muted-color);max-width:58ch;line-height:1.78}

/* ── 섹션 구획 ── */
.ab-sec{padding-top:2.9rem}
.ab-sec-head{display:flex;align-items:baseline;gap:.7rem;margin-bottom:1.15rem;padding-bottom:.55rem;border-bottom:1px solid var(--btn-border-color)}
.ab-sec-no{font-size:.72rem;font-weight:700;color:var(--link-color);letter-spacing:.1em;font-variant-numeric:tabular-nums;flex:none}
.ab-sec-head h3{margin:0;font-size:1.22rem;border:0;padding:0;line-height:1.4}
.ab-lede{color:var(--text-muted-color);line-height:1.78;max-width:62ch;margin:0 0 1.2rem}

/* ── 통계 ── */
.ab-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(136px,1fr));gap:1px;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-stat{background:var(--card-bg);padding:1.15rem .95rem;display:flex;flex-direction:column;gap:.28rem}
.ab-stat .n{font-size:1.75rem;font-weight:700;line-height:1.1;color:var(--heading-color);font-variant-numeric:tabular-nums}
.ab-stat .n small{font-size:.88rem;font-weight:500;color:var(--text-muted-color);margin-left:.15rem}
.ab-stat .l{font-size:.79rem;color:var(--text-muted-color);line-height:1.5}

/* ── 독자 카드 ── */
.ab-rings{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:.85rem}
.ab-ring{background:var(--card-bg);border:1px solid var(--btn-border-color);border-radius:10px;padding:1.05rem 1.15rem;display:flex;flex-direction:column;gap:.42rem}
.ab-ring .who{font-weight:700;color:var(--heading-color);font-size:.95rem;line-height:1.45}
.ab-ring .what{font-size:.87rem;color:var(--text-muted-color);line-height:1.68}

/* ── 프로필 ── */
.ab-profile{background:var(--card-bg);border:1px solid var(--btn-border-color);border-radius:10px;padding:1.3rem 1.4rem;display:flex;flex-direction:column;gap:.85rem}
.ab-profile .name{font-size:1.15rem;font-weight:700;color:var(--heading-color)}
.ab-profile .name span{font-size:.87rem;font-weight:500;color:var(--text-muted-color);margin-left:.5rem}
.ab-profile p{margin:0;line-height:1.78;color:var(--text-muted-color)}
.ab-profile strong{color:var(--text-color)}
.ab-chips{display:flex;flex-wrap:wrap;gap:.35rem;padding-top:.25rem}
.ab-chip{font-size:.76rem;padding:.22rem .58rem;border-radius:5px;background:var(--main-bg);border:1px solid var(--btn-border-color);color:var(--text-color)}

/* ── 연혁 타임라인 ── */
.ab-tl{position:relative;padding-left:1.55rem;margin:.2rem 0 0}
.ab-tl::before{content:"";position:absolute;left:5px;top:.5rem;bottom:.5rem;width:2px;background:var(--btn-border-color)}
.ab-ev{position:relative;padding-bottom:1.5rem}
.ab-ev:last-child{padding-bottom:0}
.ab-ev::before{content:"";position:absolute;left:-1.55rem;top:.4rem;width:12px;height:12px;border-radius:50%;background:var(--main-bg);border:2px solid var(--btn-border-color)}
.ab-ev.hl::before{background:var(--link-color);border-color:var(--link-color)}
.ab-ev .when{font-size:.74rem;font-weight:700;letter-spacing:.05em;color:var(--text-muted-color);font-variant-numeric:tabular-nums}
.ab-ev .head{font-weight:600;color:var(--heading-color);margin-top:.14rem;line-height:1.52}
.ab-ev .desc{font-size:.87rem;color:var(--text-muted-color);margin-top:.3rem;line-height:1.72}
.ab-ev .desc strong{color:var(--text-color)}

/* ── 원칙 목록 ── */
.ab-rules{display:flex;flex-direction:column;gap:.05rem;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-rule{background:var(--card-bg);padding:.95rem 1.15rem;display:flex;gap:.85rem;align-items:flex-start}
.ab-rule .k{font-weight:700;color:var(--heading-color);font-size:.9rem;flex:none;min-width:6.2rem}
.ab-rule .v{font-size:.87rem;color:var(--text-muted-color);line-height:1.68}


/* ── 사이트 정보 ── */
.ab-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.6rem 1.6rem}
.ab-meta div{font-size:.87rem;color:var(--text-muted-color);line-height:1.7}
.ab-meta b{color:var(--text-color);font-weight:600}

@media (max-width:576px){
  .ab-hero h2{font-size:1.5rem}
  .ab-rule{flex-direction:column;gap:.25rem}
  .ab-rule .k{min-width:0}
}
</style>

<div class="ab-hero">
  <span class="ab-kicker">AI 활용 미디어, 2019년부터</span>
  <h2>쏟아지는 AI를, 오늘 쓸 수 있는 형태로</h2>
  <p>
    AI 소식은 넘치는데 내 일에 어떻게 붙이는지는 아무도 알려주지 않습니다.
    논문은 어렵고, 보도자료는 무슨 말인지 모르겠고, 해외 튜토리얼은 내 환경과 맞지 않습니다.
    OPSOAI는 그 사이를 메우는 자리에 있습니다.
  </p>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">01</span>
    <h3>숫자로 보는 OPSOAI</h3>
  </div>
  <div class="ab-stats">
    <div class="ab-stat"><span class="n">612<small>편</small></span><span class="l">누적 발행 글</span></div>
    <div class="ab-stat"><span class="n">7<small>년</small></span><span class="l">2019년 2월부터</span></div>
    <div class="ab-stat"><span class="n">6<small>시간</small></span><span class="l">최근 초청 강연 분량</span></div>
    <div class="ab-stat"><span class="n">2<small>편/일</small></span><span class="l">발행 주기</span></div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">02</span>
    <h3>누구를 위해 쓰나요</h3>
  </div>
  <p class="ab-lede">한 가지 기술을 네 종류의 독자에게 각각 쓸모 있는 형태로 옮깁니다.</p>
  <div class="ab-rings">
    <div class="ab-ring">
      <span class="who">업무에 AI를 붙이려는 직장인</span>
      <span class="what">보고서와 문서, 데이터 정리를 실제로 끝내는 방법. 도구 이름이 아니라 반복 가능한 흐름을 남깁니다.</span>
    </div>
    <div class="ab-ring">
      <span class="who">연구자와 행정 실무자</span>
      <span class="what">문헌 정리부터 분석 초안까지, 근거를 열어 확인한 뒤에만 저장하는 절차를 함께 설계합니다.</span>
    </div>
    <div class="ab-ring">
      <span class="who">1인 사업자와 크리에이터</span>
      <span class="what">혼자서 기획과 제작, 마케팅을 감당하게 해주는 도구와 순서.</span>
    </div>
    <div class="ab-ring">
      <span class="who">개발자와 엔지니어</span>
      <span class="what">오픈소스 아키텍처 해부, 논문 리뷰, 벤치마크 검증. 이 블로그가 출발한 자리입니다.</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">03</span>
    <h3>운영자</h3>
  </div>
  <div class="ab-profile">
    <div class="name">정재민 <span>캐모릭스(CAMORIX) 대표</span></div>
    <p>
      카메라와 멀티모달 AI로 현장의 영상과 음성, 행동 데이터를 분석하는 비전 AI 회사를 운영하면서,
      그 과정에서 쌓인 것을 이 블로그에 적습니다.
    </p>
    <p>
      2019년 2월 첫 글은 DarkNet 소스 코드를 한 줄씩 뜯어보는 기록이었습니다.
      지금은 AI 에이전트와 MCP를 다루고, 개발자가 아닌 분들에게 AI 활용을 가르칩니다.
      <strong>7년 동안 다룬 주제가 바뀐 게 아니라, 설명해야 할 대상이 넓어졌습니다.</strong>
    </p>
    <div class="ab-chips">
      <span class="ab-chip">컴퓨터 비전</span>
      <span class="ab-chip">객체 탐지</span>
      <span class="ab-chip">DarkNet</span>
      <span class="ab-chip">엣지 추론</span>
      <span class="ab-chip">강화학습</span>
      <span class="ab-chip">멀티모달</span>
      <span class="ab-chip">LLM</span>
      <span class="ab-chip">AI 에이전트</span>
      <span class="ab-chip">MCP</span>
      <span class="ab-chip">AI 업무 활용</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">04</span>
    <h3>연혁</h3>
  </div>
  <div class="ab-tl">
    <div class="ab-ev hl">
      <div class="when">2026.08</div>
      <div class="head">고려대학교 행정학과 BK21 「AI, 데이터 기반 행정과 정책 연구역량 강화 부트캠프」 초청 강연</div>
      <div class="desc">
        초보자 대상 6시간 실습 과정, <em>AI로 행정 업무와 연구를 다시 설계하기</em>.
        설명이 아니라 결과물 중심으로 진행해, 참가자가 그날 안에
        <strong>업무 루틴 1개, 문헌 매트릭스 1개, 분석과 초안 1세트</strong>를
        직접 만들어 가는 구성이었습니다.
      </div>
    </div>
    <div class="ab-ev">
      <div class="when">2026</div>
      <div class="head">캐모릭스(CAMORIX) 설립, 대표이사</div>
      <div class="desc">
        비전 AI로 오프라인 현장의 순간을 데이터로 바꾸는 회사입니다.
        강의와 발표를 분석하는 <strong>프리마인드(PREMIND)</strong>,
        행사의 순간을 카드로 남기는 <strong>오!행성(O!PLANET)</strong>,
        그리고 낙상과 도로, 설비 위험 탐지 같은 맞춤형 비전 AI 연구와 용역을 함께합니다.
      </div>
    </div>
    <div class="ab-ev">
      <div class="when">2019.02 —</div>
      <div class="head">OPSOAI 블로그 운영</div>
      <div class="desc">
        DarkNet 소스 분석과 컴퓨터 비전 논문 리뷰로 시작해 현재 612편.
        2026년부터는 AI 활용 쪽으로 폭을 넓히고 있습니다.
      </div>
    </div>
  </div>
</div>

<!--
  ─────────────────────────────────────────────────────────────
  추가할 이력이 있으면 위 .ab-tl 안에 .ab-ev 블록을 복사해 넣으세요.
  강조하고 싶은 항목에는 class="ab-ev hl" 을 주면 점에 색이 들어갑니다.
  학위, 재직 이력, 수상, 기고 등은 확인 가능한 것만 넣는 편이 좋습니다.
  구글과 AI 답변엔진이 E-E-A-T에서 실제로 보는 부분이고,
  강의 문의 전환에도 가장 직접적으로 영향을 줍니다.

  표기 규칙: 가운뎃점(U+00B7)은 쓰지 않습니다. 쉼표나 "과/와"로 바꿔 주세요.
  ─────────────────────────────────────────────────────────────
-->

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">05</span>
    <h3>콘텐츠 제작 원칙</h3>
  </div>
  <p class="ab-lede">AI가 쓴 글이 넘치는 시대에 읽을 만한 글과 아닌 글을 가르는 건 결국 검증입니다.</p>
  <div class="ab-rules">
    <div class="ab-rule">
      <span class="k">출처를 단다</span>
      <span class="v">수치와 발표 내용에는 원문 링크를 각주로 답니다. 확인할 수 없는 주장은 쓰지 않거나, 확인되지 않았다고 명시합니다.</span>
    </div>
    <div class="ab-rule">
      <span class="k">날짜를 쓴다</span>
      <span class="v">"최근"이라고 얼버무리지 않습니다. AI 분야에서 6개월 전 정보는 대개 틀린 정보입니다.</span>
    </div>
    <div class="ab-rule">
      <span class="k">직접 돌려본다</span>
      <span class="v">도구 리뷰는 설치하고 써본 뒤에 씁니다. 안 써봤으면 안 써봤다고 밝힙니다.</span>
    </div>
    <div class="ab-rule">
      <span class="k">한계를 쓴다</span>
      <span class="v">장점만 나열된 글은 광고이지 리뷰가 아닙니다. 무엇이 안 되는지, 어떤 비용이 드는지 같이 적습니다.</span>
    </div>
    <div class="ab-rule">
      <span class="k">틀리면 고친다</span>
      <span class="v">사실관계 오류를 발견하면 본문을 수정하고 수정 사실을 남깁니다.</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">06</span>
    <h3>이 사이트에 대해</h3>
  </div>
  <div class="ab-meta">
    <div><b>광고</b><br>Google AdSense를 통해 광고를 게재하며, 그 수익으로 운영합니다.</div>
    <div><b>댓글</b><br>GitHub 계정으로 <a href="https://giscus.app">Giscus</a>를 통해 남길 수 있습니다.</div>
    <div><b>개인정보</b><br><a href="/privacy/">개인정보 처리방침</a>을 참고해 주세요.</div>
    <div><b>인용</b><br>출처와 원문 링크를 남겨주시면 자유롭게 인용하셔도 됩니다.</div>
    <div><b>연락</b><br><a href="mailto:ceo@opsoai.com">ceo@opsoai.com</a></div>
    <div><b>코드</b><br><a href="https://github.com/jjxxmiin">GitHub @jjxxmiin</a></div>
  </div>
</div>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "AboutPage",
  "mainEntity": {
    "@type": "Person",
    "name": "정재민",
    "url": "https://www.opsoai.com/about/",
    "email": "ceo@opsoai.com",
    "jobTitle": "대표이사",
    "worksFor": {
      "@type": "Organization",
      "name": "캐모릭스 (CAMORIX)",
      "url": "https://www.camorix.com"
    },
    "knowsAbout": [
      "AI 업무 활용",
      "LLM",
      "AI 에이전트",
      "Model Context Protocol",
      "컴퓨터 비전",
      "온디바이스 AI",
      "오픈소스 AI 도구"
    ],
    "sameAs": ["https://github.com/jjxxmiin"],
    "performerIn": {
      "@type": "EducationEvent",
      "name": "AI, 데이터 기반 행정과 정책 연구역량 강화 부트캠프",
      "startDate": "2026-08",
      "organizer": {
        "@type": "CollegeOrUniversity",
        "name": "고려대학교 행정학과 BK21"
      }
    }
  },
  "publisher": {
    "@type": "Organization",
    "name": "OPSOAI",
    "url": "https://www.opsoai.com/",
    "logo": "https://www.opsoai.com/assets/img/logo.png",
    "foundingDate": "2019-02"
  }
}
</script>
