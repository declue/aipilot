# Process Monitoring Tool for MCP

현재 사용중인 OS의 프로세스 현황을 조회하는 도구를 제공합니다. 프로세스별 CPU, 메모리 등 다양한 정보를 조회할 수 있습니다.

## 기능

- 프로세스 목록 조회 (필터링 및 정렬 지원)
- 특정 PID의 프로세스 상세 정보 조회
- 프로세스 트리 (부모-자식 관계) 조회
- 시스템 정보 조회 (CPU, 메모리, 디스크 사용량 등)
- 프로세스 종료
- 이름으로 프로세스 검색
- 리소스 사용량이 높은 프로세스 목록 조회

## 설치 요구사항

- Python 3.6 이상
- psutil 라이브러리

```bash
pip install psutil
```

## 환경 변수

- `PROCESS_TOOL_LOG_LEVEL`: 로그 레벨 설정 (기본값: WARNING, 옵션: DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 사용 예시

### 프로세스 목록 조회

```python
get_process_list(limit=50, sort_by="cpu_percent", sort_order="desc")
```

### 특정 PID의 프로세스 정보 조회

```python
get_process_by_pid(1234)
```

### 프로세스 트리 조회

```python
get_process_tree()  # 모든 프로세스의 트리
get_process_tree(pid=1234)  # 특정 PID를 루트로 하는 트리
```

### 시스템 정보 조회

```python
get_system_info()
```

### 프로세스 종료

```python
kill_process(1234)
```

### 이름으로 프로세스 검색

```python
get_process_by_name("chrome")
```

### 리소스 사용량이 높은 프로세스 목록 조회

```python
get_top_processes(resource_type="cpu", limit=5)  # CPU 사용량 기준
get_top_processes(resource_type="memory", limit=5)  # 메모리 사용량 기준
```

## 주요 함수 목록

| 함수 | 설명 |
|------|------|
| `get_process_list(limit=50, sort_by="cpu_percent", sort_order="desc", name_filter=None, username_filter=None, status_filter=None)` | 프로세스 목록을 가져옵니다 |
| `get_process_by_pid(pid)` | PID로 프로세스 정보를 가져옵니다 |
| `get_process_tree(pid=None)` | 프로세스 트리를 가져옵니다 |
| `get_system_info()` | 시스템 정보를 가져옵니다 |
| `kill_process(pid)` | 프로세스를 종료합니다 |
| `get_process_by_name(name, case_sensitive=False)` | 이름으로 프로세스 정보를 가져옵니다 |
| `get_top_processes(resource_type="cpu", limit=10)` | 리소스 사용량이 가장 높은 프로세스 목록을 가져옵니다 |

## 프로세스 정보 필드

프로세스 정보는 다음과 같은 필드를 포함합니다:

- `pid`: 프로세스 ID
- `name`: 프로세스 이름
- `status`: 프로세스 상태 (running, sleeping, disk-sleep, stopped, zombie, dead)
- `cpu_percent`: CPU 사용률 (%)
- `memory_percent`: 메모리 사용률 (%)
- `memory_rss`: 실제 물리 메모리 사용량 (바이트)
- `memory_vms`: 가상 메모리 사용량 (바이트)
- `username`: 프로세스 소유자 사용자 이름
- `create_time`: 프로세스 생성 시간
- `cmdline`: 명령줄 인수
- `num_threads`: 스레드 수
- `parent_pid`: 부모 프로세스 ID
- `parent_name`: 부모 프로세스 이름
- `children`: 자식 프로세스 ID 목록
- `nice`: 프로세스 우선순위
- `cwd`: 현재 작업 디렉토리
- `exe`: 실행 파일 경로
- `open_files_count`: 열린 파일 수
- `connections_count`: 네트워크 연결 수
- `io_read_count`: I/O 읽기 횟수
- `io_write_count`: I/O 쓰기 횟수
- `io_read_bytes`: I/O 읽기 바이트 수
- `io_write_bytes`: I/O 쓰기 바이트 수
- `cpu_times_user`: 사용자 모드에서 소비한 CPU 시간
- `cpu_times_system`: 시스템 모드에서 소비한 CPU 시간
- `cpu_affinity`: CPU 친화도 (프로세스가 실행될 수 있는 CPU 코어 목록)

## 시스템 정보 필드

시스템 정보는 다음과 같은 필드를 포함합니다:

- `cpu_count_physical`: 물리적 CPU 코어 수
- `cpu_count_logical`: 논리적 CPU 코어 수
- `cpu_percent`: 전체 CPU 사용률 (%)
- `cpu_percent_per_cpu`: CPU 코어별 사용률 (%)
- `memory_total`: 전체 메모리 (바이트)
- `memory_available`: 사용 가능한 메모리 (바이트)
- `memory_used`: 사용 중인 메모리 (바이트)
- `memory_percent`: 메모리 사용률 (%)
- `swap_total`: 전체 스왑 메모리 (바이트)
- `swap_used`: 사용 중인 스왑 메모리 (바이트)
- `swap_free`: 사용 가능한 스왑 메모리 (바이트)
- `swap_percent`: 스왑 메모리 사용률 (%)
- `disk_usage`: 디스크 사용량 정보
- `boot_time`: 시스템 부팅 시간
- `platform`: 운영체제 플랫폼
- `platform_version`: 운영체제 버전
- `python_version`: Python 버전
- `hostname`: 호스트 이름
- `uptime`: 시스템 가동 시간
- `process_count`: 프로세스 수
- `thread_count`: 스레드 수

## 운영체제 호환성

이 도구는 다음 운영체제에서 테스트되었습니다:

- Windows
- macOS
- Linux

psutil 라이브러리를 사용하기 때문에 대부분의 기능은 모든 운영체제에서 동일하게 작동합니다. 그러나 일부 기능(예: CPU 친화도, I/O 통계)은 운영체제에 따라 제한될 수 있습니다.

## 문제 해결

로그 레벨을 DEBUG로 설정하여 더 자세한 로그를 확인할 수 있습니다:

```bash
export PROCESS_TOOL_LOG_LEVEL=DEBUG
```

로그 파일은 프로젝트 루트 디렉토리의 `process_tool_mcp.log` 파일에서 확인할 수 있습니다.

## 보안 고려사항

- 일부 프로세스 정보는 권한이 필요할 수 있으며, 권한이 없는 경우 접근이 거부될 수 있습니다.
- 프로세스 종료 기능은 권한이 있는 프로세스에만 작동합니다.
- 시스템 중요 프로세스를 종료하면 시스템이 불안정해질 수 있으므로 주의해야 합니다.