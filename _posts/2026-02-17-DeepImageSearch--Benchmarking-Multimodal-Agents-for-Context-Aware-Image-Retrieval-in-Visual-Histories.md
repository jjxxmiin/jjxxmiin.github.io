---
layout: post
title: '사진 수만 장에서 나중에 다시 만난 사람을 찾을까: DeepImageSearch의 검색 비용과 오류 전파'
date: '2026-02-17'
categories: Tech
tags:
  - DeepImageSearch
  - DISBench
  - 이미지검색
  - 멀티모달에이전트
  - 장기시각메모리
math: true
summary: 단일 이미지 유사도를 넘어 여러 사건을 연결하는 DeepImageSearch가 어떤 도구와 메모리를 쓰며 어디서 실패하는지 분석합니다.
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.10809.png
  alt: Paper Thumbnail
---

“아침 회의 발표자가 오후 카페에서 누구와 있었나” 같은 질문은 한 번의 이미지 유사도 검색으로 풀기 어렵고, DeepImageSearch는 첫 사건을 찾은 뒤 그 단서로 다음 사건을 재검색합니다. 대신 검색·필터·검증 호출이 이어지므로 정확도 이득은 지연 시간, 도구 누락, 개인정보 범위와 함께 판단해야 합니다.

## 한 장을 찾는 검색과 사건을 잇는 검색은 다르다

CLIP 계열 검색은 각 이미지를 독립적으로 보고 텍스트와 가까운 순서로 반환합니다. “빨간 코트를 입은 사람”에는 적합하지만, 오전과 오후에 같은 사람이 등장했는지처럼 시간적 맥락이 답의 일부인 질문은 한 이미지에 모든 단서가 없습니다.

![Figure 1:Evolution of image retrieval paradigms.](/assets/img/papers/2602.10809/x1.png)
*직접 검색, 지식 기반 검색, 시각적 이력을 탐색하는 DeepImageSearch의 차이.*

DeepImageSearch는 검색을 다음과 같은 다단계 작업으로 바꿉니다.

1. 질문을 여러 조건으로 분해합니다.
2. 첫 이벤트의 후보 이미지를 검색합니다.
3. 인물·장소·시간 단서를 작업 메모리에 남깁니다.
4. 그 단서로 다른 이벤트를 다시 검색합니다.
5. 최종 후보가 모든 조건을 만족하는지 검증합니다.

이 구조에서는 첫 후보의 인물 식별이 틀리면 다음 검색 전체가 잘못된 방향으로 갈 수 있습니다. 추론 모델뿐 아니라 초기 검색기의 recall이 중요합니다.

## DISBench는 사건 안과 사건 사이를 나눠 묻는다

DISBench에는 두 유형의 질의가 있습니다.

![Figure 2:Two query types in DISBench.](/assets/img/papers/2602.10809/x2.png)
*하나의 이벤트를 좁히는 intra-event와 여러 이벤트를 잇는 inter-event 질의.*

- **Intra-event**: 공원에서 요가한 사람 중 파란 매트를 사용한 사람처럼 한 사건 내부의 속성을 조합합니다.
- **Inter-event**: 오전 마트에서 본 인물이 저녁 식당에도 등장했는지처럼 여러 사건을 연결합니다.

데이터는 VLM이 이미지의 인물·행동·장소 속성을 추출하고, 이를 memory graph로 조직한 뒤 random walk로 관계 경로와 질문 초안을 만드는 반자동 방식입니다. 마지막에는 사람이 질문의 논리와 답을 검증합니다.

![Figure 3:Semi-automated data construction pipeline.](/assets/img/papers/2602.10809/x3.png)
*속성 추출, memory graph, random walk, 사람 검증으로 이어지는 구축 과정.*

이 방식은 관계가 명확한 평가 문제를 만들기 좋지만, 실제 사진첩의 누락된 시간 정보, 흔들린 사진, 비슷한 얼굴과 우연한 동시 등장까지 그대로 재현한다는 뜻은 아닙니다.

## 에이전트의 성능은 도구와 두 메모리에 묶인다

프레임워크는 Search, Filter, Verify처럼 세분화된 도구와 ReAct 방식의 계획을 사용합니다. 작업 메모리는 현재 가설과 단서를 유지하고, 장기 메모리는 전체 visual history를 참조합니다. 첫 결과를 보고 다음 query를 바꾸는 점이 single-turn retrieval과 다릅니다.

![Figure 4:Dataset statistics of DISBench.](/assets/img/papers/2602.10809/x4.png)
*DISBench의 질의 유형과 대상 이미지 테마 분포.*

평가에는 GPT-4o, Gemini-1.5-Pro와 LLaVA 계열 모델이 언급됩니다. 같은 reasoning model이라도 제공된 검색 엔진과 필터가 중요한 인물을 후보군에서 빼면 정답에 도달할 수 없습니다. 반대로 검색 결과가 넓으면 모델은 더 많은 이미지를 비교하느라 토큰과 시간이 늘어납니다.

실패를 분석할 때는 최종 정답 하나보다 단계를 나눠야 합니다.

| 단계 | 확인할 실패 |
|---|---|
| 초기 검색 | 정답 사건이 후보에 포함되지 않음 |
| 속성 추출 | 인물·행동·장소를 잘못 읽음 |
| 상태 유지 | 이전 사건의 단서를 잊거나 섞음 |
| 검증 | 조건 일부만 맞는 후보를 최종 선택 |
| 중단 | 충분한 근거가 없는데 답을 확정 |

## Test-time scaling은 어디까지 이득인가

연구는 Best-of-N과 Beam Search로 여러 탐색 경로를 시험합니다. 더 많은 reasoning step을 허용하면 single-turn보다 성공률이 오르지만, 일정 수준 이후 향상이 수렴하는 경향을 보입니다.

![Figure 5:Effect of test-time scaling with different strategies.](/assets/img/papers/2602.10809/x5.png)
*탐색 전략과 test-time compute 증가에 따른 성능 변화.*

이는 호출 횟수를 무작정 늘려도 초기 검색 누락이나 잘못된 visual attribute를 복구하지 못한다는 뜻입니다. 폐쇄형 모델이 오픈소스 LMM보다 복잡한 tool call과 상태 유지에서 앞섰다는 설명도 있지만, 이 글에는 모델별 절대 점수와 호출 비용이 없습니다.

실서비스에서는 질문당 최대 검색 횟수, 후보 이미지 수, 시간 제한을 정하고 다음을 함께 기록해야 합니다.

- Recall@K와 최종 정답률
- 평균 및 P95 도구 호출 수
- 이미지 재인코딩 수와 응답 지연
- 근거 이미지가 부족해 답변을 보류한 비율
- 같은 질문을 반복했을 때 경로의 안정성

## 사진 기억을 연결할수록 접근 권한도 연결된다

개인 사진, 로봇 카메라, CCTV는 시간과 장소를 잇는 순간 단일 이미지보다 민감한 정보를 드러낼 수 있습니다. 검색 에이전트가 장기 메모리 전체를 볼 수 있게 하기 전에 사용자·장소·기간별 접근 범위를 분리하고, 최종 답과 함께 어떤 이미지 경로를 사용했는지 남겨야 합니다.

DeepImageSearch가 적합한 경우는 질문의 답이 여러 사건에 흩어져 있고, 단순 top-K 검색의 실패가 반복되는 환경입니다. 한 이미지의 객체나 색만 찾으면 되는 작업에는 다단계 에이전트가 불필요한 비용일 수 있습니다. 도입 여부는 “맥락을 이해한다”는 문구보다, 정답이 빠진 후보를 얼마나 복구하고 그 과정의 근거를 얼마나 감사할 수 있는지로 결정해야 합니다.

[Original Paper Link](https://huggingface.co/papers/2602.10809)
