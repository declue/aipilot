#!/usr/bin/env python3
"""
DSPilot CLI 사용자 상호작용 관리 모듈
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
