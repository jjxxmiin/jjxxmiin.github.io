---
layout: post
title: 'Cilium은 iptables보다 얼마나 빠를까: 재현 가능한 네트워크 성능 검증법'
date: '2026-05-30 18:53:55'
categories: Tech
tags:
  - 인프라
  - 웹개발
  - AI에이전트
summary: 'iptables, IPVS, Cilium eBPF를 같은 클러스터 조건에서 비교하기 위해 서비스 수, endpoint churn, 연결 유형과 정책을 고정하고 지연, CPU, drop을 측정하는 법입니다.'
description: 'Cilium과 iptables 성능을 동일한 커널, 노드, 정책에서 비교하고, endpoint 갱신, 짧은 연결, tail latency, CPU, Map pressure와 기능 동등성을 검증합니다.'
github_url: https://github.com/AIDC-AI/Pixelle-Video
faq:
  - question: 'eBPF Map은 O(1)이니 Cilium이 항상 더 빠른가요?'
    answer: '아닙니다. 실제 지연에는 연결 설정, 정책, 암호화, 프록시와 하드웨어가 함께 작용합니다. 동일 조건의 종단 부하 시험으로 p99와 자원 사용을 비교해야 합니다.'
  - question: '네트워크 벤치마크에서 평균 지연만 보면 되나요?'
    answer: 'endpoint 갱신과 scale-out 때의 p95, p99, 연결 실패, CPU, conntrack, BPF Map pressure와 정책 반영 시간을 함께 봐야 운영 효과를 판단할 수 있습니다.'
  - question: 'XDP drop 예제 성능을 서비스 메시 전체 성능으로 봐도 되나요?'
    answer: '안 됩니다. XDP의 단순 drop과 Kubernetes Service, L7 정책, mTLS 경로는 다른 작업입니다. 사용 기능과 실제 packet path를 분리해 측정해야 합니다.'
image:
  path: https://opengraph.githubassets.com/1/AIDC-AI/Pixelle-Video
  alt: "AIDC-AI/Pixelle-Video GitHub 저장소 대표 이미지"
---

Cilium이 iptables보다 빠른지는 ‘eBPF Map은 O(1)’이라는 설명만으로 결정할 수 없습니다. 서비스 수, endpoint 변경, 연결 길이, 정책, 암호화와 실제 packet path를 고정한 뒤 tail latency와 전체 자원을 비교해야 합니다. 기능이 다르거나 하드웨어가 다른 공개 수치를 그대로 가져오면 제품 선택에 쓸 수 없는 벤치마크가 됩니다.

이 글은 [eBPF](https://ebpf.io/), [Cilium 저장소](https://github.com/cilium/cilium)와 원문에 연결된 [SIGCOMM 논문](https://dl.acm.org/doi/10.1145/3387514.3406591)을 출발점으로 재현 절차를 정리합니다. 문헌의 결과는 해당 구현, 커널, 장비 조건에 한정해 읽고, 운영 후보 버전은 자체 환경에서 다시 시험해야 합니다.

## 비교 전에 어떤 변수를 반드시 고정해야 하는가?

같은 node image, kernel, CPU pinning, NIC, MTU, Kubernetes 버전과 workload 이미지를 사용합니다. kube-proxy iptables, IPVS와 Cilium 후보를 비교한다면 한 번에 data plane 하나만 바꾸고 ingress, service mesh, autoscaling과 logging 설정은 동일하게 유지합니다. cloud instance의 noisy neighbor 영향을 줄이려면 여러 번 반복하고 실행 순서를 바꿉니다.

Service와 endpoint 규모를 실제 분포에서 가져옵니다. 서비스 10개, pod 20개의 lab에서 얻은 결과는 수천 endpoint가 갱신되는 운영 병목을 보여 주지 못합니다. 반대로 비현실적인 10만 service 하나만 측정하면 평소 traffic의 비용을 놓칩니다. 정상 규모, 현재 peak와 성장 가정 세 구간을 나누세요.

기능 조건도 같아야 합니다. 한 후보에는 NetworkPolicy와 mTLS를 켜고 다른 후보에는 단순 L4 전달만 켜면 latency 차이가 data plane 때문인지 기능 때문인지 알 수 없습니다. 먼저 최소 Service 전달, 다음 L3/L4 정책, 마지막 실제 L7, 암호화 stack을 단계별로 추가해 비용의 위치를 분리합니다.

## 어떤 traffic profile을 만들어야 운영 차이가 보일까?

짧은 HTTP 요청은 connection setup과 load balancing 경로의 영향을 크게 받고, 오래 유지되는 gRPC, TCP는 steady-state 처리량과 연결 안정성을 보여 줍니다. UDP, DNS, node-local 통신, cross-node, external ingress, egress를 따로 측정합니다. request body와 response 크기도 고정해 network보다 애플리케이션 serialization이 병목이 되지 않게 합니다.

정상 부하 외에 endpoint churn을 넣습니다. 일정한 요청을 보내며 deployment rollout, HPA scale-out, in, node drain을 실행하고 신규 endpoint가 첫 요청을 받기까지의 시간, connection reset, 503, timeout과 policy 반영 지연을 기록합니다. iptables rule 또는 BPF Map이 안정된 뒤만 재는 benchmark는 control-plane update 비용을 숨깁니다.

동시 연결과 packet rate를 별도로 올립니다. 초당 요청 수가 같아도 keep-alive 1,000개와 매번 새 연결 1,000개는 kernel 부담이 다릅니다. 목표 처리량을 유지하며 p50, p95, p99, max, error와 retry를 기록하고 포화점 이후 latency curve를 그립니다. 한 점의 ‘몇 배 빠름’보다 용량 한계와 붕괴 방식이 운영에 더 유용합니다.

## XDP 코드는 무엇을 측정하는 예제인가?

원문의 다음 코드는 IPv4 source를 확인해 특정 주소를 XDP에서 drop하는 단순화된 예제입니다. 실제 차단 목록은 Map, parser와 운영 update가 필요하며, 이 결과를 Kubernetes Service 성능으로 확대할 수 없습니다.

```c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>

SEC("xdp")
int xdp_fast_drop(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if (data + sizeof(*eth) > data_end)
        return XDP_PASS;

    if (eth->h_proto != __constant_htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *iph = data + sizeof(*eth);
    if (data + sizeof(*eth) + sizeof(*iph) > data_end)
        return XDP_PASS;

    if (iph->saddr == __constant_htonl(0xC0A80164))
        return XDP_DROP;

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
```

XDP 실험에서는 packets per second, drop 정확도, CPU와 NIC driver mode를 기록합니다. generic, native, offload 등 실제 attachment mode가 다르면 결과가 달라질 수 있습니다. 테스트 packet이 다른 traffic을 실수로 drop하지 않는지 IPv6, fragment와 malformed input도 확인합니다.

Service benchmark에서는 요청이 XDP, tc, socket 또는 proxy 중 어느 경로를 지났는지 관측합니다. 단순 packet filter 결과와 socket-level acceleration, L7 proxy 비용을 별도 표로 두면 한 기능의 장점을 전체 stack의 성능이라고 오해하지 않습니다.

## 정책 성능과 정책 정확도를 어떻게 함께 잴까?

NetworkPolicy가 많을 때 throughput만 재면 빠르게 잘못 허용하는 구현도 높은 점수를 받을 수 있습니다. 허용, 거부 pair와 정책 update를 fixture로 만들고 모든 benchmark run에서 예상 verdict를 검사합니다. identity 변경, label churn, namespace 기본 거부와 DNS egress도 포함하세요.

원문에 포함된 Kafka 정책 예시는 특정 endpoint에서 topic produce를 제한하는 의도를 보여 줍니다. 실제 API와 지원 범위는 배포 버전 문서를 확인해야 하며, YAML이 적용됐다는 사실만으로 암호화, protocol variant까지 검사됐다고 가정하면 안 됩니다.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "lock-down-kafka"
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: order-service
    rules:
      kafka:
      - role: "produce"
        topic: "order-events"
```

정책을 10개, 100개, 실제 peak로 늘리며 update latency, agent CPU, proxy 사용과 data plane 지연을 측정합니다. 정책 삭제 뒤 stale 상태가 남지 않는지, control plane 단절 때 마지막 정책이 어떻게 유지되는지도 정확성 시험입니다.

## CPU와 메모리는 어디에서 합산해야 하는가?

애플리케이션 pod만 보면 sidecar 제거의 이득은 보이지만 node agent와 L7 proxy, Hubble, flow storage 비용이 빠질 수 있습니다. pod proxy, kube-proxy 또는 Cilium agent, kernel softirq, control plane과 observability backend를 동일 범위로 합산합니다. idle, steady traffic와 churn 세 상태의 CPU, RSS를 각각 봅니다.

BPF Map의 entry 수, pressure, allocation 실패, conntrack과 packet drop reason을 함께 수집합니다. 평균 CPU가 낮아도 Map limit에 닿을 때 신규 연결이 실패하면 용량 계획이 잘못된 것입니다. Hubble flow를 많이 저장하면 관측 비용이 data plane 절감보다 커질 수 있으므로 sampling, 보존 기간도 같은 조건으로 비교합니다.

비용은 시간당 instance 가격뿐 아니라 필요한 node 여유, 관측 storage, 교육과 장애 대응 시간을 포함합니다. 공개된 ‘CPU 70% 절감’ 같은 숫자는 출처, 조건을 재현하지 못하면 의사결정 표에서 제외하세요.

## 벤치마크 결과로 어떤 결정을 내려야 하는가?

도입 전 합격선을 씁니다. 예를 들어 정책 동등성 100%, error budget 이내, endpoint churn p99 개선, node CPU, 메모리 목표와 on-call 진단 시간 상한입니다. 모든 지표가 좋아야 하는 것은 아니지만 보안 기능 저하를 작은 지연 개선과 같은 가중치로 평균 내지 않습니다.

각 결과에는 commit, image, kernel, 설정, workload generator와 raw data를 보관해 재현 가능하게 합니다. 평균 그래프만 남기지 말고 실패 run과 환경 편차도 공개하세요. 버전 upgrade 때 같은 suite를 돌리면 ‘eBPF가 원래 빠르다’는 믿음 대신 실제 회귀를 발견할 수 있습니다.

결과가 현재 규모에서 차이가 작다면 전환을 미룰 수 있습니다. Cilium의 관측, 정책 기능이 별도 가치를 주는지 분리해 판단하고, 단지 benchmark 1위를 위해 data plane을 바꾸지 마세요. 반대로 peak와 churn에서 명확한 개선이 있고 기능, 운영 시험도 통과하면 작은 canary부터 적용할 근거가 생깁니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/AIDC-AI/Pixelle-Video)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목, Hubble, L7 경계]({% post_url 2026-05-25-The-End-of-the-Sidecar-Era-How-eBPF-is-Rewiring-Kubernetes-Networking-from-the-Kernel-Up %}) — Kubernetes 서비스, 정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map, 소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
- [eBPF, Cilium 서비스 메시를 어떻게 운영할까: 관측, 업그레이드, 롤백]({% post_url 2026-05-31-eBPF-and-Cilium-Is-Sidecar-less-Service-Mesh-a-Salvation-or-Another-Disaster %}) — eBPF, Cilium 데이터 플레인을 운영할 때 필요한 flow, drop, BPF Map 관측, 정책 배포, agent, proxy 장애 격리, 업그레이드 canary와 롤백 절차를 정리합니다.
- [iptables에서 Cilium으로 어떻게 옮길까: 단계별 마이그레이션과 복귀 기준]({% post_url 2026-05-30-Escaping-the-iptables-Swamp-Why-a-10-Year-Backend-Dev-Surrendered-to-eBPF-and-Cilium %}) — 쿠버네티스 kube-proxy, iptables 환경을 Cilium eBPF 데이터 플레인으로 옮길 때 필요한 현황 조사, 정책 동등성, 노드 풀 canary와 롤백 기준을 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### eBPF Map은 O(1)이니 Cilium이 항상 더 빠른가요?

아닙니다. 실제 지연에는 연결 설정, 정책, 암호화, 프록시와 하드웨어가 함께 작용합니다. 동일 조건의 종단 부하 시험으로 p99와 자원 사용을 비교해야 합니다.

### 네트워크 벤치마크에서 평균 지연만 보면 되나요?

endpoint 갱신과 scale-out 때의 p95, p99, 연결 실패, CPU, conntrack, BPF Map pressure와 정책 반영 시간을 함께 봐야 운영 효과를 판단할 수 있습니다.

### XDP drop 예제 성능을 서비스 메시 전체 성능으로 봐도 되나요?

안 됩니다. XDP의 단순 drop과 Kubernetes Service, L7 정책, mTLS 경로는 다른 작업입니다. 사용 기능과 실제 packet path를 분리해 측정해야 합니다.

## References

- [ebpf.io 원문](https://ebpf.io/)
- [GitHub 저장소](https://github.com/cilium/cilium)
- [dl.acm.org 원문](https://dl.acm.org/doi/10.1145/3387514.3406591)
