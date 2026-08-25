---
layout: post
title: "화질 좋은 AI 영상이 물리 법칙은 틀리는 이유: RISE-Video 467개 Test"
date: '2026-02-07'
categories: Tech
tags:
  - 영상생성
  - 벤치마크
  - 멀티모달
  - 월드모델
  - 로보틱스
math: true
summary: "RISE-Video가 467개 human-annotated prompt로 영상 생성기의 상식·공간 변화·물리·시간 인과를 평가하고, visual quality와 reasoning score가 갈리는 지점을 보여줍니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.05986.png
  alt: Paper Thumbnail
---

화질 좋은 AI video가 물리적으로 틀릴 수 있는 이유는 **texture와 조명은 통계적으로 그럴듯하게 만들면서도, prompt에 생략된 원인과 결과를 frame 변화로 구현하지 못할 수 있기 때문**입니다. RISE-Video는 visual quality와 implicit world rule 수행을 같은 점수로 뭉개지 않고 분리합니다.

## Prompt에 쓰지 않은 결과까지 만들어야 한다

“얼음이 든 컵에 뜨거운 물을 붓는다”는 prompt는 얼음이 녹는다고 직접 쓰지 않아도 그 상태 변화를 기대합니다. 촛불을 불면 꺼지고, 떨어진 물체는 중력 방향으로 움직이며, tool은 용도에 맞게 사용돼야 합니다. RISE-Video가 implicit rule이라 부르는 요소입니다.

Dataset은 사람이 annotation한 467개 sample과 여덟 reasoning category로 구성됩니다. General commonsense, spatial change, physical rationality, object attribute, creative reasoning, human-object interaction, domain-specific knowledge, temporal causality를 나눕니다. 동일 prompt와 initial image를 11개 text-image-to-video model에 제공해 zero-shot 생성 결과를 비교합니다.

이 구성은 “예쁘게 생성했나”보다 “명시하지 않은 필연적 결과가 실제로 일어났나”를 질문합니다. 영상 생성기를 simulation data에 쓰려면 필수적인 구분입니다.

## 네 지표가 서로 다른 실패를 잡는다

평가는 reasoning alignment, temporal consistency, physical rationality, visual quality 네 축입니다. Object가 선명하지만 잘못된 방향으로 움직일 수 있고, 물리 변화는 맞지만 frame마다 모양이 바뀔 수도 있습니다. 한 개의 종합 점수만 보면 어느 실패인지 알기 어렵습니다.

LMM 자동 평가는 video의 keyframe, 원 prompt, “얼음이 녹았는가” 같은 check item을 함께 받아 점수를 냅니다. Human 평가와 correlation을 확인해 대량 평가 비용을 줄입니다. 그러나 keyframe sampling이 짧은 물리 오류를 놓칠 수 있고, judge LMM도 text expectation에 끌릴 수 있습니다.

따라서 자동 judge는 인간 평가를 완전히 대신하기보다 candidate를 선별하는 도구로 보는 편이 안전합니다. 물리 정확도가 중요한 경우 frame-level motion이나 simulator 기반 검사도 필요합니다.

## Visual Quality가 높아도 Reasoning은 50~60점대였다

원문에 따르면 Kling과 Gen-3 Alpha 계열은 visual quality에서 80점 넘는 결과를 보였지만 reasoning alignment와 physical rationality는 50~60점대에 머물렀습니다. 특히 clipping, 불규칙한 낙하, 잘못된 state change가 관찰됐습니다. Closed model이 open model보다 전반적으로 높았지만 reasoning 격차는 visual quality 격차보다 작았습니다.

이 수치는 467개 sample, 5초 이상 output, 당시 11개 model과 평가 pipeline에 묶여 있습니다. 특정 model의 현재 성능이나 모든 video domain으로 확대할 수 없습니다. “rule을 decode했다”는 표현도 내부에 symbolic physics가 존재한다는 증거가 아니라 결과 video가 기대 rule을 따랐는지 평가한 것입니다.

## Simulation 용도라면 Failure Set부터 만든다

Content 제작에서는 artifact 몇 개를 편집할 수 있지만 robot·자율주행 simulation data에서는 잘못된 collision이나 state transition이 학습을 오염시킬 수 있습니다. 도입 전에 중력, 접촉, 액체, 도구 사용, 사건 순서처럼 업무에 중요한 rule을 별도 failure set으로 만듭니다.

같은 prompt를 여러 seed로 생성하고 네 지표를 따로 기록해야 우연한 성공을 줄일 수 있습니다. LMM judge 결과는 사람이 표본 검수하고, 문화권에 따라 달라지는 commonsense와 보편적 물리 rule을 구분합니다. RISE-Video의 핵심은 video model을 “지능적”이라고 선언하는 데 있지 않습니다. **화질 benchmark가 숨기던 암시적 인과 실패를 독립된 평가 축으로 끌어낸 것**입니다.

[Original Paper Link](https://huggingface.co/papers/2602.05986)
