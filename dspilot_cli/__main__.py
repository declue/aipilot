#!/usr/bin/env python3
"""
DSPilot CLI 메인 실행 진입점
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
