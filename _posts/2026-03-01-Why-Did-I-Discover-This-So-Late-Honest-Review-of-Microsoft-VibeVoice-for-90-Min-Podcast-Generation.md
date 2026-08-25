---
layout: post
title: 'VibeVoice로 90분 팟캐스트를 한 번에 만들까: 7.5Hz 토큰과 중단된 공식 지원'
date: '2026-03-01 18:30:18'
categories: Tech
tags:
  - VibeVoice
  - 장문TTS
  - 다중화자
  - AudioTokenizer
  - Diffusion
summary: 7.5Hz 토크나이저와 LLM·Diffusion 구조가 4명·90분 음성을 다루는 방식, community fork 의존과 환각 한계를 짚습니다.
author: AI Trend Bot
github_url: https://github.com/microsoft/VibeVoice
image:
  path: https://opengraph.githubassets.com/1/microsoft/VibeVoice
  alt: Why Did I Discover This So Late? Honest Review of Microsoft VibeVoice for 90-Min
    Podcast Generation
---

VibeVoice는 원문 기준 최대 4명의 화자와 90분 audio를 한 번의 긴 generation으로 다루도록 설계됐지만, 공식 TTS code가 내려간 상태에서는 community fork·quantization·hardware 조합을 production 지원으로 볼 수 없습니다. 장문 일관성의 가능성과 유지보수·voice misuse·script hallucination의 위험을 함께 검증해야 합니다.

## 7.5Hz가 긴 대화를 가능하게 하는 이유

기존 TTS가 높은 frame rate로 audio token을 만들면 90분 sequence가 매우 길어집니다. VibeVoice는 acoustic과 semantic 정보를 7.5Hz의 ultra-low frame-rate token으로 압축해 context가 다뤄야 할 step 수를 줄입니다. 원문은 1.5B와 7B model, 최대 90분, 최대 4명 speaker를 제시합니다.

낮은 token rate는 memory를 줄이는 대신 tokenizer가 한 step에 더 많은 음성 정보를 담아야 한다는 뜻입니다. 미세한 발음, 호흡, 배경 소리와 화자 구분을 얼마나 보존하는지는 길이 수치만으로 알 수 없습니다. “90분 생성 가능”과 90분 전체가 같은 품질·화자 identity를 유지한다는 주장도 구분해야 합니다.

## LLM은 대화 흐름을, Diffusion은 음향을 맡는다

원문은 VibeVoice를 LLM과 next-token diffusion의 hybrid로 설명합니다. LLM이 긴 script와 turn context를 처리하고, diffusion component가 acoustic texture를 생성합니다. 문장별 TTS를 따로 호출해 붙이는 방식보다 pause와 speaker turn을 한 context에서 학습할 여지가 있습니다.

그 대신 두 계층의 오류가 함께 나타납니다.

- LLM 쪽에서는 script에 없는 말이나 과도한 숨소리가 추가될 수 있습니다.
- Diffusion·tokenizer 쪽에서는 voice가 섞이거나 texture가 불안정할 수 있습니다.
- 두 사람이 동시에 말하는 overlap에서는 single line으로 뭉개지는 문제가 언급됩니다.
- Emotion과 speed는 direction cue를 조정해야 할 수 있습니다.

긴 audio를 한 번에 만들면 중간 오류 하나를 수정할 때 전체를 다시 생성해야 하는지도 중요한 workflow 질문입니다.

## Speaker tag 예시는 실행 코드가 아니다

원문은 ComfyUI에서 사용할 script 형태로 다음 예시를 보여줍니다.

```text
[S1]: (한숨) 코딩하다 막힐 때마다 산책을 가는데, 어제는 산책하다가 아예 길을 잃었어요.
[S2]: 하하, 그래서 버그는 잡았나요?
[S1]: 아뇨, 대신 기가 막힌 동네 국밥집을 찾았습니다. 버그는 내일의 저에게 맡기기로 했죠.
[S2]: 역시, 최고의 디버깅 툴은 든든한 국밥이죠!
```

이 block은 speaker와 direction cue 문법을 보여주는 입력 예시입니다. Model download, ComfyUI node 설치, checkpoint·quantization 선택, seed, output format, VRAM 설정이 없으므로 완전한 실행 가이드가 아닙니다.

원문은 Enemyx-net/VibeVoice-ComfyUI와 4-bit·8-bit model을 사용하면 RTX 3060·4070 Ti 같은 12GB VRAM에서도 실행 가능하고 Apple Silicon MPS도 지원한다고 설명합니다. 해상도에 해당하는 audio 설정, model size, 생성 길이와 속도 표가 없어 “12GB에서 90분이 쾌적하다”는 보장으로 읽을 수 없습니다.

## 공식 코드 철수는 기능보다 큰 운영 변수다

원문에 따르면 Microsoft는 2025년 8월 공개 뒤 악용 사례 우려로 9월 5일 TTS code를 내렸고, 현재 사용 흐름은 community backup에 의존합니다. 2026년 1월 ASR model이 나왔다는 설명도 TTS maintenance가 재개됐다는 뜻은 아닙니다.

도입 전에 확인할 항목은 다음과 같습니다.

1. 실제 사용하는 fork와 commit이 무엇인가
2. Weight·code license와 배포 가능한 범위
3. Security fix와 dependency update 담당자
4. Model 출처와 file checksum
5. Voice sample의 동의·삭제·output 표시 정책

장기 지원이 없는 fork는 demo에는 유용해도 business-critical production에서는 취약점과 model compatibility를 스스로 관리해야 합니다.

## 90분 데모보다 구간별 실패율을 측정한다

평가는 30초·10분·90분으로 길이를 늘리고, 각 구간에서 speaker identity, script word error, 빠진 문장, 추가 발화, pause, overlap 실패, 생성 시간과 peak VRAM을 기록해야 합니다. 같은 seed 반복에서 어느 정도 변하는지도 봅니다.

Podcast와 audiobook prototype처럼 후편집이 가능한 작업은 장문 generation의 이득이 큽니다. 반면 정확한 대본 준수와 즉시 수정, 공식 support가 중요한 service라면 문장·scene 단위 TTS가 더 관리하기 쉬울 수 있습니다. VibeVoice의 기술적 의미는 “90분 완성품을 버튼 한 번에 보장”하는 데 아니라, 7.5Hz token과 hybrid generator로 long-form speech context를 작게 만드는 방향을 보여준 데 있습니다.

참고: [Microsoft VibeVoice 저장소](https://github.com/microsoft/VibeVoice), [Community ComfyUI node](https://github.com/Enemyx-net/VibeVoice-ComfyUI)
