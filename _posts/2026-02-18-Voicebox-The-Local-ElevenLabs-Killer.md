---
layout: post
title: 'Voicebox는 ElevenLabs를 로컬로 대체할까: Qwen3-TTS 설치·GPU·동의 체크'
date: '2026-02-18'
categories: Tech
tags:
  - 음성AI
  - Qwen
  - 파이썬
  - 반도체
summary: Qwen3-TTS와 Whisper를 로컬 UI로 묶은 Voicebox의 기능, 설치 스냅샷, 하드웨어 비용과 음성 복제 동의 조건을 점검합니다.
description: 'Voicebox가 Qwen3-TTS·Whisper·편집 UI를 로컬 앱으로 묶는 구조, 설치와 GPU 비용, 음성 복제 동의·데이터 삭제 검증 기준을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/jamiepine/voicebox
  alt: "jamiepine/voicebox GitHub 저장소 대표 이미지"
---

Voicebox는 Qwen3-TTS 기반 음성 복제·합성과 Whisper 전사를 로컬 데스크톱 앱에서 처리할 수 있지만, ElevenLabs와 품질·속도·언어 지원이 동일하다고 보장하는 대체품은 아닙니다. 로컬 처리는 음성 파일의 외부 전송을 줄이는 장점이 있지만, 모델 다운로드·GPU 자원·설치 유지보수와 복제 대상의 동의는 사용자가 책임져야 합니다.

## 단순 TTS보다 로컬 제작 스튜디오에 가깝다

Voicebox는 몇 초 분량의 음성 sample로 voice profile을 만들고, 여러 sample을 조합해 합성할 수 있다고 소개됩니다. 텍스트를 음성으로 바꾸는 기능 외에도 여러 화자의 대화를 배치하는 Story Editor, timeline clip 편집, 생성 history를 제공합니다. Whisper가 업로드한 audio를 text로 변환해 다시 수정·생성하는 흐름도 포함됩니다.

이 기능 범위 때문에 비교 대상은 TTS API 하나가 아닙니다. 다음 작업을 한 앱에서 로컬로 묶는 것이 가치입니다.

- voice sample 녹음·업로드와 profile 관리
- Qwen3-TTS speech generation
- 여러 화자의 conversation 구성
- Whisper transcription
- clip 순서와 간격 편집
- 생성 파일과 설정의 local history

“몇 초면 복제”와 실제 품질은 별개입니다. 원문의 사용 가이드는 10~30초의 깨끗한 sample을 권하므로 잡음, 억양, 언어가 달라질 때 필요한 길이를 직접 비교해야 합니다.

## Tauri UI 뒤에서 Python inference가 돈다

Desktop app은 Tauri(Rust)를 사용하고, frontend는 React·TypeScript·Tailwind CSS, Zustand와 React Query로 구성된다고 설명됩니다. 로컬 Python FastAPI server가 AI inference를 담당하며 macOS에서는 MLX, 다른 플랫폼에서는 PyTorch를 선택합니다. 설정과 생성 데이터는 SQLite에 저장됩니다.

이 구조는 Electron 대신 작은 desktop shell을 쓴다는 장점이 있지만, 전체 memory는 UI만으로 결정되지 않습니다. Qwen3-TTS와 Whisper model, Python process, audio buffer가 대부분의 GPU·RAM을 사용합니다. Apple Silicon에서 기존 대비 5배 빠르다는 원문 주장도 비교 model, chip, precision이 없으므로 자신의 장비 속도로 간주하면 안 됩니다.

Local REST API를 다른 프로그램에서 호출할 수 있다는 설명도 있습니다. 편리하지만 port가 외부 interface에 노출되는지, authentication이 있는지, 다른 local process가 voice data에 접근할 수 있는지는 별도 확인해야 합니다.

## 설치 명령은 현재 버전을 보장하지 않는 스냅샷이다

원문은 Python 3.11 이상, Rust, Git, Bun을 사전 조건으로 제시합니다. macOS·Linux 예시는 다음과 같습니다.

```bash
git clone https://github.com/jamiepine/voicebox.git
cd voicebox
```

```bash
make setup  # 의존성 설치 (Python 가상환경, Node 모듈 등)
make dev    # 백엔드와 프론트엔드 동시에 실행
```

Windows에서는 두 terminal을 쓰는 수동 예시가 제공됩니다.

```bash
git clone https://github.com/jamiepine/voicebox.git
cd voicebox
bun install
```

```bash
cd backend
python -m venv venv
# 가상환경 활성화 (PowerShell)
.\venv\Scripts\activate

# 필수 패키지 설치
pip install -r requirements.txt
# Qwen3-TTS 설치
pip install git+https://github.com/QwenLM/Qwen3-TTS.git

# 서버 실행
uvicorn main:app --reload --port 17493
```

```bash
# 프로젝트 루트 폴더에서
bun run dev
```

이 명령들은 원문 시점의 개발 환경을 보여주는 핵심 조각일 뿐 완전한 설치 보증이 아닙니다. commit과 package version, CUDA·driver 호환, model weight 용량과 다운로드 위치, Windows build tool, production mode, port 보안이 빠져 있습니다. 실행 전 [Voicebox 저장소](https://github.com/jamiepine/voicebox)와 [Qwen3-TTS 저장소](https://github.com/QwenLM/Qwen3-TTS)의 현재 요구사항을 같은 시점 기준으로 대조해야 합니다.

## “무료·로컬”에도 비용과 데이터 경계가 있다

MIT license와 구독료가 없다는 설명은 cloud 사용량 과금이 없다는 의미이지 비용이 0이라는 뜻은 아닙니다. GPU 구매·전력, model 저장 공간, build와 update 시간은 남습니다. CPU만 쓸 때의 latency, 긴 대본의 memory, 동시에 여러 voice를 생성할 때의 throughput도 이 글에는 수치가 없습니다.

프라이버시는 다음 조건을 확인해야 합니다.

1. model weight를 받은 뒤 network 없이 실제 inference가 되는가
2. audio와 voice embedding이 SQLite 외 어디에 저장되는가
3. crash log나 update check에 file metadata가 포함되는가
4. local API가 loopback에만 binding되는가
5. project 삭제 시 원본 sample과 파생 audio가 함께 제거되는가

로컬 앱은 cloud 전송을 줄일 수 있지만 운영체제 계정과 파일 권한이 느슨하면 같은 PC의 다른 사용자가 데이터를 볼 수 있습니다.

## 음성 품질보다 먼저 권한을 검증한다

목소리는 비밀번호처럼 쉽게 바꿀 수 없는 식별 정보이고, 복제 음성은 사칭에 쓰일 수 있습니다. 자신 또는 명시적으로 허가받은 화자의 sample만 사용하고, 생성물이 합성 음성임을 관리하는 규칙이 필요합니다. 게임·podcast prototype과 접근성 도구처럼 허가 범위가 분명한 작업부터 시작하는 편이 안전합니다.

PoC에서는 언어·화자·sample 길이별 자연스러움, 원음 유사도, 발음 오류, 생성 시간, peak VRAM을 기록합니다. Cloud service와 비교할 때도 구독료만이 아니라 설치·장비·검수 비용을 포함해야 합니다. Voicebox의 실용적 강점은 “상용 서비스를 죽이는 무료 모델”이 아니라, voice data와 편집 workflow를 자신의 컴퓨터 안에서 직접 통제할 수 있는 open-source 작업대라는 데 있습니다.

## 음성 샘플은 어떤 조건으로 비교해야 할까?

같은 화자에게서 잡음이 적은 10초, 20초, 30초 샘플을 만들고 언어·감정·말하기 속도를 바꿔 생성합니다. 샘플이 길어질수록 품질이 반드시 좋아지는지, 원문에 없는 억양에서도 정체성이 유지되는지 확인합니다. 한 문장의 인상보다 여러 문장에 반복되는 발음 오류와 흔들림을 기록하는 편이 좋습니다.

자연스러움과 유사도는 분리해 들어야 합니다. 매끄럽지만 원화자와 닮지 않은 음성, 닮았지만 부자연스러운 운율은 서로 다른 실패입니다. 숫자·고유명사·긴 문장·화자 전환을 포함하고, Story Editor에서 clip 사이 음량과 간격이 일관되는지도 봅니다.

성능 측정은 모델 첫 로딩 시간, 첫 음성 생성 시간, 이후 반복 생성, 오디오 1분당 처리 시간을 나눕니다. VRAM 부족 때 CPU로 전환되는지와 긴 대본을 여러 clip으로 나눌 때 peak memory가 달라지는지도 확인합니다. 로컬이라는 장점이 실제 제작 대기 시간을 감당할 수 있을 때만 유효합니다.

## 음성 동의와 삭제를 어떤 기록으로 남길까?

voice profile마다 샘플 제공자, 허가한 용도, 허가 기간, 공개 가능 범위를 연결해 둘 수 있습니다. 게임 prototype에만 동의한 음성을 광고나 공개 봇에 재사용해서는 안 됩니다. 동의가 철회되면 원본 sample뿐 아니라 embedding, 생성 history와 내보낸 파생 파일의 처리 범위를 확인해야 합니다.

합성 음성을 외부에 배포할 때는 듣는 사람이 실제 발화로 오해하지 않게 표시하는 규칙이 필요합니다. 사람을 사칭하는 요청, 동의 없는 유명인·지인의 목소리, 인증 전화를 흉내 내는 용도는 기술적으로 가능하더라도 사용 범위에서 제외해야 합니다. 로컬 실행은 이런 책임을 서비스 제공자가 대신 통제해 주지 않는다는 뜻이기도 합니다.

여러 사용자가 같은 PC를 쓴다면 운영체제 계정과 프로젝트 저장 위치를 분리합니다. SQLite와 audio 폴더의 권한, 백업, 휴지통과 cache에 남는 복사본을 확인하고 local API에 인증이나 loopback 제한이 없으면 외부 연결을 차단합니다. 데이터 생명주기까지 통제할 수 있어야 “로컬 제작”이 프라이버시 이점으로 이어집니다.

프로젝트를 다른 컴퓨터로 옮기는 시험도 삭제 범위를 확인하는 데 도움이 됩니다. 내보내야 할 설정과 음성 파일을 명시하고, 백업에 원본 샘플이나 임베딩이 자동 포함되는지 살핍니다. 복구에 필요한 파일 목록이 불명확하면 사용자가 지웠다고 생각한 음성이 오래된 백업에서 다시 살아날 수 있으므로, 생성 편의성과 같은 수준으로 보관·폐기 절차를 문서화해야 합니다.

참고: [Voicebox GitHub](https://github.com/jamiepine/voicebox), [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [pocket-tts: 무거운 GPU 없이 CPU만으로 작동하는 실시간 AI 음성 합성의 원리]({% post_url 2026-07-22-pocket-tts-How-Real-Time-AI-Speech-Synthesis-Works-on-CPU-Without-Heavy-GPUs %}) — Kyutai Labs가 공개한 Pocket TTS는 단 1억 개의 매개변수와 신경망 오디오 코덱을 활용해 최신 CPU 환경에서 실시간 음성 합성과 목소리 복제를 수행하는 초경량 모델입니다. 이 글에서는 기술적 배경부터 세부 아키텍처…
- [GPU 없는 로컬 TTS에 25MB면 충분할까? KittenTTS v0.8의 조건]({% post_url 2026-03-29-Human-like-Voice-in-25MB-without-GPU-A-Deep-Dive-into-KittenTTS-Architecture %}) — 15M·25MB Nano 모델이 CPU에서 음성을 만드는 구조와 eSpeak-ng·영어 중심·감정 표현 한계를 구분해, KittenTTS가 맞는 작업을 정리합니다.
- [Spark-TTS: 인공지능이 당신의 목소리를 만드는 방법]({% post_url 2025-03-13-SparkTTS %}) — Spark-TTS는 인공지능으로 더 자연스럽고 다양한 목소리를 만드는 혁신적인 기술입니다. 복잡한 기술을 단순화해 더 효율적으로 텍스트를 음성으로 변환합니다.
<!-- internal-links:end -->
