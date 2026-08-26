---
layout: post
title: "MMM은 1분 영상을 빠르고 선명하게 만들까: Global Mean, Local Mode의 경계"
date: '2026-03-02 20:27:00'
categories: Tech
tags:
  - 디퓨전모델
  - 트랜스포머
math: true
summary: "MMM이 긴 영상의 전체 흐름과 짧은 영상의 세부 품질을 두 Head로 나누는 방식을 살펴보고, 슬라이딩 윈도 경계, 데이터, 속도 검증 과제를 정리합니다."
description: "MMM이 long-video Global mean-seeking head와 short-video Local mode-seeking head를 결합하는 원리, sliding-window 경계, head 충돌, 1분 속도와 품질 검증법을 설명합니다."
faq:
  - question: "MMM은 짧은 video data만으로 1분 서사를 학습하나요?"
    answer: "아닙니다. Short clip은 local detail을 돕고 long-video data가 global temporal structure를 맡으므로 장기 사건 연결을 배울 자료는 여전히 필요합니다."
  - question: "두 Head를 쓰면 선명도와 일관성이 모두 좋아지나요?"
    answer: "두 objective가 충돌할 수 있어 head별 ablation과 weight sweep에서 identity, window boundary, local quality의 trade-off를 확인해야 합니다."
  - question: "빠른 1분 생성은 어떤 수치로 확인해야 하나요?"
    answer: "Hardware, precision, resolution, frame rate, batch, sampling step을 고정하고 startup, wall-clock, peak memory와 quality를 baseline과 함께 측정해야 합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2602.24289.png
  alt: "MMM은 1분 영상을 빠르고 선명하게 만들까: Global Mean, Local Mode의 경계 논문 대표 이미지"
---

MMM은 1분 길이의 빠르고 선명한 생성을 목표로 하지만, 이 글의 원문만으로는 정확한 속도, 해상도, 품질 조건까지 확인할 수 없습니다. 판단하려면 Global, Local head의 독립 기여, window boundary failure와 hardware 조건을 고정한 end-to-end 생성 시간을 함께 봐야 합니다.

[MMM 프로젝트](https://primecai.github.io/mmm/)가 다루는 갈등은 분명합니다. 고품질 짧은 영상은 많지만 일관된 고품질 장편 영상 데이터는 부족합니다. 하나의 학습 목표로 전체 흐름과 프레임 세부 묘사를 모두 잡으려 하지 않고, Decoupled Diffusion Transformer의 Global Head와 Local Head에 역할을 나눈 것이 핵심입니다.

## 짧은 영상과 긴 영상은 서로 다른 것을 가르친다

긴 영상은 인물과 배경, 사건이 시간에 따라 어떻게 이어지는지 보여 줍니다. 하지만 학습할 고품질 데이터가 부족하면 세부 묘사까지 충분히 배우기 어렵습니다. 반대로 짧은 클립은 질감과 움직임의 품질을 풍부하게 보여 주지만 1분 동안 구조를 유지하는 법을 직접 가르치지는 못합니다.

MMM은 이 데이터 불균형을 “둘 중 하나를 선택하는 문제”로 보지 않습니다. 긴 영상으로 전역 구조를, 고품질 짧은 영상으로 국소 품질을 학습해 서로 다른 통계적 성향을 한 모델 안에서 결합합니다. 분리의 이점은 각 데이터가 잘 가르칠 수 있는 부분에 집중한다는 데 있습니다.

## Global Head는 평균적 흐름을 잡는다

Global Head는 희소한 장편 영상 데이터와 Flow Matching을 사용해 영상 전체의 일관된 구조를 담당합니다. 여기서 mean-seeking은 가능한 전개를 넓게 포괄하며 부드러운 흐름을 만드는 방향을 가리킵니다. 인물과 배경의 장기 상태가 갑자기 끊기지 않게 하는 역할입니다.

다만 평균을 따른다는 표현을 “서사를 이해한다”는 뜻으로 확대하면 안 됩니다. 학습 데이터에 장기 사건 연결이 부족하면 Global Head도 그 한계를 벗어나기 어렵습니다. MMM이 짧은 영상 데이터를 활용해도 장편 데이터가 완전히 필요 없어지는 것은 아닙니다.

## Local Head는 짧은 구간의 mode를 좇는다

Local Head는 고품질 짧은 영상과 짧은 영상용 teacher를 활용합니다. Reverse-KL의 mode-seeking 성향으로 가능한 출력의 평균보다 그럴듯하고 선명한 국소 패턴에 집중하도록 설계됩니다. Global Head가 정한 큰 흐름 안에서 프레임 질감과 짧은 움직임을 보완하는 역할입니다.

두 Head가 있다는 사실만으로 항상 조화되는 것은 아닙니다. 전역 상태가 요구하는 변화와 teacher가 선호하는 짧은 패턴이 충돌할 수 있고, 학습 중 두 목적의 균형을 조정해야 합니다. Global과 Local을 따로 튜닝하고 teacher까지 유지하는 복잡성도 구현 비용에 포함됩니다.

## 슬라이딩 윈도는 길이를 늘리지만 경계를 만든다

MMM은 sliding window로 긴 시간을 짧은 국소 구간으로 나누고, few-step 생성을 지향합니다. 이 방식은 모든 프레임을 한 번에 처리하는 부담을 줄이고 짧은 영상 teacher를 활용하기 쉽게 합니다.

반면 창과 창 사이에는 새로운 실패 지점이 생깁니다. 이전 구간의 작은 위치, 외형 오류가 다음 구간의 조건으로 이어지거나, 경계에서 움직임과 배경이 튈 수 있습니다. 다음 항목을 시간축 전체에서 측정해야 합니다.

- 인물, 사물의 외형과 위치가 유지되는가
- 창 경계에서 동작 속도와 카메라가 끊기지 않는가
- 프롬프트의 사건 순서가 끝까지 남는가
- 길이가 늘 때 오류가 누적되는가
- few-step이 품질과 실제 지연에 어떤 손해를 주는가

## “빠른 1분”은 조건이 공개돼야 비교할 수 있다

원문에는 기존 방식과의 정확한 정량 표, 하드웨어, 해상도, 프레임 수, 생성 시간이 제시되지 않습니다. 따라서 “순식간에 1분”이나 “프로덕션 준비 완료”라고 결론 내리기보다 [논문](https://arxiv.org/abs/2602.24289)과 [Paper ID 2602.24289](https://huggingface.co/papers/2602.24289)의 평가 조건을 확인할 필요가 있습니다.

실무 검증에서는 같은 프롬프트와 연산 예산으로 짧은 구간 품질, 장기 일관성, 실제 생성 시간, GPU 메모리를 따로 기록해야 합니다. MMM의 중요한 아이디어는 mode와 mean 중 하나가 정답이라는 주장이 아니라, 데이터의 강점에 맞춰 전역과 국소 학습 목표를 분리했다는 데 있습니다.

## 두 Head의 기여를 어떻게 분리할까

Global-only, Local-only, 두 head 결합을 같은 data, compute에서 비교합니다. Global-only가 identity와 story state를 오래 유지하지만 detail이 흐린지, Local-only가 선명하지만 scene이 drift하는지 확인합니다. 결합 model이 두 baseline의 장점을 실제로 유지해야 추가 구조가 정당화됩니다.

| 조건 | 우선 지표 | 대표 failure |
|---|---|---|
| Global-only | long identity, event order | 평균화된 texture, motion |
| Local-only | short clip sharpness | long drift, reset |
| Combined | 두 축의 Pareto 개선 | head conflict, 추가 비용 |

Head loss weight와 teacher strength를 바꾸며 quality curve를 봅니다. 한 aggregate score만 쓰면 local sharpness가 long consistency loss를 가릴 수 있습니다.

## Sliding Window Boundary를 어디서 찾을까

Window 시작, 끝 frame 번호를 log하고 boundary 전후의 optical flow, color, identity embedding과 camera motion jump를 측정합니다. Event가 boundary를 가로지르는 prompt를 일부러 넣어 action이 중간에 reset되지 않는지 확인합니다.

작은 accessory, object 위치와 background text를 state ledger로 추적합니다. 앞 window의 오류를 다음 condition으로 넣으면 drift가 누적될 수 있으므로 10초, 30초, 60초 구간별 survival을 봅니다. Overlap을 늘리면 continuity는 좋아질 수 있지만 중복 compute와 ghosting이 늘 수 있습니다.

## Local Teacher가 Global State를 무시할 때 무엇이 생기나

Short-video teacher는 현재 구간을 선명하게 만들지만 30초 전 object 상태를 모를 수 있습니다. Global head가 “door는 이미 열림”을 유지하려는데 local mode가 익숙한 닫힌 문 clip을 선호하면 state가 되돌아갈 수 있습니다. 두 head output이 크게 충돌하는 sample을 모아 arbitration이 필요한지 봅니다.

Scene change가 의도된 prompt에서는 초기 background 유지가 오히려 실패입니다. Identity를 보존하면서 location이 바뀌는 test로 단순 copy와 narrative consistency를 구분합니다.

## 실제 속도에는 무엇을 포함할까

Few-step 수뿐 아니라 text encode, initial noise, 모든 window 생성, overlap processing, decoding과 video encoding을 합친 wall-clock을 측정합니다. Batch throughput과 한 video latency를 구분하고 OOM을 피하기 위한 offload 시간도 포함합니다.

동일 resolution, FPS, duration, hardware에서 baseline과 비교하고 quality가 같거나 목표 threshold 이상일 때만 speedup을 말합니다. 실패 video 재생성률과 storage도 production cost입니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [긴 영상 배경음악이 장면 감정을 놓칠 때: NarraScore의 이중 제어]({% post_url 2026-02-14-NarraScore--Bridging-Visual-Narrative-and-Musical-Dynamics-via-Hierarchical-Affective-Control %}) — NarraScore가 영상의 전역 분위기와 시점별 Valence-Arousal 곡선을 나눠 음악 생성에 주입하는 방식, 평가 기준과 감정 단순화 한계를 다룹니다.
- [Sora 영상은 왜 물리 법칙을 틀리나: 시공간 패치와 DiT 원리]({% post_url 2025-02-19-sora %}) — Sora가 영상을 압축해 시공간 패치로 처리하는 방식과 긴 영상에서도 남는 물리, 캐릭터 일관성 문제
- [긴 영상 QA에서 전체를 요약하면 왜 틀릴까? LongVideoAgent의 구간 검색]({% post_url 2025-12-26-LongVideoAgent--Multi-Agent-Reasoning-with-Long-Videos %}) — LongVideoAgent가 긴 영상을 한 번에 요약하지 않고 질문 관련 구간을 먼저 찾은 뒤 고해상도 frame을 확인하는 이유, 역할 분리의 이득과 grounding 오류 전파를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### MMM은 짧은 video data만으로 1분 서사를 학습하나요?

아닙니다. Short clip은 local detail을 돕고 long-video data가 global temporal structure를 맡으므로 장기 사건 연결을 배울 자료는 여전히 필요합니다.

### 두 Head를 쓰면 선명도와 일관성이 모두 좋아지나요?

두 objective가 충돌할 수 있어 head별 ablation과 weight sweep에서 identity, window boundary, local quality의 trade-off를 확인해야 합니다.

### 빠른 1분 생성은 어떤 수치로 확인해야 하나요?

Hardware, precision, resolution, frame rate, batch, sampling step을 고정하고 startup, wall-clock, peak memory와 quality를 baseline과 함께 측정해야 합니다.
