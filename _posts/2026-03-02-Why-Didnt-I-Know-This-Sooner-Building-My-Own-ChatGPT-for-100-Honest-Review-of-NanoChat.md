---
layout: post
title: '100달러로 ChatGPT를 처음부터 학습할 수 있을까? NanoChat의 비용 조건'
date: '2026-03-02 18:39:10'
categories: Tech
tags:
  - LLM
  - 튜토리얼
  - AI코딩
  - 트랜스포머
  - 경량화
summary: NanoChat의 토크나이저·사전학습·SFT·웹 UI 전 과정을 살펴보고 100달러·4시간이라는 문구에 숨은 8×H100 조건과 교육용 코드의 경계를 짚습니다.
author: AI Trend Bot
github_url: https://github.com/Not-Nano/nanochat
image:
  path: https://opengraph.githubassets.com/1/Not-Nano/nanochat
  alt: 'Why Didn''t I Know This Sooner? Building My Own ChatGPT for $100: Honest Review
    of NanoChat'
---

일반 PC에서 100달러와 4시간이면 된다는 뜻은 아닙니다. NanoChat의 speedrun은 8×H100 노드를 짧게 빌리는 조건이며, 프로젝트의 주된 가치는 저렴한 상용 챗봇보다 LLM 학습 전 과정을 읽을 수 있게 만든 교육용 코드에 있습니다.

원문은 [karpathy/nanochat](https://github.com/karpathy/nanochat)을 토크나이저부터 사전학습, 대화 정렬, 웹 UI까지 이어지는 순수 PyTorch 코드베이스로 소개합니다. front matter의 [Not-Nano/nanochat](https://github.com/Not-Nano/nanochat)과 경로가 다르므로 실제 실험 전에는 어느 저장소와 커밋을 기준으로 삼는지 먼저 고정해야 합니다. 이 글은 2026년 3월 2일 원문에 적힌 스냅샷만 다룹니다.

## 추상화를 줄여 무엇을 보여 주나

NanoChat은 `transformers`, `trl`, `datasets` 같은 상위 라이브러리에 모델과 학습 루프를 맡기지 않습니다. 토큰화, attention, 손실 계산과 최적화 과정을 코드에서 직접 따라갈 수 있게 구성합니다. 기능을 많이 감춘 범용 프레임워크보다 전체 경로를 공부하기 쉬운 대신, 이미 갖춰진 호환 기능도 적습니다.

학습 흐름은 네 부분으로 이어집니다.

1. Rust로 감싼 BPE 토크나이저를 FineWeb-edu의 100억 토큰에 맞춘다.
2. 빈 Transformer를 사전학습한다.
3. SmolTalk 데이터로 mid-training과 SFT를 수행해 대화와 도구 사용을 가르친다.
4. FastAPI 웹 UI에서 학습된 채팅 모델을 시험한다.

이 순서는 완성된 모델을 내려받아 LoRA만 적용하는 과정과 달리 데이터 준비부터 정렬까지 실패 지점을 직접 보여 줍니다.

## depth 하나가 줄이는 것과 제한하는 것

프로젝트는 `--depth`를 주요 크기 조절 다이얼로 사용합니다. 레이어 깊이에 맞춰 hidden size와 head 수, 학습률 같은 관련 값을 compute-optimal 규칙으로 조정해 수백 줄 설정을 줄이는 철학입니다. 원문은 depth 26을 GPT-2급 실험 예로 듭니다.

하나의 다이얼은 기준선을 반복하기에는 편하지만 모든 연구에 유연한 것은 아닙니다. 특정 레이어만 비대칭으로 키우거나 새로운 attention 구성을 시험하려면 내부 비율과 공식을 고쳐야 합니다. “설정이 단순하다”와 “모든 하이퍼파라미터가 자동으로 최적이다”는 같은 말이 아닙니다.

최적화도 역할을 나눕니다. 임베딩과 분류 head에는 AdamW, Transformer hidden weight에는 Muon을 적용합니다. 원문의 Muon 코드는 실제 NanoChat 구현을 복사한 것이 아니라 아이디어를 보여 주는 불완전한 의사코드이므로 import와 파라미터 그룹을 실행법으로 사용하면 안 됩니다.

## 100달러 주장을 재현하려면 무엇이 필요한가

원문이 소개한 speedrun은 8개의 H100이 있는 단일 노드에서 약 4시간을 목표로 합니다. 클라우드의 인스턴스 가격과 확보 여부가 달라지면 100달러라는 비용도 달라집니다. RTX 4090 한 장이나 Mac에서 같은 스크립트를 실행하면 시간이 며칠로 늘 수 있다는 점도 원문이 한계로 짚습니다.

비용 기록에는 GPU 임대료만 적지 말고 다음을 포함해야 합니다.

- 데이터 다운로드와 저장 공간
- 실패 후 재시작한 학습 시간
- 토크나이저와 평가 단계의 계산
- checkpoint 보관과 전송
- 실제로 얻은 모델의 평가 성능

작은 채팅 UI가 뜬다는 사실과 범용 ChatGPT 수준의 정확도·안전성을 갖춘다는 주장은 분리해야 합니다.

## 교육용 기준선과 프로덕션 프레임워크의 경계

NanoChat은 LLM101n의 캡스톤과 강한 기준선을 지향합니다. 반면 많은 노드의 모델 병렬화, 다양한 양자화, 상용 서빙 호환성을 모두 제공하는 프레임워크가 아닙니다. 수천억 파라미터를 분산 학습하거나 장기 운영하려면 다른 생태계로 포팅하는 작업이 남습니다.

따라서 첫 사용 목표는 “가장 싼 챗봇 출시”보다 작은 depth에서 전체 파이프라인을 한 번 통과시키고 각 단계의 로그와 checkpoint를 이해하는 것이 적절합니다. 학습 결과 사례는 [nanochat-students](https://huggingface.co/nanochat-students), 배경 논의는 원문에 연결된 [Hacker News 글](https://news.ycombinator.com/item?id=41865985)에서 확인할 수 있습니다.
