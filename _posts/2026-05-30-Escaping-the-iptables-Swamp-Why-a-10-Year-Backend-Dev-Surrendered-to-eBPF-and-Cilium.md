---
layout: post
title: 'iptables에서 Cilium으로 어떻게 옮길까: 단계별 마이그레이션과 복귀 기준'
date: '2026-05-30 07:03:10'
categories: Tech
tags:
  - 인프라
  - 오픈소스
  - 튜토리얼
summary: '쿠버네티스 kube-proxy, iptables 환경을 Cilium eBPF 데이터 플레인으로 옮길 때 필요한 현황 조사, 정책 동등성, 노드 풀 canary와 롤백 기준을 정리합니다.'
description: 'iptables 기반 쿠버네티스를 Cilium으로 옮기기 전 기준선을 만들고, 정책 번역, 노드 풀 canary, 혼합 경로, 장애 복귀를 검증하는 단계별 마이그레이션 안내입니다.'
github_url: https://github.com/cilium/cilium
faq:
  - question: 'Cilium을 설치하면 kube-proxy를 바로 제거해도 되나요?'
    answer: '권장하지 않습니다. 현재 CNI, 서비스 경로와 정책 기능을 조사하고 별도 테스트 또는 canary 노드 풀에서 동등성을 검증한 뒤 명시한 절차로 전환해야 합니다.'
  - question: '마이그레이션 중 iptables와 eBPF 노드를 함께 운영할 수 있나요?'
    answer: '구성과 버전이 지원하는 범위에서 단계적 전환을 설계할 수 있지만, 노드 간 경로, 정책, 서비스 동작을 별도로 시험해야 합니다. 혼합 상태를 무기한 운영하면 디버깅이 어려워집니다.'
  - question: '어떤 상황에서 기존 데이터 플레인으로 복귀해야 하나요?'
    answer: '정책 우회, 대량 연결 실패, DNS 또는 서비스 도달성 회귀, 관측 불가능한 drop이 합의한 임계값을 넘으면 확장을 멈추고 검증된 이전 이미지와 설정으로 복귀해야 합니다.'
image:
  path: https://opengraph.githubassets.com/1/cilium/cilium
  alt: "cilium/cilium GitHub 저장소 대표 이미지"
---

iptables에서 Cilium으로의 전환은 CNI 패키지 하나를 교체하는 작업이 아니라 클러스터 데이터 플레인을 바꾸는 마이그레이션입니다. 현재 traffic과 정책의 기준선을 만들고, 대표 노드 풀에서 동등성과 복귀를 검증한 뒤 범위를 넓혀야 합니다. 성능 기대만으로 kube-proxy를 먼저 제거하면 장애 때 비교할 정상 경로도 함께 잃습니다.

이 글은 [eBPF](https://ebpf.io/), [Cilium의 kube-proxy 대체 설명](https://cilium.io/use-cases/kube-proxy/)과 [Cilium 저장소](https://github.com/cilium/cilium)를 참고해 전환 순서를 설명합니다. 설치 명령과 호환 조건은 배포판, 커널, Cilium 버전에 따라 달라지므로 해당 버전의 공식 절차를 기준으로 실행해야 합니다.

## 먼저 iptables가 실제 병목인지 어떻게 확인할까?

전환 전 일주일 이상 서비스, endpoint 수, 노드별 rule 규모와 동기화 시간, network CPU, conntrack 사용량, DNS, Service 오류, p50, p95, p99 지연을 기록합니다. HPA나 rollout 때 endpoint가 급변하는 구간을 따로 표시하면 애플리케이션 부하와 network rule 갱신을 구분하기 쉽습니다. 단순히 rule 줄이 많다는 사실만으로 사용자 지연의 원인이라고 확정하지 않습니다.

현재 kube-proxy mode, CNI, network policy 구현, MTU, IPAM, node-local DNS, ingress, egress, LoadBalancer와 hostNetwork 사용을 inventory로 만듭니다. NetworkPolicy 외에 운영 스크립트가 직접 만든 iptables rule, 보안 agent와 cloud firewall이 있는지도 확인하세요. 데이터 플레인을 바꾸면 이런 숨은 의존성이 먼저 깨질 수 있습니다.

성공 기준은 ‘Cilium 설치됨’이 아니라 기존 기능을 유지하면서 합의한 병목이 개선되는 것입니다. 예를 들어 endpoint 갱신 p95, 신규 pod의 첫 Service 연결 성공 시간, network CPU와 tail latency를 기준선으로 정합니다. 개선 목표가 없으면 마이그레이션 복잡성만 남을 수 있습니다.

## 정책과 서비스 동작을 어떻게 번역할까?

모든 namespace의 NetworkPolicy, 기본 허용, 거부 상태와 selector를 수집하고 실제 허용 traffic으로 테스트 fixture를 만듭니다. 문법이 변환됐다고 의미가 같다고 보지 말고 ingress, egress, DNS, host traffic, node-to-pod와 external service를 각각 확인합니다. 정책이 없는 namespace의 기본 동작도 명시해야 합니다.

Service 유형별로 ClusterIP, headless, NodePort, LoadBalancer와 externalTrafficPolicy를 시험합니다. session affinity, source IP 보존, health check와 IPv4, IPv6 사용 여부도 현재 동작을 기록하세요. 이름이 같은 기능도 packet 경로와 실패 상황에서 동작이 달라질 수 있습니다.

기존 메시나 ingress가 iptables redirect에 의존한다면 별도 목록으로 둡니다. Cilium의 eBPF 경로를 켰을 때 sidecar interception, transparent proxy와 L7 정책이 어떻게 연결되는지 작은 서비스에서 확인합니다. 데이터 플레인과 서비스 메시를 동시에 바꾸면 어느 변경이 회귀를 만들었는지 찾기 어렵기 때문에 가능하면 단계와 rollback을 분리합니다.

## SockOps 의사코드는 무엇을 설명하고 무엇을 생략하는가?

원문의 다음 코드는 socket Map을 조회해 redirect하는 개념을 단순화한 조각입니다. Map 생성, 수명주기, key 추출, 연결 상태, 오류와 커널 기능 검사가 빠져 있어 그대로 동작하는 Cilium 구성은 아닙니다.

```c
// eBPF SockOps 의사코드 (Cilium 내부 동작 원리 단순화)
SEC("sk_msg")
int bpf_tcp_forward(struct sk_msg_md *msg) {
    struct sock_key key = {};
    extract_socket_info(msg, &key);

    // eBPF Map에서 목적지 소켓 후보 조회
    if (bpf_map_lookup_elem(&socket_map, &key)) {
        return bpf_msg_redirect_hash(msg, &socket_map, &key, BPF_F_INGRESS);
    }
    return SK_PASS;
}
```

이 예시는 일부 같은 노드 socket 경로를 줄일 수 있는 원리를 보여 줄 뿐 모든 packet이 TCP/IP stack과 veth를 건너뛴다는 보장은 아닙니다. protocol, 위치와 configuration에 따라 실제 hook과 경로가 달라집니다. 마이그레이션은 의사코드의 O(1) 설명이 아니라 사용 중인 kernel과 Cilium datapath의 관측 결과로 판단해야 합니다.

BPF Map lookup도 상태가 정확히 갱신돼야 의미가 있습니다. control plane과 node agent가 단절되거나 오래된 endpoint가 남으면 빠른 lookup이 잘못된 대상으로 이어질 수 있습니다. Map pressure, sync error와 stale entry를 관측 항목에 포함합니다.

## canary 노드 풀은 어떤 순서로 넓혀야 하는가?

운영과 같은 kernel, NIC, cloud route를 쓰는 별도 테스트 클러스터에서 기능 시험을 먼저 합니다. 다음으로 stateless, 저위험 workload가 있는 작은 node pool을 canary로 정하고, 명시한 label과 scheduling 규칙으로 대상 pod만 이동합니다. 한 번에 CNI, kernel, ingress와 mesh를 모두 업그레이드하지 말고 data plane 변경만 관찰할 수 있게 합니다.

canary에는 내부, 외부 client, DNS, long-lived TCP, short HTTP, UDP, health check와 pod churn 부하를 보냅니다. node reboot, drain, agent restart, control plane 지연과 policy update 중에도 연결이 회복되는지 봅니다. 정상 traffic 평균만 확인하면 마이그레이션 순간의 connection reset과 신규 endpoint 반영 오류를 놓칩니다.

확대 단계마다 중단 시간을 둡니다. 예를 들어 5%, 20%, 50%의 node에서 동일한 지표와 오류를 한 운영 주기씩 관찰하고, 다음 단계 전 on-call과 application owner가 결과를 승인합니다. 오래 유지되는 혼합 환경은 packet이 어느 data plane을 거쳤는지 추적하기 어려우므로 canary 종료 조건과 전체 전환 또는 복귀 날짜를 미리 정합니다.

## 복귀 가능한 상태를 어떻게 보존할까?

이전 node image, kube-proxy, CNI manifest, routing, MTU와 policy snapshot을 버전으로 보관합니다. 복귀 절차는 ‘Cilium 삭제’ 한 줄이 아니라 신규 scheduling 중지, connection drain, 이전 node pool 확장, workload 이동, Service, DNS 검증과 새 component 제거 순서를 포함해야 합니다. 실행에 필요한 권한과 소요 시간도 rehearsal에서 확인합니다.

stateful connection은 단순 rollback 뒤에도 끊길 수 있습니다. connection drain 시간을 둘 수 없는 workload와 고정 source IP, external load balancer health check를 별도로 다룹니다. rollback 중 양쪽 data plane이 같은 IP, route를 주장하지 않게 소유권 전환 지점을 명시합니다.

정책 우회나 격리 실패는 지연 회귀보다 더 엄격한 중단 조건이어야 합니다. 허용하면 안 되는 traffic이 한 번이라도 통과하면 확장을 중단하고 원인을 확인합니다. 반대로 관측 도구에서 drop이 보이지 않는다는 이유만으로 packet loss가 없다고 판단하지 말고 client, server 양끝의 성공률과 외부 synthetic probe를 사용합니다.

## 마이그레이션 완료는 무엇으로 증명할까?

전체 전환 뒤에도 기준선과 같은 dashboard를 최소 한 운영 주기 유지합니다. endpoint churn, node upgrade와 peak traffic에서 network CPU, tail latency, DNS, Service 오류, Map pressure와 policy verdict를 비교합니다. application owner가 실제 업무 흐름을 통과시키고 on-call이 Hubble, Cilium 상태에서 drop 이유와 경로를 설명할 수 있어야 합니다.

직접 만든 iptables rule과 임시 호환 설정을 목록에서 제거하고, 더 이상 쓰지 않는 kube-proxy 자원, 모니터링, runbook을 정리합니다. 다만 rollback 보관 기간 동안 이전 artifact와 절차는 유지합니다. 비용 절감에는 새 agent, 관측 storage, 교육과 운영 시간도 포함해 전환 전 목표와 비교하세요.

마지막으로 버전 upgrade를 작은 node pool에서 다시 시험하는 반복 절차를 만듭니다. 최초 마이그레이션에 성공했어도 kernel, Cilium, cloud network 변경이 datapath를 바꿀 수 있습니다. 완료의 의미는 새 data plane을 한 번 띄운 것이 아니라 안전하게 upgrade, 복귀할 수 있는 운영 체계를 갖춘 것입니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/cilium/cilium)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목, Hubble, L7 경계]({% post_url 2026-05-25-The-End-of-the-Sidecar-Era-How-eBPF-is-Rewiring-Kubernetes-Networking-from-the-Kernel-Up %}) — Kubernetes 서비스, 정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map, 소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
- [eBPF, Cilium 서비스 메시를 어떻게 운영할까: 관측, 업그레이드, 롤백]({% post_url 2026-05-31-eBPF-and-Cilium-Is-Sidecar-less-Service-Mesh-a-Salvation-or-Another-Disaster %}) — eBPF, Cilium 데이터 플레인을 운영할 때 필요한 flow, drop, BPF Map 관측, 정책 배포, agent, proxy 장애 격리, 업그레이드 canary와 롤백 절차를 정리합니다.
- [Istio 사이드카를 없애도 될까: eBPF 서비스 메시와 L7 하이브리드 조건]({% post_url 2026-05-26-Time-to-Ditch-the-Sidecar-How-eBPF-is-Disrupting-Service-Mesh %}) — 파드별 Istio, Envoy 비용을 eBPF와 노드 단위 프록시로 줄일 수 있는 조건을 살펴보고, mTLS, 재시도, HTTP 라우팅 때문에 남는 L7 기능과 안전한 전환 기준을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Cilium을 설치하면 kube-proxy를 바로 제거해도 되나요?

권장하지 않습니다. 현재 CNI, 서비스 경로와 정책 기능을 조사하고 별도 테스트 또는 canary 노드 풀에서 동등성을 검증한 뒤 명시한 절차로 전환해야 합니다.

### 마이그레이션 중 iptables와 eBPF 노드를 함께 운영할 수 있나요?

구성과 버전이 지원하는 범위에서 단계적 전환을 설계할 수 있지만, 노드 간 경로, 정책, 서비스 동작을 별도로 시험해야 합니다. 혼합 상태를 무기한 운영하면 디버깅이 어려워집니다.

### 어떤 상황에서 기존 데이터 플레인으로 복귀해야 하나요?

정책 우회, 대량 연결 실패, DNS 또는 서비스 도달성 회귀, 관측 불가능한 drop이 합의한 임계값을 넘으면 확장을 멈추고 검증된 이전 이미지와 설정으로 복귀해야 합니다.

## References

- [ebpf.io 원문](https://ebpf.io/)
- [cilium.io 원문](https://cilium.io/use-cases/kube-proxy/)
- [GitHub 저장소](https://github.com/cilium/cilium)
