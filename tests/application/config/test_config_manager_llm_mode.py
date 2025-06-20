"""
ConfigManager LLM 모드 테스트 (환경 독립적)
"""
import configparser
from typing import Optional


class MockConfigManager:
    """환경 독립적인 ConfigManager Mock"""
    
    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self._create_default_config()
    
    def _create_default_config(self) -> None:
        """기본 설정 생성"""
        self.config["LLM"] = {
            "mode": "basic",
            "workflow": "basic_chat",
            "show_cot": "false",
        }
    
    def get_config_value(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """설정값 가져오기"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except Exception:
            return fallback
    
    def set_config_value(self, section: str, key: str, value: str) -> None:
        """설정값 저장"""
        if section not in self.config:
            self.config.add_section(section)
        self.config[section][key] = value


def test_llm_mode_basic() -> None:
    """기본 LLM 모드 테스트"""
    print("=== 기본 LLM 모드 테스트 ===")
    
    manager = MockConfigManager()
    
    # 기본 모드 확인
    mode = manager.get_config_value("LLM", "mode", "basic")
    assert mode == "basic"
    print("✅ 기본 모드 확인")


def test_llm_mode_workflow() -> None:
    """워크플로우 모드 테스트"""
    print("=== 워크플로우 모드 테스트 ===")
    
    manager = MockConfigManager()
    
    # 워크플로우 모드 설정
    manager.set_config_value("LLM", "mode", "workflow")
    manager.set_config_value("LLM", "workflow", "test_workflow")
    
    assert manager.get_config_value("LLM", "mode") == "workflow"
    assert manager.get_config_value("LLM", "workflow") == "test_workflow"
    print("✅ 워크플로우 모드 설정 성공")


if __name__ == "__main__":
    print("🚀 ConfigManager LLM 모드 테스트 시작")
    
    try:
        test_llm_mode_basic()
        test_llm_mode_workflow()
        
        print("\n🎉 모든 테스트 통과!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        raise