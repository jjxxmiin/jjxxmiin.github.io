---
layout: post
title: 'Redux Toolkit이 필요한 앱은 따로 있다: Zustand·RTK Query 판단법'
date: '2026-05-19 08:51:54'
categories: Tech
tags:
  - ReduxToolkit
  - RTKQuery
  - 상태관리
  - React
  - 프론트엔드
summary: 'Redux Toolkit의 Immer 기반 reducer와 RTK Query 캐시를 살펴보고, 팀 규모·상태 복잡도·서버 캐시 요구에 따라 도입 여부를 판단합니다.'
author: AI Trend Bot
github_url: https://github.com/reduxjs/redux-toolkit
image:
  path: https://opengraph.githubassets.com/1/reduxjs/redux-toolkit
  alt: 'Is Redux Dead? No, It Bit Back with RTK: A 10-Year Vet''s Deep Dive into State
    Management'
---

Redux Toolkit은 공유 상태와 서버 캐시의 변경 경로를 팀 전체가 추적해야 할 때 강하지만, 단순한 로컬 UI 상태까지 모두 넣으면 여전히 과한 선택입니다.

이 글은 [Redux Toolkit 공식 문서](https://redux-toolkit.js.org/)와 [Immer](https://github.com/immerjs/immer), [Redux Toolkit 토론](https://github.com/reduxjs/redux-toolkit/discussions)을 기준으로 RTK를 고르는 판단법을 정리합니다. 오래된 Redux의 action type, action creator, reducer와 saga 보일러플레이트를 그대로 전제로 평가하면 현재 사용 방식과 맞지 않습니다.

## createSlice가 줄인 것은 불변성 실수다

createSlice의 reducer 안에서 state.value를 직접 바꾸는 것처럼 작성할 수 있는 이유는 [Immer](https://github.com/immerjs/immer)가 draft Proxy에서 변경을 기록하고 새 불변 상태를 만들기 때문입니다. action 생성과 reducer 정의도 한곳에 모여 파일 수를 줄일 수 있습니다.

이 문법은 RTK reducer의 draft 안에서만 안전합니다. 일반 객체나 컴포넌트에서 Redux 상태를 직접 수정해도 된다는 뜻이 아닙니다. 큰 중첩 구조를 무작정 넣으면 변경 범위와 렌더 비용을 이해하기 어려우므로 상태 모양과 selector를 함께 설계해야 합니다.

## RTK Query는 서버 상태를 Store 안에서 관리한다

RTK Query는 요청 결과, 구독과 캐시 수명을 Redux Store에 연결합니다. providesTags와 invalidatesTags로 목록과 상세 데이터의 관계를 표현하면 mutation 뒤 필요한 쿼리를 다시 가져올 수 있습니다. 로딩·오류·중복 요청을 직접 slice로 구현하는 일을 줄여 주는 것이 장점입니다.

태그를 너무 넓게 무효화하면 작은 변경마다 많은 요청이 발생하고, 너무 좁게 잡으면 오래된 화면이 남습니다. 엔드포인트별 캐시 키와 구독 수를 DevTools에서 확인하고 목록 항목 하나가 바뀔 때 실제로 어떤 쿼리가 재실행되는지 회귀 테스트해야 합니다.

## 낙관적 업데이트는 실패 경쟁을 시험한다

onQueryStarted에서 캐시를 먼저 바꾸고 요청이 실패하면 undo하는 패턴은 반응이 빠른 화면을 만들 수 있습니다. 하지만 같은 항목에 여러 mutation이 겹치면 먼저 실패한 요청의 롤백이 나중 성공 결과를 덮을 수 있습니다. 요청 순서, 중복 클릭과 서버 버전 충돌을 포함해 검증해야 합니다.

결제나 좌석 예약처럼 실제 확정이 중요한 상태는 화면을 먼저 성공으로 보이게 하는 것이 위험할 수 있습니다. 좋아요처럼 되돌리기 쉬운 동작과 구분하고, 실패 메시지와 재동기화 경로를 준비하세요. 원문의 코드 조각은 개념 예시이며 앱의 동시성 정책까지 완성한 구현은 아닙니다.

## 선택은 상태의 종류와 팀 비용으로 한다

컴포넌트 몇 개의 테마, 모달과 폼 상태라면 React 로컬 상태나 가벼운 Store가 이해하기 쉽습니다. 서버 데이터가 주이고 클라이언트 전역 상태가 거의 없다면 전용 서버 캐시 도구와의 비교도 필요합니다. 반대로 복잡한 B2B 화면, 여러 기능이 공유하는 상태, 일관된 로그와 중앙 정책이 중요하다면 RTK의 규율이 이득이 될 수 있습니다.

작은 기능 하나를 RTK와 현재 대안으로 각각 구현해 코드량만 아니라 새 개발자의 이해 시간, 캐시 버그, DevTools 추적성, 번들 영향과 테스트 비용을 비교하세요. ‘Redux는 죽었다’거나 ‘엔터프라이즈에는 무조건 RTK’라는 구호보다, 변경 경로를 예측 가능하게 만드는 비용이 실제 복잡도에 맞는지가 최종 기준입니다.
