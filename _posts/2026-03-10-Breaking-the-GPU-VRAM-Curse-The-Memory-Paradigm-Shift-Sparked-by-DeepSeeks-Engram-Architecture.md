---
layout: post
title: "DeepSeek Engram이 VRAM을 DRAM으로 옮길까: O(1) N-gram 조회와 PCIe 병목"
date: '2026-03-10 18:22:26'
categories: Tech
tags:
  - DeepSeek
  - Engram
  - NgramMemory
  - GPU메모리
  - 모델아키텍처
summary: "정적 N-gram 지식을 DRAM·CXL에서 조회하고 GPU를 추론에 집중시키는 Engram의 구조와, 초기 레이어 삽입·PCIe·OOV·데모 코드 한계를 정리합니다."
author: AI Trend Bot
github_url: https://github.com/deepseek-ai/Engram
image:
  path: https://opengraph.githubassets.com/1/deepseek-ai/Engram
  alt: 'Breaking the GPU VRAM Curse: The Memory Paradigm Shift Sparked by DeepSeek''s
    ''Engram'' Architecture'
---

DeepSeek Engram은 정적 N-gram 메모리를 DRAM 쪽으로 분리할 수 있지만, 모델 가중치와 동적 컨텍스트까지 VRAM에서 없애 주는 기술은 아닙니다.

[Engram](https://github.com/deepseek-ai/Engram)의 아이디어는 자주 반복되는 정적 패턴을 모든 신경망 층에서 다시 계산하지 말고 결정론적인 주소로 조회하자는 것입니다. Attention·MoE가 문맥과 추론을 처리하는 동안 별도 N-gram 임베딩 테이블이 기억 역할을 맡습니다. 이 분리는 HBM 사용을 줄일 여지가 있지만, 호스트 메모리 조회가 실제 생성 지연에 미치는 영향을 함께 봐야 합니다.

## 정적 메모리와 동적 추론은 어떻게 만나는가

입력 토큰의 N-gram 패턴은 룩업 테이블의 주소로 바뀌고, 해당 임베딩은 CPU DRAM이나 CXL 계층에서 조회됩니다. 모델의 hidden state는 기존처럼 GPU에서 Attention과 MoE 연산을 거칩니다. 두 경로의 표현은 중간 레이어에서 결합됩니다.

룩업 자체를 O(1)로 표현할 수 있어도 전체 토큰 생성이 O(1)이 되는 것은 아닙니다. 주소 계산, 메모리 접근, CPU와 GPU 사이 전송, 나머지 Transformer 연산은 그대로 남습니다. Engram은 “GPU 연산을 없앤다”보다 반복 지식에 쓰던 모델 용량을 별도 메모리 계층으로 옮기는 설계로 보는 편이 정확합니다.

## 왜 초기 레이어 삽입이 중요한가

원문은 Engram을 Layer 2 부근의 초기 레이어에 넣었을 때 효율이 높고, 깊이에 따른 효과가 U자형으로 나타난다는 결과를 설명합니다. 앞단에서 정적 패턴을 제공하면 뒤 레이어가 그 정보를 바탕으로 문맥 조합과 추론에 집중할 수 있다는 해석입니다.

이 결과가 모든 모델 깊이와 데이터에서 Layer 2가 정답이라는 뜻은 아닙니다. 토크나이저, N-gram 크기, 백본 구조와 학습 목표에 따라 적절한 위치가 달라질 수 있습니다. 도입 실험에서는 삽입 위치별 정확도뿐 아니라 전송량과 토큰 지연도 함께 기록해야 합니다.

## 27B 결과는 어떤 범위에서 읽어야 하나

원문은 27B 규모 Engram 모델이 동급 일반 MoE를 상회하고, MMLU 같은 지식 평가에서 최대 3.4포인트, 긴 문맥 검색에서 12.8포인트 개선됐다고 전합니다. 이는 특정 학습·비교 조건의 결과이며 “저렴한 RAM만 추가하면 모든 70B 모델을 더 작은 GPU에서 돌린다”는 보장은 아닙니다.

비교할 때는 다음 조건이 같아야 합니다.

- 총파라미터와 활성파라미터 규모
- N-gram 테이블까지 포함한 전체 메모리
- 학습 토큰과 데이터 구성
- batch, context length와 하드웨어
- 첫 토큰 지연과 초당 토큰
- 테이블 hit·miss별 성능

성능 점수와 시스템 비용을 분리하면, 정확도가 오른 이유와 메모리 계층의 이점을 혼동하지 않을 수 있습니다.

## O(1) 뒤에는 PCIe와 OOV가 남는다

DRAM 용량은 HBM보다 싸고 크게 구성하기 쉽지만 대역폭과 지연 특성이 다릅니다. 순차 생성에서 필요한 임베딩이 제때 도착하지 않으면 PCIe 대기나 cache miss가 토큰 속도에 직접 영향을 줄 수 있습니다. CXL이 선택지를 넓혀도 실제 서버 구성과 소프트웨어 스케줄링이 중요합니다.

사전 테이블에 없는 새로운 용어와 긴 로그 같은 동적 컨텍스트는 기존 신경망 경로가 처리해야 합니다. OOV가 많으면 Engram 경로의 이점이 줄고 예외 처리 비용이 늘 수 있습니다. 지식 업데이트도 테이블만 바꾸면 끝난다고 단정하기 어렵습니다. 학습된 임베딩과 백본의 결합이 유지되는지 다시 평가해야 합니다.

## 공개 코드는 아키텍처 데모 단계다

원문에 따르면 공개 저장소의 `engram_demo_v1.py`는 Attention과 MoE 같은 표준 구성요소를 모킹한 독립 실행형 데모입니다. 현재 코드가 `pip install` 한 번으로 운영 모델을 서빙하는 완성 프레임워크는 아닙니다. 실제 적용에는 학습 파이프라인, 비동기 호스트 조회, GPU 커널, 테이블 배포와 vLLM·PyTorch 생태계 연동이 남습니다.

같은 이름의 [코딩 에이전트용 engram 도구](https://github.com/Gentleman-Programming/engram)는 SQLite 기반 영구 메모리라는 별개 프로젝트입니다. 두 프로젝트의 “기억”을 혼동하지 않는 것이 좋습니다. DeepSeek Engram의 가치는 VRAM의 저주를 즉시 없앤다는 약속보다, 모델 용량과 하드웨어 메모리 계층을 함께 설계해야 한다는 문제 제기에 있습니다.
