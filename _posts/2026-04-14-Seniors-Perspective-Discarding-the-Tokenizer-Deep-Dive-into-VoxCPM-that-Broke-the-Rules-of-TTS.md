---
layout: post
title: 'VoxCPM은 정말 토크나이저가 없을까: FSQ, 확산 TTS의 실제 구조'
date: '2026-04-14 06:53:59'
categories: Tech
tags:
  - 경량화
  - 음성AI
  - 트랜스포머
summary: 'VoxCPM이 기존 오디오 토큰 열 대신 의미, 음향 계층과 FSQ 병목, 로컬 확산 디코더를 쓰는 방식과 레퍼런스 품질, 장문, 사칭 위험을 정리합니다.'
description: "VoxCPM의 TSLM, RALM, FSQ, LocDiT 음성 생성 구조를 checkpoint별 사양, reference audio 품질, 장문 분할, latency, voice cloning 안전 기준으로 설명합니다."
github_url: https://github.com/OpenBMB/VoxCPM
faq:
  - question: "VoxCPM은 음성을 전혀 양자화하지 않는 tokenizer-free 모델인가요?"
    answer: "기존 audio codec의 긴 token 열은 쓰지 않지만 FSQ 병목이 있으므로, 모든 형태의 양자화가 사라졌다고 이해하면 안 됩니다."
  - question: "3초짜리 참조 음성이면 누구의 목소리든 안정적으로 복제할 수 있나요?"
    answer: "짧은 참조로 조건을 줄 수 있어도 잡음, 반향, 발화 내용과 화자 특성이 섞일 수 있어 여러 참조와 실패 조건을 시험해야 합니다."
  - question: "긴 글은 한 번에 합성하는 것이 자연스러운가요?"
    answer: "장문에서 누락이나 불명료한 발화가 생길 수 있으므로 문장 단위 분할 후 호흡, 음량, 운율 경계를 검사하는 편이 안전합니다."
image:
  path: https://opengraph.githubassets.com/1/OpenBMB/VoxCPM
  alt: "OpenBMB/VoxCPM GitHub 저장소 대표 이미지"
---

VoxCPM은 기존 오디오 코덱의 긴 이산 토큰 열을 쓰지 않지만, 표현을 전혀 양자화하지 않는 것은 아닙니다. 원문이 설명한 구조에는 FSQ 병목이 있으므로 “tokenizer-free”는 기존 음성 토크나이저를 제거했다는 의미로 제한해 읽어야 합니다. 실제 선택은 가장 좋은 sample보다 checkpoint 사양, 참조 음질, 장문 누락과 동시 요청 지연을 같은 test set으로 확인해 내려야 합니다.

## 의미 계획과 음향 세부를 나눠 만든다

MiniCPM-4 백본 위의 파이프라인은 LocEnc, TSLM, RALM과 LocDiT로 이어집니다. TSLM은 텍스트에서 발음, 강세와 큰 운율 계획을 만들고, RALM은 화자의 음색과 미세한 음향 잔차를 보탭니다. 의미와 음색을 같은 토큰에 억지로 담지 않고 계층으로 분리하는 접근입니다.

FSQ는 두 표현 사이에서 값의 범위를 제한하는 반이산 병목으로 작동합니다. 마지막 LocDiT는 지역 확산 Transformer로 잠재 표현을 파형으로 렌더링합니다. 이 구조는 “연속 파형을 그대로 자가회귀로 한 샘플씩 생성한다”는 설명과 다르며, 각 모듈의 역할을 구분해야 합니다.

| 단계 | 맡는 역할 | 결과에서 볼 실패 |
|---|---|---|
| LocEnc | 참조 음성의 국소 특징 표현 | 잡음, 반향까지 화자 특징처럼 유지 |
| TSLM | 텍스트와 큰 발음, 운율 계획 | 숫자, 고유명사 발음, 단어 누락 |
| RALM, FSQ | 화자, 음향 잔차와 병목 표현 | 음색 흔들림, 감정 과장, 정보 손실 |
| LocDiT | 잠재 표현을 최종 파형으로 생성 | 금속성 artifact, 경계 잡음, 느린 합성 |

이 표는 오류를 한 원인으로 단정하기 위한 것이 아니라 재현 실험을 나누기 위한 것입니다. 같은 텍스트에 참조만 바꿨을 때 문제가 움직이면 reference 경로를, 같은 참조에서 숫자 문장만 반복해 틀리면 텍스트, 발음 경로를 우선 점검할 수 있습니다.

“tokenizer-free”라는 이름만으로 latency나 품질 우위를 추론해서도 안 됩니다. 확산 decoder의 반복 계산, 자가회귀 단계와 serving 구현이 전체 속도를 결정합니다. 첫 audio chunk까지의 시간과 전체 RTF, GPU memory를 모델, 문장 길이별로 직접 측정해야 합니다.

## 버전별 수치는 같은 체크포인트인지 확인한다

원문은 v1.5의 44.1kHz와 6.25Hz 토큰 레이트, v2.0의 48kHz, 3초 참조 음성, VoxCPM-0.5B와 RTX 4090에서 RTF 0.17 같은 수치를 함께 소개합니다. 서로 다른 버전과 서빙 구현의 숫자를 한 모델 사양처럼 묶으면 안 됩니다. [VoxCPM 저장소](https://github.com/OpenBMB/VoxCPM)와 [0.5B 모델 페이지](https://huggingface.co/openbmb/VoxCPM-0.5B)에서 체크포인트별 샘플레이트, 요구 VRAM과 라이선스를 맞춰야 합니다.

원문의 비동기 Python 예시는 별도 nanovllm-voxcpm 구현을 가정하지만 패키지 버전, 설치와 입력 참조가 빠져 있어 완전한 실행법이 아닙니다. 공식 예제와 체크포인트가 맞는지 확인한 뒤 짧은 문장으로 먼저 재현해야 합니다.

model 이름이 같아도 sample rate와 weight version이 다르면 결과와 resource 요구량이 달라질 수 있습니다. 평가 기록에는 repository commit, checkpoint ID, inference parameter, reference 파일의 sample rate와 hardware를 남깁니다. 한 version의 품질 수치와 다른 version의 속도를 합쳐 “동시에 달성한 사양”으로 제시하지 않습니다.

설치 검증은 제공 sample이 재생되는지에서 끝내지 않습니다. 동일 입력을 두 번 생성했을 때 변화 폭, 잘못된 참조 path, GPU memory 부족과 중간 취소 시 resource가 회수되는지 확인합니다. 비동기 wrapper가 성공 상태를 반환했지만 audio가 비어 있는 경우도 실패로 기록해야 합니다.

## 출력 품질은 레퍼런스와 길이에 크게 흔들린다

제로샷 음성 복제에서는 참조에 섞인 에어컨 소음, 반향과 마이크 특성을 화자 특징처럼 따라 할 수 있습니다. 같은 화자의 깨끗한 음성과 휴대전화 녹음을 각각 넣어 발음 정확도, 화자 유사도, 잡음과 운율을 비교해야 합니다. 고해상도 출력이 깨끗한 입력을 자동으로 만들어 주지는 않습니다.

참조 test matrix에는 조용한 방, 실외 소음, 중립, 감정 발화, 짧은 3초와 더 긴 sample, 생성 문장과 같은 언어, 다른 언어를 넣습니다. 각 결과를 단순 선호도 하나로 합치지 말고 intelligibility, speaker similarity, prosody, background artifact를 나눠 사람이 blind 평가합니다. 평가자가 원본과 합성을 알고 들으면 기대가 점수에 섞일 수 있습니다.

참조 음성이 짧을수록 화자 고유 특성과 그 한 문장의 우연한 억양을 구분하기 어렵습니다. 서로 다른 문장 두세 개로 같은 음색이 유지되는지 보고, 특정 모음이나 감정에서만 닮는 결과를 안정적 복제로 세지 않습니다. 다른 사람의 음성을 negative control로 넣어 model이 텍스트 내용보다 reference identity에 실제로 반응하는지도 확인할 수 있습니다.

원문은 30초가 넘는 긴 텍스트에서 단어 누락이나 알아들을 수 없는 발화가 나타날 수 있다고 지적합니다. 문장 단위로 나눌 때는 경계의 호흡, 음량과 억양이 이어지는지도 들어야 합니다. 첫 오디오까지 걸리는 시간, 실시간 비율과 동시 요청 수를 별도로 측정해야 스트리밍 서비스 가능성을 판단할 수 있습니다.

분할기는 글자 수만 보지 말고 문장 부호, 숫자와 약어를 고려해야 합니다. 너무 짧게 자르면 매 조각의 첫 억양이 반복되고, 너무 길면 누락 위험이 커집니다. 조각 사이에 일정한 침묵을 붙이는 것만으로 해결되지 않으므로 loudness를 맞추고 경계 전후 단어를 자동 transcript와 사람이 함께 확인합니다.

load test에서는 단일 RTX 4090 수치만 복사하지 않고 목표 hardware에서 1, 2, 4개 동시 요청의 첫 chunk, 전체 생성 시간, peak VRAM과 OOM 복구를 잽니다. queue가 길어질 때 요청을 무한히 받지 말고 최대 대기와 취소 후 cleanup을 정합니다. offline batch와 interactive voice는 허용 latency가 다르므로 같은 serving 설정을 강요하지 않습니다.

## 목소리 복제에는 기술 외의 게이트가 필요하다

짧은 샘플로 화자 특성을 모방할 수 있다는 장점은 사칭과 보이스피싱 위험으로 그대로 이어집니다. 서비스에서는 음성 사용 권한을 확인하고, 복제 대상과 생성 기록을 남기며, 출력에 워터마크나 식별 수단을 적용하는 절차가 필요합니다. “Voice Design”도 실제 사람을 무단으로 흉내 내는 우회로가 되어서는 안 됩니다.

도입 판단은 가장 좋은 데모보다 잡음 참조, 긴 문장, 숫자, 고유명사와 동시 요청에서 내려야 합니다. VoxCPM은 음성 토큰화의 한계를 다른 계층 구조로 푸는 모델이지만, 입력 정제, 장문 분할, 안전 통제를 없애 주는 완성형 TTS 서비스는 아닙니다.

권한 있는 화자라도 원본 동의 범위가 광고, 번역, 실시간 대화까지 모두 포함하는지 확인해야 합니다. 참조 파일의 접근 권한과 삭제 기한, 생성 요청자, 사용 문안과 output ID를 연결해 나중에 철회, 추적할 수 있어야 합니다. 외부 공개 전에는 합성임을 알리는 표시와 신고, 차단 절차도 필요합니다.

배포 승격 기준은 checkpoint별로 고정합니다. 숫자, 날짜, 고유명사 50문장, 장문 20개와 여러 참조 조건에서 단어 누락, speaker similarity, artifact를 기록하고 기존 TTS와 blind 비교합니다. 새 weight나 serving engine을 적용한 뒤에는 같은 corpus를 다시 합성해 이전에 통과한 발음이 회귀하지 않는지 확인합니다.

합성이 중간에 실패했을 때 부분 audio를 정상 파일처럼 게시하지 않고 request ID와 실패 segment를 남깁니다. 재시도는 실패한 segment만 같은 설정으로 수행하되 앞뒤 경계가 달라지지 않는지 다시 검사합니다. model이 응답하지 않을 때 권한 없는 다른 voice나 임의 기본 화자로 조용히 fallback하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/OpenBMB/VoxCPM)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [콜센터 AI 응답이 1초 늦는 이유: VAD, Barge-in, SIP/RTP 지연 예산]({% post_url 2026-04-26-Call-Center-AI-Ending-the-Curse-of-Press-1-How-LLMs-are-Smashing-Legacy-IVR-under-the-Hood %}) — 실시간 콜센터 AI의 20ms 오디오 청크, VAD, Barge-in 흐름을 따라가며, STT, LLM, TTS와 레거시 SIP/RTP 구간의 지연, 비용, 오답 위험을 점검합니다.
- [Supertonic 99M TTS가 정말 167배 빠를까: RTF, 404MB, 음질의 교환]({% post_url 2026-05-21-The-Era-of-API-Hustling-is-Over-Implementing-167x-Faster-On-Device-TTS-with-99M-Ultra-Light-Architecture-Supertonic-Deep-Dive %}) — Supertonic의 99M 파라미터, 404MB ONNX 자산과 RTF 0.001~0.006 수치를 해석하고, 오프라인 TTS의 지연, 음질, 기기 호환성, 커스텀 음성 비용을 판단합니다.
- [Spark-TTS: 인공지능이 당신의 목소리를 만드는 방법]({% post_url 2025-03-13-SparkTTS %}) — Spark-TTS는 인공지능으로 더 자연스럽고 다양한 목소리를 만드는 혁신적인 기술입니다. 복잡한 기술을 단순화해 더 효율적으로 텍스트를 음성으로 변환합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### VoxCPM은 음성을 전혀 양자화하지 않는 tokenizer-free 모델인가요?

기존 audio codec의 긴 token 열은 쓰지 않지만 FSQ 병목이 있으므로, 모든 형태의 양자화가 사라졌다고 이해하면 안 됩니다.

### 3초짜리 참조 음성이면 누구의 목소리든 안정적으로 복제할 수 있나요?

짧은 참조로 조건을 줄 수 있어도 잡음, 반향, 발화 내용과 화자 특성이 섞일 수 있어 여러 참조와 실패 조건을 시험해야 합니다.

### 긴 글은 한 번에 합성하는 것이 자연스러운가요?

장문에서 누락이나 불명료한 발화가 생길 수 있으므로 문장 단위 분할 후 호흡, 음량, 운율 경계를 검사하는 편이 안전합니다.
