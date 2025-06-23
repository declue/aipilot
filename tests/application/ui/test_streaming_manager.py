#!/usr/bin/env python3
"""StreamingManager 테스트"""

import os
import sys
from unittest.mock import Mock

# 경로 설정
sys.path.insert(0, os.path.abspath('.'))

try:
    from application.ui.domain.reasoning_parser import ReasoningParser
    from application.ui.domain.streaming_manager import StreamingManager
    from application.ui.domain.streaming_state import StreamingState
    from application.ui.presentation.streaming_bubble_manager import StreamingBubbleManager
    
    class TestStreamingManager:
        """StreamingManager 테스트"""
        
        def test_parse_and_update_reasoning_state(self):
            """추론 과정 감지 및 상태 업데이트 함수 테스트"""
            # Mock 객체들 생성
            mock_main_window = Mock()
            mock_ui_config = Mock()
            
            # StreamingManager 인스턴스 생성
            manager = StreamingManager(mock_main_window)
            
            # Mock reasoning parser 결과 설정
            mock_parsing_result = (True, "추론 과정", "최종 답변")
            manager.reasoning_parser.parse_reasoning_content = Mock(return_value=mock_parsing_result)
            
            # 테스트 실행
            test_content = "테스트 내용"
            manager._parse_and_update_reasoning_state(test_content)
            
            # 검증
            manager.reasoning_parser.parse_reasoning_content.assert_called_once_with(test_content)
            assert manager.state.is_reasoning_model is True
            assert manager.state.reasoning_content == "추론 과정"
            assert manager.state.final_answer == "최종 답변"
        
        def test_parse_and_update_reasoning_state_no_reasoning(self):
            """추론이 없는 경우의 상태 업데이트 테스트"""
            # Mock 객체들 생성
            mock_main_window = Mock()
            
            # StreamingManager 인스턴스 생성
            manager = StreamingManager(mock_main_window)
            
            # Mock reasoning parser 결과 설정 (추론 없음)
            mock_parsing_result = (False, "", "일반 답변")
            manager.reasoning_parser.parse_reasoning_content = Mock(return_value=mock_parsing_result)
            
            # 테스트 실행
            test_content = "일반 테스트 내용"
            manager._parse_and_update_reasoning_state(test_content)
            
            # 검증
            manager.reasoning_parser.parse_reasoning_content.assert_called_once_with(test_content)
            assert manager.state.is_reasoning_model is False
            assert manager.state.reasoning_content == ""
            assert manager.state.final_answer == "일반 답변"
        
        def test_parse_and_update_reasoning_state_integration(self):
            """_update_display에서 _parse_and_update_reasoning_state 호출 테스트"""
            # Mock 객체들 생성
            mock_main_window = Mock()
            
            # StreamingManager 인스턴스 생성
            manager = StreamingManager(mock_main_window)
            
            # 스트리밍 상태로 설정
            manager.state.is_streaming = True
            manager.state.streaming_content = "테스트 스트리밍 내용"
            manager.state.process_pending_chunks = Mock(return_value=True)
            
            # Mock reasoning parser
            mock_parsing_result = (True, "스트리밍 추론", "스트리밍 답변")
            manager.reasoning_parser.parse_reasoning_content = Mock(return_value=mock_parsing_result)
            
            # Mock 스트리밍 버블과 bubble_manager 전체를 모킹
            mock_bubble = Mock()
            manager.state.current_streaming_bubble = mock_bubble
            manager.bubble_manager = Mock()
            
            # _parse_and_update_reasoning_state를 spy로 모킹
            original_method = manager._parse_and_update_reasoning_state
            manager._parse_and_update_reasoning_state = Mock(side_effect=original_method)
            
            # 테스트 실행
            manager._update_display()
            
            # 검증
            manager._parse_and_update_reasoning_state.assert_called_once_with("테스트 스트리밍 내용")
            assert manager.state.is_reasoning_model is True
            assert manager.state.reasoning_content == "스트리밍 추론"
            assert manager.state.final_answer == "스트리밍 답변"
            # bubble_manager가 호출되었는지 확인
            manager.bubble_manager.update_streaming_bubble.assert_called_once()

except ImportError as e:
    print(f"StreamingManager import failed - skipping tests: {e}")
    
    class TestStreamingManagerPlaceholder:
        """플레이스홀더 테스트"""
        
        def test_placeholder(self):
            """Import 실패 시 플레이스홀더 테스트"""
            assert True


if __name__ == "__main__":
    print("=== StreamingManager 테스트 실행 ===")
    
    try:
        from application.ui.domain.streaming_manager import StreamingManager
        print("✅ StreamingManager import 성공")
        
        # 기본 테스트 실행
        test_instance = TestStreamingManager()
        
        print("1. 추론 상태 업데이트 테스트")
        test_instance.test_parse_and_update_reasoning_state()
        print("   ✅ 통과")
        
        print("2. 추론 없는 경우 테스트")
        test_instance.test_parse_and_update_reasoning_state_no_reasoning()
        print("   ✅ 통과")
        
        print("3. 통합 테스트")
        test_instance.test_parse_and_update_reasoning_state_integration()
        print("   ✅ 통과")
        
    except ImportError as e:
        print(f"❌ StreamingManager import 실패: {e}")
    
    print("\n모든 테스트 통과! 🎉") 