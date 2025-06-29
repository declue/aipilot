#!/usr/bin/env python3
"""
DSPilot CLI 사용자 상호작용 관리 모듈
===================================

`InteractionManager` 는 CLI 애플리케이션과 **사용자 간 IO** 를 추상화합니다.

주요 책임
---------
1. 입력 수집 (get_user_input, get_new_request)
2. 확인/선택 프롬프트 처리 (get_user_confirmation, get_continue_confirmation)
3. **Full-Auto 모드** 지원 – 무인 실행 시 사용자 상호작용을 무시하고 자동 진행

상태 머신
----------
```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle -->|user input| AwaitConfirm
    AwaitConfirm -->|y| Proceed
    AwaitConfirm -->|s| Skip
    AwaitConfirm -->|m| Modify
    AwaitConfirm -->|n| Cancel
    Proceed --> Idle
    Skip --> Idle
    Modify --> Idle
    Cancel --> Idle
```

사용 예시
---------
```python
im = InteractionManager(output_manager, full_auto_mode=False)
choice = im.get_user_confirmation("파일 삭제할까요?", "delete_file", {"path": "foo.txt"})
if choice is UserChoiceType.PROCEED:
    delete_file("foo.txt")
```

테스트 전략
-----------
- `monkeypatch` 로 `builtins.input` 을 고정하여 다양한 키 입력 시나리오 검증
- Full-Auto 모드는 입력 없이 항상 True/PROCEED 를 반환하는지 확인
"""

from typing import Any, Dict

from dspilot_cli.constants import UserChoiceType
from dspilot_cli.output_manager import OutputManager


class InteractionManager:
    """사용자 상호작용 관리를 담당하는 클래스"""

    def __init__(self, output_manager: OutputManager, full_auto_mode: bool = False) -> None:
        """
        상호작용 관리자 초기화

        Args:
            output_manager: 출력 관리자
            full_auto_mode: 전체 자동 모드 여부
        """
        self.output_manager = output_manager
        self.full_auto_mode = full_auto_mode

    def get_user_confirmation(self, message: str, tool_name: str, arguments: Dict[str, Any]) -> UserChoiceType:
        """
        사용자 확인 받기

        Args:
            message: 확인 메시지
            tool_name: 도구명
            arguments: 도구 매개변수

        Returns:
            사용자 선택
        """
        # full-auto 모드에서는 자동으로 진행
        if self.full_auto_mode:
            return UserChoiceType.PROCEED

        self.output_manager.print_user_confirmation(
            message, tool_name, arguments)

        while True:
            choice = input("선택 (y/s/m/n): ").strip().lower()

            if choice in ['y', 'yes']:
                return UserChoiceType.PROCEED
            elif choice in ['s', 'skip']:
                return UserChoiceType.SKIP
            elif choice in ['m', 'modify']:
                return UserChoiceType.MODIFY
            elif choice in ['n', 'no']:
                return UserChoiceType.CANCEL
            else:
                self.output_manager.print_invalid_choice()

    def get_user_input(self, prompt: str = "👤 You: ") -> str:
        """
        사용자 입력 받기

        Args:
            prompt: 입력 프롬프트

        Returns:
            사용자 입력
        """
        return input(prompt).strip()

    def get_continue_confirmation(self) -> bool:
        """
        계속 진행할지 확인

        Returns:
            계속 진행 여부
        """
        if self.full_auto_mode:
            return True

        self.output_manager.print_continue_prompt()
        choice = input().strip().lower()
        return choice == 'y'

    def get_new_request(self) -> str:
        """
        새로운 요청 입력 받기

        Returns:
            새로운 요청
        """
        return input("새로운 요청을 입력하세요: ").strip()

    def set_full_auto_mode(self, enabled: bool) -> None:
        """
        전체 자동 모드 설정

        Args:
            enabled: 자동 모드 활성화 여부
        """
        self.full_auto_mode = enabled
