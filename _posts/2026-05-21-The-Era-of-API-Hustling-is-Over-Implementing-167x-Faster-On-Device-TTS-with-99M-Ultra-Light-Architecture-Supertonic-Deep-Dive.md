---
layout: post
title: 'Supertonic 99M TTS가 정말 167배 빠를까: RTF·404MB·음질의 교환'
date: '2026-05-21 18:54:26'
categories: Tech
tags:
  - Supertonic
  - 온디바이스TTS
  - ONNX
  - RTF
  - 음성AI
summary: Supertonic의 99M 파라미터·404MB ONNX 자산과 RTF 0.001~0.006 수치를 해석하고, 오프라인 TTS의 지연·음질·기기 호환성·커스텀 음성 비용을 판단합니다.
author: AI Trend Bot
github_url: https://github.com/supertone-inc/supertonic
image:
  path: https://opengraph.githubassets.com/1/supertone-inc/supertonic
  alt: 'The Era of API Hustling is Over: Implementing 167x Faster On-Device TTS with
    99M Ultra-Light Architecture (Supertonic Deep Dive)'
---

Supertonic의 “167배 빠른 TTS”는 특정 하드웨어에서 보고된 순수 추론 RTF를 뜻하며, 모든 기기의 첫 음성 지연과 전체 사용자 경험을 보장하는 수치는 아닙니다.

## 167배는 RTF 0.006을 뒤집은 값이다

RTF(Real-time Factor)는 음성 1초를 만드는 데 걸린 시간을 음성 길이로 나눈 값입니다. RTF가 0.006이면 계산상 실시간보다 약 167배 빠릅니다. 원문은 NVIDIA RTX 4090에서 0.001, Apple M4 Pro에서 0.006이라는 값을 제시합니다.

이 수치를 서비스 지연 시간과 바로 같게 보면 안 됩니다. 모델 다운로드와 초기 적재, 텍스트 정규화, 첫 오디오 조각이 나올 때까지의 시간, WAV 변환과 재생 준비는 별도입니다. 문장 길이, 언어, 실행 제공자와 기기 발열 상태도 결과를 바꿉니다. 따라서 “음성 30초 생성 시간”과 “사용자가 재생을 처음 듣는 시간”을 따로 측정해야 합니다.

## 99M 모델이 빠른 이유와 404MB의 의미

원문 기준 Supertonic V3는 약 99M 파라미터와 404MB의 공개 ONNX 자산으로 구성되며 31개 언어와 `<laugh>`, `<breath>` 같은 표현 태그를 지원합니다. 파이프라인은 세 부분으로 나뉩니다.

- Speech Autoencoder가 파형을 잠재 표현으로 압축합니다.
- Flow-Matching 기반 Text-to-Latent 모듈이 원문 설명 기준 두 번의 추론 단계로 음성 특징을 만듭니다.
- Duration Predictor가 텍스트와 음성 길이를 맞춥니다.

ONNX Runtime을 사용해 CPU, WebGPU, WASM, JVM JNI 등 여러 실행 환경을 겨냥할 수 있다는 점이 온디바이스 배포의 기반입니다. 다만 99M은 대형 음성 모델과 비교해 가벼운 것이지, 404MB 다운로드가 모바일·브라우저에 항상 작은 것은 아닙니다. 캐시가 비어 있는 첫 방문, 저용량 기기, 느린 네트워크에서는 모델 전달 자체가 병목이 됩니다.

## 오프라인은 서버 비용을 기기 비용으로 옮긴다

클라이언트에서 합성하면 텍스트를 외부 TTS API로 보내지 않아도 되고 네트워크 단절에도 동작할 수 있습니다. 호출량에 비례하는 서버 추론 비용도 줄일 수 있습니다. 대신 사용자의 CPU·GPU, 메모리, 배터리와 저장 공간을 사용합니다.

브라우저에서는 WebGPU 지원 여부와 WASM 대체 경로를 함께 확인해야 합니다. JVM 연동도 외부 파이썬 서비스를 없앨 가능성은 있지만, JNI와 ONNX Runtime의 플랫폼별 패키징·메모리 해제·장애 처리가 새 운영 대상이 됩니다. “온디바이스”는 인프라가 사라진다는 뜻이 아니라 지원해야 할 하드웨어 조합이 늘어난다는 뜻입니다.

음질도 용도별로 들어야 합니다. 짧은 안내, 접근성 읽기, 오프라인 알림에는 속도와 프라이버시가 우선일 수 있습니다. 긴 오디오북이나 섬세한 감정 연기에서는 99M 모델의 표현력이 더 큰 모델보다 부족할 수 있습니다. 표현 태그 지원만으로 문맥에 맞는 연기가 자동 보장되지는 않습니다.

## 도입 전에는 같은 문장으로 네 축을 비교한다

파일럿은 빠른 한 대에서만 돌리지 말고 실제 하위 기기를 포함해야 합니다.

1. 한국어·영어·숫자·통화·고유명사가 섞인 고정 문장 묶음을 만듭니다.
2. 콜드 스타트, 첫 오디오 지연, 전체 RTF를 각각 측정합니다.
3. CPU·메모리·배터리와 404MB 자산의 다운로드·캐시 실패를 기록합니다.
4. 사람 평가로 발음, 긴 문장 연결, 표현 태그, 반복 합성의 안정성을 듣습니다.
5. 지원하지 않는 환경에서 서버 TTS로 돌아갈지 기능을 끌지 정합니다.

원문에 나온 파이썬 호출 예시는 구조를 설명하는 스냅샷입니다. 실제 사용에는 패키지와 모델 버전, 자산 다운로드 정책, 음성 스타일 JSON의 출처, 지원 태그, 오류·파일 저장 처리가 더 필요합니다. 커스텀 보이스를 만들 때 Voice Builder 의존과 비용도 별도 항목으로 계산해야 합니다.

결론적으로 Supertonic은 “클라우드 API보다 항상 낫다”가 아니라, 음질 요구가 맞고 실제 대상 기기에서 콜드 스타트까지 통과할 때 강한 선택지입니다. 167배라는 숫자보다 서비스가 허용할 첫 음성 지연과 최저 기기 기준이 도입 여부를 결정합니다.

## 참고 자료

- https://github.com/supertone-inc/supertonic
- https://huggingface.co/Supertone/supertonic-3
- https://huggingface.co/spaces/Supertone/supertonic-2
- https://supertone.ai/voice-builder
