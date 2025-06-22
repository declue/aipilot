import json
import os
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
import pytest

from application.config.apps.managers.llm_profile_manager import LLMProfileManager


@pytest.fixture
def temp_profiles_file(tmp_path: Path) -> str:
    """임시 프로필 파일 경로 반환"""
    return str(tmp_path / "test_llm_profiles.json")


@pytest.fixture
def mock_profile_manager(temp_profiles_file: str) -> LLMProfileManager:
    """Mock을 사용한 LLMProfileManager 인스턴스"""
    return LLMProfileManager(temp_profiles_file)


class TestLLMProfileManager:
    """LLMProfileManager 테스트 클래스"""

    def test_init_creates_default_profiles_when_file_not_exists(self, temp_profiles_file: str):
        """파일이 없을 때 기본 프로필이 생성되는지 테스트"""
        manager = LLMProfileManager(temp_profiles_file)
        
        profiles = manager.get_llm_profiles()
        assert "default" in profiles
        assert "openai" in profiles
        assert manager.get_current_profile_name() == "default"

    def test_load_existing_profiles(self, temp_profiles_file: str):
        """기존 프로필 파일을 로드하는 테스트"""
        # 기존 프로필 파일 생성
        test_data = {
            "profiles": {
                "test_profile": {
                    "name": "테스트 프로필",
                    "api_key": "test-key",
                    "base_url": "http://test.com",
                    "model": "test-model",
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "top_k": 10,
                }
            },
            "current_profile": "test_profile"
        }
        
        with open(temp_profiles_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
        
        manager = LLMProfileManager(temp_profiles_file)
        profiles = manager.get_llm_profiles()
        
        assert "test_profile" in profiles
        assert manager.get_current_profile_name() == "test_profile"
        assert profiles["test_profile"]["name"] == "테스트 프로필"

    def test_create_llm_profile_success(self, mock_profile_manager: LLMProfileManager):
        """LLM 프로필 생성 성공 테스트"""
        profile_config = {
            "name": "새 프로필",
            "api_key": "new-key",
            "base_url": "http://new.com",
            "model": "new-model",
            "temperature": 0.8,
            "max_tokens": 2000,
            "top_k": 20,
        }
        
        mock_profile_manager.create_llm_profile("new_profile", profile_config)
        profiles = mock_profile_manager.get_llm_profiles()
        
        assert "new_profile" in profiles
        assert profiles["new_profile"]["name"] == "새 프로필"

    def test_create_llm_profile_duplicate_fails(self, mock_profile_manager: LLMProfileManager):
        """중복 프로필 생성 실패 테스트"""
        profile_config = {
            "name": "중복 프로필",
            "api_key": "dup-key",
            "base_url": "http://dup.com",
            "model": "dup-model",
            "temperature": 0.5,
            "max_tokens": 1000,
            "top_k": 10,
        }
        
        # 첫 번째 생성은 성공
        mock_profile_manager.create_llm_profile("dup_profile", profile_config)
        
        # 두 번째 생성은 실패해야 함
        with pytest.raises(ValueError, match="프로필 'dup_profile'이 이미 존재합니다"):
            mock_profile_manager.create_llm_profile("dup_profile", profile_config)

    def test_create_llm_profile_missing_required_field_fails(self, mock_profile_manager: LLMProfileManager):
        """필수 필드 누락 시 프로필 생성 실패 테스트"""
        incomplete_config = {
            "name": "불완전 프로필",
            "api_key": "incomplete-key",
            # base_url 누락
        }
        
        with pytest.raises(ValueError, match="필수 필드 'base_url'가 없습니다"):
            mock_profile_manager.create_llm_profile("incomplete_profile", incomplete_config)

    def test_update_llm_profile_success(self, mock_profile_manager: LLMProfileManager):
        """LLM 프로필 업데이트 성공 테스트"""
        # 기본 프로필 수정
        update_config = {
            "model": "updated-model",
            "temperature": 0.9,
        }
        
        mock_profile_manager.update_llm_profile("default", update_config)
        profiles = mock_profile_manager.get_llm_profiles()
        
        assert profiles["default"]["model"] == "updated-model"
        assert profiles["default"]["temperature"] == 0.9

    def test_update_llm_profile_not_exists_fails(self, mock_profile_manager: LLMProfileManager):
        """존재하지 않는 프로필 업데이트 실패 테스트"""
        update_config = {"model": "new-model"}
        
        with pytest.raises(ValueError, match="프로필 'nonexistent'을 찾을 수 없습니다"):
            mock_profile_manager.update_llm_profile("nonexistent", update_config)

    def test_delete_llm_profile_success(self, mock_profile_manager: LLMProfileManager):
        """LLM 프로필 삭제 성공 테스트"""
        # openai 프로필 삭제
        mock_profile_manager.delete_llm_profile("openai")
        profiles = mock_profile_manager.get_llm_profiles()
        
        assert "openai" not in profiles
        assert "default" in profiles  # default는 유지

    def test_delete_default_profile_fails(self, mock_profile_manager: LLMProfileManager):
        """기본 프로필 삭제 실패 테스트"""
        with pytest.raises(ValueError, match="'default' 프로필은 삭제할 수 없습니다"):
            mock_profile_manager.delete_llm_profile("default")

    def test_delete_current_profile_switches_to_default(self, mock_profile_manager: LLMProfileManager):
        """현재 프로필 삭제 시 기본 프로필로 전환 테스트"""
        # openai를 현재 프로필로 설정
        mock_profile_manager.set_current_profile("openai")
        assert mock_profile_manager.get_current_profile_name() == "openai"
        
        # openai 프로필 삭제
        mock_profile_manager.delete_llm_profile("openai")
        
        # 현재 프로필이 default로 변경되었는지 확인
        assert mock_profile_manager.get_current_profile_name() == "default"

    def test_set_current_profile_success(self, mock_profile_manager: LLMProfileManager):
        """현재 프로필 설정 성공 테스트"""
        mock_profile_manager.set_current_profile("openai")
        assert mock_profile_manager.get_current_profile_name() == "openai"

    def test_set_current_profile_not_exists_fails(self, mock_profile_manager: LLMProfileManager):
        """존재하지 않는 프로필 설정 실패 테스트"""
        with pytest.raises(ValueError, match="프로필 'nonexistent'을 찾을 수 없습니다"):
            mock_profile_manager.set_current_profile("nonexistent")

    def test_get_current_profile(self, mock_profile_manager: LLMProfileManager):
        """현재 프로필 정보 반환 테스트"""
        current_profile = mock_profile_manager.get_current_profile()
        assert current_profile["name"] == "기본 프로필"
        assert current_profile["model"] == "llama3.2"

    def test_profile_exists(self, mock_profile_manager: LLMProfileManager):
        """프로필 존재 여부 확인 테스트"""
        assert mock_profile_manager.profile_exists("default") is True
        assert mock_profile_manager.profile_exists("openai") is True
        assert mock_profile_manager.profile_exists("nonexistent") is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_llm_profiles_called(self, mock_json_dump: Mock, mock_file: Mock, mock_profile_manager: LLMProfileManager):
        """프로필 저장 메서드 호출 테스트"""
        mock_profile_manager.save_llm_profiles()
        
        # 파일이 쓰기 모드로 열렸는지 확인
        mock_file.assert_called_once_with(mock_profile_manager.llm_profiles_file, "w", encoding="utf-8")
        
        # JSON 덤프가 호출되었는지 확인
        mock_json_dump.assert_called_once()

    @patch("os.path.exists")
    def test_load_llm_profiles_file_not_exists(self, mock_exists: Mock, temp_profiles_file: str):
        """프로필 파일이 없을 때 기본 프로필 생성 테스트"""
        mock_exists.return_value = False
        
        with patch.object(LLMProfileManager, 'create_default_llm_profiles') as mock_create_default:
            manager = LLMProfileManager(temp_profiles_file)
            mock_create_default.assert_called_once()

    @patch("builtins.open", side_effect=Exception("파일 읽기 오류"))
    @patch("os.path.exists", return_value=True)
    def test_load_llm_profiles_file_error(self, mock_exists: Mock, mock_file: Mock, temp_profiles_file: str):
        """프로필 파일 읽기 오류 시 기본 프로필 생성 테스트"""
        with patch.object(LLMProfileManager, 'create_default_llm_profiles') as mock_create_default:
            manager = LLMProfileManager(temp_profiles_file)
            mock_create_default.assert_called_once() 