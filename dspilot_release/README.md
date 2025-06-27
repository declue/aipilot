# DSPilot 릴리스

DSPilot의 클린 릴리스 빌드 및 실행파일 생성을 위한 도구입니다.

## 개요

이 디렉토리는 DSPilot의 배포용 릴리스를 생성하는 도구들을 포함합니다. 주요 기능은 다음과 같습니다:

- **클린 릴리스 생성**: 주석과 docstring을 제거한 최적화된 코드 생성
- **실행파일 생성**: PyInstaller를 사용한 단일 실행파일 생성
- **의존성 최적화**: 불필요한 파일과 테스트 코드 제거

## 주요 파일

- `cli_release.py`: 릴리스 빌드 메인 스크립트
- `release_cli/`: 생성된 클린 릴리스 파일들
- `README.md`: 이 문서

## 사용법

### 기본 클린 릴리스 생성

```bash
python cli_release.py
```

### 실행파일 포함 릴리스 생성

```bash
python cli_release.py --exe
```

### 도움말 확인

```bash
python cli_release.py --help
```

## 빌드 과정

### 1단계: 클린 릴리스 생성

1. **폴더 복사**: `dspilot_cli`, `dspilot_core` 폴더를 `release_cli/`로 복사
2. **파일 필터링**: 테스트 파일, 문서 파일, 캐시 파일 제거
3. **코드 최적화**: Python 파일에서 주석과 docstring 제거
4. **설정 파일 생성**: `setup.py`, `__init__.py` 등 생성

### 2단계: 실행파일 생성 (옵션)

1. **PyInstaller 확인**: PyInstaller 설치 상태 확인
2. **진입점 생성**: `__main__.py` 파일 생성
3. **Spec 파일 생성**: PyInstaller 설정 파일 생성
4. **빌드 실행**: 단일 실행파일 생성

## 요구사항

### 기본 요구사항

- Python 3.8 이상
- 필요한 의존성 패키지들 (aiohttp, colorama, langchain 등)

### 실행파일 생성 요구사항

```bash
pip install pyinstaller
```

## 생성되는 파일 구조

```
release_cli/
├── dspilot_cli/           # CLI 모듈 (최적화됨)
├── dspilot_core/          # 코어 모듈 (최적화됨)
├── setup.py               # 설치 스크립트
├── __init__.py            # 패키지 초기화
├── README.md              # 릴리스 문서
├── dspilot.spec           # PyInstaller 설정
├── build/                 # 빌드 임시 파일
└── dist/                  # 생성된 실행파일
    └── dspilot(.exe)      # 최종 실행파일
```

## 릴리스 특징

### 코드 최적화

- **주석 제거**: 모든 Python 파일에서 주석 제거
- **Docstring 제거**: 함수, 클래스, 모듈의 docstring 제거
- **빈 줄 정리**: 불필요한 빈 줄 제거
- **테스트 코드 제외**: 모든 테스트 관련 파일 제외

### 의존성 관리

- **핵심 패키지만 포함**: 실행에 필요한 최소한의 패키지만 포함
- **GUI 라이브러리 제외**: PyQt6, tkinter 등 GUI 관련 라이브러리 제외
- **개발 도구 제외**: pytest, jupyter 등 개발 도구 제외

### 실행파일 최적화

- **단일 파일**: 모든 의존성을 포함한 하나의 실행파일
- **UPX 압축**: 실행파일 크기 최적화
- **콘솔 애플리케이션**: CLI 인터페이스 지원
