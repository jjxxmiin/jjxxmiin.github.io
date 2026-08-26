---
layout: post
title:  "라즈베리파이 Google Assistant API 설정 순서: OAuth부터 푸시투토크까지"
summary: "라즈베리파이 Google Assistant 샘플을 위해 마이크·스피커, 프로젝트와 OAuth 파일, Python 가상환경, push-to-talk 실행을 순서대로 검증합니다."
description: "라즈베리파이 Google Assistant API 설정을 오디오 장치, OAuth 자격 증명, 가상환경, push-to-talk 샘플로 나눠 진단하는 2019년 기록입니다."
image:
  path: /assets/img/thumb/googleapi.jpg
  alt: 구글 어시스턴트 끄적이기 대표 이미지
date:   2019-07-09 13:00 -0400
categories: Basics
tags:
  - Google
  - 튜토리얼
  - 파이썬
faq:
  - question: "Google Assistant 설정에서 OAuth보다 오디오를 먼저 확인하는 이유는 무엇인가요?"
    answer: "마이크와 스피커가 운영체제 수준에서 동작하지 않으면 자격 증명이 올바라도 음성 샘플은 실패합니다. 녹음과 재생을 먼저 검증하면 하드웨어 문제와 인증 문제를 분리할 수 있습니다."
  - question: "push-to-talk이 되면 hotword도 성공한 것인가요?"
    answer: "아닙니다. 이 기록에서도 push-to-talk과 wake word는 별도 단계이며 hotword 문제가 남았습니다. 음성 요청 성공과 상시 호출 감지는 서로 다른 구성으로 봐야 합니다."
  - question: "2019년 OAuth scope와 패키지 명령을 그대로 따라도 되나요?"
    answer: "현재 완전한 설치 절차로 사용하면 안 됩니다. 당시 콘솔과 패키지 흐름의 기록이므로 오디오·OAuth·가상환경·샘플을 분리하는 점검 순서를 참고해야 합니다."
---

라즈베리파이에서 Google Assistant 샘플을 실행하려면 **프로젝트·OAuth 등록보다 먼저 마이크와 스피커를 확인하고, 그다음 자격 증명과 Python 가상환경을 연결해야 합니다.** 녹음·재생, 인증, 샘플 실행은 서로 다른 실패 지점이므로 한꺼번에 설정하면 원인을 찾기 어렵습니다. 이 글의 명령은 2019년 스냅샷으로 보고, 단계별 산출물과 남은 hotword 한계를 중심으로 읽어야 합니다.

## 1. 프로젝트와 OAuth 파일 준비

기존 절차는 두 콘솔을 사용합니다.

- [Google Action Console](https://console.actions.google.com/): 프로젝트 생성과 Device registration
- [Google Cloud Console](https://console.cloud.google.com/home/dashboard): Google Assistant API 활성화와 OAuth 클라이언트 생성

![Device registration 화면](/assets/img/post_img/google/device.PNG)

기록된 순서는 다음과 같습니다.

1. Action Console에서 프로젝트를 만들고 장치를 등록합니다.
2. Cloud Console의 API 및 서비스에서 Google Assistant API를 찾아 활성화합니다.
3. 사용자 인증 정보에서 OAuth 클라이언트 ID를 만듭니다.
4. OAuth 2.0 클라이언트 JSON을 내려받아 라즈베리파이의 `/home/pi/`로 옮깁니다.

이 JSON은 뒤의 인증 명령이 읽는 입력 파일입니다. 실제 경로를 확인하기 전에 예시의 `/path/to/client/json`을 그대로 실행하면 인증 단계가 시작되지 않습니다.

## 2. 오디오 입출력부터 검증하기

연결된 녹음 장치와 재생 장치를 먼저 확인합니다.

```bash
arecord -l
aplay -l
```

기본 장치를 지정할 때 사용한 `.asoundrc` 구조는 다음과 같습니다. `<card number>`와 `<device number>`는 앞 명령의 실제 결과로 바꿔야 합니다.

```text
pcm.!default {
  type asym
  capture.pcm "mic"
  playback.pcm "speaker"
}

pcm.mic {
  type plug
  slave {
    pcm "hw:<card number>,<device number>"
  }
}

pcm.speaker {
  type plug
  slave {
    pcm "hw:<card number>,<device number>"
  }
}
```

5초 동안 녹음한 raw 파일을 다시 재생하면 API와 무관하게 입력 경로를 확인할 수 있습니다.

```bash
arecord --format=S16_LE --duration=5 --rate=16000 --file-type=raw out.raw
aplay --format=S16_LE --rate=16000 out.raw
speaker-test -t wav
```

볼륨은 `alsamixer`로 조절했습니다. 이 테스트가 실패한다면 Assistant 패키지를 다시 설치하기 전에 카드·장치 번호와 오디오 출력을 먼저 해결해야 합니다.

## 3. 가상환경·패키지·자격 증명 연결

원문에서 사용한 시스템 의존성과 Python 가상환경 명령입니다.

```bash
sudo apt-get update
sudo apt-get install portaudio19-dev libffi-dev libssl-dev
sudo apt-get install python3-dev python3-venv

python3 -m venv py3
py3/bin/python -m pip install --upgrade pip setuptools
source py3/bin/activate
```

가상환경을 활성화한 뒤 Assistant 라이브러리, SDK 샘플, OAuth 도구를 설치했습니다.

```bash
python -m pip install --upgrade google-assistant-library
python -m pip install --upgrade google-assistant-sdk[samples]
python -m pip install --upgrade google-auth-oauthlib[tool]
```

OAuth JSON의 실제 위치를 넣어 인증합니다.

```bash
google-oauthlib-tool \
  --scope https://www.googleapis.com/auth/assistant-sdk-prototype \
  --save \
  --headless \
  --client-secrets /path/to/client/json
```

명령이 안내하는 URL에서 로그인과 동의를 마친 뒤 생성된 코드를 터미널에 입력하는 흐름입니다.

## 4. 샘플 선택과 이 기록의 한계

기존 글은 두 샘플을 구분했습니다.

```bash
googlesamples-assistant-hotword --device_model_id my-model
```

```bash
googlesamples-assistant-pushtotalk \
  --project-id "INPUT/project-id" \
  --device_model_id "INPUT/device-model-id"
```

- Library 샘플: hotword 사용
- Service 샘플: push-to-talk 사용

한국어 push-to-talk 확인에는 아래 옵션을 기록했습니다.

```bash
googlesamples-assistant-pushtotalk --lang ko-KR
```

당시에는 push-to-talk이 되면 hotword가 동작하지 않는 문제가 남아 있었고, 글에서도 해결됐다고 주장하지 않았습니다.

또한 이 명령들은 2019년의 패키지명·scope·콘솔 흐름에 맞춰진 기록입니다. 현재의 완전한 설치 절차로 간주하지 말고, 실패 지점을 **오디오 → OAuth 파일 → 가상환경 → 샘플 종류** 순으로 나누는 체크리스트로 활용해야 합니다.

기존 참고 자료는 [라즈베리파이 설치 기록](https://ukayzm.github.io/installing-google-assistant/)과 [오디오 설정 설명](https://www.sigmdel.ca/michel/ha/rpi/voice_rec_02_en.html#decoder)입니다.

## 어느 단계까지 성공했는지 어떻게 판정하나

오디오 단계의 성공 기준은 마이크 입력을 파일로 저장하고 같은 장치에서 소리를 재생하는 것입니다. Assistant 샘플을 거치지 않고도 이 두 동작을 확인할 수 있어야 합니다. 장치 번호가 재부팅이나 연결 순서에 따라 달라지는지 확인하고, 녹음 파일이 비어 있다면 OAuth 설정으로 넘어가지 않습니다.

인증 단계에서는 프로젝트에서 받은 클라이언트 파일과 사용자가 승인한 토큰을 구분합니다. 파일 경로가 현재 가상환경의 실행 명령과 맞는지 확인하고, 인증 오류와 import 오류를 같은 문제로 보지 않습니다. 패키지가 다른 Python에 설치된 경우에는 자격 증명을 다시 발급해도 해결되지 않습니다.

샘플 단계에서는 텍스트 요청, push-to-talk, hotword를 별도의 기능으로 봅니다. 앞 단계가 성공한 뒤 기능을 하나씩 추가하고, 언어 옵션과 오디오 장치가 같은 실행 환경에 전달되는지 확인합니다. 이 기록처럼 push-to-talk만 작동했다면 그 상태를 성공 범위로 명시해야 완제품처럼 과장하지 않을 수 있습니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Google Assistant 로봇, IFTTT 대신 샘플 코드를 수정한 이유]({% post_url 2019-08-01-googlebot %}) — Google Assistant 로봇에서 IFTTT 웹훅·Speech API·앱인벤터를 비교하고 pushtotalk 샘플에 gTTS 음성 응답과 시리얼 동작을 연결한 선택을 설명합니다.
- [라즈베리파이에서 NCS2 추론이 막힐 때: OpenVINO IR 변환 체크리스트]({% post_url 2019-03-08-NCS2 %}) — 라즈베리파이 3와 Neural Compute Stick 2에서 OpenVINO 추론을 준비하는 흐름을 학습·동결·IR 변환·MYRIAD 실행 단계로 나눕니다. XML/BIN 쌍, input shape, output node, USB…
- [NCS2에서 YOLOv3가 실행되지 않을 때: FP16 IR 변환과 입력 Shape 점검]({% post_url 2019-03-30-YOLOOpenvino %}) — 라즈베리파이 3와 Neural Compute Stick 2에서 YOLO를 추론하기 위해 weights를 PB와 OpenVINO IR로 바꾸는 흐름을 정리합니다. FP16 지정, 416×416 입력, NHWC·NCHW 변환…
<!-- internal-links:end -->

## 자주 묻는 질문

### Google Assistant 설정에서 OAuth보다 오디오를 먼저 확인하는 이유는 무엇인가요?

마이크와 스피커가 운영체제 수준에서 동작하지 않으면 자격 증명이 올바라도 음성 샘플은 실패합니다. 녹음과 재생을 먼저 검증하면 하드웨어 문제와 인증 문제를 분리할 수 있습니다.

### push-to-talk이 되면 hotword도 성공한 것인가요?

아닙니다. 이 기록에서도 push-to-talk과 wake word는 별도 단계이며 hotword 문제가 남았습니다. 음성 요청 성공과 상시 호출 감지는 서로 다른 구성으로 봐야 합니다.

### 2019년 OAuth scope와 패키지 명령을 그대로 따라도 되나요?

현재 완전한 설치 절차로 사용하면 안 됩니다. 당시 콘솔과 패키지 흐름의 기록이므로 오디오·OAuth·가상환경·샘플을 분리하는 점검 순서를 참고해야 합니다.

## 오디오가 동작하는데 샘플이 실패할 때 무엇을 비교하나

현재 shell의 Python 경로와 가상환경 이름, 설치된 패키지를 먼저 확인합니다. Terminal 하나에서는 가상환경을 활성화했지만 다른 terminal의 명령은 시스템 Python을 사용할 수 있습니다. Import 오류가 난다면 OAuth 파일을 다시 만들기 전에 실행 interpreter와 설치 위치를 맞춥니다.

자격 증명 파일은 샘플 명령에 전달한 경로와 실제 파일 위치를 대조합니다. 상대경로는 실행 디렉터리가 바뀌면 다른 파일을 가리킬 수 있으므로 진단 중에는 명확한 위치를 확인합니다. 파일 내용을 로그에 그대로 출력하지 않고 존재 여부와 읽기 권한, 어떤 프로젝트용 파일인지 구분합니다.

인증 브라우저 흐름을 마쳤는데 요청이 거부된다면 프로젝트 설정, 승인한 사용자, 사용한 scope가 같은 흐름에 속하는지 봅니다. 이전 실행에서 만든 토큰이 다른 설정과 섞일 수도 있으므로 어느 파일을 언제 만들었는지 기록합니다. 단순히 파일을 여러 번 복사하면 어떤 자격 증명이 실제 사용됐는지 더 불명확해집니다.

샘플이 음성을 듣지만 응답하지 않는다면 인식 결과와 요청 단계, 재생 단계를 나눕니다. 마이크 frame이 들어오는지, 텍스트가 만들어졌는지, 응답 오디오가 생성됐는지, 스피커 장치로 전달됐는지를 각각 확인합니다. “아무 소리도 없다”는 한 증상 안에 네 문제가 있을 수 있습니다.

언어 옵션을 바꿀 때는 같은 고정 문장으로 비교합니다. 인식 언어와 응답 언어, 프로그램이 보내는 locale이 일치하는지 확인하고, 마이크 품질 문제와 언어 설정 문제를 섞지 않습니다. 녹음 파일을 따로 들어 보면 실제 입력이 알아들을 수 있는 수준인지 판단할 수 있습니다.

Push-to-talk이 통과한 뒤에만 hotword를 붙입니다. Wake word detector가 시작되는지, 감지 이벤트가 샘플 호출로 연결되는지, 한 번 실행한 뒤 다시 대기 상태로 돌아오는지를 별도로 시험합니다. 당시 기록에서 이 단계가 해결되지 않았다는 범위를 그대로 유지하는 것이 중요합니다.

재부팅 뒤에도 필요한 환경 변수와 오디오 설정이 유지되는지 확인합니다. 수동 terminal에서만 성공하고 서비스 실행에서 실패한다면 사용자, 작업 디렉터리, 가상환경과 장치 권한 차이를 봅니다. 이 검증을 통해 일회성 데모와 반복 가능한 실행을 구분할 수 있습니다.

오류 기록에는 실행 시각, 사용한 오디오 장치, Python 경로, 샘플 종류와 첫 오류를 남깁니다. 인증을 반복할 때마다 상태가 달라질 수 있으므로 어떤 설정에서 성공했는지 재현 가능한 명령으로 보관합니다. 다만 자격 증명과 토큰 값 자체는 로그나 공개 저장소에 넣지 않습니다.

네트워크가 끊긴 경우, 마이크가 없는 경우, 스피커 출력이 막힌 경우를 각각 시험합니다. 프로그램이 멈추는지 오류를 알리는지, 다음 요청을 받을 수 있는지 확인해야 합니다. 이 실패 조건을 설명하면 당시 샘플의 가능성과 실제 음성 기기의 운영 범위를 구분할 수 있습니다.

테스트 문장은 짧은 명령, 긴 질문, 주변 소음이 있는 입력으로 나눕니다. 인식 실패와 API 응답 실패를 같은 “Assistant 오류”로 묶지 않고, 어느 단계까지 데이터가 전달됐는지 기록합니다. 성공률을 주장하기보다 재현 가능한 실패 예시를 남기는 편이 이 기록의 범위에 맞습니다.
