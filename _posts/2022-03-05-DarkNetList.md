---
layout: post
title:  "Darknet 연결 리스트가 한 번 pop 뒤 깨지는 이유: front·back과 메모리 소유권"
summary: "Darknet list 구현의 삽입·pop 불변식과 node, val, array를 각각 누가 해제해야 하는지 코드로 추적합니다."
date:   2022-03-05 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetList.jpg
  alt: DarkNet 시리즈 - List 대표 이미지
tags:
  - Darknet소스분석
  - 연결리스트
  - C메모리관리
math: true
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
