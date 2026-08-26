---
layout: post
title: 'OpenMontage로 AI 영상을 만들 때: 에이전트 파이프라인·비용·검수 기준'
date: '2026-07-04 01:10:06'
categories: Tech
tags:
  - 파이썬
  - AI코딩
  - 영상생성
  - 음성AI
  - AI정책
summary: OpenMontage가 YAML 파이프라인·Markdown 스킬·Python 도구·Remotion과 FFmpeg를 연결해 영상 제작 단계를 조율하는 방식을 설명합니다. 설치 비용, 사람 승인, 재현성과 보안까지 포함한 파일럿 기준도 정리합니다.
description: OpenMontage의 에이전트 중심 영상 제작 구조와 research부터 compose까지의 단계, 무료·유료 도구 선택, 비용·품질·보안을 검증하는 파일럿 방법을 설명합니다.
faq:
  - question: OpenMontage는 영상 생성 모델인가요?
    answer: 아닙니다. 여러 영상·이미지·음성·검색·편집 도구를 파이프라인으로 연결하고 AI 코딩 에이전트가 제작 단계를 수행하도록 돕는 오케스트레이션 프로젝트입니다.
  - question: API 키 없이도 OpenMontage를 사용할 수 있나요?
    answer: 공식 저장소는 Piper TTS·공개 아카이브·Remotion·FFmpeg 등을 이용한 경로를 안내하지만 원하는 스타일·해상도와 장비에 따라 품질·시간·추가 도구가 달라집니다.
  - question: OpenMontage를 자동 발행 파이프라인에 바로 연결해도 되나요?
    answer: 먼저 제한된 주제로 사람 승인·저작권 확인·비용 상한·렌더 검수와 실패 복구를 시험하고, 결과가 기준을 통과한 경우에만 발행 단계와 연결하는 편이 안전합니다.
github_url: https://github.com/calesthio/OpenMontage
image:
  path: https://opengraph.githubassets.com/1/calesthio/OpenMontage
  alt: "calesthio/OpenMontage GitHub 저장소 대표 이미지"
---

**OpenMontage는 한 문장으로 영상을 만들어 주는 단일 생성 모델이 아니라, 조사·대본·장면 계획·에셋 제작·편집·렌더링을 여러 도구와 연결하는 오픈소스 제작 파이프라인입니다.** AI 코딩 에이전트가 YAML manifest와 Markdown skill을 읽고 Python 도구를 호출한다는 점이 특징이지만, 결과의 정확성·저작권·비용과 최종 품질 책임까지 자동으로 사라지는 것은 아닙니다.

[OpenMontage 공식 저장소](https://github.com/calesthio/OpenMontage)는 빠르게 바뀌는 프로젝트입니다. 이 글은 특정 스타 수나 과장된 비용 절감을 근거로 추천하지 않고, 저장소가 공개한 구조를 어떤 작업에 시험할 수 있는지와 실제 도입 전에 무엇을 검증해야 하는지를 중심으로 읽습니다.

## OpenMontage는 무엇을 만들고 무엇을 대신하지 않는가

일반적인 영상 생성 서비스는 prompt를 받아 짧은 clip 또는 image를 만듭니다. OpenMontage는 그 앞뒤의 제작 과정을 더 넓게 다룹니다. 주제를 조사하고 proposal과 script를 만들며 scene별 asset을 준비한 뒤, timeline과 자막·음성을 합쳐 최종 파일을 렌더링하는 workflow를 제공합니다. 기존 영상에서 짧은 clip을 고르거나 공개 stock footage를 조합하는 pipeline도 저장소에 설명돼 있습니다.

따라서 OpenMontage 자체의 품질을 영상 생성 model 하나의 화질로 평가하면 안 됩니다. 선택한 image·video·TTS provider, 입력 자료, scene plan, renderer, 승인 기준의 합이 결과를 만듭니다. 같은 pipeline이라도 유료 cloud model을 쓰는 구성과 local·archive asset을 쓰는 구성은 비용·속도·시각적 일관성이 다릅니다.

프로젝트가 대신하지 않는 역할도 분명합니다. 사용 허가가 불명확한 영상과 음악의 라이선스를 판단하거나, script의 사실 오류를 법적·편집적 기준으로 승인하거나, 브랜드 위험을 책임지는 주체는 여전히 사람입니다. 자동 검수 단계가 있더라도 업무별 최종 acceptance criteria와 발행 승인은 별도로 설계해야 합니다.

## 에이전트 중심 구조는 지시와 실행을 분리한다

공식 README는 OpenMontage에 전통적인 code orchestrator가 없고 AI coding assistant가 orchestrator 역할을 한다고 설명합니다. 에이전트는 `pipeline_defs/`의 YAML manifest에서 단계·도구·성공 기준을 읽고, `skills/`의 Markdown 파일에서 각 단계를 수행하는 방법을 가져옵니다. 실제 media 처리와 provider 호출은 `tools/` 아래 Python 도구가 맡습니다.

이 분리는 제작 규칙을 읽고 수정하기 쉽게 만듭니다. 새로운 documentary workflow를 추가할 때 모든 분기를 하나의 거대한 Python state machine에 넣기보다 manifest와 stage skill을 조정하고 기존 tool을 재사용할 수 있습니다. 반대로 자연어 지시가 모호하거나 agent가 잘못된 skill을 고르면 같은 입력도 다른 실행 경로를 택할 수 있습니다.

공식 흐름은 대체로 `research → proposal → script → scene_plan → assets → edit → compose`로 제시됩니다. 각 단계의 산출물을 다음 단계의 입력 계약으로 취급해야 합니다. research citation이 빠졌다면 script로 넘어가지 않고, scene에 필요한 duration·asset·voice가 없으면 비싼 생성 호출 전에 중단하는 식의 gate가 필요합니다.

에이전트가 checkpoint state를 JSON으로 남기고 선택한 provider, 비용 snapshot과 decision log를 기록하는 구조도 README에 설명돼 있습니다. 여기서 중요한 것은 ‘기억한다’는 표현이 아니라 process 재시작 뒤 어느 단계부터 안전하게 재개할 수 있는지입니다. tool 호출이 이미 외부 비용을 발생시켰다면 같은 stage를 재시도할 때 중복 생성하지 않도록 asset ID와 결과 상태를 확인해야 합니다.

## 사람 승인 지점은 창의성과 비용이 커지기 전에 둔다

OpenMontage의 Backlot storyboard 설명에는 scene별 take, prompt, asset 비용과 품질 score를 보고 render 전에 승인하는 gate가 나옵니다. 이런 승인 화면은 결과를 다 만든 뒤 폐기하는 낭비를 줄일 수 있습니다. 다만 품질 score 하나가 사람의 판단을 대신하지는 않습니다. 브랜드, 인물 표현, 자막 사실과 권리 문제는 별도 항목으로 확인해야 합니다.

승인은 단계마다 무조건 받는 방식보다 위험에 맞춰 배치합니다. 공개 자료 조사와 outline은 자동으로 진행하되 외부 유료 생성 시작 전 예상 provider·횟수·상한을 확인할 수 있습니다. 사람 얼굴·상표·민감 주제가 포함된 scene은 asset 생성과 발행 전에 추가 승인을 둡니다. 최종 render 전에는 script와 scene order를, 발행 전에는 실제 영상과 audio·caption을 확인합니다.

승인 뒤 입력이 바뀌면 이전 승인을 그대로 재사용하지 않습니다. script 한 문장이 수정돼 voice와 subtitle만 바뀌는지, 해당 scene asset과 전체 timing까지 다시 만들어야 하는지 dependency를 추적해야 합니다. 누가 어떤 version을 승인했는지 project log에 남기면 여러 사람이 작업할 때 최신본 혼선을 줄일 수 있습니다.

## Remotion·HyperFrames·FFmpeg는 서로 다른 렌더 역할을 맡는다

현재 공식 README는 React 기반 Remotion, HTML·CSS·GSAP 기반 HyperFrames와 FFmpeg를 production 도구로 설명합니다. Remotion은 data-driven explainer와 React scene stack에, HyperFrames는 motion graphics 중심의 HTML 표현에 맞는 기본 선택으로 안내됩니다. FFmpeg는 encoding, subtitle burn-in, audio mixing과 post-production에 쓰입니다.

renderer가 결정적이라고 해도 외부 생성 asset까지 항상 같다는 뜻은 아닙니다. 같은 image·audio·timeline과 코드가 고정됐다면 composition을 재현하기 쉬워지지만, cloud video model을 다시 호출하면 원본 asset이 달라질 수 있습니다. 최종 결과를 재현하려면 입력 파일의 hash, font·renderer·Node·FFmpeg version과 실행 parameter를 함께 보관해야 합니다.

frame rate, 해상도, color profile, audio sample rate와 subtitle safe area를 project 시작 전에 고정합니다. source asset이 서로 다른 frame rate와 aspect ratio를 가지면 자동 crop이나 interpolation이 의도한 구도를 망칠 수 있습니다. render 성공 여부만 보지 말고 representative frame, black frame, clipping, sync와 loudness를 검사합니다.

공식 README가 언급하는 post-render 검수에는 ffprobe, frame 추출과 audio 분석이 포함됩니다. 이는 파일 손상과 기본 기술 오류를 잡는 데 유용하지만 서사가 자연스럽고 사실이 맞는지까지 보장하지 않습니다. 자동 검사와 사람의 editorial review를 서로 다른 gate로 유지해야 합니다.

## API 키가 없는 경로도 시간과 권리 비용이 든다

저장소는 Piper TTS, Archive.org·NASA·Wikimedia Commons 등의 공개 자료, Remotion·HyperFrames와 FFmpeg를 조합한 zero-key 경로를 안내합니다. ‘API 키가 없다’는 것은 외부 생성 API 청구가 없다는 뜻에 가깝습니다. local CPU·GPU 시간, download와 storage, 사람이 자료의 사용 조건을 확인하는 비용은 남습니다.

공개 archive의 파일이 모두 동일 라이선스인 것도 아닙니다. 각 asset의 원문 page, creator, license, 변경·상업 이용 조건과 attribution을 scene manifest에 보관해야 합니다. stock service는 무료 개발자 key를 제공하더라도 API 약관과 배포 조건을 확인합니다. 출처를 찾지 못한 asset은 최종 render에서 제외할 수 있어야 합니다.

유료 image·video·voice provider를 연결할 때는 README의 예시 가격을 예산 보장으로 사용하지 않습니다. duration, resolution, retry, 실패한 take와 region·plan에 따라 비용이 달라질 수 있습니다. tool별 최대 호출 횟수와 project budget을 두고 provider가 예상 정보를 반환하지 않으면 승인 없이 실행하지 않는 정책이 필요합니다.

local model도 무료라는 말보다 capacity로 평가합니다. 한 scene 생성 시간, VRAM peak, queue와 전력, 실패율을 측정하고 cloud fallback이 언제 허용되는지 정합니다. local 결과가 품질 기준을 통과하지 못해 계속 재시도하면 싼 경로가 전체 제작 시간을 늘릴 수 있습니다.

## 설치는 Python·Node·FFmpeg 경계를 함께 시험한다

현재 Quick Start는 Python 3.10 이상, FFmpeg, Node.js 18 이상과 지원되는 AI coding assistant를 전제로 `make setup` 경로를 안내합니다. 이 숫자와 명령은 업데이트될 수 있으므로 설치 시점의 README와 lockfile을 우선합니다. 운영 image에는 성공한 exact version과 system package를 고정하는 편이 좋습니다.

Python 환경과 `remotion-composer`의 npm 의존성, font·codec은 서로 다른 실패 지점을 만듭니다. 빈 container 또는 새 VM에서 설치를 재현하고 sample project를 끝까지 render합니다. 개발자 laptop에서 이미 설치된 package에 기대 성공한 결과는 CI나 worker에서 재현되지 않을 수 있습니다.

API key는 `.env`에 모아 두더라도 agent와 모든 child process가 읽을 필요는 없습니다. provider별 최소 권한 key, project별 spending limit과 짧은 수명을 사용합니다. command log와 prompt, screenshot에 secret이 남지 않도록 redaction을 확인하고, 외부 URL download에는 allowlist·파일 크기·content type 검사와 timeout을 둡니다.

OpenMontage는 AGPL-3.0 license로 공개돼 있으므로 수정·서비스 방식이 조직의 배포 모델과 맞는지도 검토해야 합니다. 이 글은 법률 판단을 대신하지 않습니다. 사내 사용, 수정본 제공과 network service 조건이 중요하다면 정확한 license text를 담당자와 확인합니다.

## 파일럿은 짧고 검증 가능한 영상 하나로 시작한다

첫 과제로 회사의 핵심 캠페인이나 1시간 documentary를 고르면 실패 원인이 너무 많습니다. 출처가 명확한 30~60초 explainer처럼 script 정답과 asset 조건을 사람이 빠르게 검토할 수 있는 주제가 적합합니다. 동일 brief를 현재 수동 workflow와 OpenMontage pipeline으로 각각 만들어 품질과 운영비를 비교합니다.

평가 항목은 다음처럼 나눌 수 있습니다.

| 평가 축 | 기록할 내용 | 중단 신호 |
|---|---|---|
| 사실성 | 문장별 source, 잘못된 수치·인용 | source 없는 핵심 주장 |
| 시각 품질 | scene 일관성, crop, artifact, subtitle | 승인 뒤 반복되는 큰 재작업 |
| 비용 | provider별 호출·실패 take·GPU 시간 | 사전 상한을 넘긴 자동 호출 |
| 시간 | 단계별 소요, 사람 승인·재시도 | 수동 workflow보다 긴 병목이 설명되지 않음 |
| 재현성 | manifest·asset hash·version·decision log | 실패 stage부터 안전하게 재개 불가 |
| 권리·보안 | license, attribution, secret·외부 전송 | 출처 없는 asset 또는 과도한 key 권한 |

의도적으로 실패도 넣습니다. provider timeout, 잘못된 aspect ratio, 빈 search 결과, FFmpeg 오류와 승인 거절 뒤 pipeline이 어디서 멈추고 재개하는지 봅니다. 자동 fallback이 사람 승인 없이 더 비싼 provider를 부르거나 라이선스가 다른 asset으로 바꾸지 않는지 확인합니다.

두세 번의 성공 영상보다 반복 가능한 acceptance rate가 중요합니다. 주제와 길이를 바꾼 여러 project에서 첫 render 통과율, 수정 횟수, 평균·p95 비용과 완료 시간을 기록합니다. 어느 pipeline과 provider 조합이 어떤 콘텐츠에 맞았는지를 남기면 ‘에이전트가 알아서 한다’는 설명을 운영 가능한 규칙으로 바꿀 수 있습니다.

## 어떤 팀에 맞고 언제 더 단순한 도구가 나은가

여러 provider와 stock source를 조합하고, research부터 render까지 반복 가능한 제작 과정을 명시적으로 관리하려는 팀은 OpenMontage를 시험할 이유가 있습니다. YAML·Markdown으로 제작 규칙을 읽고 고치고 싶고 Python·Node·media tool을 운영할 역량이 있다면 agent-first 구조를 비교해 볼 수 있습니다.

반대로 생성 clip 몇 개를 사람이 편집하는 작은 작업, 한 provider만 쓰는 고정 template 또는 실시간 응답이 필요한 서비스에는 더 단순한 script와 renderer가 이해하기 쉬울 수 있습니다. 단계가 적은데 많은 skill과 tool registry를 유지하면 선택 오류와 업데이트 비용이 이득보다 커집니다.

도입 결론은 GitHub의 별 수나 README의 도구 개수로 내리지 않습니다. 실제 brief에서 정확한 script와 사용 가능한 asset을 만들고, 비용 상한과 승인·권리 조건을 지키며, 실패 뒤 재개 가능한지로 결정합니다. OpenMontage의 핵심 가치는 prompt 한 줄을 없애는 데 있지 않고 제작 단계와 판단 근거를 inspect 가능한 파일로 드러내는 데 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/calesthio/OpenMontage)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Claude Code로 영상을 대화하듯 편집하는 Video Use의 원리와 실전 활용법]({% post_url 2026-08-01-Video-Use-How-AI-Coding-Agents-Edit-Raw-Footage-Through-Text-and-FFmpeg %}) — Video Use는 Claude Code, Codex 등 AI 코딩 에이전트와 자연어로 대화하며 타임라인 편집 없이 영상을 완성하는 오픈소스 파이프라인입니다. 영상 프레임을 직접 LLM에 전달하는 대신 단어 단위 음성 스크립트를…
- [공개된 AI 시스템 프롬프트를 그대로 복사해도 될까? 저장소 활용 기준]({% post_url 2026-02-24-System-Prompts-And-Models-Collection %}) — 여러 AI 도구의 시스템 프롬프트를 모은 저장소에서 역할·제약·출력 형식을 분석하는 법과 진위·버전·저작권을 확인해야 하는 이유를 정리합니다.
- [OpenCut 아키텍처 가이드: AI가 영상을 편집하고 코드가 타임라인을 제어하는 방법]({% post_url 2026-07-23-OpenCut-Architecture-Guide-How-AI-Edits-Video-and-Code-Controls-the-Timeline %}) — 비공개 상용 소프트웨어가 지배하던 영상 편집 시장에 등장한 완전히 새로운 대안, OpenCut 프로젝트를 조명합니다. 프라이버시를 보장하는 로컬 기반 아키텍처부터 시작해, Rust 코어 기반의 크로스플랫폼 통합, 플러그인 생태계…
<!-- internal-links:end -->

## 자주 묻는 질문

### OpenMontage는 영상 생성 모델인가요?

아닙니다. 여러 영상·이미지·음성·검색·편집 도구를 파이프라인으로 연결하고 AI 코딩 에이전트가 제작 단계를 수행하도록 돕는 오케스트레이션 프로젝트입니다.

### API 키 없이도 OpenMontage를 사용할 수 있나요?

공식 저장소는 Piper TTS·공개 아카이브·Remotion·FFmpeg 등을 이용한 경로를 안내하지만 원하는 스타일·해상도와 장비에 따라 품질·시간·추가 도구가 달라집니다.

### OpenMontage를 자동 발행 파이프라인에 바로 연결해도 되나요?

먼저 제한된 주제로 사람 승인·저작권 확인·비용 상한·렌더 검수와 실패 복구를 시험하고, 결과가 기준을 통과한 경우에만 발행 단계와 연결하는 편이 안전합니다.

## 원문과 확인 자료

- [OpenMontage 공식 저장소와 README](https://github.com/calesthio/OpenMontage)
- [OpenMontage architecture 문서](https://github.com/calesthio/OpenMontage/blob/main/docs/ARCHITECTURE.md)
- [OpenMontage provider 안내](https://github.com/calesthio/OpenMontage/blob/main/docs/PROVIDERS.md)
