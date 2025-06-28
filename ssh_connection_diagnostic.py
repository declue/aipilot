#!/usr/bin/env python3
"""
SSH 연결 진단 도구
비밀번호가 맞는데도 인증 실패하는 경우 원인을 찾기 위한 도구
"""
import sys
import socket
import logging

try:
    import paramiko
except ImportError:
    print("❌ paramiko 라이브러리가 필요합니다: pip install paramiko")
    sys.exit(1)

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # paramiko 디버그 로깅 활성화
    paramiko_logger = logging.getLogger("paramiko")
    paramiko_logger.setLevel(logging.DEBUG)

def test_port_connection(host, port):
    """포트 연결 테스트"""
    print(f"\n🔌 포트 연결 테스트: {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ 포트 연결 성공")
            return True
        else:
            print(f"❌ 포트 연결 실패 (코드: {result})")
            return False
    except Exception as e:
        print(f"❌ 포트 연결 오류: {e}")
        return False

def get_supported_auth_methods(host, port, username):
    """서버가 지원하는 인증 방법 확인"""
    print(f"\n🔍 지원 인증 방법 확인: {username}@{host}:{port}")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 연결 시도
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password="invalid_password",  # 의도적으로 잘못된 비밀번호
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        
    except paramiko.AuthenticationException:
        # 예상된 인증 실패
        transport = ssh.get_transport()
        if transport:
            try:
                # auth_none을 통해 지원 방법 확인
                auth_methods = transport.auth_none(username)
                if auth_methods is None:
                    print("🎉 인증 없이 로그인 가능!")
                    return ["none"]
                else:
                    print(f"✅ 지원 인증 방법: {auth_methods}")
                    return auth_methods
            except paramiko.BadAuthenticationType as e:
                # 정상적인 응답
                methods_str = str(e).split(': ')[-1] if ': ' in str(e) else str(e)
                # 파싱 개선: 대괄호와 따옴표 제거
                methods_str = methods_str.strip("[]'\"")
                auth_methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
                print(f"✅ 지원 인증 방법: {auth_methods}")
                return auth_methods
            except Exception as e:
                print(f"⚠️ 인증 방법 확인 오류: {e}")
                return []
        else:
            print("❌ Transport 객체를 가져올 수 없음")
            return []
    except Exception as e:
        print(f"❌ 서버 연결 오류: {e}")
        return []
    finally:
        ssh.close()

def test_password_auth(host, port, username, password):
    """비밀번호 인증 테스트"""
    print(f"\n🔐 비밀번호 인증 테스트: {username}@{host}:{port}")
    print(f"비밀번호 길이: {len(password)}자")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 연결 시도
        print("연결 중...")
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,  # SSH 에이전트 비활성화
            look_for_keys=False  # 키 파일 검색 비활성화
        )
        
        print("✅ 비밀번호 인증 성공!")
        
        # 간단한 명령 실행 테스트
        stdin, stdout, stderr = ssh.exec_command('whoami')
        result = stdout.read().decode().strip()
        print(f"✅ 명령 실행 테스트 성공: whoami = {result}")
        
        return True
        
    except paramiko.AuthenticationException as e:
        print(f"❌ 인증 실패: {e}")
        print("\n🔍 가능한 원인:")
        print("  1. 비밀번호가 틀림")
        print("  2. 서버에서 PasswordAuthentication이 비활성화됨")
        print("  3. 사용자 계정이 SSH 로그인 불가")
        print("  4. 서버의 보안 정책으로 차단됨")
        return False
        
    except paramiko.SSHException as e:
        print(f"❌ SSH 오류: {e}")
        return False
        
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return False
        
    finally:
        ssh.close()

def test_manual_auth(host, port, username, password):
    """수동 인증 과정 테스트 (더 상세한 진단)"""
    print(f"\n🔬 수동 인증 과정 진단: {username}@{host}:{port}")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 기본 연결 (인증 없이)
        print("1. Transport 연결...")
        ssh.connect(
            hostname=host,
            port=port,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        
        transport = ssh.get_transport()
        if not transport:
            print("❌ Transport 객체 없음")
            return False
            
        print("✅ Transport 연결 성공")
        
        # 지원 인증 방법 확인
        print("2. 인증 방법 확인...")
        try:
            auth_result = transport.auth_none(username)
            if auth_result is None:
                print("🎉 인증 없이 로그인 성공!")
                return True
            print(f"지원 방법: {auth_result}")
        except paramiko.BadAuthenticationType as e:
            methods_str = str(e).split(': ')[-1] if ': ' in str(e) else str(e)
            auth_methods = [m.strip() for m in methods_str.split(',')]
            print(f"지원 방법: {auth_methods}")
            
            if 'password' not in auth_methods:
                print("❌ 서버가 비밀번호 인증을 지원하지 않음!")
                print("서버 설정 확인 필요: /etc/ssh/sshd_config의 PasswordAuthentication")
                return False
        
        # 비밀번호 인증 시도
        print("3. 비밀번호 인증...")
        try:
            success = transport.auth_password(username, password)
            if success:
                print("✅ 비밀번호 인증 성공!")
                return True
            else:
                print("❌ 비밀번호 인증 실패")
                return False
        except paramiko.AuthenticationException as e:
            print(f"❌ 비밀번호 인증 예외: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 수동 인증 오류: {e}")
        return False
        
    finally:
        ssh.close()

def main():
    """메인 함수"""
    print("DSPilot SSH 연결 진단 도구")
    print("=" * 50)
    
    # 사용자 입력
    host = input("SSH 호스트: ").strip()
    if not host:
        print("❌ 호스트를 입력해주세요")
        return
        
    port_input = input("SSH 포트 (기본 22): ").strip()
    port = int(port_input) if port_input else 22
    
    username = input("사용자명: ").strip()
    if not username:
        print("❌ 사용자명을 입력해주세요")
        return
        
    password = input("비밀번호: ").strip()
    if not password:
        print("❌ 비밀번호를 입력해주세요")
        return
    
    print("\n" + "=" * 50)
    print(f"연결 정보: {username}@{host}:{port}")
    print("=" * 50)
    
    # 디버그 로깅 활성화
    verbose = input("\n상세 로그 출력? (y/N): ").strip().lower() == 'y'
    if verbose:
        setup_logging()
    
    # 진단 시작
    success = False
    
    # 1. 포트 연결 테스트
    if not test_port_connection(host, port):
        print("\n❌ 포트 연결 실패로 진단 중단")
        return
    
    # 2. 지원 인증 방법 확인
    auth_methods = get_supported_auth_methods(host, port, username)
    if not auth_methods:
        print("\n⚠️ 지원 인증 방법을 확인할 수 없음")
    elif 'password' not in auth_methods:
        print(f"\n❌ 서버가 비밀번호 인증을 지원하지 않음: {auth_methods}")
        print("서버 관리자에게 문의하거나 키 기반 인증 사용을 고려하세요")
        return
    
    # 3. 비밀번호 인증 테스트
    success = test_password_auth(host, port, username, password)
    
    # 4. 실패시 수동 진단
    if not success:
        print("\n기본 인증 실패, 수동 진단 시작...")
        success = test_manual_auth(host, port, username, password)
    
    # 결과
    print("\n" + "=" * 50)
    if success:
        print("🎉 SSH 연결 진단 완료: 정상")
        print("DSPilot SSH Terminal에서도 정상 작동할 것입니다")
    else:
        print("❌ SSH 연결 진단 완료: 문제 발견")
        print("\n해결 방법:")
        print("1. 터미널에서 직접 테스트: ssh {}@{}".format(username, host))
        print("2. 서버 관리자에게 SSH 설정 확인 요청")
        print("3. 다른 인증 방법 (키 기반) 고려")
    print("=" * 50)

if __name__ == "__main__":
    main()
