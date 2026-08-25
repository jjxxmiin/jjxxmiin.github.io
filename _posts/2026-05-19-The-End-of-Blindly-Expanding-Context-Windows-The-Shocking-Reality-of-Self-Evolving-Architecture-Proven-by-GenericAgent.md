---
layout: post
title: 'GenericAgent는 30K 컨텍스트로 충분할까: Skill 결정화의 효과와 오염 위험'
date: '2026-05-19 18:56:47'
categories: Tech
tags:
  - GenericAgent
  - AI에이전트
  - 컨텍스트윈도우
  - Skill
  - 에이전트보안
summary: GenericAgent가 긴 대화 기록 대신 성공한 작업을 실행 가능한 Skill로 저장하는 구조를 살펴보고, 반복 비용 절감과 스킬 오염·콜드 스타트·실행 권한의 교환 조건을 정리합니다.
author: AI Trend Bot
github_url: https://github.com/lsdefine/GenericAgent
image:
  path: https://opengraph.githubassets.com/1/lsdefine/GenericAgent
  alt: 'The End of Blindly Expanding Context Windows: The Shocking Reality of ''Self-Evolving''
    Architecture Proven by GenericAgent'
---

GenericAgent의 핵심은 컨텍스트를 무작정 늘리는 것이 아니라, 한 번 검증한 작업을 실행 가능한 Skill로 저장해 다음 요청의 추론량을 줄이는 데 있습니다.

## 긴 컨텍스트보다 중요한 것은 정보 밀도다

대화 기록, 검색 문서, 도구 설명을 계속 붙이면 모델이 참고할 정보는 늘지만 핵심과 잡음도 함께 섞입니다. GenericAgent가 택한 방향은 반대입니다. 원문 기준 코어는 약 3.3K 라인, 에이전트 루프는 약 100라인이며 브라우저·터미널·파일 시스템을 다루는 9개의 원자적 도구에서 출발합니다.

차이는 성공한 도구 호출 기록을 텍스트로 계속 보관하지 않는 데서 생깁니다. 반복할 가치가 있는 절차를 파이썬 함수 형태의 Skill로 추출해 Skill Tree에 넣고, 비슷한 문제가 오면 해당 함수를 다시 호출합니다. 원문은 이 방식으로 컨텍스트를 30K 토큰 아래에 유지하고 토큰 사용량을 다른 방식의 최대 6분의 1 수준으로 줄였다고 설명합니다. 다만 이 수치는 모든 모델·저장소·업무에 그대로 적용되는 보장이 아니라 프로젝트가 제시한 결과로 읽어야 합니다.

## Skill 결정화는 무엇을 남기는가

원문이 제시한 다음 코드는 Spring Boot 로그에서 누락된 Bean 후보를 찾는 개념용 핵심 조각입니다.

```python
@skill(
    name="parse_and_fix_spring_boot_500",
    description="Analyzes Spring Boot 500 error logs and suggests the fix for missing Bean dependencies.",
    requires_tools=["read_file", "search_codebase"]
)
def parse_and_fix_spring_boot_500(log_path: str) -> dict:
    import re
    from tools import read_file, search_codebase

    log_content = read_file(log_path)
    match = re.search(r"NoSuchBeanDefinitionException: No qualifying bean of type \'(.*?)\'", log_content)

    if not match:
        return {"status": "failed", "reason": "Not a missing Bean error."}

    bean_type = match.group(1)
    implementations = search_codebase(f"implements {bean_type.split('.')[-1]}")

    return {
        "status": "success",
        "missing_bean": bean_type,
        "action": f"Add @Component or @Service to {implementations[0]}."
    }
```

이 조각만으로는 실행할 수 없습니다. `skill` 데코레이터와 `tools` 모듈 구현, 빈 검색 결과 처리, Spring 설정 방식 확인, 실행 환경과 권한 정책이 빠져 있습니다. 특히 첫 번째 구현체에 곧바로 `@Component` 또는 `@Service`를 붙이라는 결론은 조건부 후보일 뿐입니다. Skill은 정답 저장소가 아니라 검토 가능한 자동화 초안이어야 합니다.

## 반복 업무에는 유리하지만 첫 판단을 대신하지 않는다

효과가 큰 대상은 입력과 성공 조건이 비교적 일정한 반복 업무입니다. 같은 형식의 로그 분류, 저장소 검사, 정해진 보고서 생성처럼 이전 절차를 다시 실행할 수 있는 일이라면 매번 긴 추론을 재현할 이유가 없습니다.

반대로 원인이 매번 달라지는 장애 조사나 운영 서버 변경처럼 오판 비용이 큰 업무는 그대로 결정화하면 위험합니다. 첫 해결이 우연히 성공했거나 잘못된 가정을 포함하면 오류도 Skill Tree에 영구 보존됩니다. Skill이 많아질수록 어떤 버전이 언제 검증됐는지, 현재 코드와 여전히 맞는지도 관리해야 합니다. 비어 있는 Skill Tree에서 시작하는 콜드 스타트 비용 역시 사라지지 않습니다.

## 도입 전에는 재사용률보다 폐기 절차부터 정한다

작게 시험하려면 다음 순서가 현실적입니다.

1. 읽기 전용이며 성공 여부를 자동 판정할 수 있는 업무 하나를 고릅니다.
2. 새 Skill마다 입력·출력·필요 도구·검증 날짜를 기록합니다.
3. 생성 즉시 재사용하지 않고 테스트와 사람의 리뷰를 통과시킵니다.
4. 실패율과 토큰 사용량을 기존 방식과 같은 요청 묶음으로 비교합니다.
5. 코드나 외부 시스템이 바뀌면 Skill을 비활성화하거나 다시 검증합니다.

터미널과 파일 시스템을 쓰는 Skill은 샌드박스와 최소 권한이 전제입니다. 반복률이 낮거나 검증 비용이 절감액보다 크다면 긴 컨텍스트를 Skill 저장소로 바꾸는 것만으로 이득이 생기지 않습니다. GenericAgent의 실용적 교훈은 “30K면 충분하다”가 아니라, 재사용할 지식을 짧고 검증 가능한 실행 단위로 바꾸라는 데 있습니다.

## 참고 자료

- https://github.com/lsdefine/GenericAgent
- https://arxiv.org/abs/2604.17091
