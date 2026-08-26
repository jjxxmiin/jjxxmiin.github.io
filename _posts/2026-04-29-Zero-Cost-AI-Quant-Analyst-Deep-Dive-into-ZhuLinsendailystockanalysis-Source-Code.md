---
layout: post
title: 'daily_stock_analysis를 0원으로 운영할 수 있을까: GitHub Actions·데이터 품질·비용 조건'
date: '2026-04-29 18:46:15'
categories: Tech
tags:
  - LLM
  - 온디바이스AI
  - 웹개발
  - AI에이전트
summary: 'daily_stock_analysis가 GitHub Actions로 금융 데이터 수집·LLM 요약·알림을 예약 실행하는 구조와 무료 한도, 데이터 품질, 비밀 관리와 투자 판단의 한계를 분석합니다.'
description: "daily_stock_analysis의 GitHub Actions cron, 검색 provider fallback, LLM 보고서·다채널 알림을 무료 quota·secret·point-in-time data와 실패 복구 기준으로 검증합니다."
github_url: https://github.com/ZhuLinsen/daily_stock_analysis
faq:
  - question: "daily_stock_analysis를 항상 0원으로 운영할 수 있나요?"
    answer: "보장할 수 없습니다. GitHub Actions·검색 API·LLM·알림 service의 무료 quota와 실행 빈도에 따라 비용이나 제한이 생기므로 사용량을 각각 계산해야 합니다."
  - question: "검색 provider fallback이 있으면 뉴스 품질도 보장되나요?"
    answer: "아닙니다. 가용성은 높일 수 있지만 오래된 기사·동명이인·중복 보도와 잘못된 출처를 걸러 주지는 않으므로 provenance와 freshness 검사가 필요합니다."
  - question: "AI 분석 결과를 자동 주문에 연결해도 되나요?"
    answer: "안 됩니다. LLM 보고서는 투자 조언이나 검증된 예측 신호가 아니며, 우선 읽기 전용 브리핑으로 사용하고 주문 system과 권한을 분리해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/ZhuLinsen/daily_stock_analysis
  alt: "ZhuLinsen/daily_stock_analysis GitHub 저장소 대표 이미지"
---

`daily_stock_analysis`는 별도 상시 서버 없이 GitHub Actions에서 금융 데이터를 모으고 LLM 보고서와 알림을 만드는 자동화 틀로 사용할 수 있습니다. 그러나 “0원”은 각 서비스의 무료 quota 안에 머무는 특정 사용량의 결과일 뿐이며, 데이터 정확도나 투자 성과를 보장하지 않습니다. 첫 도입은 소수 종목의 읽기 전용 일일 브리핑으로 제한하고 실행 비용·출처·누락과 오류를 기록하는 편이 안전합니다.

## GitHub Actions가 예약 분석기를 대신할 수 있는 조건은 무엇인가

이 시스템은 별도의 백엔드 데몬이나 데이터베이스 없이 매일 정해진 시간에 GitHub Actions workflow가 일회성 runner를 띄우고 Python script를 실행하는 구조로 소개됩니다. CI runner는 예약 batch에 편리하지만 정확한 시각 실행, 무제한 runtime이나 영구 저장소를 보장하는 cron server는 아닙니다. 지연 실행·timeout·재시도와 artifact 보존 기간을 업무 요구와 맞춰야 합니다.

아래 표를 통해 기존의 전통적인 개인용 퀀트 봇과 이 프로젝트의 아키텍처 차이를 직관적으로 비교해 보겠습니다.

| 아키텍처 요소 | 기존 개인화 퀀트 봇 (Legacy Quant) | `daily_stock_analysis` (Modern Serverless AI) |
| :--- | :--- | :--- |
| **인프라 & 컴퓨팅** | AWS EC2, Raspberry Pi 등 상시 구동 서버 필요 | **GitHub Actions** 기반의 일회성 container(무료 quota 조건) |
| **의사결정 엔진** | 하드코딩된 규칙 (예: `if RSI < 30 then BUY`) | **멀티 LLM (OpenAI, Ollama 등)** 기반의 자연어 추론 및 대시보드 요약 |
| **데이터 수집 레이어** | 단일 소스 크롤링 (IP 차단 잦음, DOM 변경 시 크래시) | **다중 검색 API Fallback** (Anspire, SerpAPI, Tavily 등) + 증권 API |
| **결과물 전달** | 단순 로그 파일 또는 단일 메신저 알림 | 텔레그램, 디스코드, 슬랙, 비스(Feishu), 이메일 등 **다채널 Webhook 푸시** |
| **확장성** | 코드 레벨의 수정이 필수적임 | `.env` 시크릿 변수 주입만으로 컴포넌트 교체 가능 |

구조상 주목할 부분은 **데이터 수집의 graceful degradation과 fallback 처리**입니다. 단일 검색 API에 의존하면 quota가 소진되거나 장애가 발생했을 때 전체 pipeline이 멈추므로 여러 provider를 순서대로 시도합니다. 다만 최신 뉴스가 주어져도 LLM 환각이 사라지는 것은 아니고, 검색 결과 자체의 사실성과 종목 일치 여부를 별도로 검증해야 합니다.
이들은 코드 내부에 여러 검색 프로바이더를 리스트업하고 순차적으로 시도하는 로직을 구현했습니다. 다음은 이들이 API 의존성을 어떻게 다루는지 잘 보여주는 핵심 로직을 의사 코드(Pseudo-code)와 구조로 재구성한 것입니다.

```python
# 다중 검색 API Fallback 로직의 핵심 아이디어 (개념적 코드)
class NewsSearchAgent:
    def __init__(self, env_configs):
        # 우선순위가 높은 검색 엔진부터 큐에 등록
        self.search_providers = []
        if env_configs.get("ANSPIRE_API_KEYS"):
            self.search_providers.append(AnspireSearch(env_configs["ANSPIRE_API_KEYS"]))
        if env_configs.get("SERPAPI_API_KEYS"):
            self.search_providers.append(SerpApiSearch(env_configs["SERPAPI_API_KEYS"]))
        if env_configs.get("TAVILY_API_KEYS"):
            self.search_providers.append(TavilySearch(env_configs["TAVILY_API_KEYS"]))
            
    def fetch_realtime_news(self, stock_ticker):
        for provider in self.search_providers:
            try:
                # 1. API 호출 시도
                news_data = provider.search(f"{stock_ticker} latest financial news")
                # 2. 유효한 데이터가 반환되면 즉시 리턴 (단락 평가)
                if news_data and self._validate_news(news_data):
                    return self._clean_and_format(news_data)
            except RateLimitExceededException:
                logger.warning(f"[{provider.name}] Rate limit exceeded. Falling back to next provider...")
                continue
            except Exception as e:
                logger.error(f"[{provider.name}] Unexpected error: {e}")
                continue
                
        # 모든 프로바이더가 실패했을 경우의 최후의 보루 (예: 야후 파이낸스 스크래핑 등)
        return self._fallback_basic_scraping(stock_ticker)
```

사용자는 repository의 `Settings > Secrets`에 필요한 API key를 등록하고 사용 가능한 provider와 OpenAI 호환 endpoint 또는 로컬 Ollama를 구성할 수 있습니다. 키를 많이 넣는다고 복구가 자동으로 완성되는 것은 아닙니다. provider마다 결과 schema·시간대·rate limit가 다르므로 어떤 provider가 어떤 결과를 만들었는지 trace하고, 모두 실패했을 때 오래된 자료로 조용히 보고서를 만들지 실패 상태를 알려야 합니다.

Agent 전략 질의 기능은 이동평균선, 엘리어트 파동과 candlestick pattern 같은 기술 지표를 tool 형태로 LLM에 제공해 여러 단계의 분석문을 만드는 흐름으로 설명됩니다. 이는 수치 계산과 문장 생성을 연결하는 기능이지, 해당 지표가 미래 가격을 예측한다는 검증은 아닙니다. 계산 시점·가격 조정 방식·결측치와 사용한 원본을 보고서에 함께 표시해야 합니다.

## 어떤 업무에 제한해 적용할 수 있을까

첫 용도는 의사결정을 대신하는 주문 신호보다 사람이 원문을 확인할 수 있는 일일 요약이 적합합니다. 아래 시나리오는 구조를 설명하는 예이며 운영 환경과 실제 payload는 별도로 검증해야 합니다.

### 비동기 사내 브리핑 연동
기존에 Spring Boot나 Node.js로 구축된 거대한 사내 금융 데이터망이 있다고 가정해 봅시다. 이 거대한 모놀리식 시스템에 직접 LLM 파이프라인을 얹는 것은 장애 전파의 리스크가 큽니다. 이때 `daily_stock_analysis`를 독립된 마이크로서비스(혹은 크론 잡 람다)처럼 활용할 수 있습니다.
GitHub Actions에서 매일 분석된 최종 JSON 리포트 결과를 사내망의 Webhook 엔드포인트로 쏘게 설정합니다.

```json
// 전송되는 Webhook Payload 예시 (구조화)
{
  "timestamp": "2026-04-29T18:00:00Z",
  "stock_ticker": "AAPL",
  "ai_consensus": "HOLD",
  "key_catalysts": [
    "WWDC 2026 발표 기대감 선반영",
    "중국 시장 아이폰 판매량 둔화 리스크"
  ],
  "technical_indicators": {
    "MACD": "Bearish Crossover",
    "RSI_14": 45.2
  }
}
```
사내 Spring 서버는 이 payload를 받아 검토 대기 브리핑으로 전달할 수 있습니다. Webhook 인증, schema version, replay 방지와 실패 queue가 필요하며, LLM의 `ai_consensus`를 검증 없이 내부 trading algorithm의 weight로 사용해서는 안 됩니다.

### 민감한 portfolio를 위한 로컬 Ollama 구성
Docker와 로컬 Ollama endpoint를 구성하면 portfolio가 외부 LLM API로 전송되는 범위를 줄일 수 있습니다. 그러나 검색 API, container image, package download와 알림 webhook이 외부 통신을 계속할 수 있어 `BASE_URL` 한 값만으로 폐쇄망이 되지는 않습니다. egress allowlist와 실행 log를 확인하고, `.env` 파일은 image·artifact와 prompt에 포함되지 않도록 관리해야 합니다.

## 무료 운영과 데이터 품질의 실패 조건은 무엇인가

첫째, **무료 quota와 인프라 제약**입니다. GitHub Actions와 API의 무료 제공 조건은 repository 공개 여부, 실행 시간, 요청 수와 model에 따라 달라질 수 있습니다. 자산 목록과 실행 빈도가 늘면 timeout·rate limit 또는 유료 사용이 생깁니다. 종목당 검색 호출, LLM input·output token, runner minute와 알림 수를 계산해 하루·월 상한을 정해야 합니다.

둘째, **정보 품질이 검색 API에 종속**됩니다. SerpAPI나 Tavily가 오래됐거나 동명이인 회사의 뉴스를 가져오면 LLM은 그 입력으로 그럴듯하지만 잘못된 결론을 만들 수 있습니다. ticker·법인명·발행 시각, 원 출처와 중복 기사를 검증하고 인용 URL을 결과에 보존해야 합니다. 정보가 없을 때 추측 대신 “자료 부족”으로 끝내는 규칙도 필요합니다.

셋째, **설정과 비밀 관리 부담**입니다. OpenAI API, 검색 API, Telegram bot token과 Discord webhook 등 여러 secret을 구성할 수 있습니다. 필요한 channel만 활성화하고 최소 권한·만료·rotation을 적용해야 합니다. Pull request와 fork workflow가 secret에 접근하지 않는지 확인하고, report나 action log에 token과 portfolio가 출력되지 않도록 redaction을 시험합니다.

## 재현 가능한 보고서인지 어떻게 검증할까

한 보고서마다 실행 ID, code commit, model·prompt version, 각 데이터 source와 수집 시각을 함께 저장합니다. 같은 입력 snapshot으로 다시 실행했을 때 핵심 수치가 같고 문장 차이가 허용 범위 안인지 확인합니다. 시장 마감 뒤 수정된 가격이나 기사를 과거 시점의 결과에 섞으면 성능을 과대평가하므로 point-in-time data가 필요합니다.

provider fallback은 가용성 실험으로 따로 검증합니다. 첫 provider의 timeout, 빈 응답, 잘못된 schema와 quota 초과를 주입해 다음 provider로 넘어가는지, 결과가 섞이지 않는지 봅니다. 모든 provider가 실패하면 성공 표시의 보고서를 보내지 말고 누락된 종목·source와 다음 재시도 시각을 알립니다. 동일 workflow 재실행이 같은 브리핑을 여러 채널에 중복 전송하지 않도록 idempotency key도 둡니다.

pilot 표에는 종목별 데이터 freshness, 원문 일치율, 중복률, LLM 인용 정확성, 실행 성공률, p95 시간과 실제 API 사용량을 기록합니다. 사람에게 도움 된 요약과 잘못된 경고 사례를 모두 표본 검토합니다. “매수·보유” 문구의 적중률만 재면 선택 편향과 거래 비용을 놓치므로, 이 프로젝트는 검증된 quantitative strategy가 아니라 정보 정리 pipeline으로 평가하는 편이 맞습니다.

운영 승격 조건도 미리 정합니다. 누락이나 잘못된 종목 연결이 기준을 넘거나 source를 추적할 수 없으면 자동 배포를 중지합니다. 보고서는 주문 권한과 분리하고, 원장 데이터와 중요한 투자 결정은 기존 검증 절차를 유지합니다. GitHub Actions가 편리하다는 사실과 금융 의사결정을 맡길 수 있다는 결론 사이에는 별도의 성능·위험 검증이 필요합니다.

## 결론: 무료 cron보다 검증 가능한 브리핑이 핵심이다

`daily_stock_analysis`의 실질적 가치는 CI workflow, 여러 데이터 source, LLM과 알림을 작은 예약 pipeline으로 연결한 참조 구조에 있습니다. 무료 한도는 부수적인 조건이며 검색 결과가 사실인지, 실패가 보이는지, 결과를 재현할 수 있는지가 더 중요한 품질 기준입니다.

소수 종목과 한 알림 channel로 시작해 한 달 사용량과 오류 사례를 수집하고, 사람이 원문을 확인하는 브리핑으로만 사용하십시오. 자동 주문이나 투자 수익을 기대하기 전에 데이터 provenance, 비밀·quota와 실패 복구를 운영 가능한 수준으로 만드는 것이 먼저입니다. 이 글은 투자 조언이 아니며 프로젝트의 비용이나 성과를 보장하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/ZhuLinsen/daily_stock_analysis)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [TradingAgents-CN으로 자동매매해도 될까: Bull·Bear 토론과 리스크 관리의 착시]({% post_url 2026-03-01-Why-Did-I-Just-Find-This-Honest-Review-of-TradingAgents-CN-the-AI-Avengers-of-Financial-Trading %}) — 분석가·Bull/Bear 연구원·트레이더·리스크 관리자로 구성된 TradingAgents-CN을 살펴보고, 토론이 환각과 투자 위험을 없애지 못하는 이유를 정리합니다.
- [AutoHedge의 4개 Agent면 투자 위험이 줄까: Director→Quant→Risk→Execution]({% post_url 2026-04-28-Unmanned-Hedge-Fund-with-LLMs-AutoHedge-Dissecting-the-Real-Architecture-Between-Illusion-and-Practice %}) — AutoHedge가 전략·분석·위험·실행을 네 역할로 나누는 구조를 살펴보고, Pydantic JSON과 Risk Agent만으로 환각·확증 편향·실거래 위험이 사라지지 않는 이유를 짚습니다.
- [금융 API를 MCP로 감싸면 규제·권한 문제가 끝날까? 현실적인 경계]({% post_url 2026-05-08-Stop-Baking-API-Spaghetti-A-Deep-Dive-into-Financial-Services-MCP-Saving-Financial-Legacy-Systems %}) — MCP가 금융 시스템의 도구 발견과 호출 형식을 표준화하는 범위, 그리고 권한·감사·상태·고빈도 처리까지 자동 해결하지는 못하는 이유를 구분합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### daily_stock_analysis를 항상 0원으로 운영할 수 있나요?

보장할 수 없습니다. GitHub Actions·검색 API·LLM·알림 service의 무료 quota와 실행 빈도에 따라 비용이나 제한이 생기므로 사용량을 각각 계산해야 합니다.

### 검색 provider fallback이 있으면 뉴스 품질도 보장되나요?

아닙니다. 가용성은 높일 수 있지만 오래된 기사·동명이인·중복 보도와 잘못된 출처를 걸러 주지는 않으므로 provenance와 freshness 검사가 필요합니다.

### AI 분석 결과를 자동 주문에 연결해도 되나요?

안 됩니다. LLM 보고서는 투자 조언이나 검증된 예측 신호가 아니며, 우선 읽기 전용 브리핑으로 사용하고 주문 system과 권한을 분리해야 합니다.

## 참고 자료
- [GitHub 저장소](https://github.com/ZhuLinsen/daily_stock_analysis)
