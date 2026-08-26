---
source_citations:
  - name: "Darknet matrix.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/matrix.c"
layout: post
title:  "Darknet matrix를 복사, 분할할 때 생기는 버그: 행 포인터 소유권과 CSV 처리"
summary: "Darknet matrix가 행마다 따로 할당되는 구조를 바탕으로 resize, hold-out, pop_column, CSV 입출력과 top-k 정확도의 경계 조건을 설명합니다."
description: "Darknet matrix의 row pointer 소유권, deep copy, resize, hold-out, pop_column과 CSV, top-k shape를 allocation, 경계 test로 설명합니다."
date:   2022-03-08 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetMatrix.jpg
  alt: DarkNet 시리즈 - Matrix 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "Darknet matrix의 전체 값은 하나의 연속 buffer인가요?"
    answer: "아닙니다. vals는 row pointer 배열이고 각 row의 float buffer가 따로 할당됩니다."
  - question: "hold_out_matrix는 선택한 row 값을 복사하나요?"
    answer: "아닙니다. 선택한 row pointer의 소유권을 새 matrix로 옮기고 원본 active row 수를 줄입니다."
  - question: "pop_column 뒤 각 row allocation도 작아지나요?"
    answer: "아닙니다. 값을 왼쪽으로 당기고 논리 cols만 줄이며 반환된 column buffer는 호출자가 해제합니다."
---

Darknet의 `matrix`는 **하나의 연속 2차원 배열이 아니라 `float *` 행을 각각 할당한 포인터 배열**이다. 그래서 행을 hold-out할 때는 값이 아니라 포인터 소유권이 이동하고, resize나 free도 바깥 배열과 각 행을 따로 처리해야 한다.

## make, copy, free가 행마다 도는 이유

`make_matrix`는 먼저 `rows`개의 행 포인터를 만들고 각 행에 `cols`개의 float를 할당한다.

```c
matrix make_matrix(int rows, int cols)
{
    matrix m;
    m.rows = rows;
    m.cols = cols;
    m.vals = calloc(m.rows, sizeof(float *));
    for(int i = 0; i < m.rows; ++i){
        m.vals[i] = calloc(m.cols, sizeof(float));
    }
    return m;
}
```

따라서 `m.vals[0]`부터 전체 원소가 연속한다는 보장은 없다. 해제할 때도 모든 행을 먼저 free하고 마지막에 포인터 배열을 해제한다.

```c
void free_matrix(matrix m)
{
    for(int i = 0; i < m.rows; ++i){
        free(m.vals[i]);
    }
    free(m.vals);
}
```

`copy_matrix`는 행과 값을 모두 새로 만드는 deep copy다.

```c
matrix copy_matrix(matrix m)
{
    matrix c = {0};
    c.rows = m.rows;
    c.cols = m.cols;
    c.vals = calloc(c.rows, sizeof(float *));
    for(int i = 0; i < c.rows; ++i){
        c.vals[i] = calloc(c.cols, sizeof(float));
        copy_cpu(c.cols, m.vals[i], 1,
                 c.vals[i], 1);
    }
    return c;
}
```

복사본의 값을 바꿔도 원본은 바뀌지 않으며 두 matrix를 각각 해제할 수 있다. 반대로 구조체 대입 `matrix b = a`만 하면 `vals`와 모든 행 주소를 공유한다.

## resize와 pop_column은 무엇을 실제로 줄이나

`resize_matrix`는 열 수는 유지하고 행 수만 바꾼다. 커질 때는 행 포인터 배열을 늘리고 새 행을 0으로 만들며, 작아질 때는 뒤쪽 행을 먼저 해제한다.

```c
matrix resize_matrix(matrix m, int size)
{
    if(m.rows < size){
        m.vals = realloc(
            m.vals, size*sizeof(float*));
        for(int i = m.rows; i < size; ++i){
            m.vals[i] = calloc(
                m.cols, sizeof(float));
        }
    }else if(m.rows > size){
        for(int i = size; i < m.rows; ++i){
            free(m.vals[i]);
        }
        m.vals = realloc(
            m.vals, size*sizeof(float*));
    }
    m.rows = size;
    return m;
}
```

`matrix`가 값으로 전달되므로 `realloc`이 바꾼 `vals` 주소는 반환값을 받아야 호출부에 남는다.

```c
m = resize_matrix(m, new_rows);
```

반환값을 버리면 호출부는 이전 주소를 계속 들고 있을 수 있다. 또한 코드는 `realloc` 실패를 검사하지 않으므로 호출 환경에서 메모리 부족 처리까지 해주지는 않는다.

`pop_column`은 제거할 열을 새 배열로 복사하고 뒤 열을 왼쪽으로 당긴 뒤 논리적인 `cols`만 1 줄인다.

```c
float *pop_column(matrix *m, int c)
{
    float *col = calloc(m->rows, sizeof(float));
    for(int i = 0; i < m->rows; ++i){
        col[i] = m->vals[i][c];
        for(int j = c; j < m->cols-1; ++j){
            m->vals[i][j] = m->vals[i][j+1];
        }
    }
    --m->cols;
    return col;
}
```

각 행의 실제 할당 크기는 줄이지 않는다. 반환된 `col`은 호출자가 해제해야 하고, `c`가 유효 범위인지 함수가 검사하지 않는다는 점도 함께 봐야 한다.

## hold_out_matrix는 행을 복사하지 않고 넘긴다

`hold_out_matrix`는 임의의 행 주소를 새 matrix `h`에 넣고, 원본 active 구간의 마지막 행 주소를 빈자리에 옮긴다.

```c
int index = rand()%m->rows;
h.vals[i] = m->vals[index];
m->vals[index] = m->vals[--(m->rows)];
```

이 방식은 값을 복사하지 않고 선택한 행의 소유권을 `m`에서 `h`로 이동한다. `m`의 `rows`를 매번 줄이므로 같은 active 행이 다시 선택되지 않는다.

그 결과 해제 규칙이 중요하다.

- `h.vals[i]`와 남은 `m.vals[i]`는 서로 다른 행을 소유한다.
- `free_matrix(h)`는 hold-out된 행을 해제한다.
- `free_matrix(*m)`은 감소한 `m.rows` 안의 나머지 행만 해제한다.
- 원본 `m.vals` 포인터 배열의 capacity는 줄이지 않지만, `rows` 밖 주소를 다시 행처럼 사용하면 안 된다.

`n`이 `m.rows`보다 크면 반복 중 `rand()%rows`의 분모가 0이 될 수 있다. 호출 전에 `n`이 0 이상 현재 행 수 이하인지 확인해야 한다.

## CSV 로드는 파일과 열 수를 어떻게 다루나

`csv_to_matrix`는 1,024개 행 포인터로 시작해 필요할 때 두 배로 늘린다. 첫 줄의 field 수를 전체 matrix의 `cols`로 사용한다.

```c
int n = 0;
int size = 1024;
m.vals = calloc(size, sizeof(float*));

while((line = fgetl(fp))){
    if(m.cols == -1){
        m.cols = count_fields(line);
    }
    if(n == size){
        size *= 2;
        m.vals = realloc(
            m.vals, size*sizeof(float*));
    }
    m.vals[n] = parse_fields(line, m.cols);
    free(line);
    ++n;
}
```

마지막에는 행 포인터 배열을 실제 행 수로 줄인다. 그러나 제시된 함수에는 `fclose(fp)`가 없다. 이 경로를 반복 호출한다면 열린 파일이 계속 남을 수 있으므로 읽기가 끝난 지점의 close 여부를 확인해야 한다.

빈 파일이면 `m.cols`가 초기값 `-1`로 남는다. 행마다 field 수가 다른 경우에도 첫 줄의 열 수를 기준으로 `parse_fields`를 호출한다. 따라서 loader를 신뢰하기 전에 빈 파일과 열 수 불일치를 별도로 검사하는 편이 안전하다.

`matrix_to_csv`라는 이름도 파일 저장으로 오해하기 쉽다. 이 함수는 파일명을 받지 않고 `printf`로 표준 출력에 CSV를 쓴다.

```c
if(j > 0) printf(",");
printf("%.17g", m.vals[i][j]);
```

## top-k 정확도의 shape 전제

각 row의 예측에서 상위 `k` 인덱스를 뽑고, truth의 그 위치 중 하나라도 0이 아니면 correct를 1 증가시킨다.

```c
top_k(guess.vals[i], truth.cols,
      k, indexes);

for(int j = 0; j < k; ++j){
    int class_id = indexes[j];
    if(truth.vals[i][class_id]){
        ++correct;
        break;
    }
}
```

마지막 반환값은 `correct / truth.rows`다. 함수 내부에는 다음 조건을 검사하는 assert가 없다.

1. truth와 guess의 row 수가 같은가?
2. 두 matrix의 class 열 수가 같은가?
3. `k`가 1 이상 `truth.cols` 이하인가?
4. `truth.rows`가 양수인가?

이 조건이 깨지면 정확도가 틀리는 데 그치지 않고 범위를 벗어난 메모리를 읽거나 0으로 나눌 수 있다. Darknet matrix helper를 안전하게 쓰는 기준은 단순하다. **행 포인터를 새로 만들었는지, 다른 matrix로 넘겼는지, 논리 shape만 줄였는지를 함수마다 구분하고 shape 전제를 호출 전에 확인해야 한다.**

## Ownership 표와 경계 Test를 어떻게 만들까

함수별로 vals 배열과 각 row가 새로 할당되는지, 이동되는지, 논리적으로만 축소되는지 기록한다. Shallow 구조체 복사, deep copy와 hold-out을 같은 방식으로 free하지 않는다. 빈 matrix, 한 row, resize 0→N→작게, hold-out 0, 전체 row를 sanitizer로 실행한다.

Realloc은 임시 pointer로 받아 실패할 때 기존 주소를 보존하고 반환 matrix를 반드시 호출부에 대입한다. Pop column은 `c`가 0 이상 `cols` 미만인지, hold-out은 `n`이 0 이상 `rows` 이하인지 먼저 검사한다.

## CSV를 데이터 계약으로 검증하는 방법

빈 파일, 열 하나, 서로 다른 열 수, 빈 field와 숫자가 아닌 field를 넣어 parser 결과를 명시한다. 첫 줄만 cols 기준으로 삼으므로 이후 행 field 수를 별도로 세지 않으면 조용한 잘림이나 기본값이 생길 수 있다. File close와 line buffer 해제를 반복 load test로 확인한다.

CSV 출력 함수가 stdout을 쓴다는 점을 API 이름에만 기대지 말고 redirect와 locale에 따른 decimal 표기도 확인한다. Round-trip이 목표라면 NaN, Inf와 정밀도 정책을 정한다.

## Metric Shape 오류를 어떻게 막을까

Truth와 guess의 rows, cols, k 범위와 rows가 양수인지 함수 시작에서 검증한다. Multi-label truth에서는 top-k 중 하나가 nonzero이면 correct라는 정의가 원하는 metric인지도 확인한다. 한 class, k=1, k=cols와 tie score를 포함한 작은 예제를 손으로 계산한다.

## Row Pointer 배열이 깨졌는지 어떻게 찾나요?

각 row의 주소, cols와 첫 값, 마지막 값을 출력하고 주소가 서로 달라도 정상이라는 점을 전제로 검사합니다. Structure assignment로 만든 shallow copy는 vals뿐 아니라 row 주소가 모두 같고, copy_matrix 결과는 모두 달라야 합니다. 행 하나를 바꿔 원본과 copy의 값이 독립인지 확인합니다.

Rows와 실제 non-null pointer 수가 다르면 free와 array 변환이 위험합니다. Resize 실패 또는 hold-out 뒤 active 범위 밖 pointer를 순회하지 않고, debug build에서 `rows`와 `cols`가 0 이상인지와 active row가 non-null인지 검증합니다.

## Hold-out 분할을 어떻게 재현하고 평가하나요?

각 row에 고유 id를 넣고 n개를 hold-out한 뒤 원본과 h의 id 집합이 겹치지 않고 합집합이 이전 전체와 같은지 봅니다. `rand()%rows`를 쓰므로 seed와 호출 순서를 기록하며 n이 rows보다 크거나 rows 0인 경우를 먼저 거부합니다. Hold-out이 label 비율을 보존하는 stratified split은 아니라는 점도 구분합니다.

두 matrix는 서로 다른 row를 소유하지만 원본 vals pointer 배열에는 active 범위 밖 오래된 주소가 남을 수 있습니다. Rows만큼만 free하고 capacity 밖 pointer를 다시 owner로 취급하지 않습니다. 분할 뒤 두 matrix를 어느 순서로 해제해도 double free가 없어야 합니다.

## Column 제거는 어떤 Shape 변화를 만드나요?

첫 번째, 중간, 마지막 column을 pop해 반환 배열과 각 row의 왼쪽 shift를 손으로 비교합니다. Logical cols는 줄지만 row allocation capacity는 그대로이므로 다시 column을 append할 수 있다는 뜻은 아닙니다. C 범위와 cols 0을 검사하고 반환 col의 owner를 호출자로 정합니다.

Pop 후 CSV와 metric 함수는 새 logical cols만 읽어야 합니다. Shallow copy가 같은 rows를 가리키는 상태에서 한 matrix의 cols만 줄이면 두 view의 metadata가 달라져 같은 memory를 다른 shape로 해석할 수 있습니다.

## CSV Resource와 오류 행을 어떻게 관리하나요?

열 수가 다른 행을 만나면 line number와 기대, 실제 field 수를 보고하고 partial matrix를 사용할지 중단할지 정합니다. Empty file은 rows 0과 cols 0 같은 명시적 shape로 만들고 -1을 정상 column 수로 넘기지 않습니다. File descriptor는 성공, 오류 경로 모두 닫습니다.

Repeated load/free를 작은 file descriptor 한도에서 실행해 leak을 찾고, 매우 긴 line과 많은 row에서 pointer 배열 크기 곱 overflow를 검사합니다. `matrix_to_csv`가 stdout을 쓰므로 호출자가 파일을 기대하는 API와 이름을 분리합니다.

## Top-k Metric을 어떻게 손계산하나요?

Rows 2, classes 3의 score와 one-hot truth를 만들고 k=1, 2, 3의 correct를 직접 구합니다. Tie에서 top_k가 어떤 index를 선택하는지, multi-label truth에서는 하나만 맞아도 correct가 되는 정의가 목적과 같은지 봅니다. Rows 0은 NaN 대신 명시적 결과 또는 오류를 반환합니다.

Guess와 truth의 shape를 비교한 뒤 index를 읽고, k를 class 수로 제한합니다. Metric 계산이 matrix ownership을 바꾸지 않는지도 const 계약으로 확인합니다.

## 소유권은 함수 이름이 아니라 주소 변화로 판단합니다

### deep copy는 행 주소까지 모두 달라야 합니다

`copy_matrix`가 만든 결과는 바깥 `vals` 주소뿐 아니라 각 `vals[i]`도 원본과 달라야 합니다. 2행 3열처럼 작은 matrix에 행마다 고유한 값을 넣고 주소와 값을 함께 출력하면 구조체 대입과 deep copy를 바로 구분할 수 있습니다. 복사본 한 원소를 바꿨을 때 원본이 유지되고 두 matrix를 어떤 순서로 해제해도 오류가 없어야 합니다.

### hold-out은 복사가 아니라 행의 이동입니다

`hold_out_matrix` 뒤에는 선택된 행 주소가 새 matrix에 그대로 나타나고, 원본 active 구간에서는 사라져야 합니다. 분할 전 행 주소 집합과 분할 후 두 matrix의 주소 합집합이 같고 교집합이 비어 있는지 검사하면 값 비교만으로 놓치는 이중 소유권을 찾을 수 있습니다. 행 포인터 배열의 capacity 밖에 남은 옛 주소는 소유권이 없는 찌꺼기이므로 `rows`를 넘어 순회해서는 안 됩니다.

소유권 표에는 함수별로 바깥 포인터 배열, 각 행, 반환 buffer의 생성자와 해제자를 적습니다. `make_matrix`, `copy_matrix`는 행을 새로 만들고, `hold_out_matrix`는 행을 옮기며, `pop_column`은 새 열 buffer를 반환합니다. 이 세 동작을 모두 “matrix를 반환한다”는 이유로 같은 free 규칙에 묶으면 double free나 leak이 생깁니다.

## 메모리 오류 증상으로 어느 계약이 깨졌는지 찾습니다

해제 중 double free가 나면 먼저 shallow 구조체 복사와 hold-out 행의 중복 소유를 봅니다. resize 직후 use-after-free가 나타나면 반환된 matrix를 호출부에 다시 대입했는지, `realloc` 전 주소를 다른 view가 보관하고 있지 않은지 확인합니다. 반복 CSV 로드에서 파일 descriptor가 늘면 행 buffer보다 `fclose`가 빠진 성공, 오류 경로를 먼저 추적합니다.

AddressSanitizer에는 make→copy→resize→pop→free를 여러 순서로 연결한 작은 테스트가 유용합니다. Valgrind나 leak sanitizer에서는 반환된 column과 CSV line buffer, hold-out된 두 matrix를 모두 해제했는지 봅니다. 메모리 도구가 통과해도 잘못된 행을 active 범위에 남기는 논리 오류는 고유 ID 집합 검사로 따로 찾아야 합니다.

0행, 0열은 allocator마다 `calloc(0, ...)`의 반환이 다를 수 있어 주소가 NULL인지로 성공을 판정하지 않습니다. 논리 shape와 함수가 허용한 경계를 먼저 정하고, 허용하지 않는 경우에는 allocation 전에 명시적으로 거부하는 편이 디버깅하기 쉽습니다.

## 연속 buffer로 바꿀지 기존 행 포인터를 유지할지 결정합니다

### 기존 API 호환이 우선이면 행 포인터 계약을 지킵니다

Darknet helper와 호출부가 `m.vals[i]`를 독립 행으로 취급하고 hold-out에서 포인터를 이동한다면 연속 2차원 buffer로 조용히 바꾸면 소유권 의미가 달라집니다. 값 layout만 같아도 행 교환, resize와 free 동작이 달라질 수 있으므로 포팅에서는 원문 계약을 먼저 재현하는 편이 안전합니다.

### 연속성이 필요하면 새 타입과 변환 경계를 둡니다

SIMD나 외부 라이브러리 때문에 연속 메모리가 필요하다면 기존 `matrix`를 같은 이름으로 재해석하기보다 contiguous 타입과 변환 함수를 별도로 두는 방법이 명확합니다. 변환 시 rows, cols와 stride를 기록하고, 누가 원본과 변환 buffer를 해제하는지 정합니다. hold-out이 필요한 경우 값 복사 비용을 감수할지 row index view를 둘지 의사결정을 문서화해야 합니다.

성능 비교에는 원소 순회 시간뿐 아니라 행별 allocation 수, 분할, resize 비용과 변환 비용을 포함합니다. 작은 matrix에서는 구조 변경의 복잡도가 이득보다 클 수 있고, 큰 연속 연산에서는 캐시 지역성 이득이 있을 수 있으므로 실제 workload로 판단합니다.

## CSV 오류는 부분 성공보다 명시적 정책이 중요합니다

열 수가 다른 행이나 숫자가 아닌 field를 만났을 때 0으로 대체할지, 해당 행을 버릴지, 전체 로드를 실패시킬지 먼저 정합니다. 첫 줄의 열 수만 기준으로 조용히 파싱하면 학습 데이터의 label 열이 밀려도 matrix shape는 그럴듯하게 남을 수 있습니다. 오류에는 파일명, 행 번호, 기대, 실제 field 수와 원문 일부를 민감 정보 범위 안에서 남깁니다.

빈 파일은 `rows=0, cols=-1` 같은 내부 중간 상태를 정상 matrix로 넘기지 않도록 호출 경계에서 처리합니다. 매우 긴 줄, 마지막 개행이 없는 파일, 빈 field와 지수 표기, NaN, Inf를 포함한 테스트로 `count_fields`와 `parse_fields`의 계약을 맞춥니다. `matrix_to_csv`는 stdout을 사용하므로 저장 실패를 함수 반환으로 알 수 없는 범위도 문서화합니다.

round-trip 테스트는 CSV로 내보낸 뒤 다시 읽어 rows, cols와 허용 오차 안의 값을 비교합니다. 다만 locale에 따른 소수점 표기와 `%.17g`의 문자열을 현재 parser가 다시 읽을 수 있는지 확인해야 합니다. 출력 함수 이름만 보고 파일 생성과 자원 관리를 기대해서는 안 됩니다.

## top-k를 모델 선택 지표로 쓸 때 어떤 한계가 있나요?

이 함수는 truth의 상위 k 예측 index 중 하나라도 nonzero이면 행 하나를 맞은 것으로 셉니다. one-hot 분류에는 익숙한 정의지만 multi-label 문제에서는 여러 정답 중 하나만 맞혀도 전체 행이 정답이 되고, class별 누락은 드러나지 않습니다. 사용 목적에 따라 precision@k, recall@k나 class별 지표가 필요한지 결정해야 합니다.

동점 score에서 `top_k`가 어느 index를 먼저 선택하는지 고정하지 않으면 플랫폼이나 구현 변경 뒤 경계 사례가 달라질 수 있습니다. 2행 3열 예제로 k=1부터 classes까지 손계산하고, k가 0, 열 수 초과, truth가 비어 있는 경우의 반환 정책을 정합니다. metric 함수가 잘못된 shape를 조용히 읽기 전에 호출부 또는 함수 시작에서 실패시키는 편이 낫습니다.

이 글은 제시된 Darknet `matrix` helper 조각의 메모리와 shape 계약을 해설합니다. 실제 저장소 버전에서 CSV parser, `top_k`와 호출부가 수정됐을 수 있으므로 포팅 대상 커밋의 함수 선언과 해제 경로를 다시 대조해야 합니다. 특히 다른 fork가 matrix를 연속 buffer로 바꿨다면 이 글의 행별 소유권 규칙을 그대로 적용할 수 없습니다.

## 자주 남는 질문

### Darknet matrix의 전체 값은 하나의 연속 buffer인가요?

아닙니다. vals는 row pointer 배열이고 각 row의 float buffer가 따로 할당됩니다.

### hold_out_matrix는 선택한 row 값을 복사하나요?

아닙니다. 선택한 row pointer의 소유권을 새 matrix로 옮기고 원본 active row 수를 줄입니다.

### pop_column 뒤 각 row allocation도 작아지나요?

아닙니다. 값을 왼쪽으로 당기고 논리 cols만 줄이며 반환된 column buffer는 호출자가 해제합니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet matrix.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/matrix.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet Dropout은 추론 때 왜 아무것도 하지 않나]({% post_url 2022-02-21-DarkNetDropoutLayer %}) — DarkNet의 inverted dropout이 학습 중 살아남은 값과 기울기를 1/(1-p)로 키우고, 추론에서는 입력을 그대로 두는 이유와 resize 구현 주의점을 설명합니다.
- [Darknet LSTM 역전파가 헷갈리는 이유: 8개 Connected Layer와 포인터 이동]({% post_url 2022-03-07-DarkNetLSTMLayer %}) — Darknet LSTM이 hidden state와 input용 8개 connected layer로 네 gate를 만들고 시간축 포인터를 앞뒤로 옮기는 과정을 해설합니다.
- [Darknet utils.c 이름만 믿으면 틀리는 7곳: mse\_array는 MSE가 아니다]({% post_url 2022-03-22-DarkNetUtils %}) — Darknet utils.c의 CLI 파서, 문자열, 파일, CSV, 난수, 배열 helper를 기능별로 정리하고, 함수 이름과 실제 동작이 다른 부분과 범위, 0 나눗셈, 입력 변경 위험을 짚습니다.
<!-- internal-links:end -->
