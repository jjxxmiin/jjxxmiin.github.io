---
layout: post
title: 'Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목·Hubble·L7 경계'
date: '2026-05-25 18:57:37'
categories: Tech
tags:
  - Cilium
  - Kubernetes
  - eBPF
  - kubeproxy
  - Hubble
summary: Kubernetes 서비스·정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map·소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
author: AI Trend Bot
github_url: https://github.com/esengine/DeepSeek-Reasonix
image:
  path: https://opengraph.githubassets.com/1/esengine/DeepSeek-Reasonix
  alt: '🔥 The End of the Sidecar Era: How eBPF is Rewiring Kubernetes Networking from
    the Kernel Up'
---

Kubernetes의 서비스·정책 경로가 실제 병목이라면 eBPF 데이터 플레인을 시험할 가치가 있지만, 애플리케이션 병목이나 복잡한 L7 요구까지 해결되지는 않습니다.

## kube-proxy를 바꾸기 전에 병목부터 증명한다

`kube-proxy`의 `iptables` 모드는 서비스와 엔드포인트를 규칙으로 표현합니다. 클러스터가 커지면 규칙 갱신 시간과 패킷 조회 경로가 부담이 될 수 있고, 파드별 사이드카까지 있으면 사용자 공간 프록시 비용도 더해집니다. 그러나 서비스 5,000개가 반드시 규칙 50,000개와 특정 지연을 만든다는 고정식은 없습니다. Kubernetes 버전, 규칙 구조, 트래픽과 노드 상태를 함께 봐야 합니다.

먼저 확인할 것은 애플리케이션 p99, DNS, 연결 설정, 패킷 드롭, `kube-proxy` 동기화 시간과 노드 CPU입니다. DB N+1이나 애플리케이션 락이 지연의 대부분이면 CNI 교체는 복잡한 우회가 됩니다. 네트워크 구간의 증거가 있을 때만 데이터 플레인 실험의 성공 기준을 만들 수 있습니다.

## Cilium 데이터 경로는 Map과 훅으로 단계를 줄인다

eBPF 기반 CNI는 서비스·정책 정보를 BPF Map에 반영하고 커널 훅에서 목적지와 허용 여부를 결정할 수 있습니다. 같은 노드의 일부 통신은 소켓 계층에서 리다이렉트해 기존 라우팅 단계를 줄일 수 있습니다. 이 구조의 목적은 `iptables` 규칙과 파드별 프록시를 무조건 없애는 것이 아니라, L3/L4 처리를 노드의 프로그래밍 가능한 데이터 경로로 옮기는 것입니다.

원문의 `sockhash` 코드는 아이디어만 담은 스냅샷입니다.

```c
struct {
    __uint(type, BPF_MAP_TYPE_SOCKHASH);
    __uint(max_entries, 65535);
    __type(key, struct sock_key);
    __type(value, __u32);
} sock_map SEC(".maps");

SEC("sk_msg")
int bpf_tcp_bypass_proxy(struct sk_msg_md *msg) {
    struct sock_key key = {};

    extract_key_from_msg(msg, &key);

    if (bpf_sock_hash_update(msg, &sock_map, &key, BPF_ANY) == 0) {
        return bpf_msg_redirect_hash(msg, &sock_map, &key, BPF_F_INGRESS);
    }

    return SK_PASS;
}
```

`struct sock_key`와 `extract_key_from_msg`가 정의되지 않았고, Map을 채우는 소켓 이벤트 경로와 사용자 공간 로더, attach, 키의 엔디언과 오류 처리가 없습니다. helper가 허용되는 컨텍스트와 Map 갱신 흐름도 완성돼 있지 않습니다. 이 조각은 소켓 리다이렉션 개념을 읽는 용도이며 실행 가능한 Cilium 구성이나 zero-copy 보장이 아닙니다.

### Hubble은 애플리케이션 로그 밖의 증거를 보탠다

Cilium의 Hubble 같은 관측 도구는 네트워크 흐름과 정책 결정을 연결해 TCP 재전송, RST, 드롭 같은 단서를 찾는 데 도움을 줄 수 있습니다. 애플리케이션 로그에 502만 남고 패킷이 어느 정책에서 거부됐는지 모를 때 유용한 층입니다.

다만 “모든 패킷 사건을 항상 잡는다”는 기대는 피해야 합니다. 활성화한 가시성 범위, 샘플링, 암호화, 데이터 보존과 도구 버전에 따라 볼 수 있는 정보가 달라집니다. 관측 자체의 CPU·메모리·저장 비용과 민감한 네트워크 메타데이터의 접근 권한도 관리해야 합니다.

파일럿에서는 단순히 대시보드를 켜지 말고 알려진 정책 드롭, 연결 거부, 재전송을 일부러 만들어 탐지와 원인 추적이 가능한지 시험합니다. 장애 때 사용할 명령과 롤백 절차를 런북으로 남겨야 새 데이터 플레인이 또 다른 블랙박스가 되지 않습니다.

## L7 기능은 노드 프록시로 남을 수 있다

eBPF는 IP·포트 정책과 로드밸런싱에 강하지만 HTTP/2 헤더, gRPC 재시도, 카나리 규칙, mTLS 처리 같은 L7 기능은 커널 안에서 다루기 복잡합니다. 원문도 Cilium 계열 구성이 필요한 L7 처리를 위해 노드 단위 Envoy를 사용할 수 있음을 지적합니다. 즉, 선택지는 “파드별 Envoy”와 “프록시 없음” 둘뿐이 아닙니다.

현재 메시 기능을 표로 만들고 각 항목을 eBPF, 노드 프록시, 애플리케이션 중 어디가 맡을지 정해야 합니다. mTLS와 인증서 수명주기, 재시도 예산, HTTP 관측이 빠진 채 메모리만 줄이면 기능 회귀가 발생합니다.

## 같은 워크로드를 두 데이터 플레인에서 비교한다

원문이 제안한 로컬 `kind` 비교는 시작점이 될 수 있지만 프로덕션 판단에는 실제와 가까운 노드 이미지와 트래픽이 필요합니다.

1. 지원 커널과 Cilium 기능, 기존 CNI와의 마이그레이션 경로를 확인합니다.
2. 격리된 노드 풀에서 동일 서비스·정책·부하를 재현합니다.
3. p50·p99, CPU·메모리, 드롭, 정책 갱신 시간과 장애 복구 시간을 비교합니다.
4. Hubble만으로 진단할 수 없는 사례를 기록합니다.
5. L7 기능 회귀와 이전 데이터 플레인으로 돌아가는 시간을 측정합니다.

네트워크 지표가 실제로 좋아지고 팀이 Hubble과 커널 경로를 운영할 수 있을 때만 범위를 넓혀야 합니다. Cilium eBPF의 도입 근거는 유행이나 “사이드카의 종말”이 아니라, 같은 워크로드에서 검증된 데이터 플레인 개선입니다.

## 참고 자료

- https://ebpf.io/what-is-ebpf/
- https://cilium.io/blog/2021/12/01/cilium-service-mesh/
- https://github.com/cilium/cilium
- https://isovalent.com/blog/post/2021-12-ebpf-service-mesh/
