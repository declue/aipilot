#!/usr/bin/env python3
"""
SSH 연결 문제 진단 도구 (단순화 버전)
"""
import sys

try:
    import paramiko
except ImportError:
    print("❌ paramiko 라이브러리가 필요합니다: pip install paramiko")
    sys.exit(1)

def test_basic_ssh_connection():
    """기본 SSH 연결 테스트"""
    host = "202.202.202.117"
    port = 22
    username = "vtopia"
    password = "vpfl06jira"
    
    print(f"기본 SSH 연결 테스트: {username}@{host}:{port}")
    print("=" * 50)
    
    try:
        # 기본 SSH 클라이언트 생성
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("1. SSH 클라이언트 생성 완료")
        
        # 연결 시도
        print("2. 연결 시도 중...")
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        print("✅ SSH 연결 성공!")
        
        # 간단한 명령 실행
        print("3. 명령 실행 테스트...")
        stdin, stdout, stderr = ssh.exec_command('echo "Hello SSH"')
        result = stdout.read().decode().strip()
        print(f"✅ 명령 실행 성공: {result}")
        
        # 기본 터미널 채널 생성 테스트
        print("4. 터미널 채널 생성 테스트...")
        try:
            channel = ssh.invoke_shell(term='xterm', width=80, height=24)
            print("✅ 터미널 채널 생성 성공!")
            
            # 채널에서 약간의 데이터 읽기
            import time
            time.sleep(0.5)
            
            if channel.recv_ready():
                data = channel.recv(1024)
                print(f"✅ 초기 데이터 수신: {len(data)} bytes")
            
            channel.close()
            print("✅ 터미널 채널 정상 종료")
            
        except Exception as channel_error:
            print(f"❌ 터미널 채널 생성 실패: {channel_error}")
            return False
        
        ssh.close()
        print("✅ SSH 연결 정상 종료")
        return True
        
    except paramiko.AuthenticationException as e:
        print(f"❌ 인증 실패: {e}")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return False

def test_terminal_types():
    """다양한 터미널 타입 테스트"""
    host = "202.202.202.117"
    port = 22
    username = "vtopia"
    password = "vpfl06jira"
    
    terminal_types = ['xterm', 'xterm-256color', 'vt100', 'linux', 'ansi']
    
    print("\n터미널 타입 호환성 테스트:")
    print("=" * 50)
    
    for term_type in terminal_types:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=5,
                allow_agent=False,
                look_for_keys=False
            )
            
            channel = ssh.invoke_shell(term=term_type, width=80, height=24)
            print(f"✅ {term_type}: 성공")
            
            channel.close()
            ssh.close()
            
        except Exception as e:
            print(f"❌ {term_type}: 실패 - {e}")

def main():
    """메인 함수"""
    print("SSH 연결 문제 진단 도구")
    print("=" * 50)
    
    # 기본 연결 테스트
    success = test_basic_ssh_connection()
    
    if success:
        # 터미널 타입 테스트
        test_terminal_types()
        
        print("\n" + "=" * 50)
        print("✅ SSH 연결 진단 완료: 정상")
        print("DSPilot SSH Terminal에서도 정상 작동할 것입니다.")
    else:
        print("\n" + "=" * 50)
        print("❌ SSH 연결 진단 완료: 문제 발견")
        print("기본 SSH 연결에 문제가 있습니다.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
