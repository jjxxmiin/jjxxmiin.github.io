---
layout: post
title:  "Darknet matrix를 복사·분할할 때 생기는 버그: 행 포인터 소유권과 CSV 처리"
summary: "Darknet matrix가 행마다 따로 할당되는 구조를 바탕으로 resize, hold-out, pop_column, CSV 입출력과 top-k 정확도의 경계 조건을 설명합니다."
date:   2022-03-08 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetMatrix.jpg
  alt: DarkNet 시리즈 - Matrix 대표 이미지
tags:
  - Darknet소스분석
  - Matrix
  - C메모리관리
math: true
---

Darknet의 `matrix`는 **하나의 연속 2차원 배열이 아니라 `float *` 행을 각각 할당한 포인터 배열**이다. 그래서 행을 hold-out할 때는 값이 아니라 포인터 소유권이 이동하고, resize나 free도 바깥 배열과 각 행을 따로 처리해야 한다.

## make·copy·free가 행마다 도는 이유

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

이 방식은 값을 복사하지 않고 선택한 행의 소유권을 `m`에서 `h`로 이동한다. `m->rows`를 매번 줄이므로 같은 active 행이 다시 선택되지 않는다.

그 결과 해제 규칙이 중요하다.

- `h.vals[i]`와 남은 `m.vals[i]`는 서로 다른 행을 소유한다.
- `free_matrix(h)`는 hold-out된 행을 해제한다.
- `free_matrix(*m)`은 감소한 `m.rows` 안의 나머지 행만 해제한다.
- 원본 `m.vals` 포인터 배열의 capacity는 줄이지 않지만, `rows` 밖 주소를 다시 행처럼 사용하면 안 된다.

`n > m->rows`이면 반복 중 `rand()%m->rows`의 분모가 0이 될 수 있다. 호출 전에 `0 <= n <= rows`를 확인해야 한다.

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
3. `1 <= k <= truth.cols`인가?
4. `truth.rows > 0`인가?

이 조건이 깨지면 정확도가 틀리는 데 그치지 않고 범위를 벗어난 메모리를 읽거나 0으로 나눌 수 있다. Darknet matrix helper를 안전하게 쓰는 기준은 단순하다. **행 포인터를 새로 만들었는지, 다른 matrix로 넘겼는지, 논리 shape만 줄였는지를 함수마다 구분하고 shape 전제를 호출 전에 확인해야 한다.**
