---
layout: post
title:  "Google Assistant 로봇, IFTTT 대신 샘플 코드를 수정한 이유"
summary: "Google Assistant 로봇에서 IFTTT 웹훅·Speech API·앱인벤터를 비교하고 pushtotalk 샘플에 gTTS 음성 응답과 시리얼 동작을 연결한 선택을 설명합니다."
description: "라즈베리파이 Google Assistant 로봇에서 웹훅 대신 샘플 코드를 수정한 이유와 음성 입력·gTTS 응답·시리얼 제어의 실패 지점을 정리합니다."
image:
  path: /assets/img/thumb/googlebot.jpg
  alt: 구글 어시스턴트 로봇 만들기 대표 이미지
date:   2019-08-01 13:00 -0400
categories: Basics
tags:
  - Google
  - 로보틱스
  - 음성AI
  - 온디바이스AI
faq:
  - question: "IFTTT 웹훅 대신 Assistant 샘플을 수정한 이유는 무엇인가요?"
    answer: "이 프로젝트는 Assistant의 기존 응답을 유지하면서 로봇 행동을 연결하는 것이 목표였습니다. 외부 웹훅보다 pushtotalk 샘플의 명령 처리 지점에 동작을 추가하는 편이 목표 구조에 가까웠습니다."
  - question: "gTTS를 연결하면 Google Assistant 응답과 같은 기능이 되나요?"
    answer: "아닙니다. gTTS는 정한 문장을 음성 파일로 바꾸고 재생하는 역할입니다. Assistant의 질문 이해와 응답 생성, wake word와는 별도 구성입니다."
  - question: "이 기록만으로 상시 대기하는 완성 로봇을 만들 수 있나요?"
    answer: "아닙니다. 당시 코드와 의존성을 전제로 한 핵심 조각이며 wake word 문제가 남아 있습니다. 입력·명령 해석·시리얼 행동·음성 응답을 각각 검증해야 합니다."
---

이 프로젝트의 결론은 **Google Assistant의 응답 기능을 남기려면 외부 웹훅을 하나 더 두기보다 `pushtotalk.py` 샘플에 로봇 동작을 연결하는 편이 목표에 가까웠다**는 것입니다. 다만 음성 인식, 명령 분기, 시리얼 동작, TTS 재생, wake word는 각각 따로 실패할 수 있습니다. 완제품처럼 묶기 전에 고정된 텍스트 명령으로 행동을 확인하고, 그다음 음성 입출력을 연결해야 원인을 찾기 쉽습니다.

## 먼저 버린 선택지와 그 이유

목표 동작은 “앞으로 가”, “뒤로 가”, “오른쪽/왼쪽”, “안녕”, “가지 마”, “잘 가”처럼 음성 문장을 로봇 시나리오에 연결하는 것이었습니다. 검토한 방법은 다섯 가지였습니다.

| 방법 | 연결 구조 | 당시 판단한 걸림돌 |
|---|---|---|
| IFTTT Webhook | Assistant → Webhook → Flask → Raspberry Pi | 요청을 받아 줄 서버 필요 |
| Arduino·Adafruit | Assistant → Webhook → Adafruit → IoT 장치 | ESP8266 추가 필요 |
| Google Speech API | 음성 인식 결과를 직접 사용 | 비용과 Assistant 기능 결합이 불확실 |
| 스마트미러 수정 | 기존 음성 UI 일부 변경 | 필요한 부분만 수정해야 함 |
| 앱인벤터 | 앱의 speech recognition 사용 | Assistant 자체 기능과는 다른 경로 |

IFTTT는 음성을 trigger로 쓰고 Webhooks로 HTTP 요청을 보내기 쉬워 보였습니다. 하지만 로봇 쪽에서 Flask 서버를 운영해야 한다는 문제가 남았습니다.

이 프로젝트에서 중요한 것은 단순 음성 인식뿐 아니라 Google Assistant의 기능을 함께 쓰는 것이었으므로, 최종적으로 SDK 샘플 수정안을 선택했습니다.

## 선택한 흐름: Assistant 입력과 로봇 행동 분리

예상한 구조는 wake word가 Assistant를 깨우고, 인식 결과에 따라 행동과 TTS를 선택하는 방식이었습니다.

```text
Snowboy → Google Assistant → action 또는 TTS
```

Google Assistant 설치는 기존 [라즈베리파이 Assistant API 기록](https://jjxxmiin.github.io/pi/2019/07/09/googleapi/)을 전제로 했습니다. 수정 대상으로 삼은 코드는 다음 저장소의 push-to-talk 샘플입니다.

```bash
git clone https://github.com/jjxxmiin/assistant-sdk-python
vi assistant-sdk-python/google-assistant-sdk/googlesamples/assistant/grpc/pushtotalk.py
```

이 명령은 로봇 행동이 구현된 완성 코드를 제공하지 않습니다. **어느 샘플 파일을 수정했는지 보여 주는 핵심 조각**일 뿐이며, 문장과 모터 명령을 매핑하는 코드는 결과 저장소에서 확인해야 합니다.

프로젝트 결과물은 [Raspi_google_robot 저장소](https://github.com/jjxxmiin/Raspi_google_robot)에 남아 있습니다.

## 응답 음성과 시리얼 연결 조각

행동만 수행하면 음성 응답이 비기 때문에 `gTTS`로 영어와 한국어 mp3를 생성했습니다.

```bash
pip install gTTS
```

```python
from gtts import gTTS

tts = gTTS('hello', lang='en')
tts.save('hello.mp3')
```

한국어 음성을 만들 때는 같은 조각의 text와 lang을 바꿨습니다.

```python
from gtts import gTTS

tts = gTTS('안녕', lang='ko')
tts.save('hello.mp3')
```

라즈베리파이와 외부 장치의 시리얼 통신에는 `/dev/ttyAMA0`을 사용했습니다. 먼저 `raspi-config`에서 Serial Port를 켜고 Serial Console을 끈 뒤, `/boot/config.txt`에 다음 설정을 추가한 기록입니다.

```text
enable_uart=1
# disable bluetooth
dtoverlay=pi3-disable-bt
```

Bluetooth 서비스를 끄고 재부팅한 뒤 Python에서 포트를 열었습니다.

```bash
sudo systemctl disable hciuart
sudo stty -F /dev/ttyAMA0
```

```python
import serial

ser = serial.Serial('/dev/ttyAMA0', '9600')
```

이 조각 역시 명령 전송·예외 처리·모터 제어를 포함한 완성 프로그램은 아닙니다. 포트와 통신 속도를 연결했던 위치를 보여 줍니다.

## 실제로 남은 한계

Snowboy는 wake word용으로 설치를 시도했지만 ALSA 오류를 해결하지 못해 최종 결과에 사용하지 못했습니다. 기록된 오류와 시도는 다음과 같습니다.

```bash
sudo apt-get install python-pyaudio python3-pyaudio sox
sudo apt-get install portaudio19-dev python-dev swig
git clone https://github.com/kitt-ai/snowboy
sudo apt-get install libatlas-base-dev
cd snowboy/swig/Python3
make
```

`jack_control start`도 시도했지만 ALSA의 `snd_pcm_hw_params_set_period_size_near` 오류는 미해결로 남았습니다. 최종 결과는 Snowboy가 아니라 **gTTS와 Google Assistant를 시나리오 형식으로 조합한 것**입니다.

따라서 이 글은 지금 그대로 실행하는 완제품 제작법이 아닙니다. 저장할 가치가 있는 부분은 “음성 인식 수단부터 고르기”가 아니라 다음 세 결정을 분리한 과정입니다.

1. Assistant 기능을 유지할지, 음성 텍스트만 받을지 정합니다.
2. 웹훅 서버와 로컬 샘플 수정 중 운영할 구조를 고릅니다.
3. 행동 제어, 음성 응답, wake word를 서로 독립된 실패 지점으로 다룹니다.

당시 참고한 TTS 문서는 [gTTS 문서](https://gtts.readthedocs.io/en/latest/?ababcaca), 대안 음성 인식 코드는 [SpeechRecognition 예제](https://webnautes.tistory.com/1247), AIY 자료는 [공식 GitHub 저장소](https://github.com/google/aiyprojects-raspbian)입니다.

## 로봇 동작은 어떤 순서로 분리해 시험해야 하나

첫 단계에서는 음성을 빼고 문자열 명령을 직접 함수에 넣습니다. “앞으로”, “정지”처럼 고정된 입력이 올바른 시리얼 값으로 바뀌고 모터 제어 쪽에서 수신되는지 확인합니다. 이 흐름이 불안정하면 Assistant나 TTS를 추가해도 오류 원인이 더 늘어날 뿐입니다.

두 번째로 음성 결과와 명령 분기를 연결합니다. 인식된 전체 문장을 기록하고, 비슷한 표현이나 불필요한 공백이 어떤 분기로 들어가는지 확인합니다. 로봇 행동을 실행하지 않는 일반 질문은 Assistant 응답 경로에 남겨야 프로젝트가 선택한 장점이 유지됩니다.

세 번째로 음성 응답과 wake word를 독립적으로 봅니다. gTTS 파일 생성과 재생은 네트워크·파일·오디오 장치에 의존할 수 있고, wake word는 상시 입력 감지의 별도 문제입니다. 한 기능이 실패해도 정지 명령이 실행될 수 있는지처럼 안전한 기본 동작을 먼저 정해야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [라즈베리파이 Google Assistant API 설정 순서: OAuth부터 푸시투토크까지]({% post_url 2019-07-09-googleapi %}) — 라즈베리파이 Google Assistant 샘플을 위해 마이크·스피커, 프로젝트와 OAuth 파일, Python 가상환경, push-to-talk 실행을 순서대로 검증합니다.
- [Claude Code로 영상을 대화하듯 편집하는 Video Use의 원리와 실전 활용법]({% post_url 2026-08-01-Video-Use-How-AI-Coding-Agents-Edit-Raw-Footage-Through-Text-and-FFmpeg %}) — Video Use는 Claude Code, Codex 등 AI 코딩 에이전트와 자연어로 대화하며 타임라인 편집 없이 영상을 완성하는 오픈소스 파이프라인입니다. 영상 프레임을 직접 LLM에 전달하는 대신 단어 단위 음성 스크립트를…
- [Supertonic 99M TTS가 정말 167배 빠를까: RTF·404MB·음질의 교환]({% post_url 2026-05-21-The-Era-of-API-Hustling-is-Over-Implementing-167x-Faster-On-Device-TTS-with-99M-Ultra-Light-Architecture-Supertonic-Deep-Dive %}) — Supertonic의 99M 파라미터·404MB ONNX 자산과 RTF 0.001~0.006 수치를 해석하고, 오프라인 TTS의 지연·음질·기기 호환성·커스텀 음성 비용을 판단합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### IFTTT 웹훅 대신 Assistant 샘플을 수정한 이유는 무엇인가요?

이 프로젝트는 Assistant의 기존 응답을 유지하면서 로봇 행동을 연결하는 것이 목표였습니다. 외부 웹훅보다 pushtotalk 샘플의 명령 처리 지점에 동작을 추가하는 편이 목표 구조에 가까웠습니다.

### gTTS를 연결하면 Google Assistant 응답과 같은 기능이 되나요?

아닙니다. gTTS는 정한 문장을 음성 파일로 바꾸고 재생하는 역할입니다. Assistant의 질문 이해와 응답 생성, wake word와는 별도 구성입니다.

### 이 기록만으로 상시 대기하는 완성 로봇을 만들 수 있나요?

아닙니다. 당시 코드와 의존성을 전제로 한 핵심 조각이며 wake word 문제가 남아 있습니다. 입력·명령 해석·시리얼 행동·음성 응답을 각각 검증해야 합니다.

## 명령 충돌과 안전 실패를 어떻게 다뤄야 하나

음성 문장에 여러 동작 단어가 들어갈 수 있으므로 분기 우선순위를 정합니다. “앞으로 가지 말고 정지” 같은 문장을 단순 포함 검사로 처리하면 앞선 단어가 잘못 실행될 수 있습니다. 인식 결과 전체와 선택된 명령을 기록하고, 모호한 문장에는 움직이지 않는 기본 동작을 두는 편이 안전합니다.

시리얼 제어는 보낸 값과 받은 값을 모두 확인합니다. Raspberry Pi 코드가 문자열을 보냈다고 모터 제어기가 같은 경계로 읽는다는 보장은 없습니다. 줄바꿈, 명령 종료 문자, 전송 간격을 양쪽 코드에서 맞추고, 로봇을 들어 올리거나 모터 전원을 분리한 상태에서 먼저 신호를 검증합니다.

TTS 재생 중 마이크가 자신의 스피커 소리를 다시 듣는 상황도 입력과 출력의 경계를 흐릴 수 있습니다. 응답 재생 동안 다음 명령을 받을지, 재생이 끝난 뒤 대기할지를 정하고 상태를 로그로 남깁니다. 네트워크나 TTS가 실패해도 정지 동작이 지연되지 않도록 행동 제어와 음성 응답을 분리합니다.

Wake word가 없을 때는 push-to-talk이라는 운영 조건을 명확히 표시합니다. 상시 대기 로봇처럼 소개하지 않고 버튼 입력부터 명령 완료까지 어느 단계가 구현됐는지 적습니다. 이후 hotword를 추가하더라도 감지, Assistant 호출, 시리얼 행동이 한 번씩만 실행되는지 반복 시험해야 합니다.

마지막으로 알 수 없는 명령, Assistant 오류, 시리얼 단절, 프로세스 종료를 각각 시험합니다. 어느 실패에서도 이전 이동 명령이 계속 유지되지 않는지 확인해야 합니다. 데모 영상의 성공 장면보다 이 실패 경로가 실제 로봇의 완성도를 더 정확히 보여 줍니다.

명령 처리 로그에는 원문 음성, 정규화한 문장, 선택한 행동과 시리얼 값을 한 줄로 남깁니다. TTS 문장과 실제 모터 동작이 같은 의도를 가리키는지도 확인합니다. 이 기록이 있으면 로봇이 잘못 움직였을 때 인식·분기·전송 중 어느 단계가 원인인지 역추적할 수 있습니다.

반복 명령도 시험합니다. 같은 “앞으로”가 연속으로 들어올 때 속도가 누적되는지, “정지” 뒤 이전 timer가 다시 동작하는지 확인합니다. 상태를 명시적으로 관리하지 않으면 각 함수가 단독으로는 맞아도 순서에 따라 다른 결과가 날 수 있습니다.
