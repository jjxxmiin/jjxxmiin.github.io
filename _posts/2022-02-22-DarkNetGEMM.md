---
layout: post
title: "DarkNet GEMM 인자 읽는 법: TA·TB·lda·BETA"
summary: "DarkNet GEMM 호출을 C=βC+αop(A)op(B)로 해석하고, 네 가지 전치 분기와 leading dimension이 실제 메모리 인덱스에 미치는 영향을 설명합니다."
date:   2022-02-22 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetGEMM.jpg
  alt: DarkNet 시리즈 - GEMM 대표 이미지
tags:
  - DarkNet
  - GEMM
  - 행렬곱
  - OpenMP
math: true
---

DarkNet의 GEMM 호출은 `C = BETA × C + ALPHA × op(A) × op(B)`이며, `TA`와 `TB`가 두 입력을 어떤 메모리 인덱스로 읽을지 결정합니다.

## M·N·K는 결과 모양부터 말한다

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

호출을 디버깅할 때는 `TA/TB` 이름만 보지 말고 이 인덱스가 각 버퍼의 실제 할당 범위 안에 있는지, 그리고 lda·ldb가 저장된 행 간격과 맞는지를 확인해야 합니다.

## 합성곱에서는 im2col이 B를 만든다

DarkNet 합성곱층은 이미지의 겹치는 커널 영역을 `im2col`로 펼쳐 2차원 B 행렬을 만들고, 필터 행렬 A와 GEMM을 수행합니다. 완전연결층은 배치 입력과 가중치를 바로 행렬로 봅니다. 서로 다른 층이 같은 GEMM을 재사용할 수 있는 이유입니다.

네 CPU 구현은 모두 바깥 i 루프에 OpenMP `parallel for`를 사용합니다. 하지만 이 코드 조각에는 다음 검사가 없습니다.

- M·N·K가 실제 버퍼 모양과 일치하는지
- lda·ldb·ldc가 각 할당 범위를 넘지 않는지
- A·B·C가 겹치는 메모리인지
- C를 새 결과로 쓸 때 BETA가 0인지, 누적할 때 1인지

또한 여기 나온 함수는 독립 실행 예제가 아니며 DarkNet의 행렬 버퍼와 컴파일 설정 안에서 사용됩니다. 값이 이상하면 연산 수식보다 먼저 `C`의 초기값과 BETA, 전치 플래그, 세 leading dimension을 한 호출 단위로 적어 보는 것이 가장 빠릅니다.
