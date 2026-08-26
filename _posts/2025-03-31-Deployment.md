---
source_citations:
  - name: "Kubernetes Probe 공식 문서"
    url: "https://kubernetes.io/docs/concepts/workloads/pods/probes/"
  - name: "ONNX Runtime Quantization 공식 문서"
    url: "https://onnxruntime.ai/docs/how-to/quantization.html"
layout: post
title: "AI 모델 API가 뜬다고 배포가 끝난 게 아니다: 프로덕션 전 5개 Gate"
summary: "학습된 모델을 ONNX·FastAPI·Docker·Kubernetes로 옮길 때 정확도, 상태 확인, 롤백, 관측성, 비밀값과 드리프트를 어떤 순서로 검증해야 하는지 기존 예제의 위험까지 짚습니다."
description: "AI 모델 API를 프로덕션에 배포하기 전 예측 동등성·상태 검사·롤백·관측성·비밀값을 다섯 개 Gate로 나눠 검증하는 실무 체크리스트입니다."
faq:
  - question: "ONNX 변환 검사가 통과하면 예측도 같은가요?"
    answer: "아닙니다. 그래프 형식 검증과 예측 동등성은 별개이므로 대표 입력에서 원본·ONNX·양자화 모델의 출력과 정확도를 비교해야 합니다."
  - question: "liveness와 readiness는 왜 나눠야 하나요?"
    answer: "프로세스가 살아 있어도 모델 로딩이나 대표 추론이 실패할 수 있습니다. 재시작 판단과 트래픽 수신 가능 상태를 서로 다른 검사로 다뤄야 합니다."
  - question: "배포 실패 때 latest 태그로 돌아가면 되나요?"
    answer: "latest는 내용이 바뀔 수 있어 복구 기준으로 부적합합니다. 코드와 모델이 함께 묶인 이전 정상 commit SHA 같은 불변 버전을 기록해야 합니다."
image:
  path: /assets/img/thumb/Deployment.jpg
  alt: 프로덕션 환경에서의 인공지능 모델 배포 완벽 가이드 대표 이미지
date: 2025-03-31
categories: Tech
tags:
  - 경량화
  - MLOps
math: true
---

AI 모델 배포는 **API가 응답하는 순간이 아니라, 같은 입력의 결과가 맞고 장애를 감지하며 안전하게 이전 버전으로 돌아갈 수 있을 때** 완료됩니다. 아래 내용은 기존 예제에서 확인할 수 있는 구성 요소를 프로덕션 Gate로 다시 배열한 것이며, 그대로 복사해 실행하는 완성형 저장소가 아닙니다.

## Gate 1: 모델 파일이 아니라 예측 결과를 검증한다

기존 흐름은 ImageFolder로 10개 클래스를 학습한 ResNet-50을 ONNX로 내보내고, ONNX Runtime에서 추론한 뒤 동적 INT8 양자화를 적용합니다. export 설정에는 opset 12와 동적 batch 축이 포함됩니다. 이 단계에서 `onnx.checker`가 통과하는 것은 그래프 형식이 유효하다는 뜻일 뿐, PyTorch 결과와 수치적으로 같다는 보장은 아닙니다.

배포 후보마다 같은 검증 묶음을 고정해야 합니다.

1. 원본 모델과 ONNX에 동일한 대표 입력을 넣습니다.
2. class prediction뿐 아니라 출력 벡터의 차이를 비교합니다.
3. 양자화 전후 정확도와 클래스별 weighted metric을 다시 계산합니다.
4. 잘못된 확장자, 깨진 이미지, 예상 밖 크기 같은 실패 입력도 보냅니다.

양자화는 파일 크기와 계산량을 줄일 수 있지만 정확도를 무료로 보존하지 않습니다. 따라서 “변환 성공”과 “서비스 품질 유지”를 서로 다른 승인 항목으로 둬야 합니다.

## Gate 2: 프로세스 생존과 모델 정상 상태를 구분한다

기존 FastAPI 예제는 ONNX session을 전역으로 읽고 `/health`와 `/predict`를 제공하며 요청 수, 클래스별 예측 수, 처리 시간을 Prometheus 지표로 기록합니다. 여기서 단순한 health 응답은 웹 프로세스가 살아 있다는 사실만 보여줄 수 있습니다. 모델 파일을 읽을 수 있는지, 대표 입력에 정상 출력을 내는지까지 확인하려면 readiness 성격의 검사가 따로 필요합니다.

Kubernetes 예제의 두 replica, CPU·memory request와 limit, liveness/readiness probe, Service, Ingress, CPU 70% 기준의 2~10 replica HPA는 출발점입니다. 실제 값은 모델의 초기 로딩 시간과 요청량으로 다시 정해야 합니다. CORS wildcard도 편리한 개발 기본값이지 공개 서비스의 최종 정책이 아닙니다.

검수할 때는 정상 요청만 보내지 않습니다. pod 재시작 중 요청, 느린 추론, 메모리 압박, 잘못된 파일 업로드를 각각 재현하고 상태 코드와 지표가 운영자가 이해할 수 있게 남는지 봅니다.

## Gate 3: 빌드와 배포 사이에 되돌아갈 버전을 남긴다

Docker 예제는 Python 3.9와 2023년 시점의 의존성 버전을 사용하고 8080 및 metrics용 8000 포트를 노출합니다. 이는 당시의 학습용 골격입니다. 오래된 버전을 현재 환경의 안전한 조합으로 단정할 수 없고, 두 포트가 실제 애플리케이션 실행 방식과 일치하는지도 확인해야 합니다.

GitHub Actions 예제는 이미지에 `latest`와 commit SHA를 붙이고, registry secret으로 push한 뒤 `kubectl set image`와 rollout 상태를 확인합니다. 복구의 기준은 `latest`가 아니라 불변 SHA 태그입니다. 배포 전에는 다음 질문에 답할 수 있어야 합니다.

- 어떤 모델과 코드가 한 이미지에 들어갔는가
- 이전의 정상 SHA는 무엇인가
- rollout 실패를 무엇으로 판정하는가
- 새 버전의 오류율이 올라가면 누가 어떻게 되돌리는가

문서에 placeholder registry, namespace, repository가 남아 있다면 파이프라인은 아직 실행 가능한 계약이 아닙니다. 실제 값과 권한 범위를 정하기 전에는 운영 명령으로 포장하지 않는 편이 안전합니다.

## Gate 4: 대시보드보다 먼저 관측할 실패를 정한다

기존 구성은 Prometheus와 Grafana, Elasticsearch·Logstash·Kibana, Fluentd 예시를 담고 있습니다. 하지만 dashboard를 띄웠다고 관측성이 생기지는 않습니다. 요청량, 지연 시간, 오류율, 자원 사용량에 더해 모델 특유의 신호인 클래스 분포와 입력 분포 변화를 함께 봐야 합니다.

개발 예제의 `admin/admin123`, 보안 기능을 끈 단일 Elasticsearch node, `emptyDir` 저장소는 프로덕션 기본값이 될 수 없습니다. 재시작 뒤 데이터가 사라지는지, 로그에 개인정보가 들어가는지, 경보가 실제 담당자에게 도달하는지를 먼저 시험합니다. 저장 기간과 접근 권한도 모델 코드와 같은 배포 변경 사항으로 관리해야 합니다.

## Gate 5: 비밀값과 드리프트 예제를 실행 코드로 착각하지 않는다

MLflow·PostgreSQL·MinIO 예제에는 `minioadmin`과 `mlflow` 같은 하드코딩된 자격 증명이 있고, Vault 예제는 root token을 쓰는 개발 모드입니다. 이 값들은 구조를 설명하는 표식이지 운영용 비밀값이 아닙니다. Kubernetes Secret이나 Vault를 도입하더라도 최소 권한, 회전, 감사 로그가 없으면 이름만 바뀐 하드코딩에 불과합니다. NetworkPolicy 역시 실제 namespace와 통신 방향을 검증해야 합니다.

드리프트 감지 조각은 통계 검정의 p-value 0.05, 한 시간 간격 반복, webhook placeholder를 보여주지만 `fetch_recent_data`가 정의되지 않았습니다. 별도의 CronJob 예제와도 실행 방식이 겹칩니다. 그러므로 이 코드는 핵심 아이디어를 설명하는 불완전한 조각입니다. 기준 데이터 보관, 최근 데이터 수집, 다중 feature 검정, 경보 중복 억제, 재학습 승인 절차를 채우기 전에는 자동 운영으로 부르면 안 됩니다.

최종 승인표는 다섯 줄이면 충분합니다. **예측 동등성**, **실패를 반영하는 health**, **SHA 기반 rollback**, **행동 가능한 metric·log**, **회전 가능한 secret과 검증된 drift 절차**입니다. Argo CD와 통합 배포 script도 placeholder 저장소와 여러 선행 manifest를 가정하므로, 이 다섯 Gate를 대신하지 못합니다.

## Gate는 문서 항목이 아니라 배포를 멈추는 조건이다

체크리스트가 있어도 실패한 상태로 배포를 계속할 수 있다면 Gate가 아닙니다. 각 항목에는 통과 증거, 책임자, 실패했을 때의 행동이 붙어야 합니다. 예측 동등성 실패는 모델 변환을 중단하고, readiness 실패는 새 pod로 트래픽을 보내지 않으며, 오류율 상승은 이전 SHA로 되돌리는 식입니다.

간단한 배포 기록은 다음처럼 만들 수 있습니다.

| Gate | 남길 증거 | 실패 때 행동 |
|---|---|---|
| 예측 | 고정 입력별 원본·변환 출력 차이 | export·quantization 보류 |
| 상태 | cold start와 대표 추론 결과 | traffic 차단, 원인 로그 확인 |
| 복구 | 현재·이전 image SHA | 이전 정상 SHA로 rollback |
| 관측 | latency·error·모델 분포 경보 | 배포 중단 또는 담당자 호출 |
| 보안 | secret 출처·권한·회전 기록 | 노출 값 폐기와 재발급 |

## 장애 연습은 정상 요청과 다른 정보를 보여 준다

배포 전 staging에서 모델 파일을 읽지 못하는 경우, 첫 추론이 늦는 경우, 큰 입력으로 memory pressure가 생기는 경우, 의존 서비스가 timeout 나는 경우를 따로 재현합니다. 이때 사용자가 받는 상태 코드, readiness 변화, log의 원인, metric의 경보가 같은 사건을 일관되게 설명하는지 봅니다. 로그에는 실패 원인이 없고 dashboard에는 CPU만 보인다면 운영자는 모델 문제와 network 문제를 구분하기 어렵습니다.

성공 기준도 시간축으로 정합니다. 새 버전 직후에만 정상인지, 일정 요청을 처리한 뒤 memory가 계속 늘지 않는지, replica 교체 중 요청이 유실되지 않는지 확인합니다. 평균 latency만 보면 드물게 매우 느린 요청을 놓칠 수 있으므로 지연 분포와 timeout 비율을 함께 봅니다. 이 증거를 다음 배포에도 같은 형식으로 남겨야 변경 전후를 비교할 수 있습니다.

최종적으로 “API가 뜬다”는 다섯 Gate 중 일부에 불과합니다. 배포 완료는 **틀린 결과와 장애를 발견하고, 영향을 제한하며, 검증된 버전으로 돌아가는 흐름까지 실제로 실행해 본 상태**를 뜻합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Kubernetes Probe 공식 문서](https://kubernetes.io/docs/concepts/workloads/pods/probes/)
- [ONNX Runtime Quantization 공식 문서](https://onnxruntime.ai/docs/how-to/quantization.html)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [사진 위치 500m 정확도가 8.0%에서 22.1%로 오른 이유: Thinking with Map]({% post_url 2026-01-12-Thinking-with-Map--Reinforced-Parallel-Map-Augmented-Agent-for-Geolocalization %}) — 사진 단서로 지도 후보를 병렬 탐색하고 강화학습으로 검색 행동을 다듬는 구조, 정확도·비용·프라이버시 판단
- [오픈소스 LLM이 GPT API보다 싸질까: vLLM·PagedAttention·TCO 계산]({% post_url 2026-04-22-Tired-of-GPT-API-Bills-The-Real-Face-and-Serving-Optimization-Strategy-of-Open-Generative-AI-in-Production %}) — 오픈소스 LLM의 무료 가중치와 실제 서빙 비용을 구분하고, KV Cache·Continuous Batching·양자화와 GPU 이용률로 손익을 계산하는 방법을 정리합니다.
- [Supertonic 99M TTS가 정말 167배 빠를까: RTF·404MB·음질의 교환]({% post_url 2026-05-21-The-Era-of-API-Hustling-is-Over-Implementing-167x-Faster-On-Device-TTS-with-99M-Ultra-Light-Architecture-Supertonic-Deep-Dive %}) — Supertonic의 99M 파라미터·404MB ONNX 자산과 RTF 0.001~0.006 수치를 해석하고, 오프라인 TTS의 지연·음질·기기 호환성·커스텀 음성 비용을 판단합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### ONNX 변환 검사가 통과하면 예측도 같은가요?

아닙니다. 그래프 형식 검증과 예측 동등성은 별개이므로 대표 입력에서 원본·ONNX·양자화 모델의 출력과 정확도를 비교해야 합니다.

### liveness와 readiness는 왜 나눠야 하나요?

프로세스가 살아 있어도 모델 로딩이나 대표 추론이 실패할 수 있습니다. 재시작 판단과 트래픽 수신 가능 상태를 서로 다른 검사로 다뤄야 합니다.

### 배포 실패 때 latest 태그로 돌아가면 되나요?

latest는 내용이 바뀔 수 있어 복구 기준으로 부적합합니다. 코드와 모델이 함께 묶인 이전 정상 commit SHA 같은 불변 버전을 기록해야 합니다.
