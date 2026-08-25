---
layout: post
title:  "모델 경량화, Pruning·Quantization·Distillation 중 무엇부터 해야 할까?"
summary: "정확도만 보고 경량화 기법을 고르면 실제 배포 단계에서 다시 막힙니다. 지연시간·메모리·모델 크기를 먼저 정하고 프루닝, 양자화, 증류를 고르는 실전 순서를 설명합니다."
image:
  path: /assets/img/thumb/ModelCompression.jpg
  alt: 2021 Efficient Deep Learning 톺아보기 대표 이미지
date:   2021-07-19 09:10 -0400
categories: Paper
tags:
  - 경량화
  - 논문리뷰
  - 파인튜닝
  - 온디바이스AI
  - MLOps
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
