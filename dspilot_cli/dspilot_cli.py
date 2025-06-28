#!/usr/bin/env python3
"""
DSPilot CLI - 메인 진입점

사용법:
  python -m dspilot_cli                    # 대화형 모드
  python -m dspilot_cli "질문"             # 단일 질문 모드  
  python -m dspilot_cli "질문" --stream    # 단일 질문 모드 (스트리밍 출력)
  python -m dspilot_cli --diagnose         # 시스템 진단
  python -m dspilot_cli --tools            # MCP 도구 목록
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
