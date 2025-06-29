#!/usr/bin/env python3
"""
DSPilot CLI - 메인 진입점

이 스크립트는 DSPilot 에이전트를 터미널에서 손쉽게 실행할 수 있게 하는
*Wrapper* 역할을 합니다. `python -m dspilot_cli` 명령이나 `dspilot_cli.py`
파일 자체를 실행하면 내부적으로 `dspilot_cli.cli_main.main()` 코루틴을
호출해 전체 CLI 애플리케이션을 구동합니다.

주요 기능
---------
1. **실행 모드 스위칭**
   - **대화형 모드** : 추가 인자 없이 실행 시 다중 TURN 대화를 지원.
   - **단일 질문 모드** : 첫 번째 인자로 질문 문자열을 넘기면 Agent가 한 번만
     실행되고 종료.
   - `--stream` 플래그로 스트리밍 출력 가능.
2. **진단/도구 목록**
   - `--diagnose` : 환경·의존성·네트워크 체크.
   - `--tools`    : 활성화된 MCP 도구들의 메타데이터를 출력.
3. **예외 처리 및 종료 코드 관리**
   모든 예상치 못한 예외를 잡아 사용자 친화적 메시지를 보여준 뒤 적절한
   종료 코드를 반환합니다.

사용 예시
---------
```bash
# 대화형 모드
python -m dspilot_cli

# 단일 질문
python -m dspilot_cli "오늘의 IT 뉴스 알려줘"

# 스트리밍 모드
python -m dspilot_cli "AWS 신규 서비스 요약" --stream
```
"""

import asyncio
import sys
from pathlib import Path

from dspilot_cli.cli_main import main

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
