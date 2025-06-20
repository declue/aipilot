import importlib
import sys

# 테스트 패키지와 실제 프로젝트 패키지(application)가 이름 충돌을 일으키지 않도록
# 실제 프로젝트의 application 패키지를 sys.modules 에 등록합니다.
# 이를 통해 테스트 모듈 내부에서 `from application ...` 임포트가 정상 동작합니다.
if 'application' not in sys.modules:
    sys.modules['application'] = importlib.import_module('application')
