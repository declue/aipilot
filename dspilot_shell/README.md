# DSPilot SSH Terminal Manager

PySide6 기반 제품 수준 SSH 터미널 관리 프로그램입니다.

## 주요 기능

### 🚀 핵심 기능
- **멀티 탭 SSH 터미널**: 여러 SSH 연결을 동시에 관리
- **연결 관리자**: SSH 연결 정보를 저장하고 관리
- **제품 수준 터미널**: 완전한 터미널 에뮬레이션 (키보드 단축키, 색상 지원)
- **다양한 인증 방법**: 비밀번호, SSH 키, SSH 에이전트 지원

### 🎨 사용자 인터페이스
- **모던 GUI**: PySide6 기반 현대적 인터페이스
- **독 위젯**: 연결 관리자를 독립적으로 관리
- **메뉴 및 툴바**: 직관적인 메뉴 시스템
- **상태바**: 실시간 연결 상태 표시

### 🔧 고급 설정
- **연결 옵션**: 타임아웃, Keep-Alive, 압축 설정
- **터미널 설정**: 터미널 타입, 인코딩 설정
- **프록시 지원**: HTTP/SOCKS 프록시를 통한 연결

## 설치 및 실행

### 필수 요구사항
- Python 3.11+
- PySide6
- paramiko
- dspilot_core

### 실행 방법

1. **직접 실행**:
   ```bash
   python run_ssh_terminal.py
   ```

2. **모듈로 실행**:
   ```bash
   python -m dspilot_shell.app
   ```

## 프로젝트 구조

```
dspilot_shell/
├── __init__.py                 # 패키지 초기화
├── app.py                      # 메인 애플리케이션
├── main_window.py              # 메인 윈도우 클래스
├── models/                     # 데이터 모델
│   ├── __init__.py
│   └── ssh_connection.py       # SSH 연결 모델
└── widgets/                    # UI 위젯
    ├── __init__.py
    ├── connection_manager.py   # 연결 관리자 위젯
    └── terminal_widget.py      # 터미널 위젯
```

## 주요 컴포넌트

### MainWindow
- **역할**: 메인 애플리케이션 윈도우
- **기능**: 메뉴바, 툴바, 상태바, 탭 관리
- **파일**: `main_window.py`

### TerminalWidget
- **역할**: SSH 터미널 에뮬레이션
- **기능**: SSH 연결, 키 입력 처리, 터미널 출력
- **파일**: `widgets/terminal_widget.py`

### ConnectionManagerWidget
- **역할**: SSH 연결 정보 관리
- **기능**: 연결 추가/편집/삭제, 연결 목록 표시
- **파일**: `widgets/connection_manager.py`

### SSHConnection 모델
- **역할**: SSH 연결 정보 저장
- **기능**: 연결 설정, 인증 정보, 유효성 검사
- **파일**: `models/ssh_connection.py`

## 사용 방법

### 1. 새 연결 생성
1. 연결 관리자에서 "새 연결" 버튼 클릭
2. 연결 정보 입력 (호스트, 포트, 사용자명)
3. 인증 방법 선택 (비밀번호/키 파일/키 에이전트)
4. 필요시 고급 설정 구성
5. "확인" 버튼으로 연결 저장

### 2. SSH 연결
1. 연결 관리자에서 연결 선택
2. "연결" 버튼 클릭 또는 더블클릭
3. 새 탭에서 터미널 세션 시작

### 3. 터미널 사용
- **키보드 단축키**: Ctrl+C, Ctrl+D, Ctrl+Z 지원
- **방향키**: 명령 히스토리 탐색
- **복사/붙여넣기**: Ctrl+C/Ctrl+V
- **전체화면**: F11

## 설정 저장

연결 정보는 dspilot_core의 설정 시스템을 통해 자동으로 저장됩니다.
- **위치**: `app.config` 파일의 `[ssh]` 섹션
- **형식**: JSON 형태로 저장
- **보안**: 비밀번호는 저장되지 않음

## 개발 참고사항

### dspilot_core 연동
- `ConfigManager`: 설정 저장/로드
- `Logger`: 통합 로깅 시스템
- 기존 dspilot 생태계와 완전 호환

### 확장 가능성
- 플러그인 시스템 준비
- 커스텀 터미널 테마
- 추가 프로토콜 지원 (Telnet, Serial)

## 기여 및 개발

### 코드 스타일
- PEP 8 준수
- Type hints 사용
- 한국어 주석 및 문서화

### 테스트
- 단위 테스트는 구현하지 않음 (요구사항에 따라)
- 수동 테스트로 품질 관리

## 라이선스

이 프로젝트는 DSPilot의 내부 프로젝트로 개발되었습니다.

---

**DSPilot SSH Terminal Manager v1.0.0**  
*제품 수준의 SSH 터미널 관리 도구*
