#!/usr/bin/env python3
"""
DSPilot CLI 메인 실행 진입점

이 모듈은 `python -m dspilot_cli` 혹은 `dspilot_cli/__main__.py` 를 직접
실행했을 때 호출되는 *entry point* 스크립트입니다. 내부적으로
`dspilot_cli.cli_main.main()` 코루틴을 호출하여 실제 CLI 로직을 수행합니다.

동작 흐름
---------
1. **Python Path 설정** : 프로젝트 루트(두 단계 상위)를 `sys.path` 에 삽입해
   모듈 임포트 문제를 방지합니다.
2. **Async 진입** : `asyncio.run(main())` 을 통해 비동기 CLI 애플리케이션을
   시작합니다.
3. **예외 처리** :
   - `KeyboardInterrupt` : 사용자가 Ctrl+C 로 종료할 때 우아하게 메시지를
     출력합니다.
   - 일반 `Exception` : 오류 메시지를 출력하고 비 0 종료 코드를 반환합니다.

주의
----
- 본 모듈은 **가급적 수정하지 말 것** : CLI의 핵심 로직은
  `dspilot_cli.cli_main` 이하 모듈에서 관리되며, 이 스크립트는
  진입점 역할만 수행합니다.
"""

import asyncio
import sys
from pathlib import Path

from dspilot_cli.cli_main import main  # pylint: disable=wrong-import-position

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)
