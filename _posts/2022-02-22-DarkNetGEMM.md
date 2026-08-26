---
layout: post
title: "DarkNet GEMM 인자 읽는 법: TA, TB, lda, BETA"
summary: "DarkNet GEMM 호출을 C=βC+αop(A)op(B)로 해석하고, 네 가지 전치 분기와 leading dimension이 실제 메모리 인덱스에 미치는 영향을 설명합니다."
description: "DarkNet GEMM의 M, N, K, TA, TB, lda, ldb, ldc와 ALPHA, BETA 누적을 손계산, 경계, alias, 성능 검증 기준으로 설명합니다."
date:   2022-02-22 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetGEMM.jpg
  alt: DarkNet 시리즈 - GEMM 대표 이미지
tags:
  - 데이터분석
  - DarkNet
math: true
faq:
  - question: "DarkNet GEMM에서 BETA가 0과 1일 때 무엇이 다른가요?"
    answer: "0이면 기존 C를 지우고 새 곱만 쓰며, 1이면 기존 C에 ALPHA×op(A)×op(B)를 누적합니다."
  - question: "lda, ldb, ldc는 항상 행렬의 열 수인가요?"
    answer: "아닙니다. 실제 저장 buffer에서 다음 논리 행으로 이동하는 간격이며 전치 접근과 submatrix에서는 논리 열 수와 다를 수 있습니다."
  - question: "GEMM 전치 오류를 찾을 때 왜 정사각 행렬을 피해야 하나요?"
    answer: "정사각 shape에서는 잘못된 전치도 차원이 맞아 실행될 수 있으므로 M, N, K가 서로 다른 작은 행렬이 오류를 더 잘 드러냅니다."
---

DarkNet의 GEMM 호출은 `C = BETA × C + ALPHA × op(A) × op(B)`이며, `TA`와 `TB`가 두 입력을 어떤 메모리 인덱스로 읽을지 결정합니다. 평평한 포인터만 보고 행렬 모양을 짐작하지 말고 `M`, `N`, `K`와 leading dimension을 먼저 적어야 합니다. 전치 플래그가 틀려도 프로그램이 즉시 중단되지 않을 수 있으므로 작은 행렬의 수기 결과와 비교하는 편이 안전합니다.

## M, N, K는 결과 모양부터 말한다

GEMM의 결과 `C`는 `M × N`이고 두 행렬이 공유하는 축은 `K`입니다.

$$
C_{M \times N}
=
\beta C_{M \times N}
+
\alpha
op(A)_{M \times K}
op(B)_{K \times N}
$$

`TA = 0`이면 A를 그대로, 1이면 전치해서 사용합니다. `TB`도 같은 규칙입니다. `lda`, `ldb`, `ldc`는 단순히 논리적 열 개수라고 외우기보다, 각 행 또는 전치된 접근의 다음 줄로 이동할 때 쓰는 메모리 간격으로 보는 편이 정확합니다.

원문에 나온 대표 호출은 다음과 같습니다.

~~~c
gemm(0,0,m,n,k,1,a,k,b,n,1,c,n);
~~~

이는 A와 B를 전치하지 않고 `C = C + A × B`를 계산합니다. `BETA`가 1이므로 C를 덮어쓰지 않고 기존 값에 누적한다는 점이 중요합니다.

GEMM이 딥러닝 연산에서 왜 자주 쓰이는지는 원문이 연결한 [Pete Warden의 설명](https://petewarden.com/2015/04/20/why-gemm-is-at-the-heart-of-deep-learning/)도 함께 참고할 수 있습니다.

## BETA를 먼저 적용한 뒤 네 함수로 갈린다

`gemm`은 이 소스에서 `gemm_cpu`를 그대로 호출하는 얇은 래퍼입니다. CPU 함수는 먼저 C의 모든 원소에 `BETA`를 곱합니다.

~~~c
for(i = 0; i < M; ++i){
    for(j = 0; j < N; ++j){
        C[i*ldc + j] *= BETA;
    }
}
~~~

그다음 전치 플래그 조합으로 네 구현 중 하나를 고릅니다.

- `gemm_nn`: A와 B 모두 그대로
- `gemm_tn`: A만 전치
- `gemm_nt`: B만 전치
- `gemm_tt`: A와 B 모두 전치

함수 이름의 첫 글자는 A, 둘째 글자는 B의 논리적 사용 방향입니다. 예를 들어 `tn`을 두 행렬 모두 전치한다고 읽으면 실제 인덱스와 맞지 않습니다.

## 인덱스를 보면 전치가 명확해진다

NN 경로는 A의 i행 k열과 B의 k행 j열을 읽습니다.

~~~c
A[i*lda + k] * B[k*ldb + j]
~~~

NT 경로는 B를 `B[j*ldb + k]`로 읽습니다. 저장된 B의 j행을 논리적 곱셈에서는 전치된 열처럼 사용하는 방식입니다.

~~~c
A[i*lda + k] * B[j*ldb + k]
~~~

TN 경로는 A를 `A[k*lda + i]`로 읽고 B는 그대로 읽습니다.

~~~c
A[k*lda + i] * B[k*ldb + j]
~~~

TT 경로는 두 전치 접근을 함께 사용합니다.

~~~c
A[i + k*lda] * B[k + j*ldb]
~~~

호출을 디버깅할 때는 `TA/TB` 이름만 보지 말고 이 인덱스가 각 버퍼의 실제 할당 범위 안에 있는지, 그리고 lda, ldb가 저장된 행 간격과 맞는지를 확인해야 합니다.

## 합성곱에서는 im2col이 B를 만든다

DarkNet 합성곱층은 이미지의 겹치는 커널 영역을 `im2col`로 펼쳐 2차원 B 행렬을 만들고, 필터 행렬 A와 GEMM을 수행합니다. 완전연결층은 배치 입력과 가중치를 바로 행렬로 봅니다. 서로 다른 층이 같은 GEMM을 재사용할 수 있는 이유입니다.

네 CPU 구현은 모두 바깥 i 루프에 OpenMP `parallel for`를 사용합니다. 하지만 이 코드 조각에는 다음 검사가 없습니다.

- M, N, K가 실제 버퍼 모양과 일치하는지
- lda, ldb, ldc가 각 할당 범위를 넘지 않는지
- A, B, C가 겹치는 메모리인지
- C를 새 결과로 쓸 때 BETA가 0인지, 누적할 때 1인지

또한 여기 나온 함수는 독립 실행 예제가 아니며 DarkNet의 행렬 버퍼와 컴파일 설정 안에서 사용됩니다. 값이 이상하면 연산 수식보다 먼저 `C`의 초기값과 BETA, 전치 플래그, 세 leading dimension을 한 호출 단위로 적어 보는 것이 가장 빠릅니다.

## 한 호출을 어떤 표로 풀어쓰나요?

먼저 저장된 A와 B의 row, column, TA/TB 적용 뒤 논리 shape, C shape를 나란히 적습니다. 그다음 `op(A)`의 열과 `op(B)`의 행이 K로 같고 결과가 M×N인지 확인합니다. 마지막으로 각 buffer의 할당 원소 수와 최대 index를 leading dimension 식으로 계산합니다. C 포인터에는 shape 정보가 없으므로 이 검사가 없으면 범위 안의 잘못된 숫자도 정상처럼 보입니다.

M=2, N=3, K=4처럼 모두 다른 값과 1부터 시작하는 원소를 쓰면 네 전치 조합을 손으로 대조할 수 있습니다. ALPHA를 2, BETA를 0.5로 두고 C를 0이 아닌 값으로 시작하면 곱과 기존 C scaling이 모두 적용됐는지 한 시험에서 드러납니다.

## Leading Dimension은 언제 논리 폭과 달라지나요?

더 큰 matrix의 일부 row와 column만 submatrix로 곱해도 실제 다음 row까지의 간격은 원래 buffer 폭을 유지할 수 있습니다. Padding이나 alignment가 있는 buffer도 마찬가지입니다. `lda=K`라는 공식을 무조건 쓰면 연속 compact matrix에는 맞지만 view에서는 다음 row의 엉뚱한 위치를 읽습니다.

각 row 끝에 sentinel 값을 넣고 논리 영역 밖이 결과에 섞이지 않는지 확인합니다. Transpose flag가 바뀌면 어떤 index에 lda가 곱해지는지도 원문 네 loop에서 직접 봅니다. BLAS library로 교체할 때 row-major와 column-major API, transpose flag와 leading dimension 규칙을 함께 변환해야 합니다.

## BETA와 Buffer 초기화는 왜 한 계약인가요?

BETA 0이면 C 초기값이 결과에 영향을 주지 않아야 하고, BETA 1이면 이전 branch 또는 batch의 값을 의도적으로 더합니다. 새 output을 만드는 forward에서 실수로 1을 쓰면 buffer를 0으로 clear하지 않은 실행에서만 오류가 나타납니다. 반대로 gradient를 여러 sample, branch에서 모아야 하는데 0을 쓰면 앞 기여를 지웁니다.

C를 NaN과 임의 값으로 채운 시험도 유용합니다. 구현이 BETA 0에서도 먼저 `C*=0`을 계산하면 IEEE 연산에서 NaN이 남을 수 있는지 실제 code를 확인하고, 최적화 library의 beta=0 semantics와 비교합니다. 호출자와 kernel 중 누가 clear 책임을 갖는지 한 곳으로 정합니다.

## Aliasing은 어떤 결과를 망가뜨리나요?

A 또는 B와 C가 같은 memory를 공유하면 C를 쓰는 동안 아직 읽지 않은 input 원소가 바뀔 수 있습니다. 단순한 element-wise 연산과 달리 GEMM은 일반적으로 arbitrary in-place를 가정하지 않습니다. 정확히 같은 pointer뿐 아니라 offset view가 일부 겹치는지도 address 범위로 확인합니다.

필요하면 임시 C에 계산한 뒤 복사하지만 추가 memory와 비용을 명시합니다. 우연히 loop 순서에서 맞는 작은 사례를 alias 지원의 증거로 삼지 말고 모든 전치 조합과 multi-thread 경로에서 계약을 확인합니다.

## OpenMP와 수치 차이는 어떻게 평가하나요?

바깥 i row를 병렬화하면 서로 다른 thread가 다른 C row를 써야 race가 없습니다. 잘못된 ldc나 overlapping view는 논리 오류뿐 아니라 race를 만들 수 있습니다. Thread 수 1과 여러 개에서 결과가 허용 오차 안에 같은지 반복하고 sanitizer를 사용합니다.

K 방향 합산 순서나 최적화 kernel이 달라지면 float 마지막 자리는 달라질 수 있습니다. 절대 오차와 상대 오차를 함께 쓰되 NaN, 큰 systematic 차이, transpose 때문에 위치가 바뀐 결과를 단순 rounding으로 허용하지 않습니다. 큰 값과 작은 값이 섞인 matrix로 수치 안정성도 봅니다.

## 성능 최적화 전에 무엇을 고정하나요?

M, N, K가 작은 호출에서는 thread 시작 비용이 계산보다 클 수 있고, im2col 비용이 GEMM보다 큰 convolution도 있습니다. Kernel 시간만이 아니라 layout 변환과 workspace allocation을 포함해 측정합니다. CPU reference와 optimized BLAS의 같은 입력 결과를 먼저 맞춘 뒤 size별 benchmark를 합니다.

TA/TB 조합에 따라 memory locality가 달라지므로 한 shape의 평균만으로 전체 network 성능을 판단하지 않습니다. 실제 model에서 자주 나오는 shape, batch와 thread affinity를 기록해야 재현 가능한 비교가 됩니다.

## 자주 남는 질문

### DarkNet GEMM에서 BETA가 0과 1일 때 무엇이 다른가요?

0이면 기존 C를 지우고 새 곱만 쓰며, 1이면 기존 C에 ALPHA×op(A)×op(B)를 누적합니다.

### lda, ldb, ldc는 항상 행렬의 열 수인가요?

아닙니다. 실제 저장 buffer에서 다음 논리 행으로 이동하는 간격이며 전치 접근과 submatrix에서는 논리 열 수와 다를 수 있습니다.

### GEMM 전치 오류를 찾을 때 왜 정사각 행렬을 피해야 하나요?

정사각 shape에서는 잘못된 전치도 차원이 맞아 실행될 수 있으므로 M, N, K가 서로 다른 작은 행렬이 오류를 더 잘 드러냅니다.

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Deconvolutional Layer 출력 크기와 col2im 흐름]({% post_url 2022-02-18-DarkNetDeconvLayer %}) — DarkNet 전치 합성곱층이 GEMM 결과를 col2im으로 겹쳐 쓰며 공간 크기를 키우는 과정과 역전파, 초기화 주의점을 코드 차원으로 설명합니다.
- [DarkNet Connected Layer 순전파, 역전파: GEMM 차원 따라가기]({% post_url 2022-02-12-DarkNetConnectedLayer %}) — DarkNet 완전연결층이 GEMM으로 출력을 만들고, 역전파로 가중치와 입력 기울기를 계산한 뒤 모멘텀 방식으로 갱신하는 순서를 코드 기준으로 설명합니다.
- [DarkNet Convolutional Layer는 왜 im2col과 GEMM을 쓰나]({% post_url 2022-02-13-DarkNetConvolutionalLayer %}) — DarkNet 합성곱층의 출력 크기, 그룹별 im2col, GEMM 순전파, 가중치, 입력 역전파와 구현상 확인할 지점을 코드 차원으로 정리합니다.
<!-- internal-links:end -->
