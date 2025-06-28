#!/usr/bin/env python3
"""
간단한 터미널 크기 확인 스크립트
"""
import os
import subprocess

def quick_terminal_check():
    """빠른 터미널 크기 확인"""
    print("=== 터미널 크기 확인 ===")
    
    # 환경 변수
    print(f"LINES: {os.environ.get('LINES', '설정 안됨')}")
    print(f"COLUMNS: {os.environ.get('COLUMNS', '설정 안됨')}")
    print(f"TERM: {os.environ.get('TERM', '설정 안됨')}")
    
    # stty size
    try:
        result = subprocess.run(['stty', 'size'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"stty size: {result.stdout.strip()}")
        else:
            print(f"stty 실패: {result.stderr.strip()}")
    except:
        print("stty 명령 사용 불가")
    
    # tput
    try:
        lines = subprocess.run(['tput', 'lines'], capture_output=True, text=True, timeout=5)
        cols = subprocess.run(['tput', 'cols'], capture_output=True, text=True, timeout=5)
        if lines.returncode == 0 and cols.returncode == 0:
            print(f"tput: {lines.stdout.strip()}x{cols.stdout.strip()}")
        else:
            print("tput 실패")
    except:
        print("tput 명령 사용 불가")

if __name__ == "__main__":
    quick_terminal_check()
