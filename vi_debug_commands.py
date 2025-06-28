#!/usr/bin/env python3
"""
VI 터미널 문제 디버깅을 위한 간단한 명령들
"""

def print_vi_debug_commands():
    """VI 디버깅에 유용한 명령들 출력"""
    print("VI 터미널 크기 문제 디버깅 명령들:")
    print("=" * 60)
    
    print("\n1. 터미널 정보 확인:")
    print("   echo \"TERM: $TERM\"")
    print("   echo \"LINES: $LINES\"") 
    print("   echo \"COLUMNS: $COLUMNS\"")
    print("   stty size")
    print("   tput lines && tput cols")
    
    print("\n2. 터미널 크기 수동 설정:")
    print("   export TERM=vt100")
    print("   export LINES=24")
    print("   export COLUMNS=80")
    print("   stty rows 24 cols 80")
    
    print("\n3. VI 테스트:")
    print("   vi")
    print("   (VI 내에서) :set")
    print("   (VI 내에서) :set lines?")
    print("   (VI 내에서) :set columns?")
    print("   (VI 내에서) :q!")
    
    print("\n4. 대안 편집기 테스트:")
    print("   nano test.txt")
    print("   less /etc/passwd")
    
    print("\n5. 터미널 초기화:")
    print("   reset")
    print("   clear")
    
    print("=" * 60)

if __name__ == "__main__":
    print_vi_debug_commands()
