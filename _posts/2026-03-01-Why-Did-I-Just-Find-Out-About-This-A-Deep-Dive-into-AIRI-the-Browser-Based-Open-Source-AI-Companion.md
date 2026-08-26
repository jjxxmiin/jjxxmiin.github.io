---
layout: post
title: 'AIRI를 브라우저 AI 컴패니언으로 쓸까: WebGPU, WASM, 기억의 경계'
date: '2026-03-01'
categories: Tech
tags:
  - LLM
  - 음성AI
  - 파이썬
  - 웹개발
  - AI메모리
summary: 'AIRI가 WebGPU, WASM, Live2D/VRM과 모듈식 음성, 기억 계층을 조합하는 방식, 브라우저 호환성, 자원, 개인정보, 업데이트 한계를 정리합니다.'
description: 'AIRI의 WebGPU, WASM 기반 로컬 추론과 Live2D, VRM, 음성, 기억 모듈을 살펴보고, 브라우저 호환성, 자원, 개인정보, 도입 기준을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/moeru-ai/airi
  alt: "moeru-ai/airi GitHub 저장소 대표 이미지"
faq:
  - question: 'AIRI는 모든 AI 기능을 브라우저 안에서만 실행하나요?'
    answer: '로컬 WebGPU, WASM 모듈을 선택할 수 있지만 LLM, STT, TTS를 외부 API로 구성하면 대화와 음성이 해당 서비스로 전송될 수 있습니다. 각 모듈의 endpoint와 저장 위치를 따로 확인해야 합니다.'
  - question: 'WebGPU를 지원하면 어떤 기기에서도 같은 성능이 나오나요?'
    answer: '브라우저, 운영체제, GPU와 모델 크기, 메모리에 따라 성능과 지원 기능이 달라집니다. 대상 기기에서 첫 응답 시간, 지속 메모리, 발열과 fallback 동작을 직접 측정해야 합니다.'
  - question: '브라우저 기억 저장소는 민감한 대화에도 안전한가요?'
    answer: '로컬 저장은 외부 전송을 줄일 수 있지만 같은 기기의 다른 사용자, 브라우저 profile, backup과 extension 접근 위험은 남습니다. 삭제, 내보내기, 암호화와 보관 기간을 정해야 합니다.'
---

AIRI는 WebGPU, WASM과 웹 렌더링 기술을 이용해 LLM, 음성, 아바타, 기억 모듈을 조합하는 오픈소스 AI 컴패니언 프로젝트입니다. 브라우저 중심 구조는 Python, CUDA 환경을 줄일 수 있지만 모든 기능이 로컬이라는 뜻도, 낮은 사양의 모든 기기에서 원활하다는 뜻도 아닙니다. 도입 여부는 사용할 모듈의 데이터 경로, 대상 브라우저의 성능, 기억과 microphone 권한을 통제할 수 있는지로 판단해야 합니다.

## AIRI는 기존 AI 캐릭터 구성과 무엇이 다른가

AI 캐릭터 프로젝트는 model runtime, 음성, 렌더링을 한 application에 묶을 수 있습니다. AIRI 프로젝트 팀(`moeru-ai`)은 **브라우저 퍼스트**와 모듈화를 지향해 LLM, STT, TTS, avatar를 나눠 구성합니다.

### WebGPU와 WASM은 무엇을 브라우저로 옮기나
AIRI는 `WebGPU`, `WebAudio`, `Web Workers`, `WebAssembly(WASM)`, `WebSocket` 같은 웹 기술을 사용합니다. 이 구성은 일부 model runtime과 audio 처리를 별도 Python service 없이 browser에서 수행할 여지를 만듭니다. Rust로 작성된 HuggingFace `candle` 추론 엔진을 WASM으로 빌드하는 경로도 소개됩니다.

WebGPU 지원 표시만으로 충분하지는 않습니다. GPU memory, browser 구현, mobile 전력 제한과 model format이 달라지면 같은 설정도 실행되지 않거나 CPU fallback으로 느려질 수 있습니다. 지원 표와 실제 대상 기기를 구분해 시험해야 합니다.

| 핵심 비교 항목 | 기존 파이썬 기반 AI VTuber | **Project AIRI** 🌟 |
| :--- | :--- | :--- |
| **실행 및 구동 환경** | Python, native runtime 구성이 흔함 | **브라우저, desktop, PWA 경로** |
| **코어 프로그래밍 언어**| 프로젝트마다 다름 | **TypeScript / Rust, WASM 중심** |
| **캐릭터 렌더링 방식** | 외부 도구와 연동 가능 | **Live2D, VRM browser rendering** |
| **시스템 아키텍처** | 결합 방식이 프로젝트마다 다름 | **기능별 모듈 교체를 지향** |

### 기억과 음성 모듈은 어떤 경계를 갖나
AIRI는 기능별로 철저하게 쪼개져 있습니다. LLM 백엔드, STT(음성 인식), TTS(음성 합성), 캐릭터 렌더링이 전부 독립적인 패키지로 나뉘어 있죠. 
게다가 AI 컴패니언의 필수 요소인 '장기 기억(Memory Layer)' 기능을 구현하기 위해, **DuckDB WASM과 Drizzle ORM을 붙여 런타임에 브라우저 내에서 마이그레이션을 돌립니다**. 백엔드 서버 없이 브라우저 자체에서 벡터 데이터베이스와 RAG(검색 증강 생성) 로직을 처리해버리는 셈이죠. 

다음 JSON은 원문이 설명하는 모듈 조합을 개념적으로 나타냅니다.

```json
{
  "agent": {
    "name": "MyAiri",
    "memory_store": "duckdb-wasm", // 브라우저 로컬 DB에서 기억 유지
    "llm_backend": "webgpu-local", // WebGPU를 통한 브라우저 로컬 추론
    "stt_engine": "whisper-wasm",  // WASM 기반 브라우저 내장 Whisper
    "tts_engine": "edge-tts",
    "avatar": {
      "type": "vrm",
      "url": "/assets/models/my_avatar.vrm"
    }
  }
}
```
이 JSON은 실행 가능한 공식 설정 전체가 아닙니다. 실제 package 이름, endpoint, model download, CORS와 browser 권한이 생략돼 있으므로 현재 저장소 문서와 schema를 확인해야 합니다. 외부 LLM, TTS를 선택하면 이름만 browser application일 뿐 대화나 음성이 외부로 전송될 수 있습니다.

## 어떤 사용 형태부터 시험할까

### 데스크톱 컴패니언
AIRI의 desktop Tamagotchi mode에는 캐릭터가 다른 창을 가리지 않도록 hover 시 투명도와 click 통과를 조절하는 **Fade on hover™** 기능이 설명됩니다. 이 형태는 avatar rendering과 짧은 대화의 지연을 시험하기 좋습니다. 다만 항상 microphone을 듣거나 화면 상태를 관찰하도록 구성한다면 명확한 활성 표시와 즉시 끄는 제어가 필요합니다.

### Discord 연동과 게임 플레이
웹 기술 기반이라고 해서 브라우저 안에만 갇혀있는 건 아닙니다. 유연한 모듈 구조 덕분에 TCP 커넥션이나 비웹(Non-Web) 기술이 필요한 기능도 확장이 가능합니다.
Discord voice와 비전, LLM을 결합한 Minecraft, Factorio, Balatro 연동 사례가 소개됩니다. 여기서는 대화만 하는 구성보다 bot token, channel 권한, 게임 action이라는 외부 권한이 추가됩니다. 테스트 account와 private channel에서 시작하고 보내는 메시지, 행동의 rate와 허용 범위를 제한해야 합니다.

## 어떤 한계를 먼저 확인해야 하나

- **모듈 조합의 초기 설정:**
  최근 업데이트로 온보딩(Onboarding) UI가 추가되며 설정 과정이 꽤나 개선되었다고는 하지만, 다양한 모듈(음성, 아바타, DB, LLM)을 내 입맛에 맞게 조립하고 로컬 모델을 안정적으로 연동하는 과정은 주니어 개발자나 일반 유저에겐 여전히 불친절하게 느껴질 수 있습니다. 문서화가 잘 되어 있다 해도 프론트엔드 생태계에 대한 어느 정도의 이해도가 요구됩니다.
- **대상 기기의 물리적 한계:**
  브라우저에서 실행된다는 말이 낮은 사양에서도 큰 모델이 원활하다는 뜻은 아닙니다. 사용할 모델과 avatar, STT, TTS를 동시에 켠 상태에서 memory와 발열, 첫 응답 시간을 측정하고 필요하면 외부 API와 로컬 기능을 나눠야 합니다.
- **빠르게 바뀌는 생태계:**
  package와 설정 schema가 바뀌면 기존 조합이 깨질 수 있습니다. 검증된 commit과 dependency lock을 기록하고 update 전후에 음성, 기억, avatar 회귀 테스트를 실행해야 합니다.

## 기억과 개인정보는 어떻게 관리할까

DuckDB WASM과 browser storage를 이용한 기억은 서버 database 없이도 대화 맥락을 남길 수 있습니다. 하지만 browser profile이 삭제되거나 storage quota가 정리되면 기억이 사라질 수 있고, 반대로 공용 기기에서는 다른 사용자가 남은 기록을 볼 수 있습니다. 사용자별 namespace, export, delete, backup과 encryption 가능 여부를 확인해야 합니다.

기억 항목은 모델이 대화에서 추출한 해석일 수 있습니다. 사용자의 선호를 잘못 저장하면 이후 답변이 반복해서 왜곡되므로 원문 대화와 생성 시각, 수정 기능을 연결하는 편이 좋습니다. 민감한 건강, 관계, 위치 정보는 기본적으로 장기 기억에서 제외하거나 명시적 동의를 받아야 합니다.

Microphone, camera, Discord와 게임 account는 각각 다른 권한입니다. 한 번의 “companion 사용 동의”로 모두 묶기보다 기능별로 켜고 끌 수 있어야 합니다. 외부 API를 사용하면 어떤 audio와 text가 어느 provider로 가는지 화면에서 설명하고 log에 원문이 남는지도 확인해야 합니다.

## PoC는 무엇을 측정해야 하나

첫 단계에서는 text chat과 avatar만 켜고 browser별 loading time과 memory를 측정합니다. 그다음 STT, TTS, local LLM, memory를 하나씩 추가해 어느 모듈이 지연과 오류를 만드는지 분리합니다. 모든 기능을 한 번에 켜면 audio 끊김이 model, rendering, network 중 어디서 생겼는지 알기 어렵습니다.

기능별 합격선도 다릅니다. 대화는 첫 응답 시간과 맥락 일치, 음성은 인식 누락과 합성 지연, avatar는 frame drop, 기억은 정확한 회수와 삭제 반영을 봅니다. 브라우저를 새로 열거나 offline으로 바꿨을 때 fallback이 사용자에게 명확히 표시되는지도 시험해야 합니다.

## AIRI는 어떤 경우에 적합한가

웹 기술로 avatar, 음성, LLM module을 실험하고 로컬과 cloud backend를 바꿔 보려는 prototype에는 적합할 수 있습니다. 반면 장기간 지원, 엄격한 개인정보 정책, 모든 client의 동일 성능이 필요한 production에는 dependency와 browser matrix를 직접 운영할 준비가 필요합니다.

“사이버 생명체” 같은 표현보다 구성 요소의 경계를 보는 편이 현실적입니다. AIRI는 여러 AI 기능을 하나의 캐릭터 경험으로 묶는 toolkit이며, 감정이나 의도를 가진 존재임을 증명하는 시스템은 아닙니다. 사용자에게도 생성 응답과 기록 범위를 분명히 알려야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [FluidVoice: 구독료 없이 Mac에서 작동하는 온디바이스 AI 음성 받아쓰기 구축기]({% post_url 2026-08-14-FluidVoice-On-Device-AI-Dictation-for-macOS-with-Zero-Latency-and-Total-Privacy %}) — FluidVoice는 Apple Silicon 환경에서 완전 오프라인으로 동작하는 무료 오픈소스 음성 인식 및 AI 문맥 교정 애플리케이션입니다. 외부 서버 전송 없이 로컬에서 음성-텍스트 변환(STT)과 Fluid-1 모델 후처리를…
- [MiroFish의 에이전트 사회는 예측 엔진일까: GraphRAG, OASIS와 비용 폭발]({% post_url 2026-03-12-From-a-10-Day-Code-to-a-30M-RMB-Investment-A-Deep-Dive-into-the-MiroFish-Multi-Agent-Prediction-Engine-Architecture %}) — GraphRAG 기억과 OASIS 환경에서 에이전트 사회를 돌리는 MiroFish의 구조를 살펴보고, 확률 보정, 상관된 환각, Context, JSON, 운영 비용 한계를 정리합니다.
- [oh-my-pi(omp) 코딩 에이전트 분석: Hashline, LSP, DAP와 권한 검증법]({% post_url 2026-05-23-AI-Enters-the-Terminal-Silencing-Hallucinations-A-Deep-Dive-into-oh-my-pi-Architecture %}) — oh-my-pi(omp)가 content hash anchor, LSP, DAP, 하위 에이전트와 메모리를 코딩 작업에 연결하는 방식을 공식 저장소 기준으로 설명합니다. 설치, 권한, 벤치마크, 팀 파일럿의 검증 항목도 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### AIRI는 모든 AI 기능을 브라우저 안에서만 실행하나요?

로컬 WebGPU, WASM 모듈을 선택할 수 있지만 LLM, STT, TTS를 외부 API로 구성하면 대화와 음성이 해당 서비스로 전송될 수 있습니다. 각 모듈의 endpoint와 저장 위치를 따로 확인해야 합니다.

### WebGPU를 지원하면 어떤 기기에서도 같은 성능이 나오나요?

브라우저, 운영체제, GPU와 모델 크기, 메모리에 따라 성능과 지원 기능이 달라집니다. 대상 기기에서 첫 응답 시간, 지속 메모리, 발열과 fallback 동작을 직접 측정해야 합니다.

### 브라우저 기억 저장소는 민감한 대화에도 안전한가요?

로컬 저장은 외부 전송을 줄일 수 있지만 같은 기기의 다른 사용자, 브라우저 profile, backup과 extension 접근 위험은 남습니다. 삭제, 내보내기, 암호화와 보관 기간을 정해야 합니다.

## References
- [GitHub 저장소](https://github.com/moeru-ai/airi)
- [xugj520.cn 원문](https://xugj520.cn/airi-open-source-guide)
- [moeru.itch.io 원문](https://moeru.itch.io/airi)
