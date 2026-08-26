---
source_citations:
  - name: "Darknet list.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/list.c"
layout: post
title:  "Darknet 연결 리스트가 한 번 pop 뒤 깨지는 이유: front, back과 메모리 소유권"
summary: "Darknet list 구현의 삽입, pop 불변식과 node, val, array를 각각 누가 해제해야 하는지 코드로 추적합니다."
description: "Darknet 연결 list의 front, back, size 불변식, 마지막 pop 오류와 node, val, array의 분리된 소유권을 경계, 순회 test로 설명합니다."
date:   2022-03-05 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetList.jpg
  alt: DarkNet 시리즈 - List 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "마지막 원소를 pop한 뒤 어떤 상태가 되어야 하나요?"
    answer: "size는 0이고 front와 back이 모두 NULL이어야 하며, 반환된 val의 소유권은 호출자에게 남습니다."
  - question: "free_list는 각 node의 val도 해제하나요?"
    answer: "아닙니다. Node와 list 구조체만 해제하며 값까지 list가 소유할 때는 별도 contents 해제가 필요합니다."
  - question: "list_to_array는 val을 깊은 복사하나요?"
    answer: "아닙니다. 새 pointer 배열만 만들고 각 원소는 list node와 같은 val 주소를 가리킵니다."
---

Darknet의 `list` 구현에서 가장 위험한 지점은 **노드와 `val`의 소유권이 분리돼 있고, 마지막 원소를 `list_pop`한 뒤 `front`가 갱신되지 않는다는 것**이다. 삽입과 순회만 보면 단순하지만 빈 리스트의 불변식과 해제 순서를 확인하지 않으면 dangling pointer가 남는다.

## 빈 리스트가 지켜야 할 세 가지 상태

구조체는 크기와 양 끝 포인터만 가진다.

```c
typedef struct list{
    int size;
    node *front;
    node *back;
} list;
```

생성 직후에는 세 값이 함께 빈 상태를 나타낸다.

```c
list *make_list()
{
    list *l = malloc(sizeof(list));
    l->size = 0;
    l->front = 0;
    l->back = 0;
    return l;
}
```

따라서 구현 전반에서 유지해야 할 최소 불변식은 다음과 같다.

```text
size == 0  → front == NULL && back == NULL
size == 1  → front == back
size > 1   → front에서 next를 따라가면 back에 도달
```

`size`와 포인터 중 하나만 맞아서는 안전한 빈 리스트가 아니다.

## insert와 pop의 마지막 원소 경계 조건

`list_insert`는 새 node를 만들고 항상 뒤에 붙인다. `val` 자체를 복사하지 않고 포인터만 저장한다.

```c
void list_insert(list *l, void *val)
{
    node *new = malloc(sizeof(node));
    new->val = val;
    new->next = 0;

    if(!l->back){
        l->front = new;
        new->prev = 0;
    }else{
        l->back->next = new;
        new->prev = l->back;
    }
    l->back = new;
    ++l->size;
}
```

빈 리스트에서는 새 node가 `front`와 `back`이 되고, 원소가 있으면 이전 `back`의 `next`와 새 node의 `prev`가 연결된다.

`list_pop`은 마지막 node를 해제하지만 그 안의 값은 반환한다.

```c
void *list_pop(list *l)
{
    if(!l->back) return 0;
    node *b = l->back;
    void *val = b->val;
    l->back = b->prev;
    if(l->back) l->back->next = 0;
    free(b);
    --l->size;
    return val;
}
```

두 개 이상일 때는 새 `back->next`를 NULL로 만들어 연결이 맞는다. 문제는 원소가 하나일 때다. `l->back`은 NULL이 되지만 `l->front`는 방금 해제한 node를 계속 가리킨다. 이 상태에서 `free_list`나 `list_to_array`가 `front`부터 순회하면 해제된 메모리를 읽을 수 있다.

마지막 원소를 꺼내는 경로에는 다음 처리가 필요하다는 사실을 불변식에서 바로 확인할 수 있다.

```c
if(!l->back) l->front = 0;
```

또한 반환된 `val`은 pop이 해제하지 않는다. 이후 그 값을 쓸지 `free`할지는 호출자가 결정해야 한다.

## node와 val은 따로 해제된다

`free_node`는 연결된 node 구조체만 해제한다.

```c
void free_node(node *n)
{
    node *next;
    while(n){
        next = n->next;
        free(n);
        n = next;
    }
}
```

`free_list`도 이를 호출한 뒤 list 구조체를 해제할 뿐, `n->val`은 건드리지 않는다.

```c
void free_list(list *l)
{
    free_node(l->front);
    free(l);
}
```

값까지 이 list가 소유한다면 먼저 `free_list_contents`로 각 `val`을 해제하고, 이어서 `free_list`로 node와 list를 해제해야 한다.

```c
void free_list_contents(list *l)
{
    node *n = l->front;
    while(n){
        free(n->val);
        n = n->next;
    }
}
```

하지만 `val`이 문자열 상수, stack 주소, 다른 객체가 소유한 포인터라면 `free_list_contents`를 호출하면 안 된다. 이 자료구조는 `void *`만 저장하므로 소유 여부를 자체적으로 알 수 없다. list를 만드는 호출부에서 정책을 정해야 한다.

## list_to_array는 값의 깊은 복사가 아니다

배열 변환은 `size`만큼 포인터 배열을 새로 만들고 각 `val` 주소를 옮긴다.

```c
void **list_to_array(list *l)
{
    void **a = calloc(l->size, sizeof(void*));
    int count = 0;
    node *n = l->front;
    while(n){
        a[count++] = n->val;
        n = n->next;
    }
    return a;
}
```

새로 생긴 것은 `void **a`뿐이다. 배열 원소와 list node는 같은 `val`을 가리킨다. 따라서 다음을 구분해야 한다.

- 배열을 다 쓴 뒤에는 `a` 자체를 해제한다.
- `a[i]`를 해제하면 list의 `n->val`도 더는 유효하지 않다.
- list contents를 먼저 해제하면 배열의 원소도 dangling pointer가 된다.
- `size`와 실제 node 수가 다르면 할당 크기와 순회 결과가 어긋난다.

최소 테스트는 빈 리스트, 한 원소, 두 원소를 각각 만들고 `insert → pop → size/front/back 확인 → free` 순서로 실행하는 것이다. 이 작은 경계 테스트가 통과하지 않으면 parser나 option list에서 보이는 더 큰 오류도 자료구조 단계에서 시작됐을 수 있다. 이 구현을 안전하게 쓰는 기준은 연산 속도가 아니라 **양 끝 포인터의 불변식과 `val`을 누가 해제하는지 호출부까지 명시하는 것**이다.

## 연산마다 어떤 불변식을 검사할까

Insert 전후 `size` 증가, 새 back의 next NULL, 이전 back과 prev 연결을 확인한다. Pop 전후에는 size 감소, 새 back의 next NULL과 size 0이면 front도 NULL인지 본다. Debug build에서 front부터 센 node 수와 size, back부터 prev로 센 수가 같다는 검사를 두면 중간 연결 손상을 일찍 찾는다.

빈 list pop, 한 원소 pop 뒤 다시 insert, 모든 원소를 pop한 뒤 free하는 순서를 포함한다. 문제의 dangling front는 단순 size 검사만으로 발견되지 않으므로 실제 순회와 sanitizer가 필요하다.

## Val 소유권을 API에서 어떻게 표현할까

List가 owner인지 borrowed pointer container인지 생성 시 정하거나 free callback을 저장하면 호출부의 추측을 줄일 수 있다. 문자열 literal, stack pointer, heap object를 섞어 넣는 것은 하나의 `free_list_contents` 정책으로 안전하게 처리할 수 없다. Pop은 node만 없애고 val을 반환하므로 그 시점부터 해제 책임이 누구인지 문서화한다.

같은 val pointer를 두 node에 넣었다면 contents 해제는 double free가 된다. 중복을 허용하는 container에서는 refcount나 별도 owner가 필요하다. Array view가 남은 상태에서 contents를 해제하는 수명도 테스트한다.

## 순회 중 변경은 왜 위험할까

현재 node를 pop하거나 free한 뒤 `n->next`를 읽으면 use-after-free가 된다. 삭제 전 next pointer를 보존하고, 이 구현이 뒤 pop만 제공한다면 순회 중 임의 삭제를 흉내 내지 않는다. 여러 thread가 동시에 insert, pop하면 size와 양 끝 pointer 갱신이 원자적이지 않으므로 외부 lock이 필요하다.

`list_to_array`는 size로 먼저 할당한 뒤 실제 node를 순회하므로 둘이 어긋나면 overflow 또는 빈 slot이 생긴다. 변환 중 list가 바뀌지 않는다는 전제도 명시한다.

## 오류 입력과 Allocation 실패는 어떻게 처리할까

`make_list`와 `list_insert`의 malloc 결과가 null이면 이후 field 쓰기에서 crash한다. 실패를 상위로 전달할지 프로그램을 중단할지 정책을 정하고, insert 실패 때 기존 list 불변식은 그대로 유지해야 한다. Null list pointer를 각 API가 허용하는지도 문서화한다.

`list_to_array`에서 size 0의 calloc 반환값은 구현에 따라 null일 수 있으므로 빈 배열과 allocation 실패를 구분할 방법이 필요하다. 실제 node 수가 매우 커 `size*sizeof(void*)`가 overflow하지 않는지도 검사한다. Size를 signed int로 두었으므로 감소 전에 0인지 확인해 음수가 되지 않게 한다.

## Parser에서 List 오류가 어떻게 나타날까

Option line과 section을 node val로 저장하는 parser는 list 순서와 contents 수명에 의존한다. 마지막 pop 뒤 dangling front가 남으면 빈 목록을 array로 바꾸거나 free할 때 parser 입력과 무관한 crash처럼 보일 수 있다. 그래서 source line parsing을 조사하기 전에 list 불변식을 최소 test로 분리한다.

String val을 list가 소유한다면 line buffer를 재사용하기 전에 복사했는지 확인한다. 모든 node가 같은 temporary buffer를 가리키면 array 변환 후 마지막 line만 반복될 수 있다. Pointer container 문제와 text parser 문제를 구분한다.

## 고친 Pop을 어떻게 회귀 테스트할까

한 원소를 insert하고 pop한 뒤 `size==0`, `front==back==NULL`, 반환 val이 원래 pointer인지 검사한다. 이어 새 원소를 다시 insert하면 front와 back이 새 node를 가리켜야 한다. 두 원소에서는 첫 pop이 뒤 원소를 반환하고 남은 front, back이 같은 node가 되는지 본다.

마지막으로 val을 호출자가 해제한 뒤 빈 list를 free하고 sanitizer 오류가 없는지 확인한다. Contents를 list가 소유하는 경로에서는 pop하지 않은 node만 한 번씩 해제되는 test를 별도로 둔다.

## 자주 남는 질문

### 마지막 원소를 pop한 뒤 어떤 상태가 되어야 하나요?

size는 0이고 front와 back이 모두 NULL이어야 하며, 반환된 val의 소유권은 호출자에게 남습니다.

### free_list는 각 node의 val도 해제하나요?

아닙니다. Node와 list 구조체만 해제하며 값까지 list가 소유할 때는 별도 contents 해제가 필요합니다.

### list_to_array는 val을 깊은 복사하나요?

아닙니다. 새 pointer 배열만 만들고 각 원소는 list node와 같은 val 주소를 가리킵니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet list.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/list.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [DarkNet data.c 읽는 법: 이미지 경로가 X, y 배치가 되기까지]({% post_url 2022-02-17-DarkNetData %}) — DarkNet data.c의 경로 샘플링, 이미지, 라벨 동시 증강, 데이터 유형별 로더 분기와 멀티스레드 병합을 메모리 소유권 주의점까지 연결해 설명합니다.
- [Darknet image.c에서 자주 틀리는 5가지: CHW 인덱싱, 리사이즈, 메모리 소유권]({% post_url 2022-03-01-DarkNetImage %}) — Darknet의 image 구조체가 픽셀을 저장하고 복사, 리사이즈, letterbox, 증강, 탐지 결과를 그리는 흐름을 코드 기준으로 해설합니다.
- [Darknet layer 구조를 해제할 때 왜 터질까: LAYER\_TYPE과 free\_layer 소유권]({% post_url 2022-03-04-DarkNetLayer %}) — Darknet의 LAYER_TYPE enum이 실행 분기를 만드는 방식과 free_layer가 선택적 버퍼를 해제할 때 확인해야 할 메모리 소유권을 짚습니다.
<!-- internal-links:end -->
