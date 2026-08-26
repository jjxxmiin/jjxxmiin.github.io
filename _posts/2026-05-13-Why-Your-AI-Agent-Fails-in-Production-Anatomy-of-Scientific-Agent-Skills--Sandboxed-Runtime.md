---
layout: post
title: 'Scientific Agent Skills가 환각을 막아줄까: 절차 지식과 샌드박스 분리'
date: '2026-05-13 18:51:57'
categories: Tech
tags:
  - 환각문제
  - RAG
  - AI에이전트
summary: 'Scientific Agent Skills의 온디맨드 절차 주입을 살펴보고, 지시문과 실제 권한 통제를 분리해 과학 워크플로를 검증하는 방법을 정리합니다.'
description: "Scientific Agent Skills의 절차 선택, SKILL.md를 versioned protocol로 관리하고 dependency lock, sandbox manifest, golden data, provenance와 도메인 review 기준으로 검증합니다."
github_url: https://github.com/K-Dense-AI/scientific-agent-skills
faq:
  - question: "Scientific Agent Skill을 주입하면 과학 분석의 환각이 사라지나요?"
    answer: "아닙니다. 절차 누락을 줄일 수 있지만 잘못된 skill 선택, data, parameter와 model 해석 오류가 남아 중간 산출물, 근거와 전문가 검토가 필요합니다."
  - question: "SKILL.md에 network 금지를 쓰면 data 유출을 막을 수 있나요?"
    answer: "아닙니다. file, network, process, secret 권한은 sandbox와 tool capability가 model 판단과 무관하게 강제해야 합니다."
  - question: "skill update는 어떻게 검증해야 하나요?"
    answer: "source, commit, dependency를 고정하고 instruction, command, network diff, golden data의 예상 artifact와 policy denial을 재실행한 뒤 version을 승격해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/K-Dense-AI/scientific-agent-skills
  alt: "K-Dense-AI/scientific-agent-skills GitHub 저장소 대표 이미지"
---

Scientific Agent Skills는 복잡한 분석 절차를 모델이 매번 추측하지 않게 도울 수 있지만, SKILL.md의 금지 문장만으로 잘못된 코드 실행이나 데이터 유출을 막을 수는 없습니다. Skill을 versioned protocol로 취급하고 dependency, sandbox와 golden data의 중간, 최종 결과를 함께 검증해야 합니다.

[Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills)는 과학 도구의 절차, 의존성, 제약과 문제 해결법을 스킬 파일로 캡슐화해 필요한 작업에만 주입하는 접근입니다. 원문은 130여 개 툴킷과 BixBench 계열 결과를 소개하지만, 수치와 지원 범위는 해당 버전과 평가 조건에 묶어 봐야 합니다.

## RAG 문서와 절차 스킬은 목적이 다르다

일반 RAG는 질문과 비슷한 문서 조각을 찾아 배경 지식을 제공합니다. 절차 스킬은 어떤 입력을 먼저 검사하고 어느 API를 쓰며 무엇을 하면 안 되는지 실행 순서를 명시합니다. scRNA-seq 품질 관리처럼 단계의 순서와 라이브러리 버전이 결과를 바꾸는 작업에는 후자가 더 직접적인 지침이 됩니다.

모든 스킬을 한꺼번에 넣으면 다시 컨텍스트가 비대해집니다. 사용자 의도와 데이터 형식을 먼저 분류하고 꼭 필요한 스킬만 선택해야 합니다. 서로 다른 스킬의 제약이 충돌하거나 의존성 버전이 맞지 않으면 실행 전에 실패시켜야 하며, 모델이 임의로 한 규칙을 버리게 두면 안 됩니다.

skill registry에는 task, input type, required tool, package, compatible version, expected output, risk와 owner를 둡니다. Selector가 어떤 근거로 skill을 골랐는지 표시하고 score가 낮거나 두 skill이 충돌하면 자동 실행하지 않습니다. 사용자가 scRNA-seq를 요청했는데 bulk RNA 절차가 선택되는 식의 가까운 오분류를 golden routing set으로 평가합니다.

Procedure에는 precondition, parameter 범위, 단계별 invariant, stop, failure와 provenance 항목을 명시합니다. 자연어 “정상화한다”만 적지 말고 input schema, 생성 file과 validation command를 연결합니다. Model이 순서를 바꾸거나 선택 단계를 건너뛰면 executor가 상태 contract로 거부할 수 있어야 합니다.

## 지시문과 권한 통제는 두 층으로 나눈다

‘외부로 데이터를 보내지 말라’는 문장은 모델에 대한 요청일 뿐 강제 정책이 아닙니다. 파일 시스템은 읽기 전용 볼륨과 작업용 출력 디렉터리로 분리하고, 네트워크 목적지와 HTTP 동작은 샌드박스에서 허용 목록으로 제한해야 합니다. 원문이 설명하는 OpenShell 결합도 지식 주입과 런타임 통제를 각각 맡기는 구상입니다.

환자 데이터 같은 민감 정보가 있다면 식별자가 외부 요청 본문이나 로그에 들어가지 않는지 차단 테스트를 해야 합니다. 에이전트가 금지된 경로 읽기, 임의 패키지 설치, 허용되지 않은 POST를 시도하도록 만들어 정책이 모델 판단과 무관하게 거부하는지 확인하세요.

sandbox manifest에는 read-only input mount, writable output, temp, non-root, CPU, memory, wall time, process, file count, allowed executable와 egress domain을 적습니다. Package install은 runtime에서 막고 승인된 image digest와 lockfile을 사용합니다. Output path 밖 write, symlink, subprocess와 DNS redirect로 network policy를 우회하는 경우도 시험합니다.

Skill이 외부 database, API를 요구한다면 synthetic, least-privilege credential을 별도 capability로 전달합니다. Read와 write를 나누고 연구 sample 제출, 삭제 같은 side effect에는 대상, parameter와 사람 승인을 둡니다. Code, stdout, tool trace에는 patient ID와 secret을 redaction하되 재현에 필요한 version, hash는 남깁니다.

## 스킬 자체도 공급망 입력이다

스킬에는 실행 가능한 코드 조각과 패키지 설치법이 들어갈 수 있습니다. 따라서 외부 기여 파일을 단순 문서로 취급해서는 안 됩니다. 출처와 커밋을 고정하고 사람이 코드와 의존성을 검토한 뒤, 승인된 내부 레지스트리에서만 배포하는 편이 안전합니다.

업데이트할 때는 변경된 명령과 네트워크 목적지, 데이터 경로를 diff로 검사합니다. 재현 가능한 컨테이너에서 작은 고정 데이터로 실행해 예상 파일만 생성되는지도 확인합니다. 스캐너가 통과했다는 결과는 보조 신호이며 숨은 동작이 없다는 보증은 아닙니다.

승인 registry에는 원본 repository, commit, reviewer, skill hash, dependency SBOM과 compatible sandbox image를 기록합니다. Skill file이 `curl | shell`, floating package나 broad permission을 요구하면 자동 거부합니다. Transitive script와 notebook cell도 실행 code이므로 문서와 같은 review만으로 끝내지 않습니다.

새 version은 이전 golden dataset을 shadow 실행해 output schema, key metric, runtime, network와 denial이 달라진 이유를 비교합니다. Breaking procedure에는 새 major version과 migration을 붙이고 진행 중인 experiment는 고정 version을 유지합니다. Rollback artifact를 보존해 잘못된 update가 모든 agent에 즉시 전파되지 않게 합니다.

## 결과 검증은 모델 답변 밖에 둔다

정답이 알려진 표본과 실패해야 하는 표본을 함께 준비해 입력 검사, 중간 산출물, 최종 결과를 단계별로 비교합니다. 패키지 오류가 났을 때 무한 재시도하지 않도록 단계별 최대 횟수와 시간, 비용 상한을 둡니다. 결과가 임상이나 연구 결론에 영향을 준다면 도메인 전문가의 검토도 생략할 수 없습니다.

처음에는 스킬 하나와 읽기 전용 데이터로 시작해 성공률, 재시도 수, 주입 토큰, 정책 거부 기록을 측정하세요. 모델을 바꾸지 않은 A/B 평가에서 스킬이 절차 오류를 줄이고 샌드박스가 금지 행동을 막을 때만 다음 파이프라인으로 넓히는 것이 안전합니다.

## scientific provenance를 어떤 artifact로 남길까

Run manifest에 raw data hash, consent scope, skill, container, package, model, prompt, parameter, random seed, tool command와 start, end를 넣습니다. 단계별 input/output hash와 QC plot, metric을 연결해 최종 문장만 남지 않게 합니다. Model의 해석과 deterministic calculation을 분리하고 계산은 notebook, script로 재실행할 수 있어야 합니다.

Golden set에는 정상 sample, empty, corrupt, batch effect와 금지된 identifier를 넣습니다. Expected schema, range, known biological signal과 실패 code를 비교하고 모델 없는 pipeline, generic RAG와 skill 조건을 A/B합니다. BixBench 수치 대신 자체 domain의 procedure adherence, scientific accuracy, unsupported claim, runtime, token과 policy violation을 봅니다.

Domain expert는 최종 conclusion뿐 아니라 parameter 선택과 QC rejection을 검토합니다. Skill이 결과를 재현하기 쉽게 만들 수는 있지만 연구 설계, 임상 판단의 책임을 자동화하지 않습니다. Data나 tool version이 지원 범위를 벗어나면 그럴듯한 report 대신 unsupported 상태로 중단해야 합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/K-Dense-AI/scientific-agent-skills)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Claude Scientific Skills가 계산 환각을 없앨까: 코드 실행과 인과 추론의 차이]({% post_url 2026-03-02-Is-Claude-the-New-Scientist-Deep-Dive-into-Claudes-Scientific-Capabilities--Code-Execution %}) — Claude가 Python으로 계산, 통계, 차트를 실행할 때 얻는 재현성과, 잘못된 코드, 데이터 전제, 상관관계 해석에서 남는 오류를 구분합니다.
- [Langfuse로 LLM 환각 원인을 찾을 수 있을까: Trace, Span, Generation, PII]({% post_url 2026-04-23-Stop-Debugging-LLMs-with-consolelog-A-Deep-Dive-into-Langfuse-Architecture %}) — Langfuse의 계층형 Trace와 비동기 전송이 RAG 실패를 어떻게 재구성하는지 살펴보고, 프롬프트 저장에 따른 PII, 스토리지, 샘플링 문제를 점검합니다.
- [Qwen-Agent로 함수 호출, RAG, WebUI를 묶기 전 확인할 것]({% post_url 2026-03-06-Alibabas-Hidden-Weapon-Qwen-Agent-Uncovering-the-Pragmatic-Agent-Framework-Threatening-LangChains-Throne %}) — Qwen-Agent의 LLM, Tool, Memory/RAG, Agent 구조와 WebUI, 코드 실행 기능을 살피고, 원문 예제의 가짜 응답, 버전 누락, 격리 한계를 짚습니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Scientific Agent Skill을 주입하면 과학 분석의 환각이 사라지나요?

아닙니다. 절차 누락을 줄일 수 있지만 잘못된 skill 선택, data, parameter와 model 해석 오류가 남아 중간 산출물, 근거와 전문가 검토가 필요합니다.

### SKILL.md에 network 금지를 쓰면 data 유출을 막을 수 있나요?

아닙니다. file, network, process, secret 권한은 sandbox와 tool capability가 model 판단과 무관하게 강제해야 합니다.

### skill update는 어떻게 검증해야 하나요?

source, commit, dependency를 고정하고 instruction, command, network diff, golden data의 예상 artifact와 policy denial을 재실행한 뒤 version을 승격해야 합니다.
