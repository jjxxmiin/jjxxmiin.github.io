---
layout: post
title:  "모델 경량화, Pruning·Quantization·Distillation 중 무엇부터 해야 할까?"
summary: "정확도만 보고 경량화 기법을 고르면 실제 배포 단계에서 다시 막힙니다. 지연시간·메모리·모델 크기를 먼저 정하고 프루닝, 양자화, 증류를 고르는 실전 순서를 설명합니다."
description: "모델 경량화를 pruning·quantization·distillation로 나눠 지연·peak memory·파일 크기 병목과 재학습 가능성, 실제 장치 측정으로 선택하는 방법입니다."
image:
  path: /assets/img/thumb/ModelCompression.jpg
  alt: 2021 Efficient Deep Learning 톺아보기 대표 이미지
date:   2021-07-19 09:10 -0400
categories: Paper
tags:
  - 경량화
  - 튜토리얼
  - 파이썬
  - 반도체
  - 파인튜닝
faq:
  - question: "모델 파일을 줄이면 실제 추론도 항상 빨라지나요?"
    answer: "아닙니다. 파일 크기, FLOPs, peak memory와 실제 latency는 다른 지표입니다. Runtime과 hardware가 줄인 weight·연산을 효율적으로 지원하는지 장치에서 측정해야 합니다."
  - question: "Pruning과 quantization은 무엇을 다르게 줄이나요?"
    answer: "Pruning은 weight·channel·구조 일부를 제거하는 방향이고, quantization은 수와 연산의 정밀도를 낮추는 방향입니다. 지원되는 형태와 재학습 가능성을 함께 봐야 합니다."
  - question: "Distillation은 언제 검토할 수 있나요?"
    answer: "작은 student를 다시 학습할 데이터와 더 큰 teacher의 출력을 사용할 수 있을 때 비교할 수 있습니다. Teacher 품질과 student 배포 비용을 함께 평가해야 합니다."
math: true
---

모델 경량화는 가장 유명한 기법부터 적용하는 일이 아니라, 서비스가 감당할 지연시간·메모리·저장 공간과 허용 가능한 정확도 하락을 먼저 수치로 정하는 일에서 시작합니다.

이 글은 [Efficient Deep Learning: A Survey on Making Deep Learning Models Smaller, Faster, and Better](https://arxiv.org/abs/2106.08962)에 정리된 선택지를 실제 의사결정 순서로 다시 묶었습니다. 한 방법이 모든 지표를 동시에 최적화하지는 않으므로 결과는 하나의 점수가 아니라 정확도와 비용 사이의 Pareto frontier로 봐야 합니다.

## 먼저 병목과 측정 단계를 고릅니다

“모델이 무겁다”는 말에는 서로 다른 문제가 섞여 있습니다. 다운로드 크기가 문제라면 파라미터 표현과 압축률이 중요하고, 모바일 메모리가 부족하다면 실행 중 activation까지 봐야 합니다. 응답 시간이 길다면 실제 대상 하드웨어에서 지연시간을 재야 하며, 학습비가 문제라면 추론 전용 최적화만으로는 해결되지 않습니다.

따라서 비교표에는 최소한 정확도, 모델 크기, peak memory, 처리량, 단일 요청 지연시간을 함께 적는 편이 좋습니다. FLOPs가 줄어도 하드웨어와 라이브러리가 희소 연산을 빠르게 처리하지 못하면 실제 시간은 줄지 않을 수 있습니다. 경량화 전후를 같은 장치와 같은 입력 크기에서 측정해야 하는 이유입니다.

## Pruning과 Quantization은 줄이는 대상이 다릅니다

Pruning은 중요도가 낮은 가중치나 구조를 제거합니다. 개별 가중치를 지우는 unstructured pruning은 희소도가 높아도 일반 하드웨어에서 속도 이득이 작을 수 있습니다. 반면 채널이나 필터를 통째로 지우는 structured pruning은 밀집 연산 형태를 유지해 배포 이득을 얻기 쉽지만, 정확도 손실이 더 클 수 있습니다.

초기의 Optimal Brain Damage는 Hessian 대각 성분으로 가중치 민감도를 추정했습니다. 실무에서는 어떤 중요도 기준을 쓰는지만큼 pruning 일정, 재학습, 제거된 연결의 regrowth 여부가 결과에 영향을 줍니다. Lottery Ticket 관점도 흥미롭지만, 작은 부분망을 찾는 비용까지 포함해야 합니다.

Quantization은 보통 32비트 부동소수점 값을 8비트 정수처럼 더 작은 표현으로 바꿉니다. 실수 범위를 scale과 zero point로 정수 범위에 대응시키며, 가중치만 바꾸는 경우와 activation까지 바꾸는 경우를 구분해야 합니다. 학습 완료 후 적용하는 PTQ는 빠르지만 정확도 손실이 생길 수 있고, quantization-aware training은 양자화 오차를 학습 중 반영해 정확도를 회복하는 대신 재학습 비용이 듭니다. 원문 조사에서는 8비트 QAT가 모델 디스크 크기를 약 4분의 1로 줄이고 1.64배 빠르게 하면서 정확도를 가깝게 유지한 사례를 소개하지만, 이 숫자를 다른 모델과 장치에 그대로 보장값으로 쓰면 안 됩니다.

## Distillation과 효율적 구조는 다시 학습할 수 있을 때 유리합니다

Knowledge distillation은 큰 teacher가 만든 soft label과 정답 hard label을 함께 사용해 작은 student를 학습합니다. temperature로 완화한 출력 분포에는 정답 클래스 외의 관계도 담깁니다. DistilBERT 사례는 원래 성능의 97%를 유지하면서 크기를 40% 줄이고 60% 빠르게 했지만, 이 역시 특정 모델과 평가 설정의 결과입니다.

새 모델을 설계할 수 있다면 depthwise separable convolution처럼 처음부터 연산량이 작은 구조가 유리할 수 있습니다. 데이터 증강과 self-supervised learning은 압축 기법 자체라기보다 작은 모델의 일반화 성능을 보완합니다. HPO와 NAS는 좋은 조합을 자동으로 찾지만, 탐색 비용까지 총비용에 포함해야 합니다. Grid·random search, Bayesian optimization, PBT, Successive Halving과 Hyperband는 예산 배분 방식이 서로 다르므로 “자동”이라는 이유만으로 싸지는 않습니다.

## 배포 도구보다 먼저 결정할 체크리스트

TensorFlow Lite와 TensorFlow Micro, TensorFlow.js, XLA, PyTorch JIT와 TorchScript는 모델을 대상 런타임에 맞추는 도구입니다. GPU·TPU·Edge TPU·Jetson 같은 하드웨어 선택도 최종 성능을 바꿉니다. 하지만 변환 도구를 먼저 정하면 지원되지 않는 연산이나 예상 밖의 메모리 사용 때문에 모델 설계를 되돌릴 수 있습니다.

실무 순서는 다음처럼 잡을 수 있습니다. 기준 모델을 실제 장치에서 측정하고, 재학습 가능 여부를 정한 뒤, 저장 공간이 병목이면 quantization을 먼저 시험합니다. 일반 가속기에서 지연시간이 병목이면 structured pruning이나 효율적 architecture를 검토하고, 작은 모델을 다시 학습할 데이터와 teacher가 있으면 distillation을 비교합니다. 마지막에 변환된 모델의 정확도와 실제 지연시간을 다시 측정합니다.

경량화는 “작게 만든 뒤 정확도를 확인하는” 단선 작업이 아닙니다. 모델을 키워 품질을 확보한 뒤 줄이는 전략과, 작은 모델을 줄이면서 보완하는 전략 모두 가능합니다. 중요한 한계는 논문의 압축률이나 FLOPs 감소가 내 서비스의 체감 속도를 대신 증명하지 않는다는 점입니다.

## 기준 모델에서 어떤 숫자를 먼저 남기나

배포와 같은 입력 shape·batch·runtime·장치에서 warm-up 뒤 latency를 잽니다. Model load와 첫 실행, 반복 추론, 전처리·후처리 포함 전체 시간을 구분합니다. Weight 파일 크기와 peak memory, 핵심 validation 지표도 같은 표에 둡니다.

오류는 전체 평균만 보지 않고 class·입력 조건별로 나눕니다. 작은 물체나 경계 sample에서만 경량화 손실이 커질 수 있습니다. 기준 model의 실패와 압축 뒤 새로 생긴 실패를 구분할 fixture를 만듭니다.

## Pruning 결과가 실제로 이득인지 확인하는 법

Weight 일부가 0이 됐다는 사실과 runtime이 연산을 건너뛴다는 사실은 다릅니다. Unstructured sparsity가 저장은 줄여도 사용하는 kernel이 dense 계산을 그대로 하면 latency가 줄지 않을 수 있습니다. 장치와 compiler가 지원하는 형태를 확인합니다.

Channel이나 block을 제거하는 structured pruning은 tensor shape와 다음 layer 입력도 바꿉니다. 제거 뒤 fine-tuning과 accuracy 회복을 측정하고, 변환 tool이 새 구조를 실제로 내보내는지 봅니다. Pruning mask만 남고 파일·graph가 그대로인지 확인합니다.

## Quantization에서 무엇이 깨질 수 있나

Weight와 activation의 값 범위가 낮은 정밀도 표현에 맞는지 보고 calibration 또는 재학습 조건을 구분합니다. 변환이 성공해도 지원되지 않는 operator가 다른 정밀도로 남거나 CPU fallback이 생기면 예상 latency가 나오지 않을 수 있습니다.

고정 fixture로 원본과 quantized output을 비교하고 최종 class·box가 바뀌는 sample을 모읍니다. 파일 크기 감소, peak memory와 실제 실행 시간을 각각 잽니다. 낮은 정밀도 형식이 포함됐다는 로그만으로 전체 model이 원하는 경로에서 동작한다고 단정하지 않습니다.

## Distillation 실험을 공정하게 만드는 법

Teacher와 student가 같은 input과 class 의미를 사용하고, 어떤 teacher output을 학습 신호로 쓰는지 명시합니다. Student를 label만으로 학습한 baseline과 distillation 결과를 같은 schedule에서 비교해야 teacher 신호의 이득을 볼 수 있습니다.

Teacher가 틀린 sample이나 편향을 student가 따라갈 수 있다는 한계도 봅니다. Student 정확도뿐 아니라 파일·latency·memory가 실제 목표를 만족하는지 확인합니다. 학습 때 teacher 비용은 배포에서 사라져도 재학습 운영 비용에는 남습니다.

## 여러 기법을 결합할 때의 순서

한 번에 pruning·quantization·distillation을 모두 적용하지 않습니다. 각 단계 artifact와 metric을 저장하고 어떤 변경에서 성능이 떨어졌는지 추적합니다. 결합 순서가 결과를 바꿀 수 있으므로 baseline과 한 기법 결과를 먼저 확보합니다.

변환 tool과 hardware를 마지막 확인으로 미루지 않습니다. 설계 초기에 target runtime이 지원하는 operator와 정밀도를 확인하되, tool 이름이 목적을 대신하게 하지 않습니다. 지원 조건과 병목 측정이 만나는 후보를 고릅니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [2026년 로컬 LLM 모델 비교 및 그래픽 카드 사양 추천 가이드]({% post_url 2026-08-24-2026-local-llm-model-comparison-and-gpu-specification-guide %}) — 컴퓨터에 직접 거대언어모델을 띄워 쓰려는 분들을 위해 Llama 3.1, Qwen 2.5, DeepSeek-R1-Distill 모델의 성능, 필요한 그래픽 카드 사양과 메모리 크기, 선택 기준을 명확하게 비교해 정리했습니다.
- [Meta Muse Glimmer 30B 로컬 에이전트: 4비트 메모리 조건과 도입 판단]({% post_url 2026-08-11-meta-releases-open-source-muse-glimmer-30b-model-for-consumer-gpus %}) — Meta가 2026년 8월 10일 소비자용 GPU 환경에 최적화된 300억 파라미터 오픈소스 모델 Muse Glimmer를 Apache 2.0 라이선스로 출시했습니다. 4비트 양자화를 적용해 메모리 점유율을 20GB RAM 이하로…
- [Apple Mac Studio M5 Ultra 공개: 512GB 메모리와 로컬 AI 활용 조건]({% post_url 2026-08-26-apple-unveils-mac-studio-with-m5-ultra-and-512gb-memory-for-local-ai %}) — Apple은 2026년 8월 25일 M5 Max 및 M5 Ultra 칩을 탑재한 신형 Mac Studio 데스크톱을 공식 발표했습니다. M5 Ultra 모델은 최대 512GB 통합 메모리와 1.2TB/s 메모리 대역폭을 갖추어 외부…
<!-- internal-links:end -->

## 자주 묻는 질문

### 모델 파일을 줄이면 실제 추론도 항상 빨라지나요?

아닙니다. 파일 크기, FLOPs, peak memory와 실제 latency는 다른 지표입니다. Runtime과 hardware가 줄인 weight·연산을 효율적으로 지원하는지 장치에서 측정해야 합니다.

### Pruning과 quantization은 무엇을 다르게 줄이나요?

Pruning은 weight·channel·구조 일부를 제거하는 방향이고, quantization은 수와 연산의 정밀도를 낮추는 방향입니다. 지원되는 형태와 재학습 가능성을 함께 봐야 합니다.

### Distillation은 언제 검토할 수 있나요?

작은 student를 다시 학습할 데이터와 더 큰 teacher의 출력을 사용할 수 있을 때 비교할 수 있습니다. Teacher 품질과 student 배포 비용을 함께 평가해야 합니다.
