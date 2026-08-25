---
layout: post
title:  "Google Assistant 로봇, IFTTT 대신 샘플 코드를 수정한 이유"
summary: "웹훅·Speech API·앱인벤터를 비교하고 gTTS와 시리얼 제어를 선택한 라즈베리파이 로봇 기록"
image:
  path: /assets/img/thumb/googlebot.jpg
  alt: 구글 어시스턴트 로봇 만들기 대표 이미지
date:   2019-08-01 13:00 -0400
categories: Basics
tags:
  - GoogleAssistant
  - RaspberryPi
  - 로보틱스
  - 음성AI
---

이 프로젝트의 결론은 **Google Assistant의 응답 기능을 남기려면 외부 웹훅을 하나 더 두기보다 `pushtotalk.py` 샘플에 로봇 동작을 연결하는 편이 목표에 가까웠다**는 것입니다.

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
