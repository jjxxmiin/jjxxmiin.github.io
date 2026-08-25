---
layout: post
title: "GPU 없는 로컬 TTS에 25MB면 충분할까? KittenTTS v0.8의 조건"
date: '2026-03-29 06:24:34'
categories: Tech
tags:
  - KittenTTS
  - 로컬TTS
  - 온디바이스AI
  - ONNX
  - 음성합성
summary: "15M·25MB Nano 모델이 CPU에서 음성을 만드는 구조와 eSpeak-ng·영어 중심·감정 표현 한계를 구분해, KittenTTS가 맞는 작업을 정리합니다."
author: AI Trend Bot
github_url: https://github.com/KittenML/KittenTTS
image:
  path: https://opengraph.githubassets.com/1/KittenML/KittenTTS
  alt: 'Human-like Voice in 25MB without GPU: A Deep Dive into KittenTTS Architecture'
---

**영어 안내 음성을 CPU에서 오프라인으로 만들 목적이라면 25MB급 KittenTTS Nano가 후보가 되지만, 한국어와 감정 연기까지 기대하면 맞지 않습니다.** 작은 모델이라는 장점은 언어 범위와 표현력, 시스템 의존성을 함께 받아들일 때 유효합니다.

[KittenTTS 저장소](https://github.com/KittenML/KittenTTS)의 원문 스냅샷은 v0.8, Nano 15M 파라미터와 Mini 80M 파라미터, Apache 2.0 라이선스를 소개합니다. Nano의 Int8 가중치는 약 25MB이며 24kHz 출력을 목표로 합니다. “GPU가 필요 없다”는 말은 CPU 실행 경로가 있다는 뜻이지 모든 기기에서 같은 실시간 속도가 나온다는 뜻은 아닙니다.

## 작아진 비결은 음소화·스타일·추론 엔진의 분업이다

KittenTTS는 StyleTTS2 계열을 바탕으로 텍스트 처리와 음성 생성을 여러 단계로 나눕니다. 숫자·통화·약어를 정규화하고, 긴 문장은 구두점 기준으로 최대 400자 정도의 조각으로 나눕니다. eSpeak-ng가 영어 텍스트를 음소로 바꾸고, TextCleaner가 이를 토큰 ID로 매핑합니다.

목소리 특성은 모델 가중치에 모두 넣지 않고 voices.npz의 스타일 임베딩에서 가져옵니다. 짧은 문장과 긴 문장에 다른 벡터를 선택해 호흡과 억양을 조절합니다. 최종 추론은 ONNX Runtime을 사용해 무거운 PyTorch 런타임 없이 CPU에서 실행하는 구조입니다.

## 25MB와 실제 앱 메모리는 같은 숫자가 아니다

25MB는 주로 Nano 가중치 크기를 가리킵니다. 실행할 때는 ONNX Runtime, 음소화 라이브러리, 스타일 파일, 오디오 버퍼와 애플리케이션 메모리가 추가됩니다. 긴 문장을 청킹하는 이유도 첫 오디오가 나오기까지의 지연과 메모리 급증을 줄이기 위해서입니다.

따라서 라즈베리파이나 브라우저에 넣기 전에는 모델 파일 크기보다 실제 RSS 메모리, 문장 길이별 RTF, 첫 오디오 지연을 재야 합니다. 원문이 언급한 WASM·ONNX Runtime Web 경로도 완성된 브라우저 배포 절차가 아니라 적용 가능성으로 읽는 편이 안전합니다.

## 설치 예시는 전제까지 확인해야 한다

원문의 파이썬 스니펫은 모델 생성과 파일 저장 흐름을 보여 주지만, 패키지 버전·운영체제별 eSpeak-ng 설치·모델 캐시를 모두 담은 완전한 실행법은 아닙니다. 특히 Windows 배포에서는 시스템 라이브러리와 환경 변수 처리가 사용자 경험의 일부가 됩니다. 최초 모델 다운로드 뒤 오프라인으로 쓸 계획이라면 캐시 파일과 라이선스도 배포물에 포함되는지 확인해야 합니다.

시험할 때는 [Nano 모델 페이지](https://huggingface.co/KittenML/kitten-tts-nano-0.1)의 파일과 현재 저장소 문서를 같은 버전으로 맞추고, 숫자·통화·약어가 들어간 자체 문장으로 발음을 듣는 것이 좋습니다. 원문에 있던 [설정 참고 글](https://sonusahani.com/kittentts-how-to-set-up-this-25mb-ai-voice-model-locally) 역시 프로젝트 버전이 달라질 수 있는 보조 자료입니다.

## 정보 전달에는 맞지만 연기와 다국어에는 한계가 있다

짧은 시스템 알림, 오프라인 리더, 인디 게임의 임시 대사처럼 명료한 영어 전달이 우선인 작업이 잘 맞습니다. 반면 한숨·속삭임·극적인 감정 변화가 필요한 오디오북과 캐릭터 연기에서는 큰 상용 모델보다 평탄하게 들릴 수 있습니다. 괄호와 특수 기호가 많은 문장도 전처리 결과를 확인해야 합니다.

원문 시점의 주력 언어는 영어이며 한국어를 포함한 다국어 품질은 프로덕션 수준으로 단정할 수 없습니다. 결론적으로 KittenTTS를 “클라우드 TTS의 전면 대체”로 보기보다, 개인정보를 외부로 보내지 않고 제한된 영어 문장을 읽는 로컬 엔진으로 평가해야 합니다.
