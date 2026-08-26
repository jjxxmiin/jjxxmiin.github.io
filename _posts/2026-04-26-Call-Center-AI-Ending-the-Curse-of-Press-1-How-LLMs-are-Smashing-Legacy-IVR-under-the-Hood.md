---
layout: post
title: '콜센터 AI 응답이 1초 늦는 이유: VAD·Barge-in·SIP/RTP 지연 예산'
date: '2026-04-26 06:36:26'
categories: Tech
tags:
  - LLM
  - 음성AI
summary: '실시간 콜센터 AI의 20ms 오디오 청크·VAD·Barge-in 흐름을 따라가며, STT·LLM·TTS와 레거시 SIP/RTP 구간의 지연·비용·오답 위험을 점검합니다.'
description: "실시간 call center AI의 SIP/RTP→STT→LLM→TTS 지연을 VAD·barge-in turn ID, jitter·transcoding, p95·정책 tool·상담원 handoff 기준으로 검증합니다."
github_url: https://github.com/microsoft/call-center-ai
faq:
  - question: "더 빠른 LLM으로 바꾸면 콜센터 응답 지연이 해결되나요?"
    answer: "아닙니다. 전화망·transcoding, VAD, STT와 TTS까지 구간별 p95를 측정해야 실제 회선에서 느린 원인을 찾을 수 있습니다."
  - question: "Barge-in에서 TTS stop을 호출하면 고객이 즉시 듣지 않나요?"
    answer: "이미 buffer와 RTP로 나간 audio가 남을 수 있어 turn ID로 이전 chunk를 폐기하고 실제 회선에서 멈춘 시간까지 측정해야 합니다."
  - question: "환불 문의를 LLM이 자연스럽게 처리하면 자동 실행해도 되나요?"
    answer: "안 됩니다. 최신 정책·권한은 결정적 API가 판단하고 금액·대상 확인과 사람 승인 또는 상담원 escalation을 거쳐야 합니다."
image:
  path: https://opengraph.githubassets.com/1/microsoft/call-center-ai
  alt: "microsoft/call-center-ai GitHub 저장소 대표 이미지"
---

콜센터 AI의 1초 지연은 모델 하나의 문제가 아니라 STT·LLM·TTS와 전화망 변환이 이어진 결과이며, VAD와 Barge-in을 잘못 다루면 더 빠른 모델도 대화를 어색하게 만듭니다. 통화 ID·turn ID로 구간별 p95와 끼어든 뒤 실제 재생이 멈춘 시간을 재야 개선 지점을 찾을 수 있습니다.

## IVR을 없애기보다 대화 경로를 스트림으로 바꾼다

기존 IVR은 사용자의 발화가 끝난 뒤 STT, intent 분류, 정해진 답변과 TTS를 차례로 실행합니다. 단계가 끝날 때마다 다음 단계가 시작되는 turn-based 상태 머신입니다. 현대적인 CCAI는 오디오를 작은 청크로 계속 주고받는 full-duplex 스트림으로 바꿉니다.

원문은 20ms 단위 오디오 청크, WebSocket 또는 gRPC 통신과 VAD를 핵심으로 소개합니다. 사용자가 말하기 시작하면 현재 TTS 재생을 멈추고 새 발화를 듣는 Barge-in이 가능해집니다. 자연스러운 대화의 차이는 답변 문장보다 “언제 듣고 언제 멈추는가”에서 먼저 생깁니다.

그렇다고 정적 IVR을 모두 제거할 필요는 없습니다. 잔액 조회나 본인 확인처럼 경로가 명확한 업무는 결정적 흐름이 더 싸고 예측 가능할 수 있습니다. 복잡한 질문만 LLM에 보내는 하이브리드 라우팅이 비용과 위험을 줄입니다.

## speech_started 처리는 동시성 문제다

원문의 JavaScript는 WebSocket 이벤트를 파싱해 `speech_started`에서 오디오 플레이어와 현재 LLM turn을 취소하고, `audio_chunk`를 STT 파이프라인에 넣습니다. TTFT도 기록합니다.

이 코드는 의사 코드입니다. `ws`, `audioPlayer`, `llmStream`, 코덱과 버퍼 형식, 오류·재접속·인증이 정의되지 않았습니다. `stop()`과 `cancelCurrentTurn()`을 호출했다고 이미 전화망으로 나간 오디오까지 즉시 회수되는 것도 아닙니다. 새 발화와 이전 TTS가 동시에 처리될 때 어떤 turn ID를 폐기할지 상태 관리가 필요합니다.

시험할 때는 조용한 음성뿐 아니라 배경 소음, 짧은 맞장구, 긴 침묵과 사용자가 AI를 여러 번 끊는 상황을 넣어야 합니다. VAD가 소음을 발화로 오인하면 답을 계속 끊고, 임계치가 높으면 실제 끼어들기를 무시합니다.

turn 상태는 `listening`, `transcribing`, `thinking`, `speaking`, `cancelled`처럼 명시하고 모든 audio·text event에 같은 turn ID를 붙입니다. 새 `speech_started`가 오면 이전 LLM·TTS 결과가 늦게 도착해도 재생하지 않습니다. cancellation acknowledgement와 실제 child stream 종료를 구분해 resource가 계속 소비되지 않는지 봅니다.

| 상황 | 확인할 지표 | 실패 신호 |
|---|---|---|
| 짧은 맞장구 | false barge-in 비율 | “네”마다 답이 중단됨 |
| 겹친 발화 | stop→실제 회선 silence | 이전 TTS와 사용자 음성이 겹침 |
| 긴 침묵 | endpointing 시간 | 너무 일찍 turn 종료·무한 대기 |
| 배경 소음 | false speech start·STT 오류 | 반복 cancel과 비용 증가 |
| reconnect | turn·audio sequence 복구 | 이전 chunk 재생·중복 답변 |

VAD threshold 하나를 모든 channel에 쓰지 말고 codec·noise·언어별 평가 set으로 조정합니다. 너무 공격적인 endpointing은 문장 중간을 잘라 의미를 바꿀 수 있습니다. STT interim 결과와 final 결과가 달라질 때 이미 생성한 LLM response를 취소할 조건도 정합니다.

## SIP/RTP와 WebSocket 사이에서 시간이 더 든다

기존 PBX는 SIP로 통화를 설정하고 RTP로 오디오를 전달합니다. LLM 서비스가 WebSocket이나 WebRTC 스트림을 기대한다면 SBC나 FreeSWITCH 같은 중간 계층이 SIP/RTP를 연결하고 G.711 PCMU와 Opus 사이를 변환할 수 있습니다.

이 구간에서는 패킷 유실, jitter와 transcoding 지연이 생길 수 있습니다. STT나 LLM 지표만 보고 있으면 고객이 실제로 들은 지연의 원인을 놓칩니다. 통화 ID를 기준으로 다음 시간을 따로 기록해야 합니다.

- 전화망에서 첫 오디오 청크가 들어올 때까지
- VAD가 발화 시작·끝을 결정하는 시간
- STT의 중간·최종 결과 시간
- LLM 첫 토큰과 TTS 첫 오디오 시간
- TTS가 실제 회선에서 재생된 시간

레거시 전화망과 AI 스트림을 잇는 브리지는 단순 포맷 변환기가 아니라 전체 대화 상태의 일부입니다.

구간별 timestamp는 같은 clock 기준을 사용하거나 clock offset을 보정합니다. server log의 TTFT가 400ms여도 SBC queue와 RTP jitter buffer가 더해져 고객 체감은 달라질 수 있습니다. synthetic tone과 marker phrase를 실제 전화망으로 재생해 end-to-end mouth-to-ear latency를 주기적으로 측정합니다.

packet loss·jitter·reorder를 주입해 음질과 VAD가 어떻게 변하는지 봅니다. transcoding CPU가 peak 동시 통화에서 밀리면 model server가 정상이어도 전체 지연이 커집니다. active call, codec별 CPU와 dropped audio를 alert에 포함합니다.

## 900ms와 비용 10~20배는 조건부 숫자다

원문은 STT 300ms, LLM TTFT 400ms, TTS 200ms를 더한 900ms 예시를 제시합니다. 또한 모든 통화를 실시간 모델로 처리하면 기존 룰 기반 대비 비용이 10~20배 늘 수 있다고 경고합니다. 네트워크 위치, 음성 모델, 발화 길이와 과금 방식에 따라 달라지는 시나리오 숫자이지 보장값은 아닙니다.

평균 지연만 줄이기보다 p95와 고객이 말을 끊은 뒤 AI가 멈출 때까지의 시간을 봐야 합니다. 비용은 통화 건수보다 총 분, 동시 통화와 LLM으로 라우팅된 비율로 계산합니다. 장애 공지처럼 답이 정해진 전화는 캐시된 안내나 기존 IVR로 처리하고, 정책 판단이 필요한 통화만 생성 모델에 보내는 기준이 필요합니다.

## 환불 약속 전에 정책 API와 사람을 둔다

LLM은 자연스러운 문장을 만들 수 있지만 환불 권한이나 최신 정책을 스스로 보장하지 않습니다. RAG로 현재 장애 안내를 넣더라도 예상 복구 시간을 근거 없이 말하지 않도록 출처와 만료 시간을 관리해야 합니다.

환불, 계약 변경이나 민감 정보 조회는 모델의 문장을 바로 실행하지 말고 정책 API의 결정적 결과를 확인해야 합니다. 허용 범위를 벗어난 요청, 낮은 확신, 반복 실패와 화난 고객은 상담원에게 넘기는 escalation 조건을 둡니다. 녹취·프롬프트·도구 호출을 같은 통화 ID로 감사할 수 있어야 사후 원인도 찾을 수 있습니다.

콜센터 AI 도입의 첫 성공 기준은 사람을 없애는 비율이 아닙니다. 고객의 말을 끊지 않고, 틀린 약속을 하지 않으며, 필요할 때 맥락을 잃지 않고 사람에게 넘기는 비율입니다.

상담원 handoff에는 transcript 전체만 던지지 말고 본인 확인 상태, 고객 의도, 확인된 정책·tool 결과와 미해결 질문을 구조화합니다. 고객에게 전환을 알리고 상담원 연결 전까지 같은 질문을 반복하지 않습니다. 녹취 동의, 보존·삭제와 상담원 접근 권한도 통화 시작부터 일관되게 적용합니다.

파일럿은 내부·동의된 test call에서 VAD false positive, 중단 latency, 업무 해결·잘못된 약속, 사람 전환 성공과 분당 비용을 기록합니다. 평균이 좋아도 p95에서 대화가 무너지거나 취약 고객군·언어에서 오류가 크면 범위를 넓히지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/microsoft/call-center-ai)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [LiveKit Agents: 초저지연 실시간 음성 AI 에이전트를 위한 오픈소스 프레임워크]({% post_url 2026-08-04-LiveKit-Agents-Open-Source-Framework-for-Building-Realtime-Voice-AI-Agents %}) — LiveKit Agents는 WebRTC 기반의 초저지연 오디오 스트리밍을 활용해 실시간 대화형 음성 AI를 개발할 수 있는 오픈소스 프레임워크입니다. STT-LLM-TTS 조합 파이프라인부터 OpenAI Realtime API 같은…
- [VoxCPM은 정말 토크나이저가 없을까: FSQ·확산 TTS의 실제 구조]({% post_url 2026-04-14-Seniors-Perspective-Discarding-the-Tokenizer-Deep-Dive-into-VoxCPM-that-Broke-the-Rules-of-TTS %}) — VoxCPM이 기존 오디오 토큰 열 대신 의미·음향 계층과 FSQ 병목, 로컬 확산 디코더를 쓰는 방식과 레퍼런스 품질·장문·사칭 위험을 정리합니다.
- [Spark-TTS: 인공지능이 당신의 목소리를 만드는 방법]({% post_url 2025-03-13-SparkTTS %}) — Spark-TTS는 인공지능으로 더 자연스럽고 다양한 목소리를 만드는 혁신적인 기술입니다. 복잡한 기술을 단순화해 더 효율적으로 텍스트를 음성으로 변환합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### 더 빠른 LLM으로 바꾸면 콜센터 응답 지연이 해결되나요?

아닙니다. 전화망·transcoding, VAD, STT와 TTS까지 구간별 p95를 측정해야 실제 회선에서 느린 원인을 찾을 수 있습니다.

### Barge-in에서 TTS stop을 호출하면 고객이 즉시 듣지 않나요?

이미 buffer와 RTP로 나간 audio가 남을 수 있어 turn ID로 이전 chunk를 폐기하고 실제 회선에서 멈춘 시간까지 측정해야 합니다.

### 환불 문의를 LLM이 자연스럽게 처리하면 자동 실행해도 되나요?

안 됩니다. 최신 정책·권한은 결정적 API가 판단하고 금액·대상 확인과 사람 승인 또는 상담원 escalation을 거쳐야 합니다.

참고 자료:

- [openai.com 원문](https://openai.com/index/introducing-the-realtime-api/)
- [cloud.google.com 원문](https://cloud.google.com/solutions/contact-center)
- [공식 문서](https://www.twilio.com/docs/sip-trunking)
- [webrtc.org 원문](https://webrtc.org/getting-started/turn-server-and-sip)
