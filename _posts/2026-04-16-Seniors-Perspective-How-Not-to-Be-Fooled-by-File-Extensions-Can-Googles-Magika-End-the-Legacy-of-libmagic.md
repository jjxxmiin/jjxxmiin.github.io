---
layout: post
title: 'Magika로 업로드 파일을 막아도 안전할까: 1536바이트 분류의 한계'
date: '2026-04-16 06:54:57'
categories: Tech
tags:
  - AI보안
  - AI트렌드
summary: 'Magika의 앞, 중간, 끝 바이트 기반 파일 유형 분류 구조를 이해하고, 업로드 보안에서 단독 차단기가 아닌 보조 신호로 쓰는 방법을 정리합니다.'
description: "Magika의 1536-byte sampling, ONNX file type classification을 extension, MIME, parser와 교차 검증하고, polyglot, archive bomb, threshold, 격리 정책을 설계합니다."
github_url: https://github.com/google/magika
faq:
  - question: "Magika가 PDF라고 분류하면 그 파일은 안전한가요?"
    answer: "아닙니다. 파일 유형과 안전성은 다른 판단이며 실제 parser 검증, malware scan, 크기, 압축 한도와 격리 절차가 추가로 필요합니다."
  - question: "1536바이트만 읽어도 파일 전체 형식을 항상 알 수 있나요?"
    answer: "대부분의 유형을 빠르게 분류하기 위한 표본일 뿐 읽지 않은 영역, polyglot과 의도적 회피 입력까지 보장하지 않습니다."
  - question: "Magika 신뢰도 threshold는 모든 파일 형식에 같게 두면 되나요?"
    answer: "실행 파일처럼 오분류 비용이 큰 유형은 더 엄격하게 두고, 실제 업로드 표본의 형식별 혼동표로 승인, 격리, 거부 기준을 정해야 합니다."
image:
  path: https://opengraph.githubassets.com/1/google/magika
  alt: "google/magika GitHub 저장소 대표 이미지"
---

Magika는 확장자보다 나은 파일 유형 신호를 줄 수 있지만, 악성 파일이나 다중 형식 파일까지 판정하는 보안 엔진으로 단독 사용해서는 안 됩니다. 업로드에서는 extension, declared MIME, Magika, 실제 parser 결과를 교차 확인하고, 불일치나 낮은 confidence를 자동 승인하지 않는 router로 쓰는 편이 맞습니다.

[Magika](https://github.com/google/magika)는 파일의 내용을 기계학습 모델로 분류합니다. [공식 소개](https://opensource.googleblog.com/2024/02/magika-ai-powered-fast-and-efficient-file-type-identification.html)가 내세우는 장점은 빠른 CPU 추론과 많은 파일 형식에 대한 높은 정확도입니다. 다만 벤치마크 수치는 준비된 데이터셋의 결과이지, 조직의 실제 업로드 분포에서 그대로 재현된다는 약속은 아닙니다.

## 1536바이트가 파일 전체를 대신하는 방식

원문 기준 입력은 파일의 앞, 가운데, 끝에서 각각 512바이트를 뽑은 총 1536바이트입니다. 이를 사용자 정의 Keras 모델이 처리하고 ONNX Runtime으로 추론합니다. 약 1MB 모델과 파일당 1~5밀리초 수준의 CPU 지연, 99%를 넘는 벤치마크 정확도가 소개됩니다.

이 표본 추출은 전체 파일을 파싱하지 않고도 형식을 빠르게 구분하려는 절충입니다. 앞부분의 헤더만 보는 규칙보다 중간과 끝의 패턴까지 볼 수 있지만, 읽지 않은 영역의 내용은 알 수 없습니다. 서로 다른 형식을 겹쳐 만든 파일이나 의도적으로 분류기를 속이는 입력에 대한 안전 판정을 여기서 끌어내면 안 됩니다.

파일이 1536바이트보다 작거나 가운데 offset을 계산하기 어려운 streaming upload에서는 실제 library가 어떤 padding, sampling을 사용하는지 따라야 합니다. 임의로 처음 1536바이트만 넘기면 model이 학습한 입력 구성과 달라집니다. 원문의 8192바이트 API 조각처럼 일부 buffer만 받은 상태에서 “파일 끝”을 알 수 없는 구현도 주의해야 합니다.

| 신호 | 알려 주는 것 | 알려 주지 않는 것 |
|---|---|---|
| extension | 사용자가 붙인 이름 | 실제 byte 구조와 안전성 |
| declared MIME | client가 주장한 형식 | 위조, 오설정 여부 |
| Magika | 표본 byte가 닮은 file type | 악성 payload, parser 취약점 |
| 실제 parser | 해당 format으로 열리는지 | macro, script의 업무상 허용 여부 |
| malware scan | 알려진 위험 signature 등 | 모든 unknown 공격의 부재 |

각 신호의 결과를 하나의 boolean으로 너무 일찍 합치지 말고 감사 log에 보존합니다. 예를 들어 `.jpg`, `image/jpeg`인데 Magika가 executable로 분류했다면 거부하기 전에 격리하고 원본 hash와 판단 이유를 남깁니다. 반대로 네 신호가 모두 PDF라고 해도 내부 JavaScript나 embedded file 허용 정책은 별도입니다.

polyglot 파일은 둘 이상의 parser에서 의미 있는 구조로 열릴 수 있습니다. 분류기가 하나의 label을 내더라도 “다른 형식이 없다”는 증명이 되지 않습니다. 위험도가 높은 경로에서는 허용 parser로 완전히 decode한 뒤 안전한 representation으로 다시 encode하는 방법을 고려하되, 원본과 변환본의 보존, 감사 요건을 먼저 확인합니다.

## 업로드 경로에서는 라우터로 쓴다

가장 적절한 역할은 후속 처리기를 고르는 분류 신호입니다. 예를 들어 이미지로 분류된 파일은 이미지 디코더, 문서는 해당 문서 파서에 넘기고, 허용 목록 밖이거나 신뢰도가 낮은 결과는 격리합니다. 확장자, 선언된 MIME 유형, Magika 결과가 충돌하면 자동 승인하지 않는 정책이 필요합니다.

분류 뒤에도 파일 크기 제한, 압축 해제 한도, 실제 파서 검증, 악성 콘텐츠 검사와 격리 저장은 그대로 남습니다. 웹 서버 프로세스가 업로드를 직접 실행하거나 신뢰된 경로에 덮어쓰지 못하게 해야 합니다. 파일 유형을 맞혔다는 사실과 그 파일이 안전하다는 판단은 서로 다른 문제입니다.

압축 파일은 겉 형식만 맞혀도 내부 항목 수, 총 해제 크기와 경로 traversal 위험이 남습니다. archive는 별도 worker에서 CPU, memory, 시간과 중첩 depth 한도를 두고 풀며, 절대 경로나 `..`를 포함한 entry를 차단합니다. 문서 변환기도 network와 host file system을 제한한 일회성 sandbox에서 실행합니다.

업로드 원본은 web root나 실행 가능한 위치가 아닌 quarantine에 무작위 server-side 이름으로 저장합니다. client 파일명은 표시용 metadata로만 사용하고 path를 만들지 않습니다. scan, parser가 끝나기 전에는 다른 사용자가 다운로드할 수 없게 하며 결과가 timeout된 파일을 “통과”로 취급하지 않습니다.

## 원문의 API 예시는 완성된 판별기가 아니다

원문 FastAPI 조각은 업로드의 처음 8192바이트만 읽습니다. 큰 파일의 실제 가운데와 끝을 얻을 수 없으므로 Magika가 설명하는 표본 구조를 온전히 구현한 예가 아니며, 운영 가능한 보안 절차로 복사하면 안 됩니다. 메모리에 전부 올리지 않으면서 파일 크기를 확인하고 필요한 위치를 안전하게 읽는 경로가 별도로 필요합니다.

일반적인 경로는 upload를 크기 한도 안에서 임시 격리 파일로 streaming하며 hash와 실제 크기를 계산한 뒤 library API에 파일 경로를 넘기는 것입니다. 분류가 끝나면 동일 hash의 scan 결과를 재사용할 수 있지만 model, signature version과 정책 version이 달라졌다면 다시 평가해야 합니다. client 연결이 끊겼을 때 임시 파일이 남지 않는지도 확인합니다.

또한 PyPI의 [Magika 패키지](https://pypi.org/project/magika/)와 ONNX Runtime을 서비스 이미지에 넣으면 모델 파일, 런타임 크기, 초기화 시간도 측정해야 합니다. 짧은 함수 호출만 보고 전체 배포 비용을 판단해서는 안 됩니다.

## 자체 파일로 임계값을 정한다

운영 도입 전에는 정상 파일과 실제 오분류 사례를 모아 형식별 혼동표를 만듭니다. 낮은 신뢰도를 거부할지 수동 검토할지 정하고, 실행 파일이나 스크립트처럼 위험도가 높은 형식에는 더 엄격한 기준을 적용합니다. 사용자 생성 파일은 시간이 지나며 분포가 바뀌므로 오분류율과 미지원 형식을 계속 기록해야 합니다.

정상 업무 파일만으로 정확도를 계산하면 공격 경로의 false negative를 알 수 없습니다. 확장자, MIME 충돌, truncated 파일, password-protected archive, polyglot과 random bytes 같은 거부 사례를 별도 set으로 둡니다. test 파일은 실제 악성 실행물을 배포하지 않고도 정책 분기와 sandbox 동작을 검증할 수 있게 관리합니다.

threshold를 올리면 위험 파일 승인 가능성은 줄지만 정상 파일이 격리되는 비율과 사람이 검토할 queue가 늘어납니다. 형식별 false accept 비용과 review capacity를 함께 놓고 정합니다. model update 전후에 동일 corpus의 label, confidence 변화를 비교하고 갑자기 바뀐 고위험 유형은 승격을 멈춥니다.

결론적으로 Magika는 libmagic 같은 규칙 기반 판별을 무조건 폐기할 이유가 아니라, 여러 신호를 교차 검증할 수 있게 해 주는 추가 도구입니다. 두 방식이 불일치하는 사례를 감사하고 실제 파서 결과까지 확인할 때 비로소 업로드 정책이 단단해집니다.

운영 지표에는 분류 latency뿐 아니라 유형별 승인, 격리, 거부, 불일치 비율, manual review 대기와 parser crash를 포함합니다. Magika가 응답하지 않거나 model file을 읽지 못할 때 위험 업로드를 허용하는 fail-open은 피합니다. 기존 규칙 기반 경로로 제한적으로 fallback하거나 검토 queue로 보내는 선택을 명시합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/google/magika)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Shannon은 취약점 스캐너와 무엇이 다른가: 자율 펜테스트의 효용과 안전 조건]({% post_url 2026-02-09-Shannon-The-Autonomous-AI-Pentester %}) — 단순 보안 경고가 아닌 실제 해킹 공격을 수행하여 취약점을 검증하는 자율 AI 펜테스터 'Shannon'을 소개합니다. 설치부터 사용법, 아키텍처까지 상세히 알아봅니다.
- [TensorFlow 1.x 코드가 2.0에서 안 도는 이유: Session에서 Keras로 바뀐 흐름]({% post_url 2019-03-21-Tensorflow2 %}) — TensorFlow 2.0 alpha에서 Session, placeholder 중심 코드가 직접 함수 호출과 Keras 모델 흐름으로 어떻게 바뀌었는지 비교합니다. Fashion-MNIST 분류 예제로 전처리, 학습, 평가, 단일…
- [왜 VLM은 일부 토큰에서 더 취약할까: EGA의 엔트로피 공격]({% post_url 2026-01-11-Few-Tokens-Matter--Entropy-Guided-Attacks-on-Vision-Language-Models %}) — 생성 중 불확실성이 큰 토큰에 이미지 섭동을 집중하는 EGA의 위협 모델, 보고된 성공률과 방어 평가 조건
<!-- internal-links:end -->

## 자주 묻는 질문

### Magika가 PDF라고 분류하면 그 파일은 안전한가요?

아닙니다. 파일 유형과 안전성은 다른 판단이며 실제 parser 검증, malware scan, 크기, 압축 한도와 격리 절차가 추가로 필요합니다.

### 1536바이트만 읽어도 파일 전체 형식을 항상 알 수 있나요?

대부분의 유형을 빠르게 분류하기 위한 표본일 뿐 읽지 않은 영역, polyglot과 의도적 회피 입력까지 보장하지 않습니다.

### Magika 신뢰도 threshold는 모든 파일 형식에 같게 두면 되나요?

실행 파일처럼 오분류 비용이 큰 유형은 더 엄격하게 두고, 실제 업로드 표본의 형식별 혼동표로 승인, 격리, 거부 기준을 정해야 합니다.
