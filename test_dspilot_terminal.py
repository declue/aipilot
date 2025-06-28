#!/usr/bin/env python3
"""
DSPilot SSH Terminal 테스트 스크립트

VI, nano, htop 등의 전체 화면 앱이 올바른 크기로 표시되는지 테스트합니다.
"""

import os
import subprocess

def test_terminal_apps():
    """터미널 앱들이 올바른 크기로 실행되는지 테스트"""
    
    print("📋 DSPilot SSH Terminal 테스트")
    print("=" * 50)
    
    # 1. 현재 터미널 크기 확인
    try:
        result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
        if result.returncode == 0:
            rows, cols = result.stdout.strip().split()
            print(f"현재 터미널 크기: {cols}x{rows} (cols x rows)")
        else:
            print("❌ stty size 명령 실패")
    except Exception as e:
        print(f"❌ 터미널 크기 확인 실패: {e}")
    
    # 2. 환경 변수 확인
    print(f"\n환경 변수:")
    print(f"  TERM: {os.environ.get('TERM', 'undefined')}")
    print(f"  COLUMNS: {os.environ.get('COLUMNS', 'undefined')}")
    print(f"  LINES: {os.environ.get('LINES', 'undefined')}")
    
    # 3. 터미널 기능 테스트
    print(f"\n🧪 터미널 기능 테스트:")
    
    # ANSI 색상 테스트
    print("  ANSI 색상:")
    for i, color in enumerate(['검정', '빨강', '초록', '노랑', '파랑', '자홍', '청록', '흰색']):
        print(f"    \033[3{i}m{color}\033[0m", end="  ")
    print()
    
    # 커서 이동 테스트
    print("  커서 이동:")
    print("    ", end="")
    for i in range(10):
        print(f"\033[{i+1}C{i}", end="")
    print("\n    0123456789")
    
    # 4. 권장 테스트 명령어들
    print(f"\n📝 수동 테스트 권장 명령어들:")
    print("  다음 명령어들을 DSPilot SSH Terminal에서 실행해보세요:")
    print()
    print("  1. 터미널 크기 확인:")
    print("     stty size")
    print("     echo $COLUMNS $LINES")
    print()
    print("  2. VI/VIM 테스트:")
    print("     vi")
    print("     (또는 vim - 전체 화면이 올바르게 표시되는지 확인)")
    print()
    print("  3. nano 테스트:")
    print("     nano")
    print("     (상단/하단 상태바가 올바르게 표시되는지 확인)")
    print()
    print("  4. htop 테스트 (시스템에 있는 경우):")
    print("     htop")
    print("     (프로세스 목록이 전체 화면으로 올바르게 표시되는지 확인)")
    print()
    print("  5. less 테스트:")
    print("     less /etc/passwd")
    print("     (페이징이 올바르게 작동하는지 확인)")
    print()
    print("  6. top 테스트:")
    print("     top")
    print("     (터미널 크기에 맞게 표시되는지 확인)")
    print()
    
    # 5. 문제 해결 팁
    print(f"🔧 문제 해결 팁:")
    print("  • VI에서 화면이 깨져 보인다면: :set term=xterm-256color")
    print("  • 크기가 맞지 않는다면: 터미널 창 크기를 조정해보세요")
    print("  • 색상이 표시되지 않는다면: echo $TERM 확인")
    print("  • ESC 키가 작동하지 않는다면: Ctrl+[ 사용")
    print()
    print("✅ 테스트 완료")

if __name__ == "__main__":
    test_terminal_apps()
