#!/usr/bin/env python3
"""
Remote Desktop MCP 서버 테스트
"""

import base64
import io
import os

# 테스트용으로 remote_desktop 모듈 임포트
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRemoteDesktop(unittest.TestCase):
    """Remote Desktop 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 테스트용 이미지 생성
        self.test_image = Image.new('RGB', (100, 100), color='red')
        self.test_image_buffer = io.BytesIO()
        self.test_image.save(self.test_image_buffer, format='PNG')
        self.test_image_buffer.seek(0)
        self.test_image_base64 = base64.b64encode(self.test_image_buffer.getvalue()).decode('utf-8')
    
    @patch('pyautogui.screenshot')
    @patch('pyautogui.size')
    def test_capture_full_screen(self, mock_size, mock_screenshot):
        """전체 화면 캡처 테스트"""
        from tools.remote_desktop import capture_full_screen

        # Mock 설정
        mock_size.return_value = Mock(width=1920, height=1080)
        mock_screenshot.return_value = self.test_image
        
        # 함수 실행
        result = capture_full_screen()
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertIn('image', result)
        self.assertEqual(result['format'], 'PNG')
        self.assertEqual(result['width'], 1920)
        self.assertEqual(result['height'], 1080)
        
        # base64 이미지 디코딩 테스트
        image_data = base64.b64decode(result['image'])
        decoded_image = Image.open(io.BytesIO(image_data))
        self.assertIsNotNone(decoded_image)
    
    @patch('pyautogui.screenshot')
    @patch('pyautogui.size')
    def test_capture_region(self, mock_size, mock_screenshot):
        """영역 캡처 테스트"""
        from tools.remote_desktop import capture_region

        # Mock 설정
        mock_size.return_value = Mock(width=1920, height=1080)
        mock_screenshot.return_value = self.test_image
        
        # 유효한 영역 테스트
        result = capture_region(100, 100, 500, 300)
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertEqual(result['x'], 100)
        self.assertEqual(result['y'], 100)
        self.assertEqual(result['width'], 500)
        self.assertEqual(result['height'], 300)
        
        # 무효한 영역 테스트
        result = capture_region(-1, -1, 2000, 2000)
        self.assertFalse(result['success'])
        self.assertIn('Invalid coordinates', result['error'])
    
    @patch('pyautogui.size')
    @patch('pyautogui.position')
    def test_get_screen_info(self, mock_position, mock_size):
        """화면 정보 조회 테스트"""
        from tools.remote_desktop import get_screen_info

        # Mock 설정
        mock_size.return_value = Mock(width=1920, height=1080)
        mock_position.return_value = Mock(x=500, y=300)
        
        # 함수 실행
        result = get_screen_info()
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertEqual(result['screen_width'], 1920)
        self.assertEqual(result['screen_height'], 1080)
        self.assertEqual(result['mouse_x'], 500)
        self.assertEqual(result['mouse_y'], 300)
    
    @patch('pyautogui.screenshot')
    @patch('os.makedirs')
    @patch('os.path.getsize')
    def test_save_screenshot(self, mock_getsize, mock_makedirs, mock_screenshot):
        """스크린샷 저장 테스트"""
        from tools.remote_desktop import save_screenshot

        # Mock 설정
        mock_screenshot.return_value = self.test_image
        mock_getsize.return_value = 1024
        
        # 임시 디렉토리 사용
        with tempfile.TemporaryDirectory() as temp_dir:
            result = save_screenshot(filename="test.png", folder=temp_dir)
            
            # 결과 검증
            self.assertTrue(result['success'])
            self.assertIn('test.png', result['filename'])
            self.assertEqual(result['folder'], temp_dir)
    
    @patch('pyautogui.screenshot')
    def test_capture_with_annotation(self, mock_screenshot):
        """주석이 있는 캡처 테스트"""
        from tools.remote_desktop import capture_with_annotation

        # Mock 설정
        mock_screenshot.return_value = self.test_image.copy()
        
        # 함수 실행
        result = capture_with_annotation("Test Text", 50, 50, 20)
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertEqual(result['annotation'], "Test Text")
        self.assertEqual(result['annotation_x'], 50)
        self.assertEqual(result['annotation_y'], 50)
        self.assertEqual(result['font_size'], 20)
    
    @patch('pyautogui.locateOnScreen')
    @patch('pyautogui.center')
    @patch('os.path.exists')
    def test_find_element_on_screen(self, mock_exists, mock_center, mock_locate):
        """화면에서 요소 찾기 테스트"""
        from tools.remote_desktop import find_element_on_screen

        # 파일이 존재하지 않는 경우
        mock_exists.return_value = False
        result = find_element_on_screen("nonexistent.png")
        self.assertFalse(result['success'])
        
        # 요소를 찾은 경우
        mock_exists.return_value = True
        mock_locate.return_value = Mock(left=100, top=200, width=50, height=30)
        mock_center.return_value = Mock(x=125, y=215)
        
        result = find_element_on_screen("test.png", 0.8)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['found'])
        self.assertEqual(result['x'], 100)
        self.assertEqual(result['y'], 200)
        self.assertEqual(result['center_x'], 125)
        self.assertEqual(result['center_y'], 215)
        
        # 요소를 찾지 못한 경우
        mock_locate.return_value = None
        result = find_element_on_screen("test.png", 0.8)
        
        self.assertTrue(result['success'])
        self.assertFalse(result['found'])
    
    @patch('pyautogui.screenshot')
    @patch('pyautogui.size')
    @patch('pyautogui.position')
    def test_get_multimodal_analysis_data(self, mock_position, mock_size, mock_screenshot):
        """멀티모달 분석 데이터 준비 테스트"""
        from tools.remote_desktop import get_multimodal_analysis_data

        # Mock 설정
        mock_size.return_value = Mock(width=1920, height=1080)
        mock_position.return_value = Mock(x=500, y=300)
        mock_screenshot.return_value = self.test_image
        
        # 함수 실행
        result = get_multimodal_analysis_data()
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertIn('image', result)
        self.assertIn('context', result)
        self.assertTrue(result['multimodal_ready'])
        
        # 컨텍스트 정보 확인
        context = result['context']
        self.assertEqual(context['capture_type'], 'full_screen')
        self.assertEqual(context['screen_resolution'], '1920x1080')
        self.assertEqual(context['mouse_position'], '(500, 300)')
        self.assertIn('analysis_prompt', context)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_base64_encoding_decoding(self):
        """base64 인코딩/디코딩 테스트"""
        # 테스트 이미지 생성
        original_image = Image.new('RGB', (200, 200), color='blue')
        
        # base64 인코딩
        buffer = io.BytesIO()
        original_image.save(buffer, format='PNG')
        buffer.seek(0)
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # base64 디코딩
        decoded_data = base64.b64decode(encoded)
        decoded_image = Image.open(io.BytesIO(decoded_data))
        
        # 이미지 비교
        self.assertEqual(original_image.size, decoded_image.size)
        self.assertEqual(original_image.mode, decoded_image.mode)
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        from tools.remote_desktop import capture_region

        # 잘못된 파라미터로 테스트
        with patch('pyautogui.size', return_value=Mock(width=100, height=100)):
            result = capture_region(200, 200, 100, 100)
            self.assertFalse(result['success'])
            self.assertIn('error', result)


def run_performance_test():
    """성능 테스트"""
    print("🚀 성능 테스트 실행 중...")
    
    import time

    from tools.remote_desktop import capture_full_screen, get_screen_info

    # 화면 캡처 성능 테스트
    start_time = time.time()
    for i in range(5):
        with patch('pyautogui.screenshot') as mock_screenshot, \
             patch('pyautogui.size') as mock_size:
            
            mock_size.return_value = Mock(width=1920, height=1080)
            mock_screenshot.return_value = Image.new('RGB', (1920, 1080), color='red')
            
            result = capture_full_screen()
            assert result['success'], f"Capture {i+1} failed"
    
    end_time = time.time()
    avg_time = (end_time - start_time) / 5
    
    print(f"  📊 평균 캡처 시간: {avg_time:.3f}초")
    print(f"  📊 초당 캡처 가능 횟수: {1/avg_time:.1f}회")


if __name__ == "__main__":
    print("🧪 Remote Desktop MCP 서버 테스트")
    print("=" * 50)
    
    # 단위 테스트 실행
    print("📋 단위 테스트 실행 중...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 성능 테스트 실행
    run_performance_test()
    
    print("\n✅ 모든 테스트 완료!")
