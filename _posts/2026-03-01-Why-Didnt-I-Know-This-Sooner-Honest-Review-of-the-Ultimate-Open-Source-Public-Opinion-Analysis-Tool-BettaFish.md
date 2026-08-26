---
layout: post
title: "BettaFish는 에이전트 토론으로 여론 왜곡을 줄일까: 5개 역할과 크롤링 편향"
date: '2026-03-01 18:27:31'
categories: Tech
tags:
  - LLM
  - 멀티모달
  - 로보틱스
  - 멀티에이전트
  - 문서AI
summary: "Query·Insight·Media·Report Agent와 LLM Host가 협업하는 BettaFish를 살펴보고, 토론만으로 해결되지 않는 표본·출처·크롤링 편향을 정리합니다."
description: "BettaFish의 Query·Insight·Media·Report Agent와 Host 토론 구조를 설명하고 sample coverage·source provenance·agent ablation·privacy로 여론 보고서를 검증하는 법을 정리합니다."
faq:
  - question: "Agent가 다섯 개면 여론 편향이 줄어드나요?"
    answer: "역할 분리는 충돌을 드러낼 수 있지만 같은 누락된 표본·model bias를 공유하면 오류도 상관되므로 platform·기간·언어 coverage와 source를 따로 검증해야 합니다."
  - question: "감정 비율 60% 같은 숫자는 어떻게 읽어야 하나요?"
    answer: "모집단 정의, 수집 channel·시간, 중복·bot 처리와 classifier uncertainty가 함께 있어야 하며 공개 post의 비율을 전체 고객 여론으로 확대하면 안 됩니다."
  - question: "공개 web data는 자유롭게 수집·저장해도 되나요?"
    answer: "아닙니다. Platform policy·robots·개인정보·저장 기간과 사용 목적을 확인하고 허가된 방식으로만 수집하며 삭제 요청이 파생 report에도 반영돼야 합니다."
github_url: https://github.com/666ghj/BettaFish
image:
  path: https://opengraph.githubassets.com/1/666ghj/BettaFish
  alt: "666ghj/BettaFish GitHub 저장소 대표 이미지"
---

BettaFish의 여러 에이전트는 상충하는 근거를 드러내는 데 도움이 되지만, 같은 편향된 표본을 토론한다고 여론이 정확해지지는 않습니다. 도입 판단은 agent 수가 아니라 platform·기간·언어 coverage, 문장별 source와 중재 trace가 최종 report에 남는지로 내려야 합니다.

[BettaFish](https://github.com/666ghj/BettaFish)는 공개 웹, 내부 데이터베이스, 이미지·영상 분석을 역할별 에이전트에 나누고 LLM Host가 토론을 중재해 HTML 보고서로 묶는 오픈소스 파이프라인입니다. 분석 단계가 분리되어 어디서 결론이 생겼는지 추적하기 좋지만, 수집할 수 있는 데이터와 실제 여론 사이의 간극은 시스템 밖에서 검증해야 합니다.

## 다섯 역할은 무엇을 분리하는가

| 역할 | 담당 범위 | 결과에서 확인할 것 |
| :--- | :--- | :--- |
| Query Agent | 공개 웹 검색과 수집 | 출처, 수집 시각, 누락 채널 |
| Insight Agent | 내부 데이터 분석 | 데이터 권한과 표본 정의 |
| Media Agent | 이미지·영상 등 멀티모달 분석 | 캡션과 시각 해석의 근거 |
| Report Agent | 분석을 HTML 보고서로 구성 | 주장과 출처 연결 |
| LLM Host | Agent Forum의 충돌 중재 | 채택·기각 이유 |

분업은 수집과 해석, 표현을 한 프롬프트에 섞지 않는다는 장점이 있습니다. Agent Forum은 공개 반응과 내부 기록이 다를 때 모순을 표면에 올릴 수 있습니다. 다만 중재자가 어느 주장을 선택했는지 남지 않으면 최종 보고서는 다시 하나의 불투명한 LLM 답이 됩니다.

## 토론은 독립적인 증거가 있어야 의미가 있다

에이전트 수가 많아도 같은 모델, 같은 검색 결과, 같은 프롬프트 편향을 공유할 수 있습니다. Query Agent가 특정 플랫폼의 목소리만 수집하면 Insight Agent와 Media Agent의 토론도 그 표본 밖을 볼 수 없습니다. 서로 반박했다는 사실만으로 환각이 줄었다고 단정할 수 없는 이유입니다.

보고서에는 최소한 다음 항목이 필요합니다.

- 문장별 원천과 수집 시각
- 플랫폼·언어·기간별 표본 수
- 중복 게시물과 자동 생성 계정 처리 기준
- 감정·주제 분류의 불확실성
- 에이전트 의견이 갈렸던 지점과 최종 선택 이유

“부정 여론 60%” 같은 수치보다 어떤 모집단에서 어떤 글을 셌는지가 먼저입니다. 데이터가 빠진 이유까지 기록해야 결과를 재현할 수 있습니다.

## OpenAI 호환 설정은 시작 조각일 뿐이다

원문에 제시된 설정은 Insight Engine에 호환 API를 연결하는 형태입니다.

```python
LLM_SETTINGS = {
    "INSIGHT_ENGINE_API_KEY": "sk-your-api-key-here",
    "INSIGHT_ENGINE_BASE_URL": "https://api.moonshot.cn/v1",
    "INSIGHT_ENGINE_MODEL_NAME": "kimi-k2-0711-preview"
}
```

이 코드는 설정 일부이며 완전한 실행 예제가 아닙니다. 비밀 값 저장, 다른 에이전트 설정, 호출 제한, 재시도, 모델 출력 스키마, Docker와 데이터베이스 초기화가 생략돼 있습니다. 원문에 `python schema/init_database.py`가 언급되지만, 명령 한 줄만으로 권한·스키마 버전·백업까지 준비되는 것은 아닙니다.

API 키를 소스에 직접 넣지 말고 배포 환경의 비밀 관리 방식으로 주입해야 합니다. 모델을 바꾸면 같은 호환 규격을 쓰더라도 출력 구조와 멀티모달 지원, 비용이 달라질 수 있으므로 역할별 회귀 테스트가 필요합니다.

## 크롤링 인프라보다 접근 권한을 먼저 본다

공개 페이지라고 해서 자동 수집과 재사용이 모두 허용되는 것은 아닙니다. 각 플랫폼의 접근 정책, 개인정보, 저장 기간을 확인하고 허가된 방식으로만 데이터를 모아야 합니다. 안티 크롤링을 우회하기 위한 프록시나 세션 운용을 전제로 삼으면 시스템 유지비뿐 아니라 정책 위험도 커집니다.

내부 데이터와 공개 데이터를 합칠 때는 더 주의해야 합니다. 고객 문의나 사내 기록이 외부 LLM으로 전송되는지, 보고서가 개인을 식별하게 만들지 않는지 확인해야 합니다. 원문과 결과에 대한 접근 권한을 분리하고 삭제 요청이 파생 보고서에도 반영되는 절차가 필요합니다.

## 도입은 작은 사건 하나로 검증한다

한 브랜드와 짧은 기간을 정해 사람이 만든 기준 보고서와 BettaFish 결과를 비교하는 것이 좋습니다. 수집 누락, 잘못된 출처, 감정 오분류, 이미지 해석 오류, 토론 호출 수와 비용을 함께 기록합니다. 에이전트 하나를 뺐을 때 결론이 얼마나 달라지는지도 보면 각 역할의 실제 기여를 알 수 있습니다.

BettaFish는 여론의 “정답 기계”보다 복수 데이터 경로를 한 보고서로 조율하는 작업대에 가깝습니다. 표본과 출처를 감사할 수 있을 때 다중 에이전트 구조가 가치가 있고, 그렇지 않으면 화려한 토론이 기존 편향을 더 그럴듯하게 포장할 수 있습니다.

## Sample Ledger에는 무엇을 남겨야 하나

최종 report보다 먼저 수집 가능한 모집단을 표로 만듭니다. Platform, query, 수집 시작·종료, language, raw count, deduplicated count, 실패·차단 비율을 기록합니다. API와 crawl 결과가 섞이면 수집 방식도 구분합니다.

| 항목 | 왜 필요한가 |
|---|---|
| Query version | 검색어 변경에 따른 표본 차이 재현 |
| Source·timestamp | 주장 당시 공개된 evidence 확인 |
| Duplicate·repost rule | 같은 의견의 과대 집계 방지 |
| Language·region | 특정 집단의 과대표현 확인 |
| Missing channel | 결과가 말하지 못하는 범위 명시 |
| Classifier confidence | 감정·topic 수치의 불확실성 표시 |

“전체 여론” 대신 “수집한 세 platform의 공개 post”처럼 분모를 report 제목과 summary에 명시합니다. 접근할 수 없는 private group과 offline 의견은 데이터에 없다는 사실도 결과입니다.

## 다섯 Agent의 기여는 어떻게 분리할까

Query-only summary, Query+Insight, Media 추가, Forum과 Report까지 순차로 늘려 같은 evidence에서 결과를 비교합니다. 각 단계가 source coverage, factual error, contradiction 발견과 human rating을 얼마나 바꾸는지 봅니다. Agent 수가 늘어도 report가 같고 call만 증가하면 역할을 합칠 수 있습니다.

LLM Host가 어느 의견을 채택했는지 decision trace를 남깁니다. 다수결만 사용하면 같은 model의 반복 의견이 독립 evidence처럼 보일 수 있습니다. Source quality와 timestamp를 우선하고 unresolved conflict는 한쪽 결론으로 숨기지 않습니다.

같은 input을 여러 seed와 model로 실행해 sentiment·topic과 최종 recommendation의 변동성을 기록합니다. 결과가 자주 뒤집히는 문장은 confidence를 낮추거나 사람이 검수합니다.

## Media 분석의 근거는 어떻게 보존할까

Image·video caption만 report에 넣으면 model이 실제 어느 frame을 근거로 판단했는지 알기 어렵습니다. Asset URL·hash, keyframe timestamp와 detected text를 연결하고, OCR·visual interpretation을 분리합니다. Edited meme와 satire를 literal opinion으로 세지 않는 review set도 필요합니다.

Copyright와 personal identity도 고려합니다. Report에 원본 media를 복제할 수 있는지, 얼굴·계정 이름이 필요한지 검토하고 aggregate 분석에는 개인 식별자를 최소화합니다. 외부 LLM으로 보내는 asset과 내부 customer data의 경계를 나눕니다.

## Report를 배포하기 전 어떤 Gate를 둘까

문장마다 source가 있는지, 숫자의 분모와 기간이 있는지, agent inference와 직접 관측을 구분했는지 검사합니다. 위험도가 높은 reputational claim은 원문을 사람이 읽고 승인합니다. Source가 삭제·정정되면 파생 report를 갱신하는 provenance link도 둡니다.

도입 이득은 analyst time 절감, source recall, 수정률과 model·crawl 비용을 함께 비교합니다. 빠른 HTML 생성보다 잘못된 숫자와 개인정보를 배포하지 않는 것이 우선입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/666ghj/BettaFish)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DOM이 바뀌어도 웹 자동화가 살아남을까? MolmoWeb의 화면 기반 접근]({% post_url 2026-03-30-Deep-Dive-into-MolmoWeb-The-End-of-DOM-Parsing-AI2s-8B-Visual-Web-Agent-is-a-Game-Changer %}) — 스크린샷만 보고 클릭하는 8B MolmoWeb이 DOM 자동화의 취약점을 줄이는 방식과 Pass@4 수치, OCR·지연·권한 한계 및 검증 순서를 짚습니다.
- [이미지에 없는 물체를 말할 때: NoLan의 언어 사전확률 억제]({% post_url 2026-02-28-NoLan--Mitigating-Object-Hallucinations-in-Large-Vision-Language-Models-via-Dynamic-Suppression-of-Language-Priors %}) — NoLan이 이미지+텍스트 로짓에서 텍스트 전용 편향을 동적으로 억제하는 방식, POPE 개선과 두 번의 forward 비용·오탐 가능성을 정리합니다.
- [VideoLLaMA 3는 중복 프레임을 어떻게 줄일까: AVT·DiffFP]({% post_url 2025-02-22-VideoLLama3 %}) — 고해상도 입력을 토큰화하는 AVT, 유사 프레임을 덜어내는 DiffFP, 7B 벤치마크와 추론 코드의 실행 전제
<!-- internal-links:end -->

## 자주 묻는 질문

### Agent가 다섯 개면 여론 편향이 줄어드나요?

역할 분리는 충돌을 드러낼 수 있지만 같은 누락된 표본·model bias를 공유하면 오류도 상관되므로 platform·기간·언어 coverage와 source를 따로 검증해야 합니다.

### 감정 비율 60% 같은 숫자는 어떻게 읽어야 하나요?

모집단 정의, 수집 channel·시간, 중복·bot 처리와 classifier uncertainty가 함께 있어야 하며 공개 post의 비율을 전체 고객 여론으로 확대하면 안 됩니다.

### 공개 web data는 자유롭게 수집·저장해도 되나요?

아닙니다. Platform policy·robots·개인정보·저장 기간과 사용 목적을 확인하고 허가된 방식으로만 수집하며 삭제 요청이 파생 report에도 반영돼야 합니다.
