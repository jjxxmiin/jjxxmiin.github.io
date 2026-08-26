---
layout: post
title: '실시간 비디오 AI는 언제 먼저 말해야 할까? Proact-VL의 트리거 문제'
date: '2026-03-05 20:22:18'
categories: Tech
tags:
  - 영상이해
  - AI트렌드
math: true
summary: Proact-VL이 연속 영상을 보며 SPEAK 시점과 응답 길이를 함께 결정하는 방식, Live Gaming Benchmark와 오경보·지연의 절충을 정리합니다.
description: 'Proact-VL이 실시간 영상에서 SPEAK 시점과 응답 길이를 정하는 원리, 발화 누락·과잉 개입·지연·context 관리와 안전한 trigger 평가법을 설명합니다.'
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2603.03447.png
  alt: "실시간 비디오 AI는 언제 먼저 말해야 할까? Proact-VL의 트리거 문제 논문 대표 이미지"
faq:
  - question: 'Proact-VL은 중요한 장면을 발견하면 항상 먼저 말하나요?'
    answer: '모델이 SPEAK trigger를 학습하지만 사건·도메인별 recall과 false alarm이 다를 수 있습니다. 반드시 말할 사건과 침묵해야 할 사건을 따로 정의해 threshold와 timing을 검증해야 합니다.'
  - question: '게임 benchmark 성능을 안전 경고에 적용해도 되나요?'
    answer: '게임의 오경보와 의료·산업 현장의 오경보는 피해가 다릅니다. 안전 용도에는 별도 데이터·독립 센서·인간 확인과 실패 시 안전 동작이 필요합니다.'
  - question: '응답이 짧으면 실시간 요구를 만족한 건가요?'
    answer: '짧은 문장이어도 사건 인식과 생성 시작이 늦으면 경고가 쓸모없습니다. Frame 입력부터 trigger·첫 음성·완료까지 단계별 지연과 전체 자원 사용을 측정해야 합니다.'
---

중요한 장면마다 말하는 것이 정답은 아닙니다. Proact-VL은 연속 비디오에서 `<SPEAK>` 시점과 답변 길이를 스스로 결정하지만, 늦은 경고와 불필요한 참견 사이의 비용을 용도별로 조정해야 합니다.

[논문](https://arxiv.org/abs/2603.03447)이 기존 VideoLLM과 구분되는 지점은 질문을 받은 뒤 영상을 분석하는 post-hoc 방식이 아닙니다. 프레임이 들어오는 동안 맥락을 유지하고, 사용자가 묻지 않아도 현재 사건이 발화할 가치가 있는지 계속 판단합니다.

## 능동형 모델은 세 결정을 동시에 한다

첫째는 연속 perception입니다. 완성된 영상 chunk를 모두 받은 뒤 시작하지 않고 streaming 입력을 인과적으로 처리해야 합니다. 과거 프레임을 무한히 보관할 수 없으므로 오래된 정보와 최근 사건 사이에서 제한된 context를 관리해야 합니다.

둘째는 trigger입니다. 시각적 변화와 현재 맥락을 바탕으로 말할 시점을 고르고 `<SPEAK>` action을 냅니다. 사건을 알아보는 정확도뿐 아니라 필요한 순간 전에 판단을 끝내는 시간이 중요합니다.

셋째는 출력량입니다. 짧은 위험 경고에 긴 배경 설명을 붙이면 정보가 맞아도 늦습니다. Proact-VL은 상황에 따라 한 줄 반응과 긴 설명의 길이를 조절하도록 학습합니다. 무엇을 말할지, 언제 시작할지, 언제 끝낼지가 한 문제로 묶입니다.

## Live Gaming Benchmark가 측정하는 것

연구진은 실시간성이 뚜렷한 게임 장면으로 Live Gaming Benchmark를 구성했습니다. 혼자 중계하는 solo commentary, 사람과 함께 말하는 co-commentary, 플레이어에게 조언하는 user guidance를 포함합니다.

게임은 사건 변화가 빠르고 발화 기회가 자주 오기 때문에 trigger와 latency를 함께 시험하기 좋습니다. 논문은 기존 VideoLLM보다 response latency를 낮추면서 video understanding 품질을 유지한 결과를 제시합니다.

이 결과를 의료·산업 안전에 바로 옮길 수는 없습니다. 게임의 잘못된 조언과 수술·보행 보조의 잘못된 경고는 피해 크기가 다르고, 허용할 false positive와 false negative도 다릅니다.

## 먼저 말하는 AI의 실패는 두 방향이다

모델이 사건을 놓치거나 늦게 말하면 필요한 개입이 사라집니다. 반대로 아무 일도 없는데 경고하거나 너무 자주 말하면 사용자가 알림을 무시하게 됩니다. 시각 hallucination은 단순한 답변 오류를 능동적인 방해로 바꿀 수 있습니다.

Streaming inference의 계산량도 남습니다. 질문이 있을 때만 모델을 호출하는 구조와 달리 프레임이 들어오는 동안 계속 perception을 수행합니다. 원문은 edge 장치의 실제 FPS와 비용을 충분히 확정하지 않으므로, “초저지연”을 모든 하드웨어의 보장값으로 읽어서는 안 됩니다.

## 제품 평가는 정확도보다 타이밍 표가 필요하다

작은 도메인에서 다음 사건별로 기준 시점을 먼저 라벨링해야 합니다.

1. 반드시 말해야 하는 사건
2. 말해도 되지만 필요하지 않은 사건
3. 절대 끼어들면 안 되는 사건
4. 짧은 경고와 긴 설명이 필요한 사건

그다음 event recall, false alarm 수, 사건 발생부터 발화까지의 시간, 응답 길이, 시간당 GPU 사용량을 함께 측정합니다. 사람이 말하고 있는 동안 끼어드는 문제도 co-commentary에서 따로 봐야 합니다.

게이밍과 방송 보조는 잘못된 발화의 피해가 상대적으로 낮아 초기 실험에 적합합니다. 의료·보행·산업 안전은 독립 센서와 사람이 최종 판단해야 하며 Proact-VL 하나를 안전 장치로 삼으면 안 됩니다. 이 연구의 기여는 능동적 AI가 완성됐다는 데 아니라, 비디오 이해 평가에 발화 시점과 양이라는 두 축을 명시적으로 추가한 데 있습니다.

[Hugging Face 논문 페이지](https://huggingface.co/papers/2603.03447)에서 결과를 볼 때도 평균 이해 점수와 함께 latency·trigger 조건을 확인해야 합니다.

## 발화 정책은 누구의 비용을 반영해야 하나

게임 중계에서는 놓친 흥미로운 순간보다 반복되는 평범한 말이 더 불편할 수 있습니다. 보행 보조에서는 반대로 위험을 놓치는 비용이 매우 큽니다. Event class마다 false positive·false negative 비용을 정하고 동일한 threshold를 모든 사건에 적용하지 않는 편이 좋습니다.

사용자도 말이 많은 assistant와 조용한 assistant에 대한 선호가 다릅니다. 개인화는 발화 빈도·길이 범위 안에서 가능하지만 반드시 경고해야 하는 사건을 끄게 해서는 안 될 수 있습니다. 정책 설정과 safety requirement를 분리하고 현재 mode를 사용자에게 표시해야 합니다.

Co-commentary에서는 사람이 말하는 동안의 interruption이 별도 비용입니다. 단순 voice activity뿐 아니라 사람이 질문을 마치는 시점, 다른 발화자와 turn을 구분해야 합니다. 내용이 맞아도 대화를 반복해서 가로막으면 실사용 품질은 낮습니다.

## streaming context는 어떻게 제한할까

과거 frame을 계속 저장할 수 없으므로 event summary와 최근 window를 관리해야 합니다. Window가 짧으면 오래전 약속이나 목표를 잊고, 길면 memory와 latency가 늘어납니다. 시간 간격이 긴 사건을 연결하는 benchmark와 빠른 변화 benchmark를 따로 둡니다.

Frame sampling을 낮추면 compute를 줄이지만 짧은 사건을 놓칠 수 있습니다. 일정 FPS 대신 motion이나 uncertainty에 따라 sampling을 바꿀 수도 있지만 sampling policy 자체의 지연과 오류를 측정해야 합니다. Audio·controller state가 필요한 사건을 video만으로 판단할 수 있는지도 구분합니다.

Context summary가 틀리면 이후 trigger가 잘못됩니다. 원본 frame reference와 summary version을 연결하고, 새 증거가 이전 요약과 충돌할 때 수정할 수 있어야 합니다. Session이 바뀌면 과거 게임·사용자 context가 다음 session에 섞이지 않게 초기화합니다.

## 실시간 지연은 어디서 나눠 재야 하나

Camera capture와 encode, model perception, trigger decision, text generation, TTS가 각각 시간을 사용합니다. 논문의 model latency만 재면 network와 audio 출력 지연을 놓칩니다. 사건 발생 frame을 기준으로 각 단계 timestamp를 남겨 end-to-end 지연의 병목을 찾습니다.

평균 지연보다 p95와 frame drop 조건이 중요합니다. 여러 stream을 동시에 처리하거나 GPU가 다른 작업과 경쟁할 때 늦어지는지 봅니다. 늦은 경고는 내용이 정확해도 실패로 분류하고, deadline이 지난 응답은 발화하지 않는 정책도 고려합니다.

계속 perception을 수행하는 비용은 질문 기반 assistant보다 큽니다. Idle scene에서 sampling·model 호출을 줄이는 정책과 중요한 사건 recall이 유지되는지 비교합니다. 시간당 GPU·전력과 실제 유용한 발화 수를 함께 기록해야 서비스 비용을 설명할 수 있습니다.

## 안전하지 않은 trigger는 어떻게 차단할까

Safety-critical event는 Proact-VL의 판단 하나로 action을 실행하지 않습니다. 별도 sensor·rule과 일치할 때 경고하고 사람이 최종 판단하도록 설계할 수 있습니다. Model confidence가 낮거나 입력이 가려지면 침묵보다 “확인 불가” 상태를 시스템에 전달해야 합니다.

발화 내용에도 허용 범위가 필요합니다. 위험 상황에서 긴 추론이나 불확실한 원인 설명보다 짧은 관찰과 안전한 행동 안내가 우선일 수 있습니다. Medical diagnosis처럼 모델 범위를 벗어난 조언은 trigger가 맞아도 차단해야 합니다.

배포 전에는 녹화 영상 replay로 event와 timing을 반복 검증하고, live shadow mode에서 실제 사용자에게 말하지 않은 채 trigger를 수집합니다. 오경보·누락과 interruption을 검토한 뒤 낮은 위험 영역부터 발화를 켭니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [VideoAuto-R1은 어떻게 답변을 149토큰에서 44토큰으로 줄였나]({% post_url 2026-01-10-VideoAuto-R1--Video-Auto-Reasoning-via-Thinking-Once--Answering-Twice %}) — 먼저 답하고 필요할 때만 추론한 뒤 다시 답하는 TOAT 구조, 신뢰도 분기와 과신 오답의 위험
- [미로를 풀 때 프레임을 늘리면 왜 나아질까: Visual Test-Time Scaling]({% post_url 2026-02-09-Thinking-in-Frames--How-Visual-Context-and-Test-Time-Scaling-Empower-Video-Reasoning %}) — Thinking in Frames가 중간 프레임을 시각적 추론 기록으로 쓰는 방식과 프레임 수를 늘리는 테스트타임 스케일링의 효과·비용을 정리합니다.
- [InternVideo는 생성·판별 학습을 어떻게 합치나: MVM·VLC·CMA]({% post_url 2025-02-16-InternVideo %}) — InternVideo가 마스크 복원으로 시공간 표현을, 비디오-언어 대조 학습으로 의미 정렬을 익힌 뒤 Cross-Model Attention으로 결합하는 구조를 설명합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Proact-VL은 중요한 장면을 발견하면 항상 먼저 말하나요?

모델이 SPEAK trigger를 학습하지만 사건·도메인별 recall과 false alarm이 다를 수 있습니다. 반드시 말할 사건과 침묵해야 할 사건을 따로 정의해 threshold와 timing을 검증해야 합니다.

### 게임 benchmark 성능을 안전 경고에 적용해도 되나요?

게임의 오경보와 의료·산업 현장의 오경보는 피해가 다릅니다. 안전 용도에는 별도 데이터·독립 센서·인간 확인과 실패 시 안전 동작이 필요합니다.

### 응답이 짧으면 실시간 요구를 만족한 건가요?

짧은 문장이어도 사건 인식과 생성 시작이 늦으면 경고가 쓸모없습니다. Frame 입력부터 trigger·첫 음성·완료까지 단계별 지연과 전체 자원 사용을 측정해야 합니다.
