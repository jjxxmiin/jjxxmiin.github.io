---
source_citations:
  - name: "Darknet tree.c 고정 커밋 원본"
    url: "https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/tree.c"
layout: post
title:  "Darknet 계층 분류 확률이 너무 작을 때: 부모 확률을 곱하는 Tree 구조"
summary: "Darknet tree가 sibling별 조건부 확률을 부모 경로와 곱해 최종 class 확률을 만드는 방식과 tree 파일의 노드 순서·group 구성·threshold 탐색 조건을 설명합니다."
description: "Darknet tree의 sibling conditional probability와 root-path 곱, file node order·group·leaf와 threshold traversal·in-place 변환을 설명합니다."
date:   2022-03-20 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetTree.jpg
  alt: DarkNet 시리즈 - Tree 대표 이미지
tags:
  - DarkNet
  - 컴퓨터비전
math: true
faq:
  - question: "깊은 class의 최종 확률이 작은 것이 항상 문제인가요?"
    answer: "아닙니다. Root부터 해당 node까지 여러 조건부 확률을 곱하므로 깊을수록 값이 작아질 수 있습니다."
  - question: "Tree 파일에서 sibling을 떨어뜨려 적어도 되나요?"
    answer: "안 됩니다. 같은 parent의 node가 연속한다는 전제로 parent 값 변화마다 softmax group을 만듭니다."
  - question: "hierarchy_predictions를 같은 배열에 두 번 호출해도 되나요?"
    answer: "In-place로 부모 확률을 곱하므로 반복 호출하면 이미 변환된 값에 다시 곱할 수 있습니다."
---

Darknet 계층 class의 최종 확률은 해당 node 값 하나가 아니라 root부터 그 node까지의 조건부 확률을 모두 곱한 값이므로, 계층이 깊을수록 숫자가 작아지는 것이 자연스럽습니다.

`tree.c`는 flat class 목록을 부모·자식 group으로 묶고, sibling softmax 결과를 전체 계층 확률로 바꾸는 후처리를 담당합니다. 아래 코드는 Darknet의 list·파일 helper와 `tree` 구조체를 전제로 하므로 독립 실행 예제가 아닙니다.

## 최종 확률은 Root까지의 곱입니다

`get_hierarchy_probability`는 class `c`에서 시작해 `parent[c]`를 계속 따라가며 값을 곱합니다.

```c
float p = 1;
while(c >= 0){
    p = p * x[c*stride];
    c = hier->parent[c];
}
return p;
```

자식 값이 0.8이라도 부모 경로가 0.5와 0.6이면 최종 확률은 0.24입니다. Flat softmax의 0.8과 직접 비교하면 confidence가 비정상적으로 낮다고 오해할 수 있습니다. `stride`가 1이 아닐 때는 각 node 값이 연속해 있지 않으므로 배열 layout도 함께 확인해야 합니다.

`hierarchy_predictions`는 같은 계산을 전체 node에 in-place로 적용합니다. 부모 index의 값이 먼저 전체 확률로 바뀌어 있어야 자식이 올바른 경로 곱을 얻으므로, 파일의 node가 부모부터 자식 순으로 배치됐다는 전제가 중요합니다.

## Softmax Group은 같은 Parent를 공유하는 Node 묶음입니다

`read_tree`는 각 줄에서 node 이름과 parent index를 읽습니다. Parent 값이 이전 줄과 달라질 때 새 group을 시작하고 `group_offset`과 `group_size`를 기록합니다. 즉 같은 parent의 자식들이 파일 안에서 연속해 있다는 전제를 코드가 직접 사용합니다.

```c
if(parent != last_parent){
    ++groups;
    t.group_offset = realloc(t.group_offset, groups * sizeof(int));
    t.group_offset[groups - 1] = n - group_size;
    t.group_size = realloc(t.group_size, groups * sizeof(int));
    t.group_size[groups - 1] = group_size;
    group_size = 0;
    last_parent = parent;
}
```

같은 parent를 가진 node를 떨어진 위치에 다시 적으면 별도 group처럼 나뉠 수 있습니다. 파일을 만들 때 parent가 자식보다 먼저 나오고, sibling은 한 구간에 모이는지 검사해야 합니다. 단순히 parent index가 유효하다는 것만으로 충분하지 않습니다.

읽기가 끝나면 모든 node를 leaf로 시작한 뒤 parent로 등장한 node의 leaf 표시를 0으로 바꿉니다. `change_leaves`는 별도 이름 목록으로 이 표시를 다시 지정하며, 찾은 개수만 출력합니다. 목록의 오타가 있어도 전체 일치 여부를 강제하지 않습니다.

## only_leaves는 내부 Node를 0으로 만듭니다

`hierarchy_predictions`의 `only_leaves`가 참이면 부모 확률을 곱한 뒤 leaf가 아닌 node를 0으로 만듭니다. 이는 내부 category를 최종 detection label로 내보내지 않으려는 선택입니다.

이 변환은 predictions 배열 자체를 수정합니다. 같은 배열로 원래 sibling 조건부 확률과 최종 leaf 확률을 모두 분석하려면 변환 전에 복사본을 남겨야 합니다. 함수를 두 번 호출하면 부모 확률이 반복해서 곱해질 수 있으므로 한 번만 적용하는 호출 계약도 필요합니다.

## Threshold 탐색은 가장 깊은 Node를 항상 고르지 않습니다

`hierarchy_top_prediction`은 현재 group에서 가장 큰 자식을 고르고 누적 확률 `p*max`가 threshold보다 클 때만 그 자식 group으로 내려갑니다. Threshold를 넘지 못하면 root에서는 현재 최대 node를, 더 깊은 곳에서는 현재 group의 parent를 반환합니다.

따라서 threshold가 높으면 더 일반적인 상위 category에서 탐색이 멈추고, 낮으면 leaf까지 내려갈 가능성이 커집니다. 디버깅할 때는 반환 index만 보지 말고 각 단계의 group, local max, 누적 `p`를 기록해야 합니다.

최소 검증 fixture는 root 두 개, 한 root의 자식 두 개처럼 작게 만듭니다. Parent-before-child와 sibling-contiguous 순서를 지키고 손으로 경로 곱을 계산한 뒤, only_leaves와 서로 다른 threshold 결과를 비교하면 tree 파일과 확률 처리 오류를 분리할 수 있습니다.

## Tree 파일을 어떤 규칙으로 검증하나요?

각 parent index가 -1 또는 이전 node 범위인지 확인해 cycle과 미래 parent를 막습니다. 같은 parent sibling이 한 구간에 모였는지, group offset·size가 모든 node를 정확히 덮는지 봅니다. 이름 중복, 빈 이름과 leaf override 목록의 미일치도 오류 또는 명확한 경고로 처리합니다.

## Threshold 선택을 어떻게 설명하나요?

각 단계에서 local max, 누적 path probability와 threshold를 기록합니다. Threshold가 높을수록 상위 category에서 멈추는지, 낮출 때 예상 child로 내려가는지 fixture로 확인합니다. 서로 다른 깊이 node의 raw conditional 값만 비교하지 않습니다.

## In-place 변환은 어떻게 안전하게 쓰나요?

Sibling conditional과 최종 hierarchy probability가 모두 필요하면 원본을 복사한 뒤 한 copy에만 변환합니다. Only-leaves 역시 내부 node를 0으로 만들므로 후속 분석 순서를 고정합니다. Batch와 stride가 1이 아닌 배열에서 node index가 올바른 sample을 가리키는지 확인합니다.

## Cycle과 잘못된 Parent를 어떻게 찾나요?

각 node에서 parent를 따라가며 방문 set을 두고 root -1에 도달하는지 검사합니다. 자신을 parent로 두거나 이미 방문한 node로 돌아가면 확률 함수가 끝나지 않습니다. Parent가 node 수 범위 안이라는 검사뿐 아니라 parent-before-child 조건도 확인합니다.

Root가 여러 개인 forest는 허용할 수 있지만 각 root group과 top prediction 시작 규칙을 명시합니다. 연결되지 않은 node와 group에 포함되지 않은 node를 보고합니다.

## Deep Path의 수치와 Threshold를 어떻게 다루나요?

많은 확률을 곱하면 float에서 매우 작아질 수 있습니다. Ranking 목적에는 log probability 합을 고려할 수 있지만 기존 API의 실제 값과 동일한지 검증합니다. Threshold도 raw sibling 값이 아니라 누적 path 값에 적용되는 지점을 명확히 합니다.

## Leaf 목록 변경은 무엇을 검증하나요?

변경 파일의 모든 이름이 tree node와 일치하는지 개수뿐 아니라 누락 목록을 출력합니다. Internal node를 leaf로 표시하거나 모든 leaf가 사라지는 설정이 downstream detection에 미치는 영향을 봅니다. Change 후 parent·group 구조 자체는 바뀌지 않습니다.

## In-place 호출을 API에서 어떻게 표시하나요?

함수 이름과 signature만으로 prediction을 수정하는지 알기 어려우므로 mutable pointer 계약을 문서화하거나 별도 output을 받게 합니다. 변환 전후 buffer를 checksum으로 비교하고 한 pipeline에서 정확히 한 번 호출하도록 state를 관리합니다.

## Class Map과 Tree 순서를 어떻게 맞추나요?

Dataset class id, network output node index와 tree file line 번호의 mapping을 한 표로 유지합니다. 이름이 같아도 순서가 바뀌면 확률과 label이 다른 node에 연결됩니다. Checkpoint와 tree file hash를 함께 저장하고 평가 전에 known node 몇 개의 parent path를 확인합니다.

## 자주 남는 질문

### 깊은 class의 최종 확률이 작은 것이 항상 문제인가요?

아닙니다. Root부터 해당 node까지 여러 조건부 확률을 곱하므로 깊을수록 값이 작아질 수 있습니다.

### Tree 파일에서 sibling을 떨어뜨려 적어도 되나요?

안 됩니다. 같은 parent의 node가 연속한다는 전제로 parent 값 변화마다 softmax group을 만듭니다.

### hierarchy_predictions를 같은 배열에 두 번 호출해도 되나요?

In-place로 부모 확률을 곱하므로 반복 호출하면 이미 변환된 값에 다시 곱할 수 있습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [Darknet tree.c 고정 커밋 원본](https://raw.githubusercontent.com/pjreddie/darknet/f6afaabcdf85f77e7aff2ec55c020c0e297c77f9/src/tree.c)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Darknet Softmax 확률 합이 1이 아닐 때: groups와 softmax\_tree 확인법]({% post_url 2022-03-19-DarkNetSoftmaxLayer %}) — Darknet softmax_layer가 전체 입력이 아니라 group 또는 tree의 sibling 묶음마다 확률을 정규화하는 방식과 temperature, cross-entropy delta, backward 누적을 설명합니다.
- [DarkNet Compare는 두 이미지를 어떻게 순위로 바꾸나]({% post_url 2022-02-11-DarkNetCompare %}) — DarkNet compare 코드의 쌍 비교 학습, 10분할 검증, qsort 정렬과 Elo 토너먼트 흐름을 실행 전 주의점과 함께 정리합니다.
- [Darknet cfg 파서가 네트워크를 망가뜨리는 순간: route 인덱스·STEPS·가중치 순서]({% post_url 2022-03-13-DarkNetParser %}) — Darknet parser.c가 cfg 섹션을 레이어로 연결하는 흐름과 크기 전파, 쉼표 목록·route 인덱스의 경계 오류, 가중치 바이너리 순서를 코드로 점검합니다.
<!-- internal-links:end -->
