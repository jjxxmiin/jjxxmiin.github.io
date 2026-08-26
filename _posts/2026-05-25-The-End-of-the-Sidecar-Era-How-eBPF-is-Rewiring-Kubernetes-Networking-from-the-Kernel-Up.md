---
layout: post
title: 'Cilium eBPF로 kube-proxy를 바꿀 때: iptables 병목, Hubble, L7 경계'
date: '2026-05-25 18:57:37'
categories: Tech
tags:
  - 인프라
  - AI트렌드
summary: Kubernetes 서비스, 정책 경로를 Cilium eBPF 데이터 플레인으로 옮길 때의 Map, 소켓 경로와 Hubble 관측성을 살펴보고, L7 프록시와 커널 운영 조건을 점검합니다.
description: Cilium eBPF로 kube-proxy 경로를 바꿀 때 확인할 커널, CNI 조건, Hubble 관측 범위와 L7 경계, 노드 풀별 마이그레이션, 롤백 절차를 실무 기준으로 설명합니다.
faq:
  - question: Cilium을 설치하면 kube-proxy를 즉시 삭제해도 되나요?
    answer: 아닙니다. 선택한 대체 모드와 클라우드, 커널 호환성을 확인하고 격리한 노드 풀에서 서비스, 정책, 장애 복구를 검증한 뒤 전환해야 합니다.
  - question: Hubble만 있으면 Kubernetes 네트워크 장애 원인을 모두 찾을 수 있나요?
    answer: 아닙니다. 네트워크 흐름과 정책 판단에는 유용하지만 애플리케이션 내부 오류, DNS 외부 의존성, 암호화된 L7 문맥은 다른 로그와 trace가 필요할 수 있습니다.
  - question: Cilium 전환 효과는 어떤 지표로 판단하나요?
    answer: 같은 기능 조건에서 서비스 지연, 노드 CPU, 정책 갱신 시간, 드롭률과 함께 장애 진단 및 이전 경로로 되돌리는 시간을 비교해야 합니다.
github_url: https://github.com/esengine/DeepSeek-Reasonix
image:
  path: https://opengraph.githubassets.com/1/esengine/DeepSeek-Reasonix
  alt: "esengine/DeepSeek-Reasonix GitHub 저장소 대표 이미지"
---

Kubernetes의 서비스, 정책 경로가 실제 병목이라면 eBPF 데이터 플레인을 시험할 가치가 있지만, 애플리케이션 병목이나 복잡한 L7 요구까지 해결되지는 않습니다.

## kube-proxy를 바꾸기 전에 병목부터 증명한다

`kube-proxy`의 `iptables` 모드는 서비스와 엔드포인트를 규칙으로 표현합니다. 클러스터가 커지면 규칙 갱신 시간과 패킷 조회 경로가 부담이 될 수 있고, 파드별 사이드카까지 있으면 사용자 공간 프록시 비용도 더해집니다. 그러나 서비스 5,000개가 반드시 규칙 50,000개와 특정 지연을 만든다는 고정식은 없습니다. Kubernetes 버전, 규칙 구조, 트래픽과 노드 상태를 함께 봐야 합니다.

먼저 확인할 것은 애플리케이션 p99, DNS, 연결 설정, 패킷 드롭, `kube-proxy` 동기화 시간과 노드 CPU입니다. DB N+1이나 애플리케이션 락이 지연의 대부분이면 CNI 교체는 복잡한 우회가 됩니다. 네트워크 구간의 증거가 있을 때만 데이터 플레인 실험의 성공 기준을 만들 수 있습니다.

## Cilium 데이터 경로는 Map과 훅으로 단계를 줄인다

eBPF 기반 CNI는 서비스, 정책 정보를 BPF Map에 반영하고 커널 훅에서 목적지와 허용 여부를 결정할 수 있습니다. 같은 노드의 일부 통신은 소켓 계층에서 리다이렉트해 기존 라우팅 단계를 줄일 수 있습니다. 이 구조의 목적은 `iptables` 규칙과 파드별 프록시를 무조건 없애는 것이 아니라, L3/L4 처리를 노드의 프로그래밍 가능한 데이터 경로로 옮기는 것입니다.

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

다만 “모든 패킷 사건을 항상 잡는다”는 기대는 피해야 합니다. 활성화한 가시성 범위, 샘플링, 암호화, 데이터 보존과 도구 버전에 따라 볼 수 있는 정보가 달라집니다. 관측 자체의 CPU, 메모리, 저장 비용과 민감한 네트워크 메타데이터의 접근 권한도 관리해야 합니다.

파일럿에서는 단순히 대시보드를 켜지 말고 알려진 정책 드롭, 연결 거부, 재전송을 일부러 만들어 탐지와 원인 추적이 가능한지 시험합니다. 장애 때 사용할 명령과 롤백 절차를 런북으로 남겨야 새 데이터 플레인이 또 다른 블랙박스가 되지 않습니다.

## L7 기능은 노드 프록시로 남을 수 있다

eBPF는 IP, 포트 정책과 로드밸런싱에 강하지만 HTTP/2 헤더, gRPC 재시도, 카나리 규칙, mTLS 처리 같은 L7 기능은 커널 안에서 다루기 복잡합니다. 원문도 Cilium 계열 구성이 필요한 L7 처리를 위해 노드 단위 Envoy를 사용할 수 있음을 지적합니다. 즉, 선택지는 “파드별 Envoy”와 “프록시 없음” 둘뿐이 아닙니다.

현재 메시 기능을 표로 만들고 각 항목을 eBPF, 노드 프록시, 애플리케이션 중 어디가 맡을지 정해야 합니다. mTLS와 인증서 수명주기, 재시도 예산, HTTP 관측이 빠진 채 메모리만 줄이면 기능 회귀가 발생합니다.

## 같은 워크로드를 두 데이터 플레인에서 비교한다

원문이 제안한 로컬 `kind` 비교는 시작점이 될 수 있지만 프로덕션 판단에는 실제와 가까운 노드 이미지와 트래픽이 필요합니다.

1. 지원 커널과 Cilium 기능, 기존 CNI와의 마이그레이션 경로를 확인합니다.
2. 격리된 노드 풀에서 동일 서비스, 정책, 부하를 재현합니다.
3. p50, p99, CPU, 메모리, 드롭, 정책 갱신 시간과 장애 복구 시간을 비교합니다.
4. Hubble만으로 진단할 수 없는 사례를 기록합니다.
5. L7 기능 회귀와 이전 데이터 플레인으로 돌아가는 시간을 측정합니다.

네트워크 지표가 실제로 좋아지고 팀이 Hubble과 커널 경로를 운영할 수 있을 때만 범위를 넓혀야 합니다. Cilium eBPF의 도입 근거는 유행이나 “사이드카의 종말”이 아니라, 같은 워크로드에서 검증된 데이터 플레인 개선입니다.

## 전환 전 호환성 표부터 만든다

Cilium과 kube-proxy 대체는 단일 설치 플래그보다 넓은 변경입니다. Kubernetes 버전, 노드 커널과 배포판, 사용 중인 CNI, 클라우드 네트워크, IPAM 방식, NetworkPolicy, LoadBalancer, NodePort, externalTrafficPolicy 요구를 한 표에 모아야 합니다. 필요한 기능이 현재 선택한 Cilium 버전과 모드에서 지원되는지는 공식 문서의 정확한 버전으로 확인합니다.

노드 이미지가 여러 종류라면 같은 커널 기능을 가정하지 않습니다. BTF와 helper, cgroup 구성, 방화벽 관리 도구가 다를 수 있습니다. 관리형 Kubernetes에서는 제공자가 허용하는 CNI 교체 범위와 지원 책임도 확인해야 합니다. 기술적으로 동작하더라도 지원 계약 밖의 구성이면 장애 대응 비용이 커질 수 있습니다.

기존 NetworkPolicy와 서비스 동작을 테스트 케이스로 변환하는 작업도 선행합니다. 허용돼야 하는 연결뿐 아니라 차단돼야 하는 연결, DNS, hostNetwork, DaemonSet, 외부 IP와 health check를 포함합니다. ‘파드끼리 통신된다’는 smoke test만으로는 경계 기능의 회귀를 찾기 어렵습니다.

## 노드 풀별 전환은 트래픽 경계를 명확히 해야 한다

새 데이터 플레인을 일부 노드에만 적용하면 이전 노드와 새 노드 사이의 경로가 생깁니다. 어느 CNI가 라우팅과 정책을 맡는지, 서비스 endpoint가 양쪽 노드에 있을 때 연결이 어떻게 흐르는지 검증해야 합니다. canary workload를 새 노드에 고정하고 외부, 노드 간, 노드 내부 트래픽을 각각 시험합니다.

전환 중에는 정책을 두 시스템에 동시에 적용하는 기간이 생길 수 있습니다. 이중 적용이 더 안전하다고 단정할 수 없습니다. 규칙의 우선순위가 다르면 한쪽에서 허용하고 다른 쪽에서 차단할 수 있기 때문입니다. 배포 단계마다 source of truth와 실제 enforcement 지점을 문서화하고, 노드별 활성 모드를 대시보드에서 확인할 수 있게 합니다.

롤백 경로도 시작 전에 정합니다. 새 노드로의 스케줄을 중단하고 workload를 배출한 뒤 이전 노드에서 서비스가 같은 IP, DNS, 정책으로 복구되는지 연습합니다. BPF Map과 CNI 상태 파일이 남은 채 플러그인만 바꾸면 예측하기 어려운 경로가 생길 수 있으므로 공식 제거, 복구 절차를 자동화하고 시간을 측정해야 합니다.

## Hubble 질문을 장애 시나리오와 연결한다

관측 도구의 가치는 화면 수보다 실제 질문에 답하는 속도에서 나옵니다. “정책이 어느 identity를 왜 차단했는가”, “SYN 이후 응답이 없는가”, “DNS 요청이 어느 endpoint까지 갔는가”처럼 자주 발생하는 질문별 조회법과 필요한 보존 기간을 런북에 적습니다. 샘플링 때문에 놓칠 수 있는 흐름과 수집기 장애도 함께 표시합니다.

flow 데이터에는 IP, workload identity, 포트와 통신 관계처럼 민감할 수 있는 메타데이터가 담깁니다. 접근 권한, 마스킹, 보존과 외부 전송 범위를 로그 정책에 포함해야 합니다. 모든 이벤트를 오래 저장하면 비용이 커지므로 정상 흐름은 집계하고 정책 거부, 오류는 필요한 기간만 자세히 보관하는 방식을 검토할 수 있습니다.

Hubble 관측과 애플리케이션 trace를 요청 시간, service identity로 연결하면 네트워크 구간과 애플리케이션 구간을 나누기 쉽습니다. 다만 네트워크 흐름이 성공했다고 업무 요청까지 성공한 것은 아닙니다. HTTP 상태와 DB trace, 외부 API 로그를 함께 봐야 ‘네트워크 문제 없음’이라는 결론을 내릴 수 있습니다.

## 성능보다 먼저 정책 동등성을 통과시킨다

첫 비교 단계에서는 기존과 새 경로에서 허용, 거부 결과가 같은지 확인합니다. 그다음 동일한 TLS, 로그와 L7 기능을 켜고 서비스 수, endpoint 변화와 부하를 늘려 정책 갱신 시간과 데이터 경로 자원을 측정합니다. 기능을 줄인 새 구성을 기존 구성보다 빠르다고 비교하면 도입 효과가 과장됩니다.

정상 부하 외에 endpoint 급증, rollout, 노드 drain, 컨트롤 플레인 단절과 Map 압박을 시험합니다. 평균 지연보다 p99, 연결 실패, 드롭 이유, 복구 시간과 노드별 편차를 봅니다. 서비스가 큰 환경에서는 전체 숫자 하나보다 규모 구간별 결과가 유용합니다.

성공 기준은 예를 들어 ‘정책 회귀 0건, p99 악화 없음, 노드당 자원 감소, 정해진 시간 안에 원인 확인과 롤백 가능’처럼 여러 조건으로 둡니다. 성능 개선 하나만 만족하고 보안 정책이나 복구 목표를 놓치면 확대하지 않습니다.

<!-- primary-sources:start -->
## 원문과 버전 확인

- [공식 GitHub 저장소](https://github.com/esengine/DeepSeek-Reasonix)
<!-- primary-sources:end -->

<!-- internal-links:start -->
## 함께 읽으면 이해가 이어지는 글

- [iptables에서 Cilium으로 어떻게 옮길까: 단계별 마이그레이션과 복귀 기준]({% post_url 2026-05-30-Escaping-the-iptables-Swamp-Why-a-10-Year-Backend-Dev-Surrendered-to-eBPF-and-Cilium %}) — 쿠버네티스 kube-proxy, iptables 환경을 Cilium eBPF 데이터 플레인으로 옮길 때 필요한 현황 조사, 정책 동등성, 노드 풀 canary와 롤백 기준을 정리합니다.
- [eBPF XDP 훅은 패킷을 어디서 막을까: 커널 경로와 Verifier 읽기]({% post_url 2026-05-25-Is-the-Sidecar-Pattern-Dead-Unveiling-the-True-Face-of-eBPF-Hooking-Networks-at-the-Kernel-Level %}) — XDP가 NIC 드라이버 가까이에서 패킷을 처리하는 위치와 PASS, DROP 반환값을 코드로 읽고, Verifier, Map, 커널 호환성과 L7 기능의 한계를 구분합니다.
- [eBPF, Cilium 서비스 메시를 어떻게 운영할까: 관측, 업그레이드, 롤백]({% post_url 2026-05-31-eBPF-and-Cilium-Is-Sidecar-less-Service-Mesh-a-Salvation-or-Another-Disaster %}) — eBPF, Cilium 데이터 플레인을 운영할 때 필요한 flow, drop, BPF Map 관측, 정책 배포, agent, proxy 장애 격리, 업그레이드 canary와 롤백 절차를 정리합니다.
<!-- internal-links:end -->

## 자주 묻는 질문

### Cilium을 설치하면 kube-proxy를 즉시 삭제해도 되나요?

아닙니다. 선택한 대체 모드와 클라우드, 커널 호환성을 확인하고 격리한 노드 풀에서 서비스, 정책, 장애 복구를 검증한 뒤 전환해야 합니다.

### Hubble만 있으면 Kubernetes 네트워크 장애 원인을 모두 찾을 수 있나요?

아닙니다. 네트워크 흐름과 정책 판단에는 유용하지만 애플리케이션 내부 오류, DNS 외부 의존성, 암호화된 L7 문맥은 다른 로그와 trace가 필요할 수 있습니다.

### Cilium 전환 효과는 어떤 지표로 판단하나요?

같은 기능 조건에서 서비스 지연, 노드 CPU, 정책 갱신 시간, 드롭률과 함께 장애 진단 및 이전 경로로 되돌리는 시간을 비교해야 합니다.

## 참고 자료

- [ebpf.io 원문](https://ebpf.io/what-is-ebpf/)
- [cilium.io 원문](https://cilium.io/blog/2021/12/01/cilium-service-mesh/)
- [GitHub 저장소](https://github.com/cilium/cilium)
- [isovalent.com 원문](https://isovalent.com/blog/post/2021-12-ebpf-service-mesh/)
