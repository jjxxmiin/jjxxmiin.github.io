---
layout: post
title: '시각 토큰을 줄였더니 환각이 늘었다면: AgilePruner의 선택 기준'
date: '2026-03-08 20:19:35'
categories: Tech
tags:
  - 환각문제
  - 경량화
  - 튜토리얼
  - 트랜스포머
  - 문서AI
math: true
summary: 'AgilePruner가 어텐션·다양성 기반 가지치기를 유효 랭크와 엔트로피로 비교하고 입력별로 전환하는 이유와 적용 한계를 설명합니다.'
description: 'AgilePruner가 attention·diversity pruning을 entropy로 선택하는 원리와, visual token 절감이 작은 정보·환각·지연에 미치는 영향을 검증하는 법을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.01236.png
  alt: "시각 토큰을 줄였더니 환각이 늘었다면: AgilePruner의 선택 기준 논문 대표 이미지"
faq:
  - question: '시각 토큰을 절반으로 줄이면 지연도 절반이 되나요?'
    answer: 'Vision encoding·language decoding·memory 이동과 pruning 자체 비용이 남으므로 같은 비율로 줄지 않습니다. End-to-end first token·generation latency와 peak memory를 실제 runtime에서 측정해야 합니다.'
  - question: 'Attention이 낮은 토큰은 안전하게 버려도 되나요?'
    answer: '작은 글자·드문 물체·여러 영역 비교에서는 초기 attention이 낮아도 정답에 필요할 수 있습니다. 중요 영역 누락과 객체 환각을 task별로 확인해야 합니다.'
  - question: '논문의 entropy threshold를 그대로 사용해도 되나요?'
    answer: 'Model·layer·해상도와 문서·자연 이미지 분포가 달라지면 entropy 범위도 달라집니다. 자체 validation에서 threshold별 품질·비용과 경계 불안정을 다시 보정해야 합니다.'
---

AgilePruner의 답은 모든 이미지에 같은 토큰 가지치기를 적용하지 말고, 어텐션 엔트로피로 입력 복잡도를 가늠해 어텐션 기반과 다양성 기반 방식을 바꾸라는 것입니다. 속도를 얻기 위해 토큰을 줄이더라도 환각과 세부 정보 손실을 함께 측정해야 합니다.

## 두 가지 가지치기는 잃는 정보가 다르다

대형 비전·언어 모델은 한 장의 이미지를 많은 시각 토큰으로 바꿉니다. 토큰 수를 줄이면 메모리와 계산량을 아낄 수 있지만, 어떤 토큰을 버리느냐에 따라 답의 근거도 달라집니다.

어텐션 기반 방식은 모델이 중요하게 본 토큰을 남깁니다. 배경이 단순하고 관심 대상이 분명할 때는 효율적일 수 있지만, 작은 물체나 여러 영역을 함께 비교해야 하는 화면에서는 낮은 어텐션이 곧 불필요함을 뜻하지 않을 수 있습니다. 다양성 기반 방식은 서로 비슷한 표현을 줄이고 다른 특징을 남기려 하지만, 실제로 필요한 의미 다양성을 보존하는지는 별도 검증이 필요합니다.

## 유효 랭크가 드러낸 직관의 빈틈

원문에서 AgilePruner는 피처 다양성을 유효 랭크, 즉 effective rank로 살핍니다. 분석 결과는 다양성 지향 방법이 이름과 달리 기대만큼 다양한 표현을 남기지 못할 수 있음을 지적합니다. CHAIR를 이용한 환각 평가에서는 보존된 토큰의 수뿐 아니라 잘못 남은 특징이 존재하지 않는 물체를 답하게 만드는지도 중요하게 봅니다.

이 결과를 “다양성 방식은 항상 나쁘다”로 읽으면 안 됩니다. 단순한 장면과 복잡한 장면에서 필요한 정보 구조가 다르다는 것이 연구의 출발점입니다. 같은 유지 비율에서도 입력에 따라 어텐션 집중도와 피처 분포가 달라지므로 단일 규칙의 평균 점수만으로 운영 설정을 고르기 어렵습니다.

## 엔트로피로 입력별 경로를 고른다

AgilePruner는 어텐션 엔트로피를 가벼운 라우팅 신호로 사용합니다. 어텐션이 일부 영역에 모여 엔트로피가 낮은 단순 입력은 어텐션 기반 가지치기로 보내고, 관심 영역이 넓게 퍼진 복잡한 입력은 다양성 보존을 더 고려하는 방식으로 보냅니다. 모든 이미지에 무거운 분석을 추가하지 않고 이미 계산되는 신호로 선택한다는 점이 실용적인 아이디어입니다.

적용할 때는 엔트로피 임계값을 논문의 숫자 그대로 옮기기보다 자신의 모델, 비전 인코더, 해상도와 데이터에 맞춰 다시 정해야 합니다. 문서 화면, 자연 이미지, 차트처럼 분포가 다른 자료를 섞으면 같은 엔트로피가 같은 난도를 뜻하지 않을 수 있습니다.

## 적용 전에는 세 축을 함께 재야 한다

[프로젝트 페이지](https://cvsp-lab.github.io/AgilePruner)와 [논문 페이지](https://huggingface.co/papers/2603.01236)를 출발점으로 삼되, 실제 통합에서는 다음을 같은 실험에서 기록해야 합니다.

- 토큰 유지율과 GPU 메모리, 첫 토큰까지의 지연
- 일반 정확도뿐 아니라 객체 환각과 작은 세부 정보 누락
- 낮은 엔트로피와 높은 엔트로피 구간별 성능
- 가지치기를 끈 기준선과 각 단일 방식, 적응형 방식의 차이
- 임계값 주변에서 라우팅이 자주 바뀌는지 여부

이 연구는 모델 전체를 교체하는 완성형 배포 절차가 아니라 시각 토큰 선택 정책에 관한 연구입니다. 특정 LVLM에 연결하는 코드, 지원 레이어와 캐시 구조, 재학습 필요 여부는 사용 환경에서 따로 확인해야 하며, 절감률만 보고 정확도 저하를 숨기지 않아야 합니다.

## 토큰 수와 실제 비용은 어떻게 연결되나

Visual token이 줄면 cross-attention과 KV cache 일부 비용은 줄 수 있지만 vision encoder가 이미 전체 image를 처리한 뒤 pruning한다면 앞단 계산은 그대로입니다. Pruning score와 routing 계산도 추가됩니다. 단계별 profile로 어느 연산이 줄었는지 확인해야 합니다.

첫 token 지연과 이후 text generation의 영향도 다릅니다. Image token은 prompt processing에 크게 작용하지만 긴 답변은 language decoding이 대부분을 차지할 수 있습니다. 짧은 VQA와 긴 설명을 같은 절감률로 계산하지 않습니다.

Memory 절감은 batch·concurrency 증가로 이어질 때 운영 가치가 커집니다. 단일 request의 peak만 보지 말고 목표 동시성에서 OOM·queue와 throughput을 측정합니다. Token 수를 줄였는데 kernel shape가 hardware에 비효율적이면 속도 이득이 작을 수도 있습니다.

## 복잡도 신호는 어떤 입력에서 틀릴까

배경이 단순한 영수증은 attention entropy가 낮아도 작은 합계 숫자 하나가 매우 중요합니다. 복잡한 자연 장면은 entropy가 높지만 질문은 큰 빨간 자동차 하나만 요구할 수 있습니다. Image 전체 복잡도와 질문에 필요한 정보 복잡도를 구분해야 합니다.

Entropy는 어떤 layer와 head에서 계산하는지에 따라 달라집니다. 초기 layer는 texture에 넓게 반응하고 깊은 layer는 semantic object에 집중할 수 있습니다. 논문 설정과 자신의 model 위치를 맞추고 head aggregation이 중요한 소수 head를 평균으로 숨기지 않는지 봅니다.

Threshold 근처 입력은 작은 noise로 pruning 경로가 바뀔 수 있습니다. Resize·crop·JPEG 변화에서 routing과 answer가 안정적인지 확인하고, 불확실 구간에서는 더 보수적인 유지율을 선택할 수 있습니다.

## 환각과 누락은 어떻게 분리해 평가할까

객체 질문에서는 실제로 없는 object를 추가한 경우와 존재하는 작은 object를 놓친 경우를 따로 셉니다. Token pruning이 배경 근거를 버려 언어 prior에 의존하면 hallucination이 늘 수 있습니다. CHAIR 외에도 제품의 class와 질문 유형에 맞는 근거 검사를 사용합니다.

문서·차트에서는 OCR 문자와 표 cell·axis label을 영역별로 평가합니다. 전체 answer accuracy가 같아도 중요 숫자의 근거 token이 사라져 reasoning이 불안정할 수 있습니다. 모델이 어떤 region을 남겼는지 overlay로 저장하고 오류와 연결합니다.

사람 평가에는 pruning off 결과를 숨기고 두 답의 근거 충실도와 세부 누락을 비교합니다. 말투나 길이 차이가 판단을 흐리지 않게 final answer 형식을 맞춥니다.

## 유지율과 threshold는 어떻게 고를까

Pruning off, attention-only, diversity-only, adaptive의 네 기준을 동일 input·runtime으로 측정합니다. 유지율을 여러 단계로 낮춰 품질-지연 curve를 만들고 중요한 task의 최소 품질을 만족하는 점을 고릅니다. 평균 accuracy가 아니라 worst slice를 제약으로 둘 수 있습니다.

문서와 자연 이미지의 entropy 분포가 다르면 domain별 threshold 또는 router가 필요할 수 있습니다. 다만 규칙이 많아질수록 운영과 drift 감지가 어려워집니다. 가장 단순한 설정이 충분한지 먼저 확인하고 adaptive 경로가 실제로 단일 방식보다 이득인지 ablation합니다.

## 배포 후 무엇을 감시할까

요청별 domain, entropy, 선택 방법, 유지 token, latency와 confidence를 표본 log에 남깁니다. 원본 image는 개인정보 때문에 보존하지 않더라도 안전한 feature 통계와 사용자 오류 feedback을 연결할 수 있습니다. 분포가 바뀌면 threshold를 다시 보정합니다.

모델·vision encoder·quantization을 바꾸면 attention 분포도 변할 수 있으므로 pruning 설정을 독립적으로 승계하지 않습니다. Canary에서 pruning off fallback과 비교하고 품질 회귀가 감지되면 adaptive 정책을 끌 수 있어야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [이미지에 없는 물체를 말할 때: NoLan의 언어 사전확률 억제]({% post_url 2026-02-28-NoLan--Mitigating-Object-Hallucinations-in-Large-Vision-Language-Models-via-Dynamic-Suppression-of-Language-Priors %}) — NoLan이 이미지+텍스트 로짓에서 텍스트 전용 편향을 동적으로 억제하는 방식, POPE 개선과 두 번의 forward 비용·오탐 가능성을 정리합니다.
- [Claude for Legal이 법률 환각을 끝낼까: 출처·권한·승인 설계]({% post_url 2026-05-18-The-End-of-Paying-Settlements-for-Hallucinations-A-Developers-Deep-Dive-into-Claude-for-Legal-and-Its-True-Impact %}) — Claude for Legal의 도구 연결 구조를 법률 검색, 문서 수정, 외부 전송으로 나눠 보고 환각·권한·감사 위험을 통제하는 기준을 정리합니다.
- [물리 문제에서 그림 한 줄을 놓치면? P1-VL의 시각·논리 학습]({% post_url 2026-02-11-P1-VL--Bridging-Visual-Perception-and-Scientific-Reasoning-in-Physics-Olympiads %}) — P1-VL이 올림피아드 물리의 도식 정보를 추론과 연결하는 커리큘럼 RL, PhysicsMinions 검증 구조와 벤치마크 해석법을 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 시각 토큰을 절반으로 줄이면 지연도 절반이 되나요?

Vision encoding·language decoding·memory 이동과 pruning 자체 비용이 남으므로 같은 비율로 줄지 않습니다. End-to-end first token·generation latency와 peak memory를 실제 runtime에서 측정해야 합니다.

### Attention이 낮은 토큰은 안전하게 버려도 되나요?

작은 글자·드문 물체·여러 영역 비교에서는 초기 attention이 낮아도 정답에 필요할 수 있습니다. 중요 영역 누락과 객체 환각을 task별로 확인해야 합니다.

### 논문의 entropy threshold를 그대로 사용해도 되나요?

Model·layer·해상도와 문서·자연 이미지 분포가 달라지면 entropy 범위도 달라집니다. 자체 validation에서 threshold별 품질·비용과 경계 불안정을 다시 보정해야 합니다.
