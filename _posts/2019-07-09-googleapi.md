---
layout: post
title:  "라즈베리파이 Google Assistant API 설정 순서: OAuth부터 푸시투토크까지"
summary: "오디오 장치 확인, OAuth 클라이언트 등록, 가상환경 설치와 샘플 실행을 잇는 2019년 체크리스트"
image:
  path: /assets/img/thumb/googleapi.jpg
  alt: 구글 어시스턴트 끄적이기 대표 이미지
date:   2019-07-09 13:00 -0400
categories: Basics
tags:
  - GoogleAssistant
  - RaspberryPi
  - OAuth
  - 음성AI
---

라즈베리파이에서 Google Assistant 샘플을 실행하려면 **프로젝트·OAuth 등록보다 먼저 마이크와 스피커를 확인하고, 그다음 자격 증명과 Python 가상환경을 연결해야 합니다.**

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
