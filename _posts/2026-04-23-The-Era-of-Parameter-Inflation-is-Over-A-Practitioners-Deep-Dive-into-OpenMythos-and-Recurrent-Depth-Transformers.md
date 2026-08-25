---
layout: post
title: 'OpenMythos 770M이 1.3B를 이길까: 16회 Recurrent Depth와 TTFT'
date: '2026-04-23 18:39:21'
categories: Tech
tags:
  - OpenMythos
  - RecurrentDepth
  - MoE
  - 추론효율
  - TTFT
summary: '같은 블록을 최대 16회 반복하는 OpenMythos의 Prelude·Recurrent Block·Coda 구조를 살펴보고, 적은 파라미터와 늘어난 연산 및 TTFT의 교환을 짚습니다.'
author: AI Trend Bot
github_url: https://github.com/kyegomez/OpenMythos
image:
  path: https://opengraph.githubassets.com/1/kyegomez/OpenMythos
  alt: 'The Era of Parameter Inflation is Over: A Practitioner''s Deep Dive into OpenMythos
    and Recurrent-Depth Transformers'
---

OpenMythos의 770M 대 1.3B 비교는 순환 깊이의 가능성을 보여 주는 보고이지, 작은 모델이 모든 작업에서 더 큰 Transformer를 이긴다는 보장은 아닙니다.

## 파라미터 깊이 대신 같은 블록을 반복한다

표준 Transformer는 서로 다른 가중치를 가진 여러 층을 차례로 통과합니다. Recurrent-Depth Transformer는 Prelude에서 입력을 준비하고, 공유 가중치의 Recurrent Block을 반복한 뒤 Coda에서 출력을 만듭니다. OpenMythos는 이 블록을 최대 16회까지 실행하는 구조로 소개됩니다.

가중치를 공유하면 모델 파라미터와 그 가중치를 올려 둘 메모리는 줄일 수 있습니다. 그러나 같은 블록을 열여섯 번 계산하면 연산은 늘어납니다. “가볍다”는 말은 파라미터 메모리, 학습 메모리, 첫 토큰 지연과 총 처리량 가운데 무엇을 측정했는지에 따라 달라집니다.

원문은 770M 파라미터가 1.3B Transformer 수준과 비교된 결과를 소개합니다. 모델 크기 숫자만 보지 말고 동일 데이터·토큰 예산·연산량·평가 항목에서 비교됐는지를 확인해야 도입 판단에 쓸 수 있습니다.

## 루프가 같은 생각을 반복하지 않게 하는 장치

반복부는 이전 상태 `h_t`와 Prelude의 원본 입력 `e`를 섞어 다음 상태를 만듭니다. 원문이 LTI-stable injection이라고 부른 구조는 매 루프에 입력을 다시 주입해 정보 소실이나 발산을 억제하려는 장치입니다. 학습된 `A`와 `B`가 두 신호의 비율을 조절한다는 설명입니다.

MoE 라우터는 루프 깊이에 따라 다른 전문가를 선택할 수 있고, ACT(Adaptive Computation Time)는 누적 정지 확률을 보고 일찍 멈추게 합니다. 단순 질문은 적게, 복잡한 질문은 최대 루프까지 계산한다는 목표입니다. MLA는 KV Cache를 줄이는 구성으로 소개되며 원문은 10~20배 절감 가능성을 언급합니다.

이 기능들은 서로 독립적인 마케팅 체크박스가 아닙니다. 정지 기준이 너무 이르면 품질이 떨어질 수 있고, 늘 최대 깊이까지 가면 동적 계산의 이점이 줄어듭니다. MoE 라우팅이 깊이에 따라 실제로 역할을 나누는지도 분석과 ablation으로 확인해야 합니다.

## Python 조각은 수학적 흐름을 그린 의사 코드다

원문 `forward` 함수는 루프 안에서 MoE와 MLA 출력을 계산하고, `A * h_t + B * e`로 원본 입력을 재주입한 뒤 `should_halt`로 멈춥니다. 이는 연구 아이디어를 읽기 쉽게 재구성한 코드입니다.

`self.moe_layer`, `self.mla_attention`, `A`, `B`와 정지 함수가 정의되지 않았고 텐서 shape, 정규화, residual, 손실과 학습 절차도 없습니다. 그대로 실행하거나 OpenMythos 저장소의 실제 구현이라고 인용할 수 없습니다. 특히 반복 학습의 안정성은 한 줄의 덧셈으로 보장되지 않으며 원문도 행렬의 spectral radius를 통제하는 어려움을 지적합니다.

재현 실험에서는 고정 루프 1·4·8·16회와 ACT를 나눠 정확도, 첫 토큰 지연과 최대 메모리를 측정해야 합니다. 그래야 공유 가중치의 효과와 더 많은 계산의 효과를 구분할 수 있습니다.

## VRAM 절약이 TTFT 증가로 돌아올 수 있다

파라미터가 적으면 제한된 VRAM에 모델을 올리기 쉽지만, 첫 토큰 전에 반복 블록을 여러 번 거치면 TTFT가 길어질 수 있습니다. 스트리밍 챗봇에서는 사용자가 이 침묵을 직접 느낍니다. 배치 분석에서는 몇 초의 추가 지연보다 모델 상주 메모리가 중요한 경우도 있습니다.

또한 vLLM과 TensorRT-LLM 같은 기존 서빙 엔진은 평면적인 층 구조와 PagedAttention에 맞춰 최적화되어 있다는 한계가 원문에 제시됩니다. 동적 루프와 깊이별 MoE가 일반 최적화 경로에 맞지 않으면, 파라미터에서 아낀 비용을 커스텀 커널과 운영 인력으로 다시 지불할 수 있습니다.

CPU에서 “파라미터를 한 번만 올리고 루프를 돌리면 된다”는 설명도 속도 보장은 아닙니다. 메모리에 들어가는가와 요구 지연 안에 계산되는가는 별도 지표입니다.

## 프로덕션보다 연구용 기준선으로 시작한다

첫 시험은 자동 주문이나 실시간 채팅이 아니라 오프라인 평가가 적합합니다. 같은 입력에서 루프별 품질, halt 분포, TTFT, 처리량과 전력·메모리 사용을 기록하십시오. 쉬운 문제에 정말 일찍 멈추는지, 어려운 문제에서 추가 루프가 실제 정답을 늘리는지도 봐야 합니다.

학습 안정성과 서빙 지원이 확인되지 않았다면 기존 모델을 바로 교체할 이유는 없습니다. OpenMythos의 실질적 질문은 “파라미터를 더 쌓을 것인가”가 아니라 “공유 가중치에 계산 시간을 더 쓸 때 같은 예산에서 무엇이 좋아지는가”입니다.

참고 자료:

- https://github.com/kyegomez/OpenMythos
- https://www.marktechpost.com/2026/04/19/meet-openmythos-an-open-source-pytorch-reconstruction-of-claude-mythos-where-770m-parameters-match-a-1-3b-transformer/
- https://awesomeagents.ai/openmythos-recasts-claude-mythos-as-looped-moe-transformer/
- https://36kr.com/p/2744747065985025
