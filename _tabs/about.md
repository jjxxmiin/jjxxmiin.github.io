---
layout: page
title: About
icon: fas fa-circle-info
order: 1
permalink: /about/
description: OPSOAI 운영자 정재민 소개. 한림대학교 컴퓨터공학 박사과정, 캐모릭스 대표. SCI 논문 7편, 특허 6건, 멀티모달 AI와 비전 AI 연구 이력.
---

<style>
/* 색은 전부 Chirpy 테마 변수로만 쓴다. 하드코딩하면 다크모드에서 글자가 사라진다. */

.ab-hero{display:flex;flex-direction:column;gap:.7rem;padding:.2rem 0 1.5rem;border-bottom:2px solid var(--heading-color);margin-bottom:.4rem}
.ab-kicker{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--text-muted-color)}
.ab-hero h2{margin:0;font-size:1.75rem;line-height:1.35;border:0;padding:0;text-wrap:balance}
.ab-hero p{margin:0;color:var(--text-muted-color);max-width:60ch;line-height:1.75}

.ab-sec{padding-top:2.8rem}
.ab-sec-head{display:flex;align-items:baseline;gap:.7rem;margin-bottom:1.1rem;padding-bottom:.55rem;border-bottom:1px solid var(--btn-border-color)}
.ab-sec-no{font-size:.72rem;font-weight:700;color:var(--link-color);letter-spacing:.1em;font-variant-numeric:tabular-nums;flex:none}
.ab-sec-head h3{margin:0;font-size:1.2rem;border:0;padding:0;line-height:1.4}
.ab-lede{color:var(--text-muted-color);line-height:1.75;max-width:62ch;margin:0 0 1.1rem}

.ab-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-stat{background:var(--card-bg);padding:1.1rem .95rem;display:flex;flex-direction:column;gap:.25rem}
.ab-stat .n{font-size:1.65rem;font-weight:700;line-height:1.1;color:var(--heading-color);font-variant-numeric:tabular-nums}
.ab-stat .n small{font-size:.85rem;font-weight:500;color:var(--text-muted-color);margin-left:.15rem}
.ab-stat .l{font-size:.78rem;color:var(--text-muted-color);line-height:1.5}

.ab-profile{background:var(--card-bg);border:1px solid var(--btn-border-color);border-radius:10px;padding:1.25rem 1.35rem;display:flex;flex-direction:column;gap:.8rem}
.ab-profile .name{font-size:1.15rem;font-weight:700;color:var(--heading-color)}
.ab-profile .name span{font-size:.85rem;font-weight:500;color:var(--text-muted-color);margin-left:.5rem}
.ab-profile p{margin:0;line-height:1.75;color:var(--text-muted-color)}
.ab-profile strong{color:var(--text-color)}
.ab-chips{display:flex;flex-wrap:wrap;gap:.35rem;padding-top:.2rem}
.ab-chip{font-size:.76rem;padding:.22rem .58rem;border-radius:5px;background:var(--main-bg);border:1px solid var(--btn-border-color);color:var(--text-color)}

/* 이력 행: 기간 + 내용 */
.ab-rows{display:flex;flex-direction:column;gap:.05rem;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-row{background:var(--card-bg);padding:.85rem 1.1rem;display:grid;grid-template-columns:9.5rem 1fr;gap:1rem;align-items:baseline}
.ab-row .when{font-size:.78rem;font-weight:600;color:var(--text-muted-color);font-variant-numeric:tabular-nums;white-space:nowrap}
.ab-row .what{font-size:.9rem;color:var(--text-color);line-height:1.6}
.ab-row .what em{font-style:normal;color:var(--text-muted-color);font-size:.85rem}

/* 논문 목록 */
.ab-papers{display:flex;flex-direction:column;gap:.05rem;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-paper{background:var(--card-bg);padding:.8rem 1.1rem;display:flex;flex-direction:column;gap:.2rem}
.ab-paper .jr{display:flex;flex-wrap:wrap;align-items:baseline;gap:.45rem}
.ab-paper .j{font-weight:700;font-size:.85rem;color:var(--heading-color)}
.ab-paper .badge{font-size:.7rem;padding:.1rem .4rem;border-radius:4px;background:var(--main-bg);border:1px solid var(--btn-border-color);color:var(--text-muted-color);font-variant-numeric:tabular-nums}
.ab-paper .badge.first{background:var(--link-color);border-color:var(--link-color);color:var(--main-bg);font-weight:700}
.ab-paper .t{font-size:.85rem;color:var(--text-muted-color);line-height:1.55}

.ab-tl{position:relative;padding-left:1.5rem}
.ab-tl::before{content:"";position:absolute;left:5px;top:.5rem;bottom:.5rem;width:2px;background:var(--btn-border-color)}
.ab-ev{position:relative;padding-bottom:1.35rem}
.ab-ev:last-child{padding-bottom:0}
.ab-ev::before{content:"";position:absolute;left:-1.5rem;top:.4rem;width:12px;height:12px;border-radius:50%;background:var(--main-bg);border:2px solid var(--btn-border-color)}
.ab-ev.hl::before{background:var(--link-color);border-color:var(--link-color)}
.ab-ev .when{font-size:.74rem;font-weight:700;letter-spacing:.04em;color:var(--text-muted-color);font-variant-numeric:tabular-nums}
.ab-ev .head{font-weight:600;color:var(--heading-color);margin-top:.12rem;line-height:1.5}
.ab-ev .desc{font-size:.86rem;color:var(--text-muted-color);margin-top:.25rem;line-height:1.7}

.ab-awards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:.7rem}
.ab-award{background:var(--card-bg);border:1px solid var(--btn-border-color);border-radius:8px;padding:.85rem 1rem;display:flex;flex-direction:column;gap:.2rem}
.ab-award .a{font-weight:600;font-size:.88rem;color:var(--heading-color);line-height:1.45}
.ab-award .b{font-size:.78rem;color:var(--text-muted-color)}

.ab-rules{display:flex;flex-direction:column;gap:.05rem;background:var(--btn-border-color);border:1px solid var(--btn-border-color);border-radius:10px;overflow:hidden}
.ab-rule{background:var(--card-bg);padding:.9rem 1.1rem;display:flex;gap:.85rem;align-items:flex-start}
.ab-rule .k{font-weight:700;color:var(--heading-color);font-size:.88rem;flex:none;min-width:6rem}
.ab-rule .v{font-size:.86rem;color:var(--text-muted-color);line-height:1.65}

.ab-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.55rem 1.5rem}
.ab-meta div{font-size:.86rem;color:var(--text-muted-color);line-height:1.65}
.ab-meta b{color:var(--text-color);font-weight:600}

@media (max-width:576px){
  .ab-hero h2{font-size:1.42rem}
  .ab-row{grid-template-columns:1fr;gap:.2rem}
  .ab-rule{flex-direction:column;gap:.2rem}
  .ab-rule .k{min-width:0}
}
</style>

<div class="ab-hero">
  <span class="ab-kicker">OPSOAI</span>
  <h2>AI를 연구하고, 만들고, 쓰는 방법을 적습니다</h2>
  <p>
    멀티모달 AI와 비전 AI를 연구하면서 제품으로 만들고 있습니다.
    그 과정에서 확인한 것을 2019년부터 이곳에 기록해 왔습니다.
  </p>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">01</span>
    <h3>운영자</h3>
  </div>
  <div class="ab-profile">
    <div class="name">정재민 <span>Jaemin Jeong</span></div>
    <p>
      <strong>주식회사 캐모릭스(CAMORIX) 대표이사</strong>이자
      한림대학교 컴퓨터공학과 박사과정 연구원입니다.
      수면 다원검사 신호를 다루는 멀티모달 딥러닝으로 학위 연구를 했고,
      지금은 카메라와 멀티모달 AI로 현장의 영상과 음성, 행동 데이터를 분석하는
      제품을 만듭니다.
    </p>
    <p>
      2019년 2월 첫 글은 DarkNet 소스 코드를 한 줄씩 뜯어보는 기록이었습니다.
      지금은 AI 에이전트와 MCP를 다루고, 개발자가 아닌 분들에게 AI 활용을 가르칩니다.
      <strong>다루는 주제가 바뀐 게 아니라 설명해야 할 대상이 넓어졌습니다.</strong>
    </p>
    <div class="ab-chips">
      <span class="ab-chip">멀티모달 딥러닝</span>
      <span class="ab-chip">생체신호 AI</span>
      <span class="ab-chip">컴퓨터 비전</span>
      <span class="ab-chip">객체 탐지</span>
      <span class="ab-chip">모델 경량화</span>
      <span class="ab-chip">온디바이스 추론</span>
      <span class="ab-chip">LLM</span>
      <span class="ab-chip">AI 에이전트</span>
      <span class="ab-chip">MCP</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">02</span>
    <h3>숫자</h3>
  </div>
  <div class="ab-stats">
    <div class="ab-stat"><span class="n">7<small>편</small></span><span class="l">SCI 저널 논문<br>(Q1 5편, 제1저자 2편)</span></div>
    <div class="ab-stat"><span class="n">9<small>편</small></span><span class="l">국제학술대회 발표</span></div>
    <div class="ab-stat"><span class="n">6<small>건</small></span><span class="l">특허 (등록 3, 출원 3)</span></div>
    <div class="ab-stat"><span class="n">627<small>편</small></span><span class="l">블로그 누적 글</span></div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">03</span>
    <h3>학력과 경력</h3>
  </div>
  <div class="ab-rows">
    <div class="ab-row">
      <span class="when">2026.01 ~ 현재</span>
      <span class="what">주식회사 캐모릭스 <strong>대표이사</strong><br><em>AI 솔루션 사업과 연구개발 총괄</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2021.01 ~ 현재</span>
      <span class="what">주식회사 미러로이드 <strong>인공지능 연구 책임</strong><br><em>AI 모델 연구개발 총괄. 초기 멤버로 합류</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2021.03 ~ 현재</span>
      <span class="what">한림대학교 AIAC Lab 연구원 <strong>박사과정</strong><br><em>멀티모달 생체신호 AI 연구</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2023.06 ~ 2024.07</span>
      <span class="what">캐나다 오타와대학교 <strong>방문연구원</strong><br><em>딥러닝 국제 공동연구</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2026.09</span>
      <span class="what">한림대학교 컴퓨터공학과 <strong>공학박사</strong> <em>(졸업 예정)</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2021.03</span>
      <span class="what">한림대학교 컴퓨터공학과 <strong>공학석사</strong></span>
    </div>
    <div class="ab-row">
      <span class="when">2019.09</span>
      <span class="what">한림대학교 컴퓨터공학과 <strong>공학사</strong></span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">04</span>
    <h3>연구</h3>
  </div>
  <p class="ab-lede">
    수면 단계 분류와 수면무호흡 중증도 판별을 다루는 멀티모달 딥러닝,
    그리고 모델 경량화가 주된 연구 주제입니다.
  </p>
  <div class="ab-papers">
    <div class="ab-paper">
      <div class="jr"><span class="j">npj Digital Medicine</span><span class="badge">Q1</span><span class="badge">IF 15.2</span><span class="badge">2025</span></div>
      <span class="t">Explainable vision transformer for automatic visual sleep staging on multimodal PSG signals</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">Expert Systems with Applications</span><span class="badge">Q1</span><span class="badge">IF 7.5</span><span class="badge">2026</span></div>
      <span class="t">PSG-free multi-view facial imaging and attention-based fusion for OSA severity classification</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">SLEEP</span><span class="badge first">제1저자</span><span class="badge">Q1</span><span class="badge">IF 5.7</span><span class="badge">2023</span></div>
      <span class="t">Standardized image-based polysomnography database and deep learning algorithm for sleep-stage classification</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">ICT Express</span><span class="badge first">제1저자</span><span class="badge">Q1</span><span class="badge">IF 4.1</span><span class="badge">2021</span></div>
      <span class="t">Filter combination learning for CNN model compression</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">IEEE Access</span><span class="badge">Q2</span><span class="badge">IF 3.7</span><span class="badge">2023</span></div>
      <span class="t">Automatic sleep stage classification using deep learning algorithm for multi-institutional database</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">Journal of Personalized Medicine</span><span class="badge">Q1</span><span class="badge">IF 3.0</span><span class="badge">2022</span></div>
      <span class="t">Deep learning application to clinical decision support system in sleep stage classification</span>
    </div>
    <div class="ab-paper">
      <div class="jr"><span class="j">Electronics</span><span class="badge">Q2</span><span class="badge">IF 2.6</span><span class="badge">2021</span></div>
      <span class="t">Zero-keep filter pruning for energy and power efficient deep neural networks</span>
    </div>
  </div>
  <p class="ab-lede" style="margin-top:1rem">
    위 저널 논문 외에 IEEE ICCE, IEEE ICCE-Asia, IEEE BigData, ICTC 등
    국제학술대회에서 9편을 발표했습니다.
    IEEE BigData 2024 ORDDC에는 도로 위험물 검출 논문으로 초청 발표했습니다.
  </p>

  <h4 style="margin:1.6rem 0 .7rem;font-size:1rem">연구개발 과제</h4>
  <div class="ab-rows">
    <div class="ab-row">
      <span class="when">2024</span>
      <span class="what">차량 라이브뷰 영상 기반 스마트 도로안전 모니터링 시스템<br><em>책임연구원, 지오멕스소프트</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2023</span>
      <span class="what">노령 환자 낙상과 재활 모니터링을 위한 Edge형 Healthcare 시스템<br><em>책임연구원, 지오멕스소프트</em></span>
    </div>
    <div class="ab-row">
      <span class="when">2021 ~ 2022</span>
      <span class="what">AI-HUB 수면질 평가와 수면장애 진단 이미지 데이터 구축<br><em>구축 총괄, 과학기술정보통신부</em></span>
    </div>
  </div>

  <h4 style="margin:1.6rem 0 .7rem;font-size:1rem">특허</h4>
  <div class="ab-rows">
    <div class="ab-row">
      <span class="when">등록 2023</span>
      <span class="what">인공지능 모델의 파라미터 저장을 위한 필터 조합 학습 네트워크 시스템</span>
    </div>
    <div class="ab-row">
      <span class="when">등록 2023</span>
      <span class="what">다채널 생체 신호 이미지 기반 수면 단계 분류 전자 장치와 방법</span>
    </div>
    <div class="ab-row">
      <span class="when">등록 2023</span>
      <span class="what">기계학습모델 공유 또는 판매를 위한 시스템</span>
    </div>
    <div class="ab-row">
      <span class="when">출원 2026</span>
      <span class="what">발표 화면과 발화의 정합성 기반 발표자 피드백 제공 방법</span>
    </div>
    <div class="ab-row">
      <span class="when">출원 2025</span>
      <span class="what">시니어 헬스케어를 위한 인공지능 모니터링 솔루션</span>
    </div>
    <div class="ab-row">
      <span class="when">출원 2025</span>
      <span class="what">모니터링 데이터 기반 자동 보고서 생성 시스템</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">05</span>
    <h3>만든 것</h3>
  </div>
  <div class="ab-rows">
    <div class="ab-row">
      <span class="when">PREMIND</span>
      <span class="what">멀티모달 AI 기반 강의와 발표 분석 SaaS. 기획과 개발 총괄<br><em>한림대학교 교수학습지원센터 신임교원 강의평가 도구로 채택</em></span>
    </div>
    <div class="ab-row">
      <span class="when">O!PLANET</span>
      <span class="what">행사 대여형 AI 키오스크 플랫폼. 기획과 개발 총괄<br><em>대학 축제와 지역 행사 현장 실증</em></span>
    </div>
    <div class="ab-row">
      <span class="when">비전 AI 용역</span>
      <span class="what">낙상 감지, 도로 위험 탐지, 설비 검침과 검사. 연구 총괄<br><em>산학 공동연구와 기술용역</em></span>
    </div>
    <div class="ab-row">
      <span class="when">미러로이드</span>
      <span class="what">스마트미러와 포토부스용 AI 모델 개발 총괄<br><em>헤어와 인물, 배경 검출 및 세분화, 이미지 생성</em></span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">06</span>
    <h3>수상과 선정</h3>
  </div>
  <div class="ab-awards">
    <div class="ab-award">
      <span class="a">스마트 ICT 디바이스 전국 공모전 일반부문 대상</span>
      <span class="b">과학기술정보통신부 장관상, 2025.10</span>
    </div>
    <div class="ab-award">
      <span class="a">NIPA 인공지능 문제해결 경진대회 1위</span>
      <span class="b">과학기술정보통신부 주최</span>
    </div>
    <div class="ab-award">
      <span class="a">DACON 위성관측 데이터 활용 AI 경진대회 2위</span>
      <span class="b">한국원자력연구원 주최</span>
    </div>
    <div class="ab-award">
      <span class="a">강원 창업 탄탄대로 공공데이터 아이디어 공모전 대상</span>
      <span class="b">KNU 창업진흥원장상, 2025.08</span>
    </div>
    <div class="ab-award">
      <span class="a">수도강원권 IP/IR 네트워킹데이 우수상</span>
      <span class="b">강원지식재산센터, 2026.07</span>
    </div>
    <div class="ab-award">
      <span class="a">하나 소셜벤처 유니버시티 최종 우수팀</span>
      <span class="b">하나금융그룹, 2025.12</span>
    </div>
    <div class="ab-award">
      <span class="a">ICT 동북권 창업아이디어 경진대회 장려상</span>
      <span class="b">강원정보문화진흥원장상, 2025.08</span>
    </div>
    <div class="ab-award">
      <span class="a">창업중심대학 지원사업 선정</span>
      <span class="b">중소벤처기업부, 2026.04</span>
    </div>
  </div>
</div>

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">07</span>
    <h3>강연</h3>
  </div>
  <div class="ab-tl">
    <div class="ab-ev hl">
      <div class="when">2026.08</div>
      <div class="head">고려대학교 행정학과 BK21 「AI, 데이터 기반 행정과 정책 연구역량 강화 부트캠프」 초청 강연</div>
      <div class="desc">
        초보자 대상 6시간 실습 과정, <em>AI로 행정 업무와 연구를 다시 설계하기</em>.
        설명이 아니라 결과물 중심으로 진행해, 참가자가 그날 안에
        업무 루틴 1개와 문헌 매트릭스 1개, 분석과 초안 1세트를 만들어 가는 구성이었습니다.
      </div>
    </div>
  </div>
</div>

<!--
  ─────────────────────────────────────────────────────────────
  강연 이력이 늘면 위 .ab-tl 안에 .ab-ev 블록을 복사해 넣으세요.
  강조하려면 class="ab-ev hl" 을 줍니다.

  표기 규칙: 가운뎃점(U+00B7)은 쓰지 않습니다. 쉼표나 "과/와"로 바꿔 주세요.
  이력서 원본(정재민_이력서_국문양식.pdf)에는 생년월일과 주소, 연락처가 있습니다.
  그 항목들은 공개 페이지에 옮기지 않았고, 파일 자체도 .gitignore 로 막아 두었습니다.
  ─────────────────────────────────────────────────────────────
-->

<div class="ab-sec">
  <div class="ab-sec-head">
    <span class="ab-sec-no">08</span>
    <h3>이 블로그</h3>
  </div>
  <p class="ab-lede">
    2019년 2월부터 627편을 썼습니다. 논문 리뷰와 오픈소스 분석으로 시작해
    지금은 AI를 실제 업무에 붙이는 방법까지 다룹니다.
    개발자와 연구자는 물론, AI를 업무에 쓰려는 분들을 함께 독자로 봅니다.
  </p>
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
    <span class="ab-sec-no">09</span>
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
    "alternateName": "Jaemin Jeong",
    "url": "https://www.opsoai.com/about/",
    "email": "ceo@opsoai.com",
    "jobTitle": "대표이사",
    "worksFor": {
      "@type": "Organization",
      "name": "주식회사 캐모릭스 (CAMORIX)",
      "url": "https://www.camorix.com"
    },
    "alumniOf": {
      "@type": "CollegeOrUniversity",
      "name": "한림대학교 컴퓨터공학과"
    },
    "knowsAbout": [
      "멀티모달 딥러닝",
      "생체신호 AI",
      "컴퓨터 비전",
      "모델 경량화",
      "온디바이스 AI",
      "LLM",
      "AI 에이전트",
      "Model Context Protocol",
      "AI 업무 활용"
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
