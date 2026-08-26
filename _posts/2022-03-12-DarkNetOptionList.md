---
source_citations:
  - name: "Darknet option_list.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/option_list.c"
layout: post
title:  "Darknet data.cfg 옵션이 조용히 잘못 읽히는 이유: '=' 파싱과 문자열 수명"
date:   2022-03-12 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetOptionList.jpg
  alt: DarkNet 시리즈 - Option List 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
summary: "Darknet option_list.c가 설정 한 줄을 key와 value로 나누는 과정, used 추적, 기본값 처리, 원본 문자열에 기대는 메모리 소유권을 코드 중심으로 점검합니다."
description: "Darknet option_list.c의 in-place key=value parsing, used 상태와 atoi, atof 기본값을 따라 빈 key, NULL value, 문자열 수명 실패를 설명합니다."
math: true
faq:
  - question: "등호가 없는 설정 줄은 현재 read_option에서 거부되나요?"
    answer: "아닙니다. Loop가 len에서 끝나 조건을 통과해 val이 NULL인 항목이 삽입될 수 있습니다."
  - question: "option_insert는 key와 value 문자열을 복사하나요?"
    answer: "아닙니다. 원본 line buffer 안의 pointer를 저장하므로 그 buffer 수명이 option 사용보다 길어야 합니다."
  - question: "quiet 조회는 used 상태도 바꾸지 않나요?"
    answer: "아닙니다. 기본값 메시지만 생략하며 key가 있으면 일반 조회처럼 used를 1로 바꿉니다."
---

Darknet의 옵션 파서는 `key=value` 한 줄을 직접 잘라 보관하므로, `=`이 없는 줄과 문자열 수명을 먼저 점검해야 합니다. 특히 현재 `read_option`은 `=`이 전혀 없는 줄을 정상적으로 거부하지 못합니다.

## 설정 파일은 줄 단위로 읽고 원본 버퍼를 보관한다

`read_data_cfg`는 파일을 열어 `fgetl`로 한 줄씩 읽고, `strip`으로 앞뒤를 정리합니다. 빈 줄과 `#`, `;`로 시작하는 줄은 즉시 해제하며, 나머지는 `read_option`에 넘깁니다.

```c
list *read_data_cfg(char *filename)
{
    FILE *file = fopen(filename, "r");
    if(file == 0) file_error(filename);
    char *line;
    int nu = 0;
    list *options = make_list();

    while((line = fgetl(file)) != 0){
        ++nu;
        strip(line);
        switch(line[0]){
            case '\0':
            case '#':
            case ';':
                free(line);
                break;
            default:
                if(!read_option(line, options)){
                    fprintf(stderr,
                        "Config file error line %d, could parse: %s\n",
                        nu, line);
                    free(line);
                }
                break;
        }
    }
    fclose(file);
    return options;
}
```

파싱에 성공한 `line`은 이 함수에서 해제하지 않습니다. 그 이유는 다음 단계에서 `key`와 `val`이 별도 복사본이 아니라 그 한 줄 안을 가리키기 때문입니다. 따라서 정리 코드를 바꿀 때는 노드와 `kvp`만 볼 것이 아니라, 원본 줄을 누가 언제 해제하는지도 함께 정해야 합니다.

## read_option의 경계 조건에는 실제 함정이 있다

`read_option`은 처음 만난 `=`을 널 문자로 바꿉니다. `key`는 문자열 시작점, `val`은 그 바로 다음 문자를 가리킵니다.

```c
int read_option(char *s, list *options)
{
    size_t i;
    size_t len = strlen(s);
    char *val = 0;

    for(i = 0; i < len; ++i){
        if(s[i] == '='){
            s[i] = '\0';
            val = s+i+1;
            break;
        }
    }
    if(i == len-1) return 0;

    char *key = s;
    option_insert(options, key, val);
    return 1;
}
```

이 조건문을 입력별로 대입하면 차이가 드러납니다.

- `width=416`: `key`와 `val`이 나뉘어 저장됩니다.
- `width=`: `=`이 마지막 문자라서 0을 반환합니다.
- `width`: 반복문이 `i == len`으로 끝나므로 `i == len-1`이 거짓입니다. 결국 `val == 0`인 항목이 삽입됩니다.
- `=416`: 빈 키도 별도 검사 없이 삽입됩니다.

따라서 “`=`이 없으면 오류”라고 이해하면 현재 코드와 다릅니다. 최소한 `val`이 설정되었는지, 키와 값이 비어 있지 않은지를 검사해야 안전합니다. `option_insert` 역시 문자열을 복사하지 않고 포인터만 저장합니다.

```c
void option_insert(list *l, char *key, char *val)
{
    kvp *p = malloc(sizeof(kvp));
    p->key = key;
    p->val = val;
    p->used = 0;
    list_insert(l, p);
}
```

`val`은 대개 할당 블록의 중간 주소이므로 따로 `free(val)`할 수 없습니다. 이 표현을 유지한다면 원본 시작 주소인 `key`와 `kvp`, 리스트 노드의 해제 책임을 일관되게 설계해야 합니다.

## 조회는 값을 반환하는 동시에 used 상태를 바꾼다

`option_find`는 키가 일치하면 `used = 1`로 바꾸고 값 포인터를 반환합니다. 단순 조회처럼 보이지만 리스트 상태를 변경하는 함수입니다.

```c
char *option_find(list *l, char *key)
{
    node *n = l->front;
    while(n){
        kvp *p = (kvp *)n->val;
        if(strcmp(p->key, key) == 0){
            p->used = 1;
            return p->val;
        }
        n = n->next;
    }
    return 0;
}

void option_unused(list *l)
{
    node *n = l->front;
    while(n){
        kvp *p = (kvp *)n->val;
        if(!p->used){
            fprintf(stderr, "Unused field: '%s = %s'\n", p->key, p->val);
        }
        n = n->next;
    }
}
```

그래서 `option_unused`는 단순히 파일에 있던 모든 옵션이 아니라, 조회되지 않은 옵션을 찾아내는 진단 도구입니다. 철자가 틀린 설정이나 이 빌드에서 사용하지 않는 필드를 찾는 데 유용하지만, 조회 함수가 호출되기만 해도 사용된 것으로 표시된다는 한계가 있습니다.

문자열, 정수, 실수 조회 함수는 모두 이 함수 위에 얹혀 있습니다.

```c
char *option_find_str(list *l, char *key, char *def)
{
    char *v = option_find(l, key);
    if(v) return v;
    if(def) fprintf(stderr, "%s: Using default '%s'\n", key, def);
    return def;
}

int option_find_int(list *l, char *key, int def)
{
    char *v = option_find(l, key);
    if(v) return atoi(v);
    fprintf(stderr, "%s: Using default '%d'\n", key, def);
    return def;
}

float option_find_float_quiet(list *l, char *key, float def)
{
    char *v = option_find(l, key);
    if(v) return atof(v);
    return def;
}
```

`quiet` 변형은 기본값 사용 메시지만 생략합니다. 키가 있으면 똑같이 `used`가 바뀝니다. 또한 `atoi`와 `atof` 결과를 바로 쓰므로, 잘못된 문자열과 실제 0을 구별하거나 범위를 확인하는 검증은 이 코드에 없습니다.

## metadata를 읽을 때 값의 사용 시점을 지켜야 한다

`get_metadata`는 먼저 `names`를 찾고, 없으면 `labels`를 찾습니다. 둘 다 없으면 오류를 출력하고, 클래스 수는 기본값 2로 읽습니다.

```c
metadata get_metadata(char *file)
{
    metadata m = {0};
    list *options = read_data_cfg(file);

    char *name_list = option_find_str(options, "names", 0);
    if(!name_list) name_list = option_find_str(options, "labels", 0);
    if(!name_list) {
        fprintf(stderr, "No names or labels found\n");
    } else {
        m.names = get_labels(name_list);
    }
    m.classes = option_find_int(options, "classes", 2);
    free_list(options);
    return m;
}
```

중요한 순서는 `get_labels(name_list)`가 `free_list(options)`보다 먼저 실행된다는 점입니다. `name_list`가 옵션 줄 내부를 가리키므로, 리스트를 정리한 뒤 이 포인터를 다시 쓰는 구조로 순서를 바꾸면 수명 문제가 생길 수 있습니다.

설정 문제를 추적할 때는 다음 네 가지를 함께 보면 됩니다. 원문 한 줄에 `=`이 실제로 있는지, 변환 전에 문자열 형식이 맞는지, 필요한 키가 `used`로 표시됐는지, 옵션 리스트를 정리한 뒤에도 내부 포인터를 보관하고 있지 않은지입니다.

## Parser 입력 표에는 어떤 줄을 넣나요?

`key=value`, `key=`, `=value`, `key`, 여러 등호, 앞뒤 공백과 inline comment를 각각 넣고 성공 여부와 key, val을 기록합니다. 최소 조건은 등호를 실제로 찾고 key와 value가 비어 있지 않은지 확인하는 것입니다. 허용할 문법을 정하지 않은 채 strip 결과만 믿으면 오타가 default 설정으로 조용히 넘어갑니다.

Duplicate key가 있으면 첫 항목을 반환하는지 마지막 값을 덮는지 현재 순회 순서를 확인하고 경고 정책을 둡니다. Case sensitivity와 공백 normalization도 실제 cfg와 일치시킵니다.

## 숫자 Conversion을 어떻게 안전하게 하나요?

`atoi`와 `atof`는 잘못된 문자열과 정상 0을 구분하기 어렵고 trailing text도 놓칠 수 있습니다. 변환 종료 pointer와 overflow를 확인하는 함수로 전체 문자열이 소비됐는지 검사하고, batch, width, probability처럼 옵션별 범위도 검증합니다. Default 사용과 명시적 0을 로그에서 구분합니다.

Used를 변환 성공 전에 표시하면 잘못된 값도 unused 진단에서 사라집니다. 조회, parse와 validation 상태를 분리하거나 오류를 즉시 반환합니다.

## Memory를 어떤 순서로 해제하나요?

Key는 allocation 시작, val은 같은 block 중간 pointer이므로 둘을 각각 free하지 않습니다. Kvp, 원본 line, node와 list 구조체 중 누가 무엇을 소유하는지 표로 정하고 한 번씩 해제합니다. Metadata처럼 value를 사용해 외부 data를 먼저 load한 뒤 option storage를 정리합니다.

Option pointer를 장기 보관해야 한다면 별도 문자열 copy를 만든다. List만 free했을 때 contents와 line이 남는지 또는 함께 사라지는지는 실제 free helper와 대조해 leak, dangling pointer를 sanitizer로 확인합니다.

## Duplicate와 Unknown Option을 어떻게 다루나요?

같은 key가 두 번 나오면 현재 front 순회에서 어느 값을 반환하는지 확인하고, 조용히 첫 값만 쓰는 대신 line 번호와 함께 중복을 보고합니다. Unknown option은 `option_unused`로 찾되 조회만 하고 실제 적용하지 않은 값도 used가 될 수 있다는 한계를 보완합니다. Parser가 지원하는 key 목록과 type, 범위를 section별로 검증하는 편이 명확합니다.

Deprecated key를 alias할 때는 두 이름이 동시에 있으면 우선순위를 정합니다. 오타를 default로 바꾸는 행동은 학습을 실행되게 만들지만 잘못된 설정을 숨기므로 required option과 optional default를 구분합니다.

## 문자열 안의 특수 문자는 어떻게 처리하나요?

현재 첫 등호에서 key와 val을 나누므로 value 안 추가 등호는 남을 수 있습니다. Inline `#`, `;`를 comment로 볼지 literal로 볼지, 따옴표와 escape를 지원하는지 문법을 명시합니다. Path에 공백이나 등호가 들어간 fixture로 실제 strip 결과를 확인합니다.

빈 line 검사 전에 line[0]을 읽는 흐름과 UTF-8 key 비교도 안전한지 봅니다. Config encoding과 newline을 고정해 플랫폼별 차이를 줄입니다.

## Metadata Pointer 수명을 어떻게 테스트하나요?

Option에서 받은 names path를 list free 전과 후에 읽는 최소 test를 만들고, get_labels가 내부에서 즉시 copy 또는 file load를 마치는지 확인합니다. Long-lived reference가 필요하면 value를 독립 copy해 option storage와 수명을 분리합니다.

Read/free를 반복해 원본 line, kvp, node와 list가 정확히 한 번씩 해제되는지 sanitizer로 봅니다. Parse 실패 line은 즉시 free되고 성공 line은 option owner가 정리하는 경로가 달라야 합니다.

## 자주 남는 질문

### 등호가 없는 설정 줄은 현재 read_option에서 거부되나요?

아닙니다. Loop가 len에서 끝나 조건을 통과해 val이 NULL인 항목이 삽입될 수 있습니다.

### option_insert는 key와 value 문자열을 복사하나요?

아닙니다. 원본 line buffer 안의 pointer를 저장하므로 그 buffer 수명이 option 사용보다 길어야 합니다.

### quiet 조회는 used 상태도 바꾸지 않나요?

아닙니다. 기본값 메시지만 생략하며 key가 있으면 일반 조회처럼 used를 1로 바꿉니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet option_list.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/option_list.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet layer 구조를 해제할 때 왜 터질까: LAYER\_TYPE과 free\_layer 소유권]({% post_url 2022-03-04-DarkNetLayer %}) — Darknet의 LAYER_TYPE enum이 실행 분기를 만드는 방식과 free_layer가 선택적 버퍼를 해제할 때 확인해야 할 메모리 소유권을 짚습니다.
- [Darknet network.c 학습, 예측 흐름: subdivisions 업데이트와 포인터 수명 함정]({% post_url 2022-03-10-DarkNetNetwork %}) — Darknet network가 layer forward, backward, update를 연결하는 방식과 learning-rate, batch 변경, 예측 출력, detection 메모리의 경계 조건을 추적합니다.
- [Darknet RNN의 State 포인터가 깨질 때: batch, steps 메모리 계약 읽기]({% post_url 2022-03-16-DarkNetRNNLayer %}) — Darknet rnn_layer가 세 connected layer를 시간축으로 이동시키는 구조와 batch를 steps로 나누는 이유, state 포인터, shortcut, 역방향 순회의 위험 조건을 코드로 점검합니다.
<!-- internal-links:end -->
