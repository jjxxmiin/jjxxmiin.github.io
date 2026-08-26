---
layout: post
title: 'Agent Zero에 컴퓨터를 통째로 줘도 될까: Docker 권한의 실제 경계'
date: '2026-04-21 18:30:58'
categories: Tech
tags:
  - 인프라
  - AI보안
  - MCP
  - AI에이전트
summary: 'Agent Zero의 터미널, 코드 실행형 구조를 살펴보고, Docker를 완전한 격리로 오해하지 않기 위한 권한, 네트워크, 승인 체크리스트를 정리합니다.'
description: "Agent Zero의 terminal, code execution을 Docker kernel, mount, socket, capability, egress 경계, package supply chain, approval binding, audit, 복구 기준으로 검증합니다."
github_url: https://github.com/agent0ai/agent-zero
faq:
  - question: "Agent Zero를 Docker 안에서 실행하면 host와 완전히 격리되나요?"
    answer: "아닙니다. host kernel을 공유하며 mount, Docker socket, capability, network 설정에 따라 host 자원과 비밀정보에 닿을 수 있습니다."
  - question: "터미널 명령마다 사람 승인을 받으면 안전한가요?"
    answer: "명령 문자열뿐 아니라 작업 directory, 환경, 예상 file, network 변경과 만료를 묶고 승인 뒤 값이 바뀌면 다시 검토해야 합니다."
  - question: "Agent Zero에 적합한 첫 업무는 무엇인가요?"
    answer: "입력, 결과를 버릴 수 있고 외부 side effect가 없는 일회성 data 변환이나 격리 저장소의 정적 분석부터 시험하는 것이 좋습니다."
image:
  path: https://opengraph.githubassets.com/1/agent0ai/agent-zero
  alt: "agent0ai/agent-zero GitHub 저장소 대표 이미지"
---

Agent Zero에 Linux 터미널을 주면 도구를 미리 정의하지 않은 작업도 수행할 수 있지만, Docker 컨테이너를 완전한 가상 머신처럼 믿고 운영 권한을 건네서는 안 됩니다. 안전성은 Agent의 설명이 아니라 mount, socket, capability, egress와 승인 가능한 side effect를 얼마나 작게 제한했는지로 결정됩니다.

[Agent Zero](https://github.com/agent0ai/agent-zero)는 모델이 터미널에서 명령과 코드를 만들고 실행하며 필요하면 패키지를 설치하는 범용 에이전트 접근을 보여 줍니다. 이 유연성은 고정된 API 도구 목록을 넘어서는 데서 나오고, 바로 그 지점이 가장 큰 위험이기도 합니다.

## API 목록 대신 컴퓨터를 주면 달라지는 것

정해진 날씨 API나 검색 함수만 호출하는 에이전트는 허용된 행동이 코드에 드러납니다. 터미널형 에이전트는 파일을 만들고 스크립트를 작성하며 새 유틸리티를 설치해 처음 보는 문제에도 대응할 수 있습니다. 원문은 검색, 메모리, 다른 에이전트와의 통신, skill과 MCP 연결 같은 확장 지점을 설명합니다.

반면 행동 공간이 넓어지면 검증해야 할 명령도 넓어집니다. 모델이 틀린 패키지를 설치하거나 로그에 나온 문장을 지시로 오해하고, 실패를 고치려다 더 큰 변경을 만들 수 있습니다. ‘스스로 도구를 만든다’는 장점은 허용되지 않은 도구도 만들 수 있다는 뜻입니다.

행동을 “shell 사용” 하나로 보지 않고 읽기, local write, package install, network, process, system 변경으로 나눕니다. 업무마다 필요한 범주만 열고 나머지는 실행기에서 거부합니다. prompt에 “안전하게 행동하라”고 적는 것은 filesystem, kernel 권한을 대신하지 않습니다.

| 경계 | 기본값 | 열기 전 검증 |
|---|---|---|
| filesystem | 일회성 workspace만 write | host, home, secret mount 없음 |
| process | non-root, 제한된 PID, CPU, memory | privilege escalation, fork 폭주 차단 |
| kernel | capability 제거, system call 제한 | 필요한 syscall과 image별 profile |
| network | outbound 차단 | domain, port allowlist와 DNS log |
| package | 임의 설치 차단, version 고정 | registry, hash, install script 검토 |
| external write | 기본 미지원 | 대상, diff, idempotency, 사람 승인 |

Agent가 새 script를 만들면 script 내용과 실행 명령을 한 사건으로 연결합니다. 승인한 command가 이후 다운로드한 code를 실행하거나 shell expansion으로 다른 경로를 지울 수 있으므로 문자열 allowlist만으로 충분하지 않습니다. workspace diff와 network 계획을 실행 전에 보여 주고 실제 결과와 대조합니다.

## Docker 경계는 설정만큼만 강하다

컨테이너는 호스트 커널을 공유하므로 VM과 같은 경계가 아닙니다. 호스트 디렉터리, Docker 소켓이나 민감한 환경 변수를 연결하면 에이전트가 컨테이너 밖의 중요한 자원에 닿을 수 있습니다. root 사용자, 과도한 capability와 넓은 네트워크도 격리 효과를 약하게 만듭니다.

실험용 컨테이너에는 호스트 볼륨을 연결하지 않고 권한이 낮은 사용자와 제한된 파일 시스템을 사용합니다. 운영 자격 증명은 넣지 않으며, 외부 네트워크는 필요한 목적지만 허용합니다. CPU, 메모리, 저장 공간과 실행 시간을 제한해 잘못된 반복이 호스트를 고갈시키지 못하게 해야 합니다.

특히 `/var/run/docker.sock`을 mount하면 container가 다른 container나 host mount를 가진 새 workload를 만들 수 있어 경계가 무너질 수 있습니다. source repository가 필요하면 read-only 원본에서 일회성 copy를 만들고 결과 diff만 꺼냅니다. user namespace, read-only root filesystem과 temporary filesystem을 실제 image에서 함께 시험합니다.

base image와 설치 package도 공급망입니다. image digest, OS package와 Python, Node lockfile을 고정하고 build provenance와 취약점 점검을 둡니다. Agent가 문제 해결을 위해 임의 Git URL의 script를 pipe로 실행하지 못하게 하며 새 dependency는 별도 검토 artifact로 남깁니다.

network allowlist에는 model API뿐 아니라 package registry, Git host와 callback endpoint가 포함될 수 있습니다. 모든 outbound payload를 읽기는 어려워도 목적지, byte, task를 기록하고 예상하지 못한 domain은 막습니다. DNS rebinding이나 redirect가 allowlist를 우회하지 않는지 확인합니다.

## 성공보다 실패와 복구를 시험한다

무해한 작업만 시켜 보고 안전하다고 결론 내리면 안 됩니다. 존재하지 않는 패키지, 끊긴 네트워크, 충돌하는 지시, 매우 큰 로그를 주고 최대 반복 수 안에서 멈추는지 확인합니다. 삭제나 외부 전송, 시스템 설정 변경을 시도할 때 사람 승인을 요구하는지도 검증합니다.

승인 화면에는 자연어 “파일 수정” 대신 대상 path, 예상 diff, 실행 command, network, external effect와 rollback 가능성을 표시합니다. 승인은 task, container, action hash와 만료에 결속하고 argument가 바뀌면 재승인합니다. 오래된 버튼이나 다른 사용자의 승인으로 새 process에 stdin이 전달되지 않아야 합니다.

failure injection에는 disk full, child process hang, package checksum 불일치, model timeout과 container 강제 종료를 포함합니다. 실패 뒤 orphan process, volume, network가 남지 않고 마지막 audit와 diff를 복구할 수 있는지 봅니다. retry는 같은 외부 write를 두 번 수행하지 않도록 idempotency key나 상태 조회를 먼저 사용합니다.

터미널 출력은 빠르게 문맥을 채웁니다. 전체 로그를 계속 모델에 되먹이면 중요한 오류가 밀려나고 비용이 커질 수 있습니다. 원문 출력은 별도 보관하되 모델에는 종료 코드와 필요한 구간만 전달하고, 어떤 요약이 사용됐는지 추적할 수 있어야 합니다.

요약에는 생략한 line 범위와 원문 artifact ID를 붙입니다. Agent가 요약에서 보지 못한 error를 “없음”으로 결론 내리지 않도록 truncation을 명시합니다. ANSI, binary, secret pattern을 정리하되 사람 감사용 원문에도 접근 권한과 보존 기한을 둡니다.

## 적합한 업무는 피해 범위로 고른다

일회용 데이터 변환, 격리된 저장소의 정적 분석, 재현 가능한 실험처럼 입력과 결과를 버릴 수 있는 작업부터 시작하는 편이 좋습니다. 운영 배포, 고객 데이터 수정, 결제처럼 외부 효과가 큰 업무는 자유 터미널보다 좁게 정의한 도구와 승인 흐름이 적합합니다.

원문의 Docker 명령과 구성은 특정 시점의 시작 예시일 뿐, 안전한 운영 설정 전체가 아닙니다. 이미지 버전을 고정하고 실행마다 새 컨테이너를 만들며 명령, 파일 변경, 네트워크 요청을 감사한 뒤 폐기하세요. 작업 성공률과 함께 사람이 막은 위험 행동, 재시도 비용, 복구 시간을 기록해야 범용성이 실제 가치인지 판단할 수 있습니다.

파일럿은 같은 작업을 좁은 API 도구 Agent와 자유 terminal Agent에 각각 줍니다. 성공률, 사람 승인, 검토, 새 dependency, network 목적지, 처리 시간과 격리 위반 시도를 비교합니다. 범용성이 성공률을 높이지 않거나 감사 부담만 늘면 행동 공간을 다시 줄입니다.

컨테이너 폐기 전 결과 manifest에는 기준 image, source commit, 모든 command, exit code, file hash와 허용된 network를 남깁니다. 결과를 production으로 옮길 때는 container에서 만든 binary나 script를 그대로 신뢰하지 않고 기존 CI와 review를 통과시킵니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/agent0ai/agent-zero)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [AI 코딩 에이전트에 터미널 권한을 줘도 될까? Goose의 안전 경계]({% post_url 2026-03-15-Beyond-Code-Suggestions-Taking-the-Keyboard-Dissecting-Blocks-Open-Source-AI-Agent-Goose %}) — Block의 오픈소스 에이전트 Goose가 명령 실행과 MCP 도구를 연결하는 방식을 살피고, 샌드박스, 최소 권한, 모델 선택의 실무 기준을 정리합니다.
- [DeepSeek-TUI를 coding agent로 써도 될까: Terminal, Shell 권한, 검증 기준]({% post_url 2026-05-03-Turn-Off-Copilot-and-Cursor-How-DeepSeek-TUI-in-the-Terminal-Proves-the-True-Essence-of-Engineering %}) — DeepSeek-TUI가 terminal에서 model, file, shell, MCP를 연결하는 구조를 살펴보고, native 기능 주장, context 압축, fan-out 비용과 자동 실행 권한의 위험을 검증합니다.
- [Gemini CLI에 파일 수정 권한을 줘도 될까: Plan Mode, MCP 안전선]({% post_url 2026-03-20-Why-the-Gemini-CLI-an-AI-Agent-in-the-Terminal-Disrupted-a-10-Year-Developers-Workflow-feat-MCP-Architecture-Deep-Dive %}) — Gemini CLI의 도구 반복, MCP 연결, Plan Mode와 ask_user를 기준으로 로컬 코딩 에이전트의 권한, 컨텍스트, 검토 범위를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Agent Zero를 Docker 안에서 실행하면 host와 완전히 격리되나요?

아닙니다. host kernel을 공유하며 mount, Docker socket, capability, network 설정에 따라 host 자원과 비밀정보에 닿을 수 있습니다.

### 터미널 명령마다 사람 승인을 받으면 안전한가요?

명령 문자열뿐 아니라 작업 directory, 환경, 예상 file, network 변경과 만료를 묶고 승인 뒤 값이 바뀌면 다시 검토해야 합니다.

### Agent Zero에 적합한 첫 업무는 무엇인가요?

입력, 결과를 버릴 수 있고 외부 side effect가 없는 일회성 data 변환이나 격리 저장소의 정적 분석부터 시험하는 것이 좋습니다.
