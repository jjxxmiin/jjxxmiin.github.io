---
layout: post
title: 'eBPF, Cilium 서비스 메시를 어떻게 운영할까: 관측, 업그레이드, 롤백'
date: '2026-05-31 18:59:12'
categories: Tech
tags:
  - 인프라
  - 웹개발
  - AI에이전트
summary: 'eBPF, Cilium 데이터 플레인을 운영할 때 필요한 flow, drop, BPF Map 관측, 정책 배포, agent, proxy 장애 격리, 업그레이드 canary와 롤백 절차를 정리합니다.'
description: 'Cilium 운영을 flow, drop, Map pressure 관측, 정책 변경 canary, node agent, L7 proxy 장애 runbook, 버전 업그레이드와 데이터 플레인 롤백 기준으로 정리합니다.'
github_url: https://github.com/FareedKhan-dev/train-llm-from-scratch
faq:
  - question: 'Cilium을 쓰면 tcpdump만으로 네트워크 장애를 찾을 수 있나요?'
    answer: '항상 그렇지는 않습니다. XDP, tc, socket hook에서 처리된 packet은 기존 관찰 지점과 다를 수 있어 flow verdict, drop reason, agent 상태와 BPF Map을 함께 봐야 합니다.'
  - question: 'CiliumNetworkPolicy는 적용 전에 어떻게 검증하나요?'
    answer: '허용, 거부 traffic fixture와 selector 대상을 확인하고 test namespace와 canary workload에 먼저 적용합니다. 정책 반영 지연과 예상 밖 drop, 허용을 관찰한 뒤 확대하세요.'
  - question: 'Cilium 업그레이드 롤백은 Helm 버전만 되돌리면 끝나나요?'
    answer: '아닙니다. agent, operator, proxy, CRD와 BPF state 호환성, node image와 connection을 함께 고려해야 합니다. 공식 upgrade path와 사전 rehearsal로 복귀 단계를 검증하세요.'
image:
  path: https://opengraph.githubassets.com/1/FareedKhan-dev/train-llm-from-scratch
  alt: "FareedKhan-dev/train-llm-from-scratch GitHub 저장소 대표 이미지"
---

eBPF, Cilium 데이터 플레인은 설치보다 운영 모델이 더 중요합니다. packet이 어느 hook에서 허용, drop됐는지, 정책과 BPF Map이 최신인지, agent, L7 proxy 장애가 어디까지 번지는지를 온콜이 설명할 수 있어야 합니다. 업그레이드 전 canary와 검증된 복귀 절차가 없다면 sidecar 비용을 줄이고 더 어려운 장애를 얻을 수 있습니다.

이 글은 [eBPF](https://ebpf.io/), [Cilium](https://cilium.io/), [Cilium 저장소](https://github.com/cilium/cilium)와 [Isovalent 자료](https://isovalent.com/blog/)에 연결된 원문을 바탕으로 운영 질문을 정리합니다. 실제 명령, CRD와 upgrade path는 사용하는 Cilium, Kubernetes, Linux 버전의 공식 문서를 따라야 합니다.

## 운영자는 어떤 control, data plane 상태를 봐야 하는가?

control plane은 Service, endpoint, identity와 policy를 계산해 node agent에 전달하고, data plane은 attach된 eBPF program과 Map, proxy에서 packet을 처리합니다. API가 정상이어도 특정 node의 Map이 오래됐거나 program load가 실패하면 일부 pod만 통신하지 못할 수 있습니다. cluster 전체 ‘정상’ 하나가 아니라 node, endpoint별 desired와 realized 상태 차이를 봐야 합니다.

기본 dashboard에는 agent, operator 가용성, endpoint regeneration, policy revision, BPF Map pressure, program load error, conntrack, flow drop reason, DNS와 L7 proxy 오류를 넣습니다. application SLI인 request 성공률, p99와 같은 시간축으로 맞추면 network 변화와 사용자 영향을 연결할 수 있습니다. telemetry backend 자체의 drop과 sampling도 표시해야 ‘관측되지 않음’을 ‘문제 없음’으로 오해하지 않습니다.

node image, kernel, Cilium image와 configuration hash를 inventory로 유지하세요. 특정 kernel pool에서만 drop이 늘거나 mixed version upgrade 중 문제가 생길 때 공통점을 빠르게 찾을 수 있습니다. 임시 설정과 debug flag에는 소유자, 만료일을 붙여 정상 설정으로 굳지 않게 합니다.

## packet이 사라졌을 때 어떤 순서로 좁혀 갈까?

먼저 client, server 양쪽의 DNS, Service endpoint와 application listen 상태를 확인합니다. 다음으로 source, destination identity, policy verdict와 drop reason을 flow 관측에서 찾고 해당 node의 endpoint, agent 상태를 확인합니다. 그 뒤 BPF Map과 program attachment, route, MTU, cloud firewall로 내려갑니다. 처음부터 모든 Map을 dump하면 신호보다 데이터가 많아집니다.

XDP, tc 또는 socket hook에서 packet이 처리되면 전통적인 tcpdump 위치에서 기대한 packet이 보이지 않을 수 있습니다. ‘capture에 없음’은 network에 들어오지 않았다는 뜻이 아닙니다. 어느 hook 전후에서 관찰하는지 기록하고 Hubble 같은 flow 정보, kernel counter와 양끝 synthetic probe를 교차 확인합니다.

incident timeline에는 policy, Cilium, kernel, node 변화, endpoint churn과 control plane 단절을 함께 놓습니다. 변경 직후 특정 identity만 거부됐다면 application 재시작보다 policy revision과 Map sync를 먼저 확인할 수 있습니다. 반대로 모든 flow가 허용인데 server가 응답하지 않으면 L7 proxy나 application까지 범위를 옮깁니다.

## XDP 예제를 운영 코드로 오해하면 왜 위험한가?

원문의 다음 예제는 Ethernet, IPv4 header 경계를 검사한 뒤 특정 주소를 drop하는 개념 조각입니다. IPv6, fragment, Map 기반 목록, byte order와 update, audit를 완성하지 않았고 서비스 메시의 mTLS, L7 기능과도 별개입니다.

```c
SEC("xdp")
int xdp_drop_prog(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if (data + sizeof(struct ethhdr) > data_end)
        return XDP_PASS;

    struct iphdr *ip = data + sizeof(struct ethhdr);
    if (data + sizeof(struct ethhdr) + sizeof(struct iphdr) > data_end)
        return XDP_PASS;

    if (ip->saddr == bpf_htonl(0x0A000001)) {
        return XDP_DROP;
    }

    return XDP_PASS;
}
```

운영 program은 artifact hash와 source, compiler version을 추적하고 허용 node, interface에서만 attach합니다. 새로운 drop 조건은 test packet, replay와 canary에서 false positive를 검사하고, attach 전 기존 program과 충돌을 확인합니다. emergency detach 명령은 권한 있는 담당자가 rehearsal해야 합니다.

고속 경로의 debug print나 모든 packet event 수집은 CPU와 storage를 소모할 수 있습니다. 문제 재현 시간과 endpoint를 제한하고 sampling 뒤 원상 복구합니다. 관측을 켠 행위가 성능 문제를 더 악화시키지 않는지도 runbook에 포함합니다.

## 네트워크 정책 변경은 어떻게 안전하게 배포할까?

원문의 CiliumNetworkPolicy 조각은 `backend-api`로 들어오는 8080/TCP 중 GET, 특정 path를 허용하려는 예시입니다. 실제 지원, proxy 경로, 다른 method와 기존 connection 동작은 버전과 구성에서 검증해야 합니다.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-strict-rule"
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/public/.*"
```

배포 전에 selector가 선택하는 실제 endpoint 수와 현재 허용 flow를 미리 봅니다. test namespace에서 GET, POST, 일치, 불일치 path, health check와 운영에 필요한 내부 호출을 fixture로 실행합니다. canary workload에 정책을 먼저 적용하고 예상 allow, deny, proxy error와 policy revision 반영 시간을 관찰합니다.

정책 diff에는 새 허용뿐 아니라 제거되는 허용, 대상 endpoint 변화와 rollback manifest를 표시합니다. emergency 때문에 광범위한 allow를 넣었다면 만료와 제거 조건을 설정합니다. 정책 적용 실패를 ‘안전하게 이전 상태 유지’로 볼지 ‘부분 적용’ 가능성이 있는지 제품 동작을 확인하고 node별 realized revision을 검사합니다.

## agent와 L7 proxy 장애는 어떻게 격리할까?

node agent 재시작 중 기존 connection과 신규 connection이 어떻게 동작하는지 시험합니다. control plane이 끊겼을 때 마지막 정책이 유지되는지, 새 endpoint가 준비되지 않는지와 복구 뒤 stale state가 정리되는지를 runbook에 적습니다. agent가 죽었다는 alert만이 아니라 해당 node의 사용자 SLI와 연결해 우선순위를 정합니다.

sidecarless 구성도 L7 기능을 위해 node-level proxy를 사용할 수 있습니다. proxy 과부하나 crash의 blast radius가 pod 하나가 아니라 node의 여러 workload로 커질 수 있으므로 L7 traffic 양, queue, connection, memory와 restart를 따로 관측합니다. L4-only service와 L7 proxy 경로를 분리하면 장애 때 영향을 받지 않는 traffic을 유지하기 쉽습니다.

Map pressure나 identity 할당 지연에는 단순 agent restart보다 원인을 먼저 봅니다. 제한을 무작정 늘리면 memory가 고갈될 수 있고 restart가 상태 재생성을 한꺼번에 유발할 수 있습니다. capacity threshold, endpoint churn rate와 cleanup 상태를 보고 traffic drain, node 교체, 확장 중 안전한 대응을 선택합니다.

## 업그레이드와 롤백은 어떤 단위로 연습해야 하는가?

upgrade 전 공식 호환 경로, Kubernetes, kernel, CRD와 설정 변경을 확인하고 현재 state, manifest와 node image를 snapshot합니다. 별도 cluster에서 policy, Service, DNS, L7, encryption과 node reboot suite를 통과한 뒤 작은 node pool을 canary로 올립니다. data plane upgrade와 kernel, CNI, ingress 변경을 같은 창에 묶지 않습니다.

canary 동안 endpoint regeneration, program load, Map migration, connection reset, drop, error와 application p99를 이전 pool과 비교합니다. 버전이 섞인 기간의 지원 범위와 최대 시간을 정하고, 다음 batch는 on-call과 service owner가 승인합니다. 새 기능을 즉시 켜지 말고 version upgrade 안정화 뒤 별도 변경으로 배포하면 rollback을 단순화할 수 있습니다.

rollback은 Helm release만 되돌리는 명령이 아닐 수 있습니다. CRD, Map, proxy와 agent state의 하위 호환성, 이미 바뀐 node image와 장기 connection을 고려해야 합니다. 검증된 이전 image의 새 node pool로 workload를 drain해 옮기는 방식도 준비하고, 양쪽 datapath가 동시에 route를 소유하지 않게 전환 순서를 명시합니다.

## incident 후 무엇을 남겨야 다음 장애가 짧아질까?

사용자 영향, 최초 drop 또는 policy 변화, control, data plane 상태와 어떤 관측이 비어 있었는지 timeline으로 남깁니다. 근본 원인을 ‘eBPF 문제’처럼 넓게 쓰지 말고 특정 policy revision, Map stale, loader 실패, MTU 또는 proxy saturation처럼 재현 가능한 조건으로 좁힙니다.

재발 방지는 dashboard 하나 추가로 끝내지 않습니다. synthetic probe, policy fixture, preflight, upgrade suite와 rollback rehearsal 중 어느 단계에서 잡혔어야 하는지 연결합니다. 임시 debug 권한, broad allow policy와 pinned Map이 제거됐는지 incident 종료 checklist에서 확인합니다.

운영 합격 기준은 정상 때 낮은 latency뿐 아니라 장애 때 packet 경로를 설명하고 제한 시간 안에 안전한 상태로 복귀하는 능력입니다. 이 기준을 정기 game day에서 재검증하면 eBPF 데이터 플레인이 블랙박스가 아니라 관리 가능한 기반이 됩니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/FareedKhan-dev/train-llm-from-scratch)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목, Hubble, L7 경계]({% post_url 2026-05-25-The-End-of-the-Sidecar-Era-How-eBPF-is-Rewiring-Kubernetes-Networking-from-the-Kernel-Up %}) — Kubernetes 서비스, 정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map, 소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
- [iptables에서 Cilium으로 어떻게 옮길까: 단계별 마이그레이션과 복귀 기준]({% post_url 2026-05-30-Escaping-the-iptables-Swamp-Why-a-10-Year-Backend-Dev-Surrendered-to-eBPF-and-Cilium %}) — 쿠버네티스 kube-proxy, iptables 환경을 Cilium eBPF 데이터 플레인으로 옮길 때 필요한 현황 조사, 정책 동등성, 노드 풀 canary와 롤백 기준을 정리합니다.
- [사이드카를 없애도 될까: eBPF 서비스 메시의 경계와 선택 기준]({% post_url 2026-05-29-The-End-of-Sidecar-Pattern-How-eBPF-is-Disrupting-Service-Mesh-at-the-Kernel-Level %}) — eBPF, Cilium이 파드별 프록시의 L3/L4 역할을 어디까지 줄일 수 있는지 살펴보고, mTLS, L7 라우팅, 관측 요구에 따라 사이드카 유지 여부를 판단합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Cilium을 쓰면 tcpdump만으로 네트워크 장애를 찾을 수 있나요?

항상 그렇지는 않습니다. XDP, tc, socket hook에서 처리된 packet은 기존 관찰 지점과 다를 수 있어 flow verdict, drop reason, agent 상태와 BPF Map을 함께 봐야 합니다.

### CiliumNetworkPolicy는 적용 전에 어떻게 검증하나요?

허용, 거부 traffic fixture와 selector 대상을 확인하고 test namespace와 canary workload에 먼저 적용합니다. 정책 반영 지연과 예상 밖 drop, 허용을 관찰한 뒤 확대하세요.

### Cilium 업그레이드 롤백은 Helm 버전만 되돌리면 끝나나요?

아닙니다. agent, operator, proxy, CRD와 BPF state 호환성, node image와 connection을 함께 고려해야 합니다. 공식 upgrade path와 사전 rehearsal로 복귀 단계를 검증하세요.

## References

- [ebpf.io 원문](https://ebpf.io/)
- [cilium.io 원문](https://cilium.io/)
- [GitHub 저장소](https://github.com/cilium/cilium)
- [isovalent.com 원문](https://isovalent.com/blog/)
