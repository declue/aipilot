#!/usr/bin/env python3
"""
PTY 크기 테스트 및 진단 도구
VI, nano, htop 등이 올바른 크기로 표시되는지 확인
"""

import subprocess
import os

def test_pty_size():
    """PTY 크기 관련 테스트"""
    print("🔍 PTY 크기 진단 도구")
    print("=" * 50)
    
    # 1. 현재 터미널 크기 확인
    print("1. 현재 터미널 크기:")
    try:
        result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
        if result.returncode == 0:
            rows, cols = result.stdout.strip().split()
            print(f"   stty size: {rows}행 x {cols}열")
        else:
            print("   ❌ stty size 실패")
    except Exception as e:
        print(f"   ❌ stty 오류: {e}")
    
    # 2. 환경 변수 확인
    print("\n2. 터미널 관련 환경 변수:")
    env_vars = ['TERM', 'COLUMNS', 'LINES', 'SHELL', 'TERM_PROGRAM']
    for var in env_vars:
        value = os.environ.get(var, '(설정되지 않음)')
        print(f"   {var}: {value}")
    
    # 3. tput 명령어로 크기 확인
    print("\n3. tput 명령어 결과:")
    try:
        cols_result = subprocess.run(['tput', 'cols'], capture_output=True, text=True)
        lines_result = subprocess.run(['tput', 'lines'], capture_output=True, text=True)
        
        if cols_result.returncode == 0 and lines_result.returncode == 0:
            cols = cols_result.stdout.strip()
            lines = lines_result.stdout.strip()
            print(f"   tput: {lines}행 x {cols}열")
        else:
            print("   ❌ tput 명령 실패")
    except Exception as e:
        print(f"   ❌ tput 오류: {e}")
    
    # 4. Python으로 터미널 크기 확인
    print("\n4. Python shutil로 크기 확인:")
    try:
        import shutil
        size = shutil.get_terminal_size()
        print(f"   shutil: {size.lines}행 x {size.columns}열")
    except Exception as e:
        print(f"   ❌ shutil 오류: {e}")
    
    # 5. 터미널 기능 테스트
    print("\n5. 터미널 기능 테스트:")
    
    # 커서 위치 저장/복원 테스트
    print("   커서 제어 테스트:")
    print("   \x1b[s", end="")  # 커서 위치 저장
    print("이동된 위치", end="")
    print("\x1b[u", end="")  # 커서 위치 복원
    print("원래 위치")
    
    # 색상 테스트
    print("   ANSI 색상 테스트:")
    for i in range(8):
        print(f"\x1b[3{i}m색상{i}\x1b[0m", end="  ")
    print()
    
    # 6. VI 테스트 안내
    print(f"\n6. 전체 화면 앱 테스트 권장사항:")
    print("   DSPilot SSH Terminal에서 다음 명령어들을 테스트해보세요:")
    print()
    print("   ✓ vi 또는 vim:")
    print("     - 전체 화면이 올바르게 표시되는지 확인")
    print("     - :set 명령으로 lines=? columns=? 값 확인")
    print("     - 방향키와 ESC키가 올바르게 작동하는지 확인")
    print()
    print("   ✓ nano:")
    print("     - 상단/하단 상태바가 올바르게 표시되는지 확인")
    print("     - Ctrl+G로 도움말이 올바르게 표시되는지 확인")
    print()
    print("   ✓ less /etc/passwd:")
    print("     - 페이징이 터미널 크기에 맞게 작동하는지 확인")
    print("     - q로 종료가 올바르게 작동하는지 확인")
    print()
    print("   ✓ top 또는 htop:")
    print("     - 프로세스 목록이 터미널 크기에 맞게 표시되는지 확인")
    print("     - 실시간 업데이트가 올바르게 작동하는지 확인")
    
    print(f"\n7. 문제 해결 팁:")
    print("   ✓ 크기가 맞지 않으면: 터미널 창 크기 조정 후 새로 연결")
    print("   ✓ VI에서 깨져 보이면: :set term=xterm-256color")
    print("   ✓ 색상이 안 보이면: export TERM=xterm-256color")
    print("   ✓ 방향키가 안 되면: 키 매핑 확인 필요")
    
    print(f"\n✅ PTY 크기 진단 완료")

if __name__ == "__main__":
    test_pty_size()
