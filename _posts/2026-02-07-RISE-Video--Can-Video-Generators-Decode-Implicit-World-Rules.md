---
layout: post
title: "화질 좋은 AI 영상이 물리 법칙은 틀리는 이유: RISE-Video 467개 Test"
date: '2026-02-07'
categories: Tech
tags:
  - 로보틱스
  - 영상생성
math: true
summary: "RISE-Video가 467개 human-annotated prompt로 영상 생성기의 상식, 공간 변화, 물리, 시간 인과를 평가하고, visual quality와 reasoning score가 갈리는 지점을 보여줍니다."
description: "RISE-Video가 467개 prompt, 8개 category로 video generator의 암시적 상식, 물리, 시간 인과를 평가하는 방식, LMM judge 편향과 simulation 적용 전 failure test를 설명합니다."
faq:
  - question: "영상 화질 점수가 높으면 물리적으로도 정확한가요?"
    answer: "아닙니다. Texture, 조명과 frame 선명도는 높아도 중력 방향, 충돌, 상태 변화와 사건 순서가 틀릴 수 있어 visual quality와 reasoning, physical score를 분리해야 합니다."
  - question: "RISE-Video의 LMM judge만으로 model을 평가해도 되나요?"
    answer: "대량 candidate 선별에는 유용하지만 keyframe이 짧은 오류를 놓치고 judge가 prompt expectation에 끌릴 수 있어 human audit와 가능한 물리 rule 검사를 병행해야 합니다."
  - question: "467개 test 결과를 simulation 안전성으로 바로 옮길 수 있나요?"
    answer: "아닙니다. 해당 prompt, 11개 model, 평가 시점의 결과이며 robot, 자율주행에는 업무별 collision, state transition failure set과 여러 seed 검증이 추가로 필요합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.05986.png
  alt: "화질 좋은 AI 영상이 물리 법칙은 틀리는 이유: RISE-Video 467개 Test 논문 대표 이미지"
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

Content 제작에서는 artifact 몇 개를 편집할 수 있지만 robot, 자율주행 simulation data에서는 잘못된 collision이나 state transition이 학습을 오염시킬 수 있습니다. 도입 전에 중력, 접촉, 액체, 도구 사용, 사건 순서처럼 업무에 중요한 rule을 별도 failure set으로 만듭니다.

같은 prompt를 여러 seed로 생성하고 네 지표를 따로 기록해야 우연한 성공을 줄일 수 있습니다. LMM judge 결과는 사람이 표본 검수하고, 문화권에 따라 달라지는 commonsense와 보편적 물리 rule을 구분합니다. RISE-Video의 핵심은 video model을 “지능적”이라고 선언하는 데 있지 않습니다. **화질 benchmark가 숨기던 암시적 인과 실패를 독립된 평가 축으로 끌어낸 것**입니다.

## 암시적 Rule 하나를 어떤 Check Item으로 바꿀까

Prompt에 기대 결과를 직접 써 버리면 model이 rule을 추론했는지 문장을 복사했는지 구분하기 어렵습니다. 먼저 원인만 주고, annotation에는 관측 가능한 결과와 금지할 변화, 발생 순서를 분리해 적습니다.

예를 들어 “사람이 촛불을 향해 분다”는 prompt에는 다음 check를 둘 수 있습니다.

| 구분 | 확인 항목 |
|---|---|
| 기대 결과 | 불꽃이 작아지거나 꺼짐 |
| 시간 순서 | 부는 동작 뒤에 불꽃 변화 발생 |
| 유지 조건 | 사람, 촛대의 identity와 scene 유지 |
| 금지 결과 | 바람 전에 불이 꺼짐, 촛불이 이동, 증식 |

“얼음에 뜨거운 물”도 단순히 cup이 예쁜지보다 얼음의 크기, 상태가 시간에 따라 변하는지 확인합니다. State change가 한 frame에서만 보였다가 되돌아가면 causal transition을 유지하지 못한 것입니다. Check item을 observable event로 쓰면 인간과 LMM judge가 같은 기준을 적용하기 쉽습니다.

## Prompt Pair로 Rule 사용 여부를 어떻게 확인할까

한 prompt의 성공은 training example과 비슷해서 우연히 나온 결과일 수 있습니다. Object, 원인을 하나씩 바꾼 minimal pair를 만듭니다. 뜨거운 물과 차가운 물, 놓은 공과 위로 던진 공, 열려 있는 container와 닫힌 container처럼 원인 차이에 맞춰 결과도 달라져야 합니다.

두 prompt의 video가 거의 같으면 model이 causal condition을 무시했을 가능성이 있습니다. 반대로 원인만 조금 바꿨는데 background와 identity까지 모두 달라지면 비교가 어렵습니다. 같은 initial image와 가능한 한 같은 생성 설정을 사용하고 여러 seed에서 rule adherence의 평균, 분산을 봅니다.

Category별 점수도 따로 둡니다. Spatial change에는 강하지만 tool use가 약한 model을 하나의 reasoning score로 순위화하면 실제 용도와 맞지 않을 수 있습니다. Production failure set에서 중요한 category에 가중치를 주되, benchmark 원점수와 업무용 가중 점수를 구분해 보고합니다.

## LMM Judge가 놓치는 오류는 무엇인가

Keyframe judge는 충돌 순간의 clipping, 잠깐 뒤집힌 object, 원인보다 먼저 나타난 결과를 sampling 사이에서 놓칠 수 있습니다. Frame rate와 event duration을 고려해 keyframe을 고르고, motion이 중요한 rule에는 짧은 연속 clip 또는 trajectory 기반 검사를 추가합니다.

Judge가 “얼음은 녹아야 한다”는 text expectation에 끌려 실제 pixel evidence가 약한데도 점수를 줄 수 있습니다. Prompt를 가린 visual-only 판정, 원인, 결과를 바꾼 negative video와 사람이 만든 calibration set으로 false positive를 측정합니다. 인간 평가와 correlation 하나만 보지 말고 category별 disagreement를 audit합니다.

## 생성 Data를 학습에 쓰기 위한 합격선

Simulation data로 사용할 때는 화질이 아니라 downstream 위험으로 합격선을 정합니다. Collision, object count, contact sequence처럼 rule로 검사 가능한 항목은 자동 validator를 쓰고, 액체, deformable object처럼 복잡한 항목은 사람이 표본을 봅니다. 실패 sample이 섞인 비율과 그 data로 학습한 policy의 오류를 연결해 기록합니다.

Content 제작이라면 일부 오류 clip을 걸러 내는 비용으로 충분할 수 있습니다. Robot training이라면 작은 물리 오류도 반복 학습돼 위험하므로 더 엄격한 threshold와 실제 simulator, sensor data 대조가 필요합니다. RISE-Video 점수는 이 결정의 시작점이며 업무별 validation을 대신하지 않습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [로봇 비디오가 물체를 뚫고 지나간다면? Kinema4D의 URDF, Pointmap 제어]({% post_url 2026-03-18-Kinema4D--Kinematic-4D-World-Modeling-for-Spatiotemporal-Embodied-Simulation %}) — 로봇 기구학에서 만든 3D 궤적과 pointmap을 비디오 생성에 넣는 Kinema4D의 구조, Robo4D-200K 학습 범위와 물리 한계를 살펴봅니다.
- [Sora 영상은 왜 물리 법칙을 틀리나: 시공간 패치와 DiT 원리]({% post_url 2025-02-19-sora %}) — Sora가 영상을 압축해 시공간 패치로 처리하는 방식과 긴 영상에서도 남는 물리, 캐릭터 일관성 문제
- [대화문만으로 장편 AI 영상을 만들 수 있을까: ScripterAgent와 VSA의 현실적 한계]({% post_url 2026-01-27-The-Script-is-All-You-Need--An-Agentic-Framework-for-Long-Horizon-Dialogue-to-Cinematic-Video-Generation %}) — 대화를 장면별 실행 대본으로 바꾸는 두 에이전트 구조와 장면 일관성, 평가, 비용의 한계를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 영상 화질 점수가 높으면 물리적으로도 정확한가요?

아닙니다. Texture, 조명과 frame 선명도는 높아도 중력 방향, 충돌, 상태 변화와 사건 순서가 틀릴 수 있어 visual quality와 reasoning, physical score를 분리해야 합니다.

### RISE-Video의 LMM judge만으로 model을 평가해도 되나요?

대량 candidate 선별에는 유용하지만 keyframe이 짧은 오류를 놓치고 judge가 prompt expectation에 끌릴 수 있어 human audit와 가능한 물리 rule 검사를 병행해야 합니다.

### 467개 test 결과를 simulation 안전성으로 바로 옮길 수 있나요?

아닙니다. 해당 prompt, 11개 model, 평가 시점의 결과이며 robot, 자율주행에는 업무별 collision, state transition failure set과 여러 seed 검증이 추가로 필요합니다.

[Original Paper Link](https://huggingface.co/papers/2602.05986)
