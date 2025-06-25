#!/usr/bin/env python3
"""
DuckDuckGo MCP 서버를 직접 실행하여 오류를 확인하는 스크립트
"""

import subprocess
import sys
from pathlib import Path


def test_duckduckgo_server():
    """DuckDuckGo MCP 서버를 직접 실행하여 오류 메시지를 확인"""
    
    project_root = Path(__file__).resolve().parents[2]
    duck_path = project_root / "tools" / "web_search" / "duckduckgo.py"
    
    # 가상환경의 Python 실행 파일 경로
    venv_python = project_root / "venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print(f"❌ 가상환경 Python을 찾을 수 없습니다: {venv_python}")
        python_executable = sys.executable
    else:
        python_executable = str(venv_python)
    
    print(f"🚀 DuckDuckGo MCP 서버 직접 실행 테스트")
    print(f"   Python: {python_executable}")
    print(f"   Script: {duck_path}")
    print("-" * 60)
    
    try:
        # subprocess로 서버를 실행하고 stderr 출력을 캡처
        result = subprocess.run(
            [python_executable, str(duck_path)],
            capture_output=True,
            text=True,
            timeout=10  # 10초 후 타임아웃
        )
        
        print(f"🔍 Return Code: {result.returncode}")
        print(f"📝 STDOUT:")
        print(result.stdout or "(비어 있음)")
        print(f"❌ STDERR:")
        print(result.stderr or "(비어 있음)")
        
        # 로그 파일도 확인
        log_file = project_root / "duckduckgo_mcp.log"
        if log_file.exists():
            print(f"📄 로그 파일 내용 ({log_file}):")
            with open(log_file, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("📄 로그 파일이 생성되지 않았습니다.")
            
    except subprocess.TimeoutExpired:
        print("⏰ 프로세스가 10초 후 타임아웃되었습니다 (정상적으로 실행 중일 수 있음)")
    except Exception as e:
        print(f"💥 실행 중 예외 발생: {e}")

if __name__ == "__main__":
    test_duckduckgo_server() 