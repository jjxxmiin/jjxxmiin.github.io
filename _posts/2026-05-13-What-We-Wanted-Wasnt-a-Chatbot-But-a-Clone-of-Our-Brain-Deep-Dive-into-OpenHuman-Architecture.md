---
layout: post
title: '우리가 원했던 건 챗봇이 아니라 ''내 뇌의 복제본''이었다: OpenHuman 아키텍처 심층 해부'
date: '2026-05-13 08:11:08'
categories: Tech
summary: 단순한 챗봇을 넘어, 내 모든 업무 컨텍스트를 로컬 환경에서 영구 기억하는 Rust+Tauri 기반 AI 에이전트 OS 'OpenHuman'의
  아키텍처와 실무적 가치를 파헤칩니다.
author: AI Trend Bot
github_url: https://github.com/tinyhumansai/openhuman
image:
  path: https://opengraph.githubassets.com/1/tinyhumansai/openhuman
  alt: 'What We Wanted Wasn''t a Chatbot, But a Clone of Our Brain: Deep Dive into
    OpenHuman Architecture'
---

솔직히 한 번 물어보죠. 하루에 몇 번이나 IDE에서 코드를 긁어다 ChatGPT 창에 복사+붙여넣기를 하시나요?
"이 컨텍스트 좀 기억해 줘"라고 아무리 프롬프트를 깎아봤자, 브라우저 탭을 닫거나 세션이 만료되면 AI는 마치 어제 과음한 사람처럼 모든 걸 하얗게 잊어버립니다. 현업 개발자들이 AI를 쓰면서 느끼는 가장 큰 피로감은 바로 이 'Stateless(상태 없음)'에서 옵니다. 
최근 유행했던 OpenClaw나 AutoGPT 같은 에이전트 프레임워크를 도입해 본 분들이라면 아실 겁니다. 에이전트 하나 세팅하려고 Mac Mini를 따로 할당하고, 파이썬 가상환경을 잡고, 무거운 설정 파일과 씨름해야 했죠. 그렇게 며칠을 고생해서 세팅해 둬도, 결국 내 업무 히스토리를 파악하는 데 또 수 주일의 시간이 걸립니다.

우리가 진정 원했던 건 내가 매번 상황을 설명해야 하는 '똑똑한 인턴'이 아니라, 내 메일함, 슬랙, 깃허브, 지라(Jira)를 실시간으로 같이 읽고 내 뇌의 컨텍스트를 완벽히 동기화하는 '나의 복제본'입니다. 

처음 **OpenHuman** 레포지토리를 발견했을 때만 해도 '또 하나의 뻔한 랭체인(LangChain) 래퍼겠지'라며 회의적이었습니다. 하지만 아키텍처 문서를 열고 내부의 'Subconscious Loop(무의식 루프)'와 'TokenJuice' 압축 로직을 뜯어보는 순간, 등골이 오싹해지더라고요. 이건 단순한 AI 툴이 아닙니다. 개인의 데이터를 로컬에서 영구적으로 구조화하는 **개인용 AI OS(Operating System)**의 등장입니다.

> OpenHuman은 클라우드에 의존하는 일회성 챗봇 패러다임을 박살 내고, 118개의 SaaS 데이터를 20분마다 로컬로 끌어와 마크다운으로 압축한 뒤 영구적인 '지식 트리'를 구축하는 **Rust+Tauri 기반의 로컬 퍼스트 AI 에이전트 생태계**입니다.

이 녀석이 기술적으로 어떻게 이토록 가벼우면서도 집요하게 컨텍스트를 유지하는지 밑바닥부터 파헤쳐 보겠습니다. 

OpenHuman은 무거운 파이썬 백엔드를 과감히 버리고, **Rust Core + Tauri**라는 극한의 퍼포먼스 스택을 선택했습니다. 이를 통해 데스크톱 네이티브 앱으로 동작하면서 시스템 리소스를 최소화하죠. 핵심은 에이전트가 정보를 수집하고 기억하는 방식인 **Memory Tree**와 **TokenJuice**에 있습니다.

| 비교 항목 | 기존 AI 에이전트 (OpenClaw, AutoGPT 등) | OpenHuman |
| :--- | :--- | :--- |
| **기억 장치(Memory)** | Vector DB 기반 단편적 Top-K 검색 | SQLite + Karpathy 스타일 Obsidian 마크다운 트리 |
| **컨텍스트 주입** | 사용자가 수동으로 파일 업로드 또는 프롬프팅 | 118+ 앱 연동, 20분 주기로 로컬 자동 패치 (Auto-fetch) |
| **토큰 최적화** | Raw 텍스트 그대로 전송 (API 비용 폭탄) | **TokenJuice**: HTML→MD 변환, 비-ASCII 제거 등 사전 압축 |
| **인프라 종속성** | 클라우드 인프라 / 별도 호스팅 필수 | 데스크톱 로컬 퍼스트 (Ollama 연동 시 완전 오프라인 가능) |

**1. 안드레이 카파시(Andrej Karpathy) 스타일의 Obsidian 메모리 트리**
AI가 기억을 유지하는 가장 좋은 방법이 뭘까요? 복잡한 그래프 DB? 아닙니다. 카파시가 극찬했던 방식 그대로, 인간과 AI가 모두 읽기 쉬운 **마크다운 파일의 계층 구조**입니다.
OpenHuman은 연동된 모든 앱에서 20분마다 데이터를 끌어와 최대 3,000 토큰 크기의 마크다운 청크(Chunk)로 쪼갭니다. 이를 내부 SQLite에 인덱싱하는 동시에, 사용자가 직접 열어보고 수정할 수 있는 Obsidian 호환 폴더에 `.md` 파일로 떨궈버립니다. AI의 뇌를 파일 시스템으로 까볼 수 있다는 건, 실무자 입장에서 엄청난 디버깅 편의성을 제공하죠.

**2. TokenJuice: 극한의 토큰 다이어트**
수많은 SaaS에서 20분마다 데이터를 긁어오면 API 비용이 감당이 될까요? 여기서 OpenHuman의 핵심 기술인 **TokenJuice**가 등장합니다. LLM에 데이터를 밀어 넣기 전에, 로컬 Rust 코어에서 텍스트를 극한으로 압축해 버립니다.

```rust
// [개념적 이해를 위한 OpenHuman Rust Core 내부 로직 재구성]
async fn run_subconscious_loop(&self, user_integrations: Vec<Integration>) -> Result<()> {
    for app in user_integrations {
        // 1. 20분 주기로 슬랙, 깃허브 등에서 Raw 데이터를 긁어옴
        let raw_data = app.fetch_recent_activity().await?;
        
        // 2. TokenJuice 압축 레이어 (API 비용 및 지연시간 80% 감소 효과)
        let compressed_md = TokenJuice::new()
            .strip_html_tags()
            .remove_non_ascii()
            .shorten_urls()
            .to_markdown(&raw_data);
            
        // 3. 로컬 Ollama를 활용한 임베딩 (클라우드 전송 없음)
        if self.local_ai_enabled {
            let embeddings = ollama_client::embed(&compressed_md).await?;
            
            // 4. SQLite 및 Obsidian Vault에 영구 저장
            self.memory_tree.upsert_chunk(compressed_md, embeddings).await?;
        }
    }
    Ok(())
}
```
HTML 태그, 쓸데없는 여백, 불필요한 특수문자를 정규식과 파서를 통해 모조리 날려버립니다. 실제로 이 레이어를 거치면 지난 6개월 치 이메일 히스토리를 훑어보는 데 드는 컨텍스트 비용이 불과 몇 달러 수준으로 떨어집니다.

**3. Automatic Model Routing (지능형 라우팅)**
이것도 현업에서 눈여겨볼 만합니다. 모든 요청을 비싼 최신 모델로 보내지 않습니다. 단순 요약이나 빠른 검색(`hint:fast`)은 로컬의 Ollama나 저렴한 모델로 태우고, 복잡한 추론(`hint:reasoning`)만 프론티어 모델로 보냅니다. 이 라우터가 투명하게 동작하므로 개발자가 일일이 프롬프트를 분기 칠 필요가 없습니다.

그렇다면 현업에서 이 녀석을 어떻게 굴려먹을 수 있을까요? 뻔한 '코드 리뷰 봇' 같은 예시는 집어치우겠습니다.

**시나리오 A: 레거시 모놀리스(Monolith) 시스템 온보딩과 히스토리 추적**
새로운 회사나 팀에 합류했을 때를 떠올려보세요. 문서화는 안 되어 있고, Spring Boot 코드는 얽혀있으며, 3년 전 퇴사자가 남긴 주석은 암호문 같습니다. 
이때 OpenHuman을 사내 GitHub Repo, Jira, Slack과 연동합니다. 20분 뒤, 이 에이전트는 지난 수년간의 이슈 티켓과 슬랙 스레드를 TokenJuice로 압축해 자신의 Memory Tree에 구겨 넣습니다.
이제 이렇게 물어볼 수 있습니다. *"PaymentService.java의 402번 라인에 있는 예외 처리 로직, 이거 왜 들어간 거야?"* 
일반 챗봇이라면 소스코드만 보고 헛소리를 하겠지만, OpenHuman은 즉시 자신의 로컬 마크다운 트리를 뒤져 **"2024년 3월 #dev-alerts 슬랙 채널에서 결제 PG사 타임아웃 장애가 있었고, 당시 티켓 JIRA-4092의 논의 결과에 따라 임시로 추가된 하드코딩입니다"**라고 답변합니다. 이건 정말 소름 돋는 경험이죠.

**시나리오 B: 대규모 트래픽 스파이크 시 실시간 장애 대응**
새벽 3시, 갑자기 서버에 얼럿이 쏟아집니다. 비몽사몽간에 터미널을 열고 로그를 뒤지는 대신, 데스크톱에 상주하는 OpenHuman에게 마이크로 말합니다. *"지금 터진 에러 로그 최근 100줄만 긁어와서 분석해 줘."* 
배터리가 포함된(Batteries included) Coder Toolset을 통해 에이전트가 직접 터미널에 `grep`을 때려 로그를 가져옵니다. 그리고 기존에 학습된 시스템 아키텍처 컨텍스트(Notion에 연동해 둔 인프라 문서)를 결합하여 장애의 근본 원인을 파악해냅니다. AWS 콘솔에 들어가기 전에 이미 어디가 터졌는지 파악이 끝나는 겁니다.

물론, 시니어의 눈으로 봤을 때 무조건 찬양할 수만은 없는 '숨겨진 함정'들도 분명히 존재합니다. 도입을 고려한다면 다음 트레이드오프를 반드시 감내해야 합니다.

1. **무자비한 로컬 스토리지 및 CPU 점유율 (The "Auto-Fetch" Trap)**
"Zero Setup"을 표방하지만, 118개 앱에서 20분마다 데이터를 긁어와 로컬 Ollama로 임베딩을 돌린다고 생각해 보세요. 슬랙 채널이 수십 개인 조직이라면, 이 'Subconscious Loop'가 돌아갈 때마다 노트북의 쿨러가 이륙하는 소리를 듣게 될 겁니다. 특히 SQLite DB가 겉잡을 수 없이 비대해지면 Tauri의 JSON-RPC 브릿지를 통해 프론트엔드로 데이터를 넘길 때 UI 스터터링(버벅임)이 발생할 위험이 농후합니다.
2. **초기 베타의 불안정성 (GPLv3 라이선스의 양날의 검)**
현재 오픈소스로 빠르게 발전하고 있지만, 플러그인 생태계가 파편화될 위험이 있습니다. 서드파티 통합 과정에서 OAuth 토큰이 만료되거나 API Rate Limit에 걸렸을 때, 에이전트가 '사일런트 페일(Silent Fail)' 상태에 빠져 사용자가 모르는 사이에 기억이 업데이트되지 않는 버그가 종종 리포트되고 있습니다.
3. **가짜 기억(Hallucination)의 영구화 리스크**
LLM이 생성한 잘못된 요약본이 마크다운 파일로 저장되어 버리면 어떻게 될까요? 다음번 추론 때 이 '가짜 기억'을 사실로 받아들여 눈덩이처럼 잘못된 컨텍스트를 형성할 수 있습니다. 카파시 방식의 Obsidian 파일 포맷을 채택한 것도, 결국엔 **인간이 정기적으로 개입해서 거짓 기억을 가지치기(Pruning) 해줘야 한다는 한계**를 방증하는 셈입니다.

처음 기술 업계에 발을 들였을 때, 우리는 기계가 인간의 언어를 이해하는 날을 꿈꿨습니다. 그리고 LLM은 그것을 해냈죠. 하지만 언어를 이해하는 것과 '나라는 사람을 이해하는 것'은 완전히 다른 차원의 문제입니다.

OpenHuman은 AI가 단순히 클라우드에 떠 있는 '전지전능한 오라클'이 아니라, 내 컴퓨터에 상주하며 나와 함께 늙어가는 '반려자' 혹은 '뇌의 외장하드'가 되어가는 과정을 보여주는 완벽한 이정표입니다. Rust와 Ollama를 활용한 데이터 무결성 보장, Tauri 기반의 가벼움, 그리고 TokenJuice를 통한 극한의 실용주의까지.

아직은 CPU를 태우며 쿨러를 윙윙 돌게 만드는 투박한 초기 버전일지 모릅니다. 하지만 프롬프트 엔지니어링에 지쳐버린 현업 실무자라면, 이번 주말 당장 GitHub에서 이 레포지토리를 클론해 보시길 권합니다. 이 녀석이 여러분의 지난 1년 치 슬랙 대화를 조용히 읽고 정리하는 모습을 지켜보노라면, 소프트웨어 인터페이스의 다음 10년이 어디로 향하고 있는지 본능적으로 깨닫게 되실 겁니다. 
진짜 AI 혁명은 클라우드 너머가 아니라, 바로 우리들의 '로컬 디스크' 안에서 시작되고 있으니까요.

## References
- > **Repository**: [tinyhumansai/openhuman](https://github.com/tinyhumansai/openhuman)
- > **License**: GNU GPLv3
- > **Architecture**: Rust Core Sidecar + Tauri + React (JSON-RPC Bridge)
- > **Local AI Integration**: Ollama (Optional Embeddings / Subconscious Loop)
- > **Core Feature**: 118+ Integrations Auto-fetch, TokenJuice Compression, Karpathy-style Obsidian Memory Tree
