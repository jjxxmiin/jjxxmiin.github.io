---
layout: post
title: "기술 뉴스 30개 채널을 읽지 않고 따라갈 수 있을까? TrendRadar의 필터 설계"
date: '2026-04-02 06:44:13'
categories: Tech
tags:
  - 업무자동화
  - LLM
summary: "GitHub Actions, SQLite, R2와 LLM 요약을 엮는 TrendRadar에서 정보 과부하를 줄이는 필터 순서, 상태 동기화와 API 비용 한계를 정리합니다."
description: "TrendRadar가 source, dedup, rule, LLM summary, delivery를 잇고 SQLite state를 R2에 보존하는 구조, concurrent run, missed news, action rate, API cost 검증법을 설명합니다."
faq:
  - question: "Channel을 많이 연결하면 trend coverage가 좋아지나요?"
    answer: "Source 수는 늘지만 duplicate, low-quality post가 briefing을 잠식할 수 있어 source precision, missed critical news와 독자가 실제 행동한 비율을 함께 봐야 합니다."
  - question: "LLM으로 모든 article을 먼저 요약하면 되나요?"
    answer: "Cost와 noise를 줄이려면 trusted source, time, URL dedup, cheap rule을 먼저 적용하고 남은 candidate에만 semantic filter, summary를 써야 합니다."
  - question: "SQLite file을 R2에 올리면 중복 상태가 안전하게 유지되나요?"
    answer: "Concurrent run이 서로 덮어쓸 수 있으므로 lock, object version, single writer와 failed upload rollback, backup restore test가 필요합니다."
github_url: https://github.com/sansan0/TrendRadar
image:
  path: https://opengraph.githubassets.com/1/sansan0/TrendRadar
  alt: "sansan0/TrendRadar GitHub 저장소 대표 이미지"
---

**TrendRadar로 여러 기술 뉴스 채널을 한 번에 요약할 수 있지만, LLM에 보내기 전에 소스, 키워드, 중복을 강하게 줄여야 정보 피로와 API 비용이 함께 내려갑니다.** 모든 글을 수집한 뒤 요약하는 방식은 피드를 하나 더 만드는 데 그칠 수 있습니다.

성공 기준은 발송 기사 수가 아니라 중요한 release, security notice recall, 잘못된 요약률과 독자가 저장, 조치한 항목의 비율입니다. State concurrency와 source policy까지 운영할 사람이 있을 때 자동 briefing이 실제 시간을 줄입니다.

[TrendRadar 저장소](https://github.com/sansan0/TrendRadar)의 원문 스냅샷은 30여 개 플랫폼 수집, 의미 기반 필터와 요약, 여러 메신저 전송을 하나의 파이프라인으로 설명합니다. 핵심은 AI 요약보다 휘발성 GitHub Actions에서 읽은 항목을 기억하는 상태 관리와 처리 순서입니다.

## 상태는 SQLite에 남기고 휘발성 러너 밖으로 옮긴다

Actions 러너는 작업이 끝나면 사라지므로 로컬 DB만 두면 다음 실행에서 중복 기사를 다시 보냅니다. 원문은 SQLite 파일을 Cloudflare R2 같은 S3 호환 저장소와 동기화해 시작할 때 복원하고, 처리 후 다시 업로드하는 방식을 소개합니다. Redis TTL도 중복 제거 수단으로 언급됩니다.

파일 하나를 내려받고 올리는 구조는 단순하지만 실행이 겹치면 나중 작업이 이전 상태를 덮어쓸 수 있습니다. 업로드 버전 검사, 동시 실행 제한, 실패 시 마지막 정상 DB 보관이 필요합니다. DB에 원문과 사용자 관심사가 담긴다면 저장소 접근 권한과 암호화도 확인해야 합니다.

## LLM은 마지막 필터여야 비용을 통제할 수 있다

먼저 신뢰할 소스와 시간 범위를 고르고 URL, 제목 기준으로 중복을 제거합니다. 다음으로 키워드와 규칙으로 명백히 관련 없는 항목을 버린 뒤 남은 글만 의미 분석과 요약에 보냅니다. 원문이 소개한 include_standalone은 소스별 독립 요약을 만들 수 있지만 호출 수가 늘어날 수 있습니다.

의사 코드는 R2 복원, 중복 제거, relevance check, summary, 메신저 전송의 순서를 보여 주는 목업입니다. 실제 함수, 인증, 설정 파일이 정의되지 않아 완전 실행법이 아닙니다. [다른 TrendRadar 포크](https://github.com/joyce677/TrendRadar)도 연결돼 있으므로 어느 저장소와 버전을 쓰는지 먼저 고정해야 합니다.

## 브리핑은 기사 수보다 행동 가능한 항목으로 평가한다

사내 기술 레이더라면 사용하는 스택의 보안 공지와 주요 릴리스만 골라 근거 링크, 영향 범위, 확인할 담당자를 함께 보여 주는 편이 낫습니다. 경쟁사나 트렌드 감시도 감정 분석 결과를 사실처럼 쓰지 말고 원문으로 돌아갈 수 있게 해야 합니다. 요약 모델이 부정확한 원인을 덧붙일 수 있기 때문입니다.

한 주 동안 사람이 실제로 저장하거나 행동한 항목의 비율, 중복률, 놓친 중요 소식, 한 브리핑의 토큰 비용을 기록합니다. 요약 길이가 짧아졌다는 이유만으로 정보 품질이 좋아진 것은 아닙니다.

## 수집 정책과 비개발자 운영 난도를 포함한다

일부 플랫폼은 rate limit과 anti-bot 방어가 있어 수집이 자주 깨질 수 있습니다. 우회보다 공식 RSS와 허용된 API를 우선하고 각 사이트의 이용 조건을 지켜야 합니다. GitHub Actions secret, cron, R2 자격 증명, 메신저 webhook을 관리할 사람이 없는 팀에서는 무료 인프라도 운영비가 됩니다.

[HelloGitHub 소개](https://hellogithub.com/repository/7c29e6231d68407bb0a77f98fc8494ff)와 원문의 [사용 사례 글](https://medium.com/@mdabir1203/how-to-use-trendradar-to-predict-global-trends-before-they-happen-4f8152bc239a)은 아이디어 참고 자료입니다. TrendRadar의 성공 기준은 더 많은 소식을 보내는 것이 아니라, 적은 수의 검증 가능한 항목으로 독자가 바로 판단하게 하는 것입니다.

## Filter Funnel은 어떤 순서가 효율적인가

단계가 뒤로 갈수록 비싼 처리를 둡니다.

```text
source allowlist, time window
→ canonical URL, content hash dedup
→ keyword, language, project rule
→ semantic relevance
→ source-grounded summary
→ delivery, feedback
```

각 gate에서 input, output count와 false drop sample을 남깁니다. Keyword에서 버린 글 중 중요한 security advisory가 없는지 audit하고, semantic filter가 특정 language, source를 체계적으로 낮게 평가하지 않는지 봅니다.

## 중요 소식 누락을 어떻게 측정할까

한 달 동안 team이 수동으로 중요하다고 표시한 gold set을 만들고 pipeline recall을 봅니다. New version, vulnerability, deprecation과 ecosystem news를 나눕니다. Summary quality만 평가하면 수집되지 않은 article은 보이지 않습니다.

| 지표 | 의미 |
|---|---|
| Critical recall | 반드시 봐야 할 소식을 찾았나 |
| Precision | briefing에서 실제 유용한 비율 |
| Duplicate rate | 같은 사건을 반복했나 |
| Source latency | 공개부터 전달까지 시간 |
| Action rate | 저장, ticket, upgrade로 이어졌나 |

독자가 mute, skip한 item도 feedback으로 쓰되 popular taste가 security notice를 제거하지 않게 priority channel을 분리합니다.

## SQLite, R2 동기화가 깨지는 Scenario

두 Actions run이 같은 DB를 restore하고 각각 update한 뒤 upload하면 마지막 writer가 다른 run의 row를 잃을 수 있습니다. Workflow concurrency group, R2 object version, ETag와 compare-and-swap을 검토합니다. Upload 실패 때 local success를 전송 완료로 표시하지 않습니다.

DB schema migration과 old runner rollback도 test합니다. Daily backup, checksum과 restore drill을 두고 credential rotation 뒤에도 scheduled run이 작동하는지 확인합니다. State에는 article body보다 minimal hash, status만 저장해 privacy, size를 줄일 수 있습니다.

## Summary는 어떤 Evidence를 남겨야 하나

Headline, source link, publication time, direct claim과 model inference를 분리합니다. LLM이 “영향”을 덧붙이면 근거 문장을 citation으로 연결하고 source에 없는 예측은 labeled interpretation으로 둡니다.

같은 article을 model, prompt version별로 regression하고 숫자, version, date 오류를 자동 검사합니다. Link가 죽거나 paywall이면 summary confidence를 낮추고 원문 확인 불가를 표시합니다.

## Cost는 한 Briefing 단위로 계산한다

Collection compute, R2, Redis, LLM input, output, messaging과 사람 review 시간을 합칩니다. Source와 item별 token을 보면 가장 noisy한 channel과 expensive summary를 찾을 수 있습니다. API limit를 넘으면 중요한 priority item을 먼저 처리하고 low-priority는 다음 run으로 미룹니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/sansan0/TrendRadar)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [LangBot으로 여러 메신저를 함께 운영해도 될까: 이벤트, 세션, Rate Limit 설계]({% post_url 2026-05-16-Ending-the-Fragmentation-Hell-of-LLM-Chatbots-A-Deep-Dive-into-LangBots-Architecture %}) — LangBot의 멀티 파이프라인과 메신저 어댑터 구조를 살펴보고, 여러 채널에서 세션, 권한, 스트리밍, Rate Limit을 일관되게 운영하는 기준을 정리합니다.
- [n8n 셀프호스팅이 정말 더 쌀까: 큐, 로그, 메모리 비용 계산법]({% post_url 2026-04-12-An-Escape-Route-for-Developers-Tired-of-Zapiers-Killer-Bills-n8n-Architecture-and-Pragmatic-Adoption-Guide %}) — n8n의 JSON 워크플로, Item 반복, Redis 큐, 워커 구조를 살펴보고 SaaS 실행료 대신 생기는 운영, DB, 메모리 비용과 도입 기준을 정리합니다.
- [Evolver 자가 진화 Agent를 운영에 맡겨도 될까: Gene, Gate, Rollback]({% post_url 2026-04-24-The-Death-of-the-Prompt-Engineer-A-10-Year-Seniors-Deep-Dive-into-Evolvers-Self-Evolving-AI-Architecture %}) — Evolver가 로그에서 Gene, Capsule 변경 후보를 만드는 흐름을 살펴보고, Validation Gate, 영향 범위, Git 롤백만으로는 부족한 운영 안전장치를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Channel을 많이 연결하면 trend coverage가 좋아지나요?

Source 수는 늘지만 duplicate, low-quality post가 briefing을 잠식할 수 있어 source precision, missed critical news와 독자가 실제 행동한 비율을 함께 봐야 합니다.

### LLM으로 모든 article을 먼저 요약하면 되나요?

Cost와 noise를 줄이려면 trusted source, time, URL dedup, cheap rule을 먼저 적용하고 남은 candidate에만 semantic filter, summary를 써야 합니다.

### SQLite file을 R2에 올리면 중복 상태가 안전하게 유지되나요?

Concurrent run이 서로 덮어쓸 수 있으므로 lock, object version, single writer와 failed upload rollback, backup restore test가 필요합니다.
