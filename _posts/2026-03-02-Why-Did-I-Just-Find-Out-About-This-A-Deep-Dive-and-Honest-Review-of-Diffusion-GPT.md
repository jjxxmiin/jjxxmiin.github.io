---
layout: post
title: '이미지 생성 모델이 너무 많다면? Diffusion-GPT 라우터의 선택 기준'
date: '2026-03-02 18:49:10'
categories: Tech
tags:
  - 디퓨전모델
  - 이미지생성
  - 튜토리얼
  - 파인튜닝
summary: Diffusion-GPT가 프롬프트를 분석해 여러 전문 디퓨전 모델 중 하나를 고르는 네 단계와 라우팅 지연·오선택·모델 로딩 비용을 짚습니다.
description: "Diffusion-GPT가 LLM·Tree-of-Thought·Advantage Database로 specialist diffusion model을 routing하는 원리, catalog drift·cold start·오선택과 fallback 비용을 설명합니다."
faq:
  - question: "Diffusion-GPT는 새로운 image generator인가요?"
    answer: "직접 생성하는 foundation model보다 prompt를 분석해 catalog의 existing specialist 중 하나를 고르는 router이며 최종 품질은 선택 model에도 의존합니다."
  - question: "Training-free이면 새 model을 등록만 하면 되나요?"
    answer: "Generator 전체 재학습은 피하지만 model card·domain·resource 정보를 catalog에 넣고 representative prompt의 human preference와 routing regression을 갱신해야 합니다."
  - question: "Router가 틀리면 어떤 fallback이 필요한가요?"
    answer: "Confidence가 낮거나 top candidates 차이가 작으면 default model·user 선택 또는 두 후보 preview로 전환하고 routing·load·generation 실패를 구분해야 합니다."
github_url: https://github.com/HKUNLP/diffusion-gpt
image:
  path: https://opengraph.githubassets.com/1/HKUNLP/diffusion-gpt
  alt: "HKUNLP/diffusion-gpt GitHub 저장소 대표 이미지"
---

모델을 매번 사람이 바꿀 필요는 없습니다. Diffusion-GPT는 LLM이 프롬프트의 대상과 스타일을 해석하고, 인간 선호 기록을 참고해 모델 풀에서 적합한 디퓨전 모델 하나를 고르는 라우팅 프레임워크입니다. 다만 catalog coverage, routing 오선택과 model cold start가 single-model baseline보다 나은지는 end-to-end 품질·latency·cost로 확인해야 합니다.

[논문](https://arxiv.org/abs/2401.10061)은 모든 요청을 하나의 범용 모델로 처리하는 대신 이미 존재하는 도메인별 전문가를 조합합니다. 핵심 경쟁력은 새 이미지를 직접 그리는 기초 모델보다 어떤 모델에 작업을 맡길지 결정하는 앞단에 있습니다.

## 선택은 네 단계를 거친다

첫 단계에서 LLM이 사용자 프롬프트를 피사체, 장면, 스타일 같은 의미 단위로 분석합니다. 단순히 “anime”라는 단어가 있는지 보는 규칙보다 문맥을 읽기 위한 과정입니다.

두 번째 단계는 Tree-of-Thought 검색입니다. 한 후보를 바로 확정하지 않고 여러 선택 경로를 펼쳐 각 전문 모델이 요청에 맞는 이유를 비교합니다.

세 번째 단계에서는 Advantage Database의 인간 선호 피드백을 결합해 후보를 다시 평가합니다. 과거에 비슷한 프롬프트에서 어떤 모델의 결과가 선호됐는지 반영한 뒤 하나를 고릅니다. 마지막으로 선택된 모델이 실제 이미지를 생성합니다.

이 구조는 라우터, 모델 카탈로그, 선호 데이터, 생성 실행기가 모두 있어야 완성됩니다. 원문에 적힌 Python 클래스는 이 흐름을 설명하려고 만든 의사코드이며 실제 저장소 API나 완전한 실행 절차가 아닙니다.

## Training-free가 뜻하는 정확한 범위

Diffusion-GPT는 전문가 모델을 하나의 거대한 모델로 다시 파인튜닝하지 않고 모델 풀에 추가하는 plug-and-play 방식을 내세웁니다. 이 의미에서 새 모델을 편입할 때 전체 생성기를 재학습하지 않는 training-free 라우팅입니다.

그렇다고 아무 모델 파일이나 넣으면 특성을 자동으로 완벽히 알아낸다는 뜻은 아닙니다. 카탈로그에 모델 설명과 적용 범위를 넣고, Advantage Database가 새 모델을 비교할 피드백을 확보해야 합니다. 모델이 늘수록 선택지가 좋아질 수도 있지만 비슷한 후보가 많아져 라우팅이 어려워질 수도 있습니다.

논문은 SD 1.5와 SDXL 계열 비교에서 Aesthetic Score와 ImageReward가 개선된 결과를 제시합니다. 이는 해당 모델 풀과 평가 프롬프트에서 올바른 전문가 선택이 단일 모델보다 유리할 수 있다는 근거입니다.

## 서비스에서는 생성 전 비용이 생긴다

라우터가 내리는 결정은 무료가 아닙니다. 매 요청마다 LLM이 프롬프트를 분석하고 ToT로 후보를 탐색하면 첫 이미지가 나오기 전 지연과 호출 비용이 추가됩니다. 같은 의도의 요청을 묶어 캐시할 수 있지만, 표현이 조금만 달라져도 기존 결정을 재사용해도 되는지 확인해야 합니다.

더 큰 병목은 모델 가중치입니다. 수십 개 모델을 GPU 메모리에 모두 올릴 수 없다면 선택 뒤 스토리지에서 불러오는 cold start가 생깁니다. 라우팅 정확도가 높아도 모델 교체 시간이 길면 사용자 경험은 나빠질 수 있습니다.

따라서 평가에는 이미지 점수 외에도 다음 항목이 필요합니다.

- 라우팅 결정 시간
- 모델 교체와 첫 이미지까지 걸린 시간
- 라우터가 선택한 모델과 사람 선택의 일치율
- 상위 두 후보 결과의 실제 선호 차이
- 모델별 메모리 점유와 동시 요청 처리량

## 언제 라우터가 단일 모델보다 나은가

실사, 애니메이션, 건축처럼 요구가 분명히 갈리고 각 분야의 전문가 모델을 이미 운영한다면 라우터의 이점이 큽니다. 반대로 요청 범위가 좁거나 모델 교체 비용이 높은 서비스라면 잘 조정한 단일 모델이 더 단순하고 빠를 수 있습니다.

가장 안전한 도입은 모든 요청을 즉시 자동 라우팅하는 것이 아닙니다. 기존 로그를 대상으로 라우터의 추천만 기록하고, 사람이 고른 모델과 결과 품질을 비교한 뒤 높은 확신 구간부터 자동화하는 것입니다. 저장소는 [GitHub](https://github.com/HKUNLP/diffusion-gpt)에서 확인할 수 있으며, 글의 구조와 API는 발표 시점 스냅샷으로 봐야 합니다.

## Model Catalog에는 어떤 정보가 있어야 하나

이름과 style 설명만 있으면 LLM이 marketing 문구로 model을 고를 수 있습니다. Supported subject·style, resolution·license, inference memory·latency, safety restriction와 evaluation version을 구조화합니다.

| Catalog field | Routing에 필요한 이유 |
|---|---|
| Domain·negative cases | 잘하는 영역과 failure 범위 |
| Prompt format | trigger word 의존과 입력 변환 |
| Hardware·precision | load 가능 여부와 latency |
| License·usage scope | commercial·redistribution 제한 |
| Eval date·version | weight update 뒤 stale score 방지 |

Model file이나 configuration이 바뀌면 이전 preference를 그대로 재사용하지 않습니다. Catalog entry와 weight hash를 연결하고 representative prompt를 다시 평가합니다.

## Routing Accuracy는 어떻게 측정할까

Prompt마다 전문가가 고른 one-hot 정답을 전제하기보다 candidate별 실제 image를 blind preference로 비교합니다. Router top-1, top-2와 default model result를 같은 seed budget으로 생성하고 human·task metric을 봅니다. 두 model 차이가 거의 없는 case는 오선택 cost가 낮습니다.

Prompt를 실사·anime·text rendering·spatial relation과 ambiguous multi-style로 나눕니다. Catalog에 없는 domain에서는 자신 있게 틀린 model을 고르지 않고 out-of-catalog를 감지하는지 봅니다. Wording을 조금 바꿨을 때 route가 불안정하게 뒤집히는지도 기록합니다.

## Cold Start와 Concurrency를 어떻게 계산할까

Router decision time, storage에서 weight load, warm-up와 image generation을 분리합니다. Popular model을 resident하게 두고 long-tail model을 on-demand load할 수 있지만 concurrent request가 다른 model로 분산되면 GPU thrashing이 생길 수 있습니다.

Cache hit rate, model switch 수, first-image p95와 GPU memory를 기록합니다. Routing quality가 조금 좋아도 user latency가 크게 늘면 top candidates를 same resident pool로 제한하거나 single default가 나을 수 있습니다.

## Human Preference Database가 낡으면 무엇이 생기나

과거 preference가 특정 aesthetic과 user group에 치우치면 새 request에서도 같은 model을 과추천할 수 있습니다. Domain·time·annotator segment를 기록하고 pair 수가 적은 route의 confidence를 낮춥니다. Business KPI와 general aesthetic score를 섞지 않습니다.

Feedback loop에서 router가 고른 model만 노출하면 다른 candidate data가 줄어 self-reinforcement가 생길 수 있습니다. 작은 exploration bucket으로 alternative를 평가하되 user consent와 생성 비용을 관리합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/HKUNLP/diffusion-gpt)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [PhotoDoodle은 30~50쌍으로 스타일을 배울까: 배경 보존 구조와 실행 코드 함정]({% post_url 2025-03-03-PhotoDoodle %}) — PhotoDoodle의 OmniEditor 사전학습과 EditLoRA 미세조정, positional encoding cloning이 배경을 보존하는 방식, 비교·ablation 결과와 예제 코드의 해상도 주의점을 정리합니다.
- [Diffusion 학습 코드는 왜 원본 이미지 대신 Noise를 맞출까?]({% post_url 2023-03-06-StableDiffusion %}) — DDPM 코드의 perturb_x·get_losses·sample 흐름을 따라 정답 noise를 예측하는 학습과 역순 denoising 추론을 연결하고, Stable Diffusion·conditioning의 위치를 설명합니다.
- [Fooocus가 Stable Diffusion WebUI보다 쉬운 이유: Linux 설치부터 Preset 선택까지]({% post_url 2024-02-13-Fooocus %}) — 복잡한 확장 설정보다 prompt와 image 선택에 집중하려는 사용자를 위해 Fooocus의 Linux 설치 흐름, anime·realistic preset, input image와 advanced 기능을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Diffusion-GPT는 새로운 image generator인가요?

직접 생성하는 foundation model보다 prompt를 분석해 catalog의 existing specialist 중 하나를 고르는 router이며 최종 품질은 선택 model에도 의존합니다.

### Training-free이면 새 model을 등록만 하면 되나요?

Generator 전체 재학습은 피하지만 model card·domain·resource 정보를 catalog에 넣고 representative prompt의 human preference와 routing regression을 갱신해야 합니다.

### Router가 틀리면 어떤 fallback이 필요한가요?

Confidence가 낮거나 top candidates 차이가 작으면 default model·user 선택 또는 두 후보 preview로 전환하고 routing·load·generation 실패를 구분해야 합니다.
