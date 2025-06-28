#!/usr/bin/env python3
"""
VI 터미널 크기 테스트 스크립트
"""
import os

def test_terminal_size():
    """터미널 크기 테스트"""
    print("터미널 크기 정보 확인")
    print("=" * 50)
    
    # 환경 변수에서 크기 확인
    lines = os.environ.get('LINES', '알 수 없음')
    columns = os.environ.get('COLUMNS', '알 수 없음')
    term = os.environ.get('TERM', '알 수 없음')
    
    print(f"LINES (행): {lines}")
    print(f"COLUMNS (열): {columns}")
    print(f"TERM: {term}")
    
    # stty로 실제 터미널 크기 확인
    try:
        import subprocess
        result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
        if result.returncode == 0:
            size_parts = result.stdout.strip().split()
            if len(size_parts) == 2:
                stty_rows, stty_cols = size_parts
                print(f"stty size: {stty_rows}행 x {stty_cols}열")
            else:
                print(f"stty size 출력: {result.stdout.strip()}")
        else:
            print("stty size 실행 실패")
    except Exception as e:
        print(f"stty 명령 오류: {e}")
    
    # tput으로 터미널 크기 확인
    try:
        result_lines = subprocess.run(['tput', 'lines'], capture_output=True, text=True)
        result_cols = subprocess.run(['tput', 'cols'], capture_output=True, text=True)
        
        if result_lines.returncode == 0 and result_cols.returncode == 0:
            tput_rows = result_lines.stdout.strip()
            tput_cols = result_cols.stdout.strip()
            print(f"tput: {tput_rows}행 x {tput_cols}열")
        else:
            print("tput 명령 실행 실패")
    except Exception as e:
        print(f"tput 명령 오류: {e}")
    
    print("\n" + "=" * 50)
    print("VI 테스트:")
    print("1. 'vi test.txt' 실행")
    print("2. VI에서 ':set' 입력하여 설정 확인")
    print("3. 'lines='와 'columns=' 값 확인")
    print("4. ':q!' 로 종료")
    print("=" * 50)

if __name__ == "__main__":
    test_terminal_size()
