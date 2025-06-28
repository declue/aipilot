#!/usr/bin/env python3
"""
DSPilot SSH Terminal Manager 실행 스크립트
"""
import sys
from pathlib import Path

# 현재 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dspilot_shell.app import main

if __name__ == "__main__":
    sys.exit(main())
