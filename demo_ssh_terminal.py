#!/usr/bin/env python3
"""
DSPilot SSH Terminal Manager 사용 예제 및 데모
"""
from pathlib import Path

# 예제 연결 설정을 app.config에 추가하는 함수
def create_demo_config():
    """데모용 설정 파일 생성"""
    config_path = Path(__file__).parent / "app.config"
    
    # 기본 설정이 없다면 생성
    if not config_path.exists():
        demo_config = """[DEFAULT]
# DSPilot SSH Terminal Manager 설정

[ssh]
# SSH 연결 설정 (JSON 형태)
connections = []

[ui]
# UI 설정
theme = default
font_size = 10
auto_save = true

[terminal]
# 터미널 기본 설정
default_encoding = utf-8
default_terminal_type = xterm-256color
scrollback_lines = 1000

[security]
# 보안 설정
save_passwords = false
auto_connect = false
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(demo_config)
        
        print(f"데모 설정 파일 생성: {config_path}")
    else:
        print(f"기존 설정 파일 사용: {config_path}")

def main():
    """데모 실행"""
    print("DSPilot SSH Terminal Manager 데모")
    print("=" * 50)
    
    # 데모 설정 생성
    create_demo_config()
    
    print("\n📋 주요 기능:")
    print("1. 멀티탭 SSH 터미널")
    print("2. 연결 정보 저장 및 관리") 
    print("3. 다양한 인증 방법 지원")
    print("4. 제품 수준 터미널 에뮬레이션")
    print("5. 현대적인 PySide6 GUI")
    
    print("\n🚀 사용 방법:")
    print("1. 'python run_ssh_terminal.py' 실행")
    print("2. 좌측 연결 관리자에서 '새 연결' 클릭")
    print("3. SSH 서버 정보 입력")
    print("4. '연결' 버튼으로 터미널 세션 시작")
    
    print("\n⌨️  키보드 단축키:")
    print("- Ctrl+N: 새 연결")
    print("- Ctrl+C: 복사")
    print("- Ctrl+V: 붙여넣기")
    print("- F11: 전체화면")
    print("- Ctrl+Q: 종료")
    
    print("\n💡 팁:")
    print("- 연결 정보는 자동으로 저장됩니다")
    print("- 비밀번호는 보안상 저장되지 않습니다")
    print("- 여러 탭을 동시에 사용할 수 있습니다")
    print("- 터미널 크기는 자동으로 조정됩니다")
    
    print(f"\n📁 설정 파일 위치: {Path.cwd() / 'app.config'}")
    print(f"📚 문서: {Path.cwd() / 'dspilot_shell' / 'README.md'}")
    
    print("\n" + "=" * 50)
    print("데모 준비 완료! run_ssh_terminal.py를 실행하세요.")

if __name__ == "__main__":
    main()
