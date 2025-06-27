#!/usr/bin/env python3
"""
DSPilot CLI - 리팩토링된 고급 LLM + MCP + ReAct Agent CLI 도구
SOLID 원칙과 단일 책임 원칙을 적용한 구조

사용법:
  python dspilot_cli.py                    # 대화형 모드
  python dspilot_cli.py "질문"             # 단일 질문 모드
  python dspilot_cli.py --diagnose         # 시스템 진단
  python dspilot_cli.py --tools            # MCP 도구 목록
"""

import asyncio
import sys
from pathlib import Path

from dspilot_cli.refactored_cli import main

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# 리팩토링된 CLI 시스템 사용


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
