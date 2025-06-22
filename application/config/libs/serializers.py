"""
설정 파일 직렬화기 구현

다양한 설정 파일 형식(INI, JSON, YAML, TOML)을 지원합니다.
"""

import configparser
import json
import logging

import tomli
import tomli_w
import yaml

from application.config.libs.interfaces import ConfigDict, ConfigType, IConfigSerializer

logger = logging.getLogger(__name__)


class JSONConfigSerializer(IConfigSerializer):
    """JSON 설정 파일 직렬화기"""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def serialize(self, config_data: ConfigDict) -> str:
        """JSON으로 직렬화"""
        try:
            return json.dumps(config_data, indent=self.indent, ensure_ascii=self.ensure_ascii)
        except Exception as e:
            logger.error("JSON 직렬화 실패: %s", e)
            raise

    def deserialize(self, config_text: str) -> ConfigDict:
        """JSON에서 역직렬화"""
        try:
            return json.loads(config_text)
        except Exception as e:
            logger.error("JSON 역직렬화 실패: %s", e)
            raise


class INIConfigSerializer(IConfigSerializer):
    """INI 설정 파일 직렬화기"""

    def __init__(self, interpolation=None):
        self.interpolation = interpolation

    def serialize(self, config_data: ConfigDict) -> str:
        """INI로 직렬화"""
        try:
            config = configparser.ConfigParser(interpolation=self.interpolation)

            # ConfigDict를 ConfigParser 형식으로 변환
            for section_name, section_data in config_data.items():
                if isinstance(section_data, dict):
                    config.add_section(str(section_name))
                    for key, value in section_data.items():
                        config.set(str(section_name), str(key), str(value))
                else:
                    # 최상위 레벨 값들은 DEFAULT 섹션에 저장
                    if not config.has_section("DEFAULT"):
                        config.add_section("DEFAULT")
                    config.set("DEFAULT", str(section_name), str(section_data))

            # StringIO로 변환
            from io import StringIO

            string_io = StringIO()
            config.write(string_io)
            return string_io.getvalue()
        except Exception as e:
            logger.error("INI 직렬화 실패: %s", e)
            raise

    def deserialize(self, config_text: str) -> ConfigDict:
        """INI에서 역직렬화"""
        try:
            config = configparser.ConfigParser(interpolation=self.interpolation)
            config.read_string(config_text)

            result = {}
            for section_name in config.sections():
                result[section_name] = dict(config[section_name])

            # DEFAULT 섹션 처리
            if config.defaults():
                result["DEFAULT"] = dict(config.defaults())

            return result
        except Exception as e:
            logger.error("INI 역직렬화 실패: %s", e)
            raise


class YAMLConfigSerializer(IConfigSerializer):
    """YAML 설정 파일 직렬화기"""

    def __init__(self, default_flow_style: bool = False):
        self.default_flow_style = default_flow_style
        try:

            self.yaml = yaml
        except ImportError:
            raise ImportError("YAML 지원을 위해 PyYAML 패키지가 필요합니다: pip install PyYAML")

    def serialize(self, config_data: ConfigDict) -> str:
        """YAML로 직렬화"""
        try:
            return self.yaml.dump(
                config_data, default_flow_style=self.default_flow_style, allow_unicode=True
            )
        except Exception as e:
            logger.error("YAML 직렬화 실패: %s", e)
            raise

    def deserialize(self, config_text: str) -> ConfigDict:
        """YAML에서 역직렬화"""
        try:
            return self.yaml.safe_load(config_text) or {}
        except Exception as e:
            logger.error("YAML 역직렬화 실패: %s", e)
            raise


class TOMLConfigSerializer(IConfigSerializer):
    """TOML 설정 파일 직렬화기"""

    def __init__(self):
        try:

            self.tomli = tomli
            self.tomli_w = tomli_w
        except ImportError:
            raise ImportError(
                "TOML 지원을 위해 tomli, tomli-w 패키지가 필요합니다: pip install tomli tomli-w"
            )

    def serialize(self, config_data: ConfigDict) -> str:
        """TOML로 직렬화"""
        try:
            return self.tomli_w.dumps(config_data)
        except Exception as e:
            logger.error("TOML 직렬화 실패: %s", e)
            raise

    def deserialize(self, config_text: str) -> ConfigDict:
        """TOML에서 역직렬화"""
        try:
            return self.tomli.loads(config_text)
        except Exception as e:
            logger.error("TOML 역직렬화 실패: %s", e)
            raise


# 직렬화기 팩토리
class SerializerFactory:
    """설정 직렬화기 팩토리"""

    _serializers = {
        ConfigType.JSON: JSONConfigSerializer,
        ConfigType.INI: INIConfigSerializer,
        ConfigType.YAML: YAMLConfigSerializer,
        ConfigType.TOML: TOMLConfigSerializer,
    }

    @classmethod
    def create_serializer(cls, config_type: ConfigType, **kwargs) -> IConfigSerializer:
        """설정 타입에 맞는 직렬화기 생성

        Args:
            config_type: 설정 파일 타입
            **kwargs: 직렬화기별 추가 옵션

        Returns:
            직렬화기 인스턴스

        Raises:
            ValueError: 지원하지 않는 설정 타입인 경우
        """
        if config_type not in cls._serializers:
            raise ValueError(f"지원하지 않는 설정 타입: {config_type}")

        serializer_class = cls._serializers[config_type]
        return serializer_class(**kwargs)

    @classmethod
    def get_supported_types(cls) -> list[ConfigType]:
        """지원되는 설정 타입 목록 반환"""
        return list(cls._serializers.keys())

    @classmethod
    def register_serializer(cls, config_type: ConfigType, serializer_class: type) -> None:
        """새로운 직렬화기 등록

        Args:
            config_type: 설정 파일 타입
            serializer_class: 직렬화기 클래스
        """
        cls._serializers[config_type] = serializer_class
        logger.info("새로운 직렬화기 등록: %s -> %s", config_type, serializer_class.__name__)


# 편의 함수들
def serialize_config(config_data: ConfigDict, config_type: ConfigType, **kwargs) -> str:
    """설정 데이터를 지정된 형식으로 직렬화"""
    serializer = SerializerFactory.create_serializer(config_type, **kwargs)
    return serializer.serialize(config_data)


def deserialize_config(config_text: str, config_type: ConfigType, **kwargs) -> ConfigDict:
    """지정된 형식의 설정 텍스트를 역직렬화"""
    serializer = SerializerFactory.create_serializer(config_type, **kwargs)
    return serializer.deserialize(config_text)
