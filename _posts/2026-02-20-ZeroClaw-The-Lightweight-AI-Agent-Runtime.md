---
layout: post
title: 'ZeroClaw는 RAM 5MB로 무엇을 실행하나: Rust 런타임 검증 기준'
date: '2026-02-20'
categories: Tech
tags:
  - 파이썬
  - LLM
  - 웹개발
  - 경량화
  - 로보틱스
summary: Node.js 기반의 무거운 AI 에이전트는 이제 그만. 3.4MB 단일 바이너리, 10ms 부팅 속도, 5MB 미만의 메모리 사용량을
  자랑하는 Rust 기반 초경량 AI 런타임 'ZeroClaw'를 소개합니다. 설치부터 아키텍처, 실제 사용법까지 상세하게 알아봅니다.
description: 'ZeroClaw가 Rust 단일 바이너리와 내장 메모리·도구 trait로 에이전트를 구성하는 방식, 5MB·10ms 수치와 권한·비용 검증법을 설명합니다.'
image:
  path: https://opengraph.githubassets.com/1/zeroclaw-labs/zeroclaw
  alt: "zeroclaw-labs/zeroclaw GitHub 저장소 대표 이미지"
---

**ZeroClaw**는 Rust 단일 바이너리에 채널·메모리·도구 인터페이스를 넣은 경량 AI 에이전트 런타임입니다. 저장소가 제시하는 3.4MB 바이너리, 5MB 미만 메모리, 10ms 미만 부팅은 런타임 수치이며 외부 LLM이나 로컬 모델의 자원까지 포함한다고 볼 수 없습니다. 도입 전에는 같은 기능을 켠 상태의 종단 메모리·응답 시간과 파일·셸·채널 권한을 대상 하드웨어에서 확인해야 합니다.

---

## ZeroClaw는 무엇을 경량화한 것인가?

대부분의 자율 AI 에이전트(Autonomous Agents)는 실행하기 위해 고사양의 하드웨어가 필요합니다. Node.js 런타임이나 무거운 Python 의존성을 설치하다 보면, 에이전트가 아무 일도 하지 않는 '유휴(Idle)' 상태에서도 수백 MB의 메모리를 점유하곤 하죠.

ZeroClaw는 런타임 의존성과 대기 자원을 줄이는 방향을 택합니다.

*   **Node.js? Python? 필요 없습니다.** Rust로 작성된 단일 바이너리 하나면 끝입니다.
*   외부 DB 대신 내장 메모리 엔진을 사용할 수 있습니다.
*   LLM은 설정한 외부 API나 로컬 endpoint가 별도로 필요할 수 있습니다.

## README의 자원 수치는 어디까지 포함할까?

README에 소개된 주요 수치는 다음과 같습니다. 비교 조건이 없는 비율과 배수는 자체 환경에서 재현해야 합니다.

### 1. 초경량 (Ultra-Lightweight)
가장 놀라운 점은 리소스 효율성입니다.
*   **메모리 사용량**: **5MB 미만**으로 보고됩니다.
*   **바이너리 크기**: 약 **3.4MB**. (정적 링크된 단일 파일)
*   **부팅 속도**: **10ms 미만**으로 보고됩니다. 첫 LLM 응답 시간과는 다릅니다.

### 2. 이식성
ARM, x86, RISC-V 지원과 **단일 정적 바이너리** 배포를 소개합니다. 각 릴리스에 필요한 target과 기능이 실제로 제공되는지 확인해야 합니다.

### 3. 내장 메모리 엔진
보통 AI 에이전트를 만들려면 Pinecone이나 Elasticsearch 같은 무거운 벡터 데이터베이스를 연결해야 합니다. 하지만 ZeroClaw는 다릅니다.
*   **의존성 제로(Zero Dependency)**: 외부 DB 설치가 필요 없습니다.
*   **하이브리드 검색**: 벡터 유사도 0.7과 키워드 0.3의 결합 설정이 소개됩니다. 데이터별 조정이 필요합니다.
*   **자동 호출(Auto-Recall)**: 작업 문맥에 맞춰 필요한 기억을 자동으로 불러옵니다.

### 4. 보안 기능
페어링과 샌드박스 기능이 소개되지만 실제 격리 범위와 기본 설정을 확인해야 합니다.
*   **페어링 시스템**: 새로운 연결이 들어오면 보안 페어링 코드를 요구합니다.
*   **샌드박스(Sandboxing)**: 파일 시스템 접근이나 도구 실행이 격리된 환경에서 이루어집니다.

---

## Trait 기반 구조는 무엇을 교체할 수 있게 하나?

Rust의 Trait 시스템으로 하위 시스템을 공통 인터페이스로 정의합니다.

1.  **Providers (공급자)**: OpenAI 호환 API는 물론, 로컬 모델이나 커스텀 엔드포인트도 설정 파일만 바꾸면 즉시 교체 가능합니다.
2.  **Channels (채널)**: CLI, 슬랙, 디스코드 등 에이전트와 소통하는 창구입니다.
3.  **Memory (메모리)**: SQLite와 자체 벡터 엔진을 사용하여 데이터를 로컬에 안전하게 저장합니다.
4.  **Tools (도구)**: 쉘 실행, 파일 조작, 브라우저 제어 등의 기능을 수행하며, 이 모든 것은 'Trait'으로 추상화되어 있어 확장이 쉽습니다.

설정으로 provider와 channel, 일부 도구 구성을 바꿀 수 있지만 새 구현이나 compile이 필요한 확장도 있을 수 있습니다. 현재 문서를 기준으로 범위를 확인해야 합니다.

---

## 설치 전에 어떤 명령과 비밀 키를 확인해야 하나?

아래는 원문 시점의 빌드·설치 예시입니다. 실행 전 저장소의 현재 요구 사항과 스크립트, target 지원을 확인해야 합니다.

**1. 소스 코드 클론 및 빌드**

```bash
git clone https://github.com/zeroclaw-labs/zeroclaw.git
cd zeroclaw
# 릴리즈 모드로 빌드 (최적화 적용)
cargo build --release --locked
```

**2. 바이너리 설치**

```bash
# 시스템 경로에 설치
cargo install --path . --force --locked
```

만약 Rust 환경을 세팅하기 귀찮다면, 프로젝트에서 제공하는 **원클릭 부트스트랩 스크립트**나 **Docker** 이미지를 사용할 수도 있습니다.

**초기 설정 (Onboarding):**
설치 후에는 `onboard` 명령어로 초기 설정을 진행합니다. API 키나 기본 공급자를 대화형으로 설정할 수 있습니다.

```bash
zeroclaw onboard --interactive
# 또는 바로 키 입력
zeroclaw onboard --api-key "sk-your-key-here" --provider openrouter
```

---

## 첫 실행에서는 어떤 동작부터 시험해야 할까?

처음에는 상태와 진단처럼 변경이 없는 명령부터 확인하고, 제한된 작업 공간에서만 agent를 실행합니다.

**1. 상태 확인**
현재 에이전트의 건강 상태와 연결된 채널, 메모리 상태를 확인합니다.
```bash
zeroclaw status
```

**2. 자가 진단 (Doctor)**
문제가 생겼을 때 설정 파일이나 환경 변수, 네트워크 연결을 점검해줍니다.
```bash
zeroclaw doctor
```

**3. 에이전트 실행**
기본 데몬을 실행하여 에이전트를 대기 상태로 만듭니다. 이제 설정된 채널(예: 터미널이나 메신저)을 통해 명령을 내릴 수 있습니다.
```bash
zeroclaw run
```

**4. 설정 파일 (Configuration)**
`zeroclaw.toml` 또는 `config.json` 파일을 통해 에이전트의 성격(Persona)과 사용 가능한 도구를 정의합니다. Markdown 파일로 에이전트의 정체성을 서술할 수도 있어(AIEOS 지원), 개발자가 아닌 사람도 쉽게 에이전트를 커스터마이징 할 수 있습니다.

---

## 다른 런타임과 어떻게 공정하게 비교할까?

왜 사람들이 ZeroClaw에 열광하는지, 기존의 대표주자인 OpenClaw와 비교해보면 명확해집니다.

| 특징 | OpenClaw (Node.js) | NanoBot (Python) | **ZeroClaw (Rust)** |
| :--- | :--- | :--- | :--- |
| **언어** | TypeScript | Python | **Rust** |
| **메모리(RAM)** | 같은 기능에서 측정 필요 | 같은 기능에서 측정 필요 | 저장소 보고 **5MB 미만** |
| **부팅 속도** | 같은 환경에서 측정 필요 | 같은 기능에서 측정 필요 | 저장소 보고 **10ms 미만** |
| **바이너리 크기** | ~28MB (배포판) | N/A (스크립트) | **3.4 MB** |
| **운영 비용** | 구성별 계산 | 구성별 계산 | 하드웨어·LLM API·운영 포함 계산 |

언어와 기본 바이너리만 다른 비교는 충분하지 않습니다. 같은 provider·channel·memory 크기·도구를 켜고 LLM 응답과 도구 실행을 포함한 종단 자원과 실패율을 측정해야 합니다.

---

## 어떤 환경에서 후보가 될 수 있을까?

1.  **홈 오토메이션**: 라즈베리 파이 제로 같은 저사양 기기에 설치하여, 집안의 IoT 기기를 제어하는 지능형 비서로 활용.
2.  **DevOps 봇**: 서버에 가볍게 띄워두고 로그를 감시하거나 간단한 배포 명령을 수행하는 상주형 에이전트.
3.  **임베디드 AI**: 로봇이나 드론 등 리소스가 극도로 제한된 환경에서의 자율 판단 모듈.

---

## 결론: ZeroClaw를 선택해도 되는 조건은 무엇인가?

ZeroClaw는 대기 메모리와 시작 시간이 중요한 엣지·상주 환경에서 검토할 수 있습니다. 필요한 provider와 channel, 도구가 지원되고 네트워크 중단 뒤에도 안전하게 복구되는지가 기능 수보다 중요합니다.

파일·셸·브라우저 권한은 작은 바이너리와 무관하게 큰 영향을 줄 수 있습니다. 별도 사용자와 제한된 경로에서 시작하고, pairing을 우회하는 입력과 sandbox의 mount·network 경계를 시험하며, 외부 LLM으로 전달되는 데이터와 비용을 기록해야 합니다.

## 5MB와 10ms를 어떻게 재측정해야 할까?

기본 바이너리의 idle 상태를 먼저 측정한 뒤 memory, channel, tool을 하나씩 켜 자원 변화와 부팅 시간을 기록합니다. 첫 실행과 warm 상태, release build와 debug build를 구분하고 사용한 commit·target·설정을 남깁니다. 기능 구성이 다른 수치를 한 표에서 직접 비교하면 안 됩니다.

응답 시간은 프로세스 시작, provider 호출, memory 검색, 도구 실행으로 나눕니다. 런타임이 10ms에 켜져도 모델 API가 수초 걸리면 실제 사용자 경험의 병목은 달라집니다. 로컬 모델을 같은 장치에서 실행할 경우 그 가중치·RAM·전력도 종단 비용에 포함해야 합니다.

메모리 데이터가 커질 때 검색 지연과 파일 크기가 어떻게 변하는지도 시험합니다. 0.7·0.3 혼합 가중치가 대표 질의에서 정답을 찾는지, 권한이 다른 기억을 섞지 않는지 확인합니다. 작은 초기 데이터에서의 런타임 수치만으로 장기 상주 성능을 보장할 수 없습니다.

상주 환경에서는 하루 이상 실행한 뒤에도 RSS가 계속 증가하지 않는지 확인합니다. 채널 연결을 끊었다가 다시 붙이고, provider timeout과 손상된 memory record를 넣어 process가 복구되는지도 봅니다. 작은 시작 메모리가 장기 안정성을 뜻하지 않으므로 재시작 횟수, 실패한 요청과 복구 시간까지 같은 표에 남겨야 합니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Agno: 순수 파이썬 기반 고성능 멀티 에이전트 시스템과 AgentOS 구축]({% post_url 2026-08-21-Agno-Pure-Python-Multi-Agent-Framework-and-Production-AgentOS-Runtime %}) — Agno(구 Phidata)는 복잡한 그래프나 체인 추상화 없이 순수 파이썬 코드만으로 멀티 에이전트를 구축할 수 있는 고성능 오픈소스 프레임워크입니다. 기존 프레임워크 대비 에이전트 인스턴스화 속도가 최대 5,000배 빠르고 메모리…
- [jcode의 14ms 부팅은 무엇을 바꿀까: Rust Harness·Semantic Memory·Swarm 검증 기준]({% post_url 2026-05-01-I-Deleted-Claude-Code-Deep-Dive-into-jcode-the-14ms-Rust-based-Agent-Harness-that-Changes-Everything %}) — jcode가 제시하는 14ms 부팅·27.8MB idle RAM, vector semantic memory와 daemon 기반 swarm 구조를 살펴보고, 수치 재현·검색 오류·동시 편집·API 비용의 도입 조건을 정리합니다.
- [DeerFlow 2.0이 Node.js OOM을 없앤다고? 먼저 프로젝트가 맞는지 확인해야 한다]({% post_url 2026-03-30-Review-To-Stop-the-3-AM-OOM-Alarms-A-Deep-Dive-into-DeerFlow-20-Architecture-and-Trade-offs %}) — 연결된 ByteDance 저장소와 본문의 Rust 스트림 엔진 설명이 맞지 않는 DeerFlow 글을 점검하고, 미검증 코드·벤치마크를 거르는 기준을 정리합니다.
<!-- internal-links:end -->

## References
- [GitHub 저장소](https://github.com/zeroclaw-labs/zeroclaw)
- [zeroclaw.bot 원문](https://zeroclaw.bot/)
- [zeroclaw.net 원문](https://zeroclaw.net)
