# OPSOAI 성장 실험 — 2026-09-13

목표는 글 개수가 아니라 검색 방문과 실제 독자의 재방문 증가다. 기존 오전 뉴스와
오후 실용 가이드 예약은 유지하고, 앞으로 28일간 검색 의도와 배포 효과를 측정한다.
수익과 성장의 보장은 하지 않는다. 방문 데이터와 광고 수익은 별도 지표다.

## 참고 영상에서 가져온 운영 원칙

[배움의 현장, 알파남 김지수 인터뷰](https://www.youtube.com/watch?v=YIntzoHQZjs),
2026-09-08 게시. 한국어 자동 자막으로 내용을 확인했다. 수익·자산은 출연자 주장이고,
블로그만의 순이익이나 초보자의 기대수익으로 검증된 값이 아니다. 설명란에는 강의와
자료 신청 홍보가 있다.

- [12:36](https://www.youtube.com/watch?v=YIntzoHQZjs&t=756): 독자가 당장 해결하려는 질문을 출발점으로 삼는다.
- [15:08](https://www.youtube.com/watch?v=YIntzoHQZjs&t=908): 시의성 있는 질문과 구매·신청 등 행동에 가까운 질문을 구분한다.
- [25:02](https://www.youtube.com/watch?v=YIntzoHQZjs&t=1502): 반복 작업은 템플릿으로 표준화한다.
- [31:24](https://www.youtube.com/watch?v=YIntzoHQZjs&t=1884): 원문을 채널에 맞는 요약으로 바꾸어 독자가 원문으로 오는 경로를 만든다.

우리에게 적용할 판단: AI 분야 안에서 실제 검색 질문을 해결하고, 요약에도 유용한 답을
제공한다. 결론을 숨겨 클릭을 유도하거나 광고를 본문·버튼으로 오인하게 만들지 않는다.
[Google의 독자 중심 콘텐츠 기준](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)과
[광고 배치 기준](https://support.google.com/adsense/answer/1346295)을 따른다.

## 이번 변경

1. Search Console의 검색어 분석에서 `site:` 점검용 질의를 제외했다.
   페이지 집계는 원래 총량을 유지한다. 검색어 데이터는 일부 익명 질의를 포함하지
   않으므로 검색어 합계와 전체 클릭·노출은 일치하지 않을 수 있다.
2. 실제 검색 반응이 있는 DreamZero 글의 제목을 `World Action Model(WAM)이란?`으로
   시작하게 수정했다. URL과 핵심 내용은 유지해 제목 변경 효과를 따로 관찰한다.
3. 뉴스와 가이드를 발행할 때 Threads·LinkedIn용 배포 초안을 자동 생성한다.
   검증된 제목과 description을 재사용하며, 추가 생성형 API 비용은 없다.
   플랫폼별 UTM 링크로 유입을 구분한다. 자동 게시는 하지 않는다.
4. 발행 성공 후 GitHub Actions의 `distribution-drafts` 아티팩트에 초안을 보관한다.
   보관 기간은 14일이다. 실제 원문 배포 완료 후 검토하고 게시한다.

## 매주 반복할 순서

- `python automation/search_console.py --days 28 --report all`로 실제 검색 질문 확인.
- 기존 글이 답할 수 있는 질문이면 해당 글을 보완하고, 같은 주제 새 URL을 만들지 않는다.
- 새 가이드는 핵심 답 → 적용 조건 → 실행 단계 → 실패 시 대안 순서로 구성한다.
- 직접 테스트가 필요한 비교·추천은 결과와 증빙을 확보한 뒤 작성한다.
- 사진·도표는 이해를 도울 때 넣고, 변화·영향·제한을 짧게 하이라이트한다.
- 원문 배포 확인 후 배포 초안을 검토해 게시한다. 채널별 유입 세션과 참여를 비교한다.
- 인기나 CPC, 수익은 측정 근거 없이 추정하지 않는다. 돈이 되는 주제라는 이유만으로
  블로그 전문 분야와 무관한 의료·금융·연예 기사로 확장하지 않는다.

## 평가와 다음 결정

측정 기간은 완결된 28일 구간으로 고정한다. 첫 기준선과 보고서는 비공개 로컬
`.growth-state/`에 보관하며 공개 저장소와 사이트 빌드에 넣지 않는다.

- 검색: Search Console 전체 클릭·노출, 실제 질문별 클릭, 제목 수정 글의 CTR.
- 방문: GA4 자연검색 세션, 한국 자연검색 세션, 배포 채널별 참여 세션.
- 읽기: book_open, book_complete 등 기존 이벤트의 실제 수집 여부를 확인하고 비교.
- 수익: AdSense 데이터가 확보되면 실제 수익·RPM과 생성 비용을 별도로 기록.

일주일 만의 작은 변동으로 승패를 판단하지 않는다. 노출 자체가 적으면 제목 실험의
결론을 보류한다. 수요가 확인된 질문에 자료를 보완하고, 방문도 참여도 없는 채널은
배포 방식 또는 대상 독자를 바꾼다. 검증된 결과를 얻기 전에는 발행량을 늘리지 않는다.

## 배포 초안 수동 생성

```bash
python tools/build_distribution_pack.py \
  --post _posts/2026-09-13-openai-launches-agents-api-in-public-beta-with-managed-codex-harness.md \
  --output .growth-state/distribution
```

출력은 JSON과 Markdown이다. `.growth-state`는 Git에서 제외한다. 외부 채널의 글쓰기나
메시지 전송은 별도의 명시적 게시 요청이 있을 때만 진행한다.
