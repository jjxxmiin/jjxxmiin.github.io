---
layout: post
title: "인간 1인칭 영상이 로봇 학습에 바로 쓰이지 못하는 이유: PhysBrain E2E"
date: '2025-12-23'
categories: Tech
tags:
  - 로보틱스
  - 멀티모달
  - 트랜스포머
  - AI에이전트
  - 논문리뷰
math: true
summary: "PhysBrain이 인간 egocentric video를 perception·intention/action·state change가 연결된 E2E 데이터로 바꾸는 과정과, 사람 손에서 robot gripper로 옮길 때 남는 간극을 설명합니다."
image:
  path: https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2512.16793.png
  alt: Paper Thumbnail
---

인간의 1인칭 영상이 로봇 학습에 도움이 되려면 **그대로 넣는 것이 아니라, 무엇을 보고 왜 움직였으며 물체 상태가 어떻게 바뀌었는지를 근거와 함께 구조화해야 합니다.** PhysBrain은 값비싼 robot demonstration을 완전히 대체한다기보다, 방대한 human egocentric video를 물리적 추론 데이터로 바꾸는 다리입니다.

## 사람과 로봇은 비슷한 시점을 보지만 같은 몸을 갖지 않는다

인터넷의 일반 video는 camera 밖에서 행동을 찍은 third-person 시점이 많습니다. 로봇은 자기 camera에서 손이나 gripper와 대상 물체를 보므로 관찰 분포가 다릅니다. Ego4D와 EPIC-KITCHENS 같은 human egocentric data는 이 시점 차이를 줄이는 후보입니다.

그러나 사람 손의 자유도, 감각, 힘 조절은 robot gripper와 다릅니다. “컵을 집는다”는 의미는 공유할 수 있어도 관절 trajectory를 그대로 복사할 수는 없습니다. PhysBrain의 목표는 인간 동작을 곧바로 motor command로 변환하는 것이 아니라, VLM이 행동 전후의 물리적 관계와 다음 action을 더 잘 추론하도록 supervision을 만드는 데 있습니다.

## E2E pipeline은 영상에서 세 종류의 질문을 만든다

원문의 E2E pipeline은 raw video를 perception, intention/action, state change 축의 VQA로 바꿉니다.

- perception: 어떤 물체가 어디에 있고 서로 어떤 관계인가
- intention/action: 사용자가 무엇을 하려 하며 다음 행동은 무엇인가
- state change: 행동 뒤 대상의 위치·형태·상태가 어떻게 달라졌는가

답을 영상 근거에 연결하기 위해 bounding box, trajectory, temporal consistency가 함께 사용됩니다. 이 grounding이 없으면 그럴듯한 문장만 늘어나고 실제 frame에서 확인할 수 없는 supervision이 섞일 수 있습니다. 자동 생성 뒤에는 질문과 답이 같은 시간 구간을 가리키는지, 가려진 물체를 보았다고 쓰지 않았는지 검수해야 합니다.

이 과정으로 약 300만 개의 E2E data point가 구성됩니다. 수량 자체보다 세 축이 연결된다는 점이 중요합니다. 물체를 찾는 능력만 높여서는 “왜 그 물체를 잡아야 하는가”와 “잡은 뒤 무엇이 변하는가”를 학습하기 어렵기 때문입니다.

## 평가는 지식 문제와 행동 전이를 나눠 봐야 한다

원문은 EgoThink와 EgoVQA로 egocentric reasoning을, SimplerEnv로 robot policy 전이를 평가합니다. 이때 VQA 정답률 상승과 실제 manipulation 성공은 같은 지표가 아닙니다. 영상 설명을 잘하는 모델이 지연 없이 안전한 action을 낸다고 단정할 수 없습니다.

수치 표현에도 주의가 필요합니다. 원문 summary에는 SimplerEnv 성공률 53.9%라고 쓰였지만 본문에는 53.9% 높은 성공이라는 다른 표현이 섞여 있습니다. 분모와 비교 baseline이 다른 두 문장은 같은 뜻이 아니므로, 원 논문의 표를 확인하지 않은 채 확정 수치로 재인용하면 안 됩니다. 여기서는 “전이 개선이 보고됐다”는 범위까지만 결론으로 사용합니다.

## 실제 적용 전에는 세 개의 간극을 다시 측정한다

첫째는 morphology gap입니다. 손가락으로 가능한 접촉이 gripper에는 불가능할 수 있습니다. 둘째는 dynamics gap입니다. video에는 torque와 접촉력 같은 정보가 직접 보이지 않습니다. 셋째는 latency gap입니다. offline video reasoning과 real-time control은 요구 시간이 다릅니다.

따라서 human video로 pretraining한 뒤에는 실제 robot observation에서 object grounding을 재검증하고, action 표현을 로봇 형태에 맞게 연결하며, 폐루프에서 실패했을 때 멈추는 안전 조건을 넣어야 합니다. PhysBrain의 실용적 가치는 robot data를 없애는 데 있지 않습니다. **robot data가 맡아야 할 저수준 제어 전에, 인간 영상으로 일반적인 물체·행동·상태 변화 이해를 넓히는 것**이 더 정확한 해석입니다.

[Original Paper Link](https://huggingface.co/papers/2512.16793)
