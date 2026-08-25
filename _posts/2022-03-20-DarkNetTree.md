---
layout: post
title:  "Darknet 계층 분류 확률이 너무 작을 때: 부모 확률을 곱하는 Tree 구조"
summary: "Darknet tree가 sibling별 조건부 확률을 부모 경로와 곱해 최종 class 확률을 만드는 방식과 tree 파일의 노드 순서·group 구성·threshold 탐색 조건을 설명합니다."
date:   2022-03-20 16:00 -0400
categories: DarkNet
image:
  path: /assets/img/thumb/DarkNetTree.jpg
  alt: DarkNet 시리즈 - Tree 대표 이미지
tags:
  - DarkNet
  - YOLO
  - 컴퓨터비전
  - C언어
  - 아키텍처분석
math: true
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
