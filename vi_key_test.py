#!/usr/bin/env python3
"""
VI 키 입력 테스트 스크립트
"""

def test_vi_keys():
    """VI에서 사용하는 키들을 테스트"""
    print("VI 키 입력 테스트")
    print("=" * 50)
    print("다음 키들을 DSPilot SSH Terminal에서 테스트해보세요:")
    print()
    print("기본 이동:")
    print("  h, j, k, l  - 왼쪽, 아래, 위, 오른쪽 이동")
    print("  w, b        - 단어 이동")
    print("  0, $        - 줄 시작/끝")
    print("  gg, G       - 파일 시작/끝")
    print()
    print("편집:")
    print("  i, a        - 삽입 모드")
    print("  o, O        - 새 줄 삽입")
    print("  x, dd       - 삭제")
    print("  yy, p       - 복사/붙여넣기")
    print()
    print("명령:")
    print("  :w          - 저장")
    print("  :q          - 종료")
    print("  :wq         - 저장 후 종료")
    print("  :q!         - 강제 종료")
    print()
    print("검색:")
    print("  /text       - 검색")
    print("  n, N        - 다음/이전 검색 결과")
    print()
    print("ESC         - 명령 모드로 전환")
    print()
    print("테스트 방법:")
    print("1. DSPilot SSH Terminal에서 'vi test.txt' 실행")
    print("2. 위의 키들이 올바르게 작동하는지 확인")
    print("3. 특히 방향키, ESC, 명령 입력이 정상인지 확인")

if __name__ == "__main__":
    test_vi_keys()
