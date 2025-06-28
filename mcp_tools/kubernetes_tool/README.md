# Kubernetes Tool for MCP

Kubernetes API를 통해 클러스터 상황, pod 현황, 로그 조회, 이벤트 조회 등 다양한 observability 기능을 제공하는 도구입니다.

## 기능

- 클러스터 정보 조회
- 노드 목록 및 상세 정보 조회
- 네임스페이스 목록 조회
- 파드 목록 및 상세 정보 조회
- 파드 로그 조회
- 서비스 목록 조회
- 디플로이먼트 목록 조회
- 이벤트 목록 조회
- 특정 노드의 파드 목록 조회
- 특정 서비스에 연결된 파드 목록 조회

## 설치 요구사항

- Python 3.6 이상
- kubernetes Python 패키지
- 유효한 kubeconfig 파일 또는 클러스터 내부에서 실행 시 서비스 계정 권한

```bash
pip install kubernetes
```

## 환경 변수

- `KUBECONFIG`: kubeconfig 파일 경로 (기본값: ~/.kube/config)
- `KUBERNETES_TOOL_LOG_LEVEL`: 로그 레벨 설정 (기본값: WARNING, 옵션: DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 사용 예시

### 클러스터 정보 조회

```python
get_cluster_info()
```

### 특정 네임스페이스의 파드 목록 조회

```python
get_pods(namespace='default')
```

### 파드 로그 조회

```python
get_pod_logs(name='nginx-pod', namespace='default', tail_lines=100)
```

### 특정 네임스페이스의 이벤트 조회

```python
get_events(namespace='kube-system')
```

### 파드 상세 정보 조회

```python
describe_pod(name='nginx-pod', namespace='default')
```

### 특정 노드에서 실행 중인 파드 목록 조회

```python
get_pods_by_node(node_name='worker-1')
```

### 특정 서비스에 연결된 파드 목록 조회

```python
get_pods_by_service(service_name='nginx', namespace='default')
```

## 주요 함수 목록

| 함수 | 설명 |
|------|------|
| `get_cluster_info()` | Kubernetes 클러스터 정보를 가져옵니다 |
| `get_nodes()` | Kubernetes 노드 목록을 가져옵니다 |
| `get_namespaces()` | Kubernetes 네임스페이스 목록을 가져옵니다 |
| `get_pods(namespace=None, label_selector=None, field_selector=None)` | Kubernetes 파드 목록을 가져옵니다 |
| `get_pod_logs(name, namespace, container=None, tail_lines=100, previous=False)` | Kubernetes 파드 로그를 가져옵니다 |
| `get_services(namespace=None, label_selector=None)` | Kubernetes 서비스 목록을 가져옵니다 |
| `get_deployments(namespace=None, label_selector=None)` | Kubernetes 디플로이먼트 목록을 가져옵니다 |
| `get_events(namespace=None, field_selector=None, sort_by="lastTimestamp")` | Kubernetes 이벤트 목록을 가져옵니다 |
| `describe_pod(name, namespace)` | Kubernetes 파드 상세 정보를 가져옵니다 |
| `get_pods_by_node(node_name)` | 특정 노드에서 실행 중인 파드 목록을 가져옵니다 |
| `get_pods_by_service(service_name, namespace)` | 특정 서비스에 연결된 파드 목록을 가져옵니다 |

## 인증

이 도구는 다음 방법 중 하나로 Kubernetes API에 인증합니다:

1. kubeconfig 파일 사용 (기본값: ~/.kube/config)
2. 클러스터 내부에서 실행 시 서비스 계정 토큰 사용

## 문제 해결

로그 레벨을 DEBUG로 설정하여 더 자세한 로그를 확인할 수 있습니다:

```bash
export KUBERNETES_TOOL_LOG_LEVEL=DEBUG
```

로그 파일은 프로젝트 루트 디렉토리의 `kubernetes_tool_mcp.log` 파일에서 확인할 수 있습니다.