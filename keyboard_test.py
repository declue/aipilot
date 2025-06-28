#!/usr/bin/env python3
"""
키 입력 테스트 스크립트 - DSPilot SSH Terminal용
"""

def main():
    print("🔧 DSPilot SSH Terminal 키 입력 테스트")
    print("=" * 50)
    print()
    print("1. 기본 테스트:")
    print("   - 먼저 'echo hello' 입력해보세요")
    print("   - Enter 키가 정상 작동하는지 확인")
    print()
    print("2. 방향키 테스트:")
    print("   - 방향키 ↑ ↓ ← → 를 눌러보세요")
    print("   - 명령 히스토리가 올바르게 작동하는지 확인")
    print()
    print("3. VI 테스트:")
    print("   - 'vi test.txt' 실행")
    print("   - 'i' 키로 삽입 모드 진입")
    print("   - 'hello world' 입력")
    print("   - ESC 키로 명령 모드로 전환")
    print("   - ':wq' 입력하여 저장 후 종료")
    print()
    print("4. 제어 키 테스트:")
    print("   - Ctrl+C (인터럽트)")
    print("   - Ctrl+D (EOF)")
    print("   - Ctrl+L (화면 클리어)")
    print()
    print("5. 문제 발생 시 확인할 점:")
    print("   - 이상한 문자열이 출력되는가?")
    print("   - 키 입력이 중복으로 들어가는가?")
    print("   - VI에서 커서 이동이 정상인가?")
    print("   - ESC키가 올바르게 작동하는가?")
    print()
    print("✅ 테스트를 순서대로 진행해보세요.")

if __name__ == "__main__":
    main()
