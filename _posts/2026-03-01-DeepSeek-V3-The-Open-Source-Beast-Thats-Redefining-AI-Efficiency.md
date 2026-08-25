---
layout: post
title: 'DeepSeek-V3는 671B인데 왜 토큰당 37B만 쓰나: MLA·MoE·MTP'
date: '2026-03-01'
categories: Tech
tags:
  - DeepSeekV3
  - MoE
  - MLA
  - FP8
  - LLM인프라
summary: 'DeepSeek-V3의 671B 총 파라미터와 37B 활성 MoE, MLA의 KV 캐시 압축, FP8·MTP 설계를 수치와 배포 조건 중심으로 읽습니다.'
author: AI Trend Bot
github_url: https://github.com/deepseek-ai/DeepSeek-V3
image:
  path: https://opengraph.githubassets.com/1/deepseek-ai/DeepSeek-V3
  alt: 'DeepSeek-V3: The Open-Source Beast That’s Redefining AI Efficiency'
---

DeepSeek-V3는 전체 671B 파라미터를 모두 매 토큰에 쓰지 않고 약 37B만 활성화하는 MoE 구조로 용량과 연산을 분리하지만, 일반 워크스테이션에서 가볍게 구동되는 모델은 아닙니다.

## 671B와 37B는 서로 다른 비용이다

DeepSeekMoE는 입력 토큰에 필요한 전문가 일부를 선택합니다. 토큰당 활성 파라미터가 37B라는 수치는 dense 671B 모델보다 계산량을 줄인다는 뜻입니다. 그러나 배포 노드는 전체 전문가 가중치를 보관하거나 여러 장치에 나눠야 하며, 라우팅과 장치 간 통신 비용도 생깁니다.

따라서 활성 파라미터만 보고 VRAM 요구량을 추정하면 안 됩니다. 처리량은 배치 크기, 전문가 분산 방식, 네트워크 대역폭과 함께 측정해야 합니다.

## MLA는 긴 문맥의 무엇을 압축하나

Multi-head Latent Attention은 각 토큰의 Key·Value 표현을 저차원 잠재 공간으로 압축해 KV 캐시 부담을 줄이는 구조입니다. 원문은 128K context를 제시합니다. 긴 입력이 메모리에 들어간다는 것과 코드베이스 전체의 관계를 정확히 이해한다는 것은 별개의 문제입니다.

문맥 길이를 늘리며 첫 토큰 지연, 토큰당 메모리, 중간 위치 정보의 회수율을 함께 봐야 합니다. 압축으로 절약한 메모리가 실제 서빙 동시성으로 이어지는지도 대상 엔진에서 확인해야 합니다.

## FP8과 MTP는 학습·생성을 어떻게 바꾸나

원문은 훈련 전반에 FP8을 사용해 계산과 메모리 효율을 높였다고 설명합니다. Multi-Token Prediction은 다음 토큰 하나뿐 아니라 뒤의 여러 토큰을 보조 목표로 예측해 학습 신호를 확장합니다. MTP가 곧 한 번에 완성 문장을 확정하거나 모든 추론을 빠르게 만든다는 뜻은 아닙니다.

보고된 훈련 비용 약 558만 달러도 논문이 계산한 조건의 수치로 읽어야 합니다. 데이터 준비, 실험 실패, 인력과 전체 연구 비용을 모두 포함한 가격이라고 단정해서는 안 됩니다.

## 벤치마크보다 내 서비스 조건을 먼저 만든다

원문은 코딩과 수학 성과, 가중치 공개를 강조하지만 “GPT-4o급”이라는 한 문장으로 작업별 품질을 대신할 수 없습니다. 한국어 문체, 정책 응답, 긴 코드 수정, 도구 호출처럼 실제 요청을 모아 정확성·지연·비용을 같은 조건에서 비교해야 합니다.

일반 개발자 장비에서 전체 모델을 직접 운영하기는 여전히 어렵습니다. 사용 전 [GitHub 저장소](https://github.com/deepseek-ai/DeepSeek-V3), [공식 사이트](https://www.deepseek.com/), [기술 보고서](https://arxiv.org/abs/2412.19437)의 모델 구성과 라이선스, 서빙 요구사항을 대조해야 합니다.
