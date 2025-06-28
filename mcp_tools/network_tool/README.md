# Network Diagnostic Tool for MCP

다양한 네트워크 상황 진단을 도와주는 도구를 제공합니다. DNS 조회, TCP 통신 테스트, 현재 IP 조회, 핑 테스트, 트레이스라우트, 포트 스캔 등의 기능을 포함합니다.

## 기능

- DNS 조회 및 역방향 DNS 조회
- TCP 연결 테스트
- 로컬 및 공인 IP 주소 정보 조회
- Ping 테스트
- Traceroute 테스트
- 네트워크 인터페이스 정보 조회
- 포트 스캔
- HTTP 요청 테스트
- SSL 인증서 정보 확인

## 설치 요구사항

- Python 3.6 이상
- 필요한 Python 패키지:
  - requests
  - ipaddress

```bash
pip install requests ipaddress
```

## 환경 변수

- `NETWORK_TOOL_LOG_LEVEL`: 로그 레벨 설정 (기본값: WARNING, 옵션: DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 사용 예시

### DNS 조회

```python
dns_lookup('example.com')
```

### 역방향 DNS 조회

```python
reverse_dns_lookup('8.8.8.8')
```

### TCP 연결 테스트

```python
test_tcp_connection('example.com', 80)
```

### 현재 IP 주소 정보 조회

```python
get_ip_address_info()
```

### Ping 테스트

```python
ping('google.com', count=5)
```

### Traceroute 테스트

```python
traceroute('google.com', max_hops=20)
```

### 네트워크 인터페이스 정보 조회

```python
get_network_interfaces()
```

### 포트 스캔

```python
scan_ports('example.com', ports=[80, 443, 8080])
```

### HTTP 요청 테스트

```python
http_request('https://example.com')
```

### SSL 인증서 정보 확인

```python
check_ssl_certificate('example.com')
```

## 주요 함수 목록

| 함수 | 설명 |
|------|------|
| `dns_lookup(hostname)` | DNS 조회를 수행합니다 |
| `reverse_dns_lookup(ip_address)` | 역방향 DNS 조회를 수행합니다 |
| `test_tcp_connection(host, port, timeout=5)` | TCP 연결 테스트를 수행합니다 |
| `get_ip_address_info()` | 로컬 및 공인 IP 주소 정보를 가져옵니다 |
| `ping(host, count=4)` | Ping 테스트를 수행합니다 |
| `traceroute(host, max_hops=30)` | Traceroute 테스트를 수행합니다 |
| `get_network_interfaces()` | 네트워크 인터페이스 정보를 가져옵니다 |
| `scan_ports(host, ports=None, timeout=1)` | 포트 스캔을 수행합니다 |
| `http_request(url, method="GET", timeout=10)` | HTTP 요청을 수행합니다 |
| `check_ssl_certificate(host, port=443)` | SSL 인증서 정보를 확인합니다 |

## 운영체제 호환성

이 도구는 다음 운영체제에서 테스트되었습니다:

- Windows
- macOS
- Linux

운영체제별로 일부 기능(특히 traceroute, ping, 네트워크 인터페이스 정보 조회)의 출력 형식이 다를 수 있으나, 도구는 이러한 차이를 처리하도록 설계되었습니다.

## 문제 해결

로그 레벨을 DEBUG로 설정하여 더 자세한 로그를 확인할 수 있습니다:

```bash
export NETWORK_TOOL_LOG_LEVEL=DEBUG
```

로그 파일은 프로젝트 루트 디렉토리의 `network_tool_mcp.log` 파일에서 확인할 수 있습니다.

## 보안 고려사항

- 포트 스캔은 대상 시스템에서 침입 시도로 간주될 수 있으므로 권한이 있는 시스템에서만 사용하세요.
- 일부 네트워크에서는 traceroute와 같은 진단 도구의 사용을 제한할 수 있습니다.
- SSL 인증서 확인 시 기본적으로 인증서 유효성 검사를 건너뛰므로, 보안이 중요한 상황에서는 추가 검증이 필요할 수 있습니다.