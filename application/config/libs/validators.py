"""
설정 검증기 구현

다양한 설정 형태에 대한 검증 로직을 제공합니다.
"""

import logging
import re
from typing import Any, Dict, List

import jsonschema

from application.config.libs.interfaces import ConfigDict, IConfigValidator, ValidationResult

logger = logging.getLogger(__name__)


class SchemaValidator(IConfigValidator):
    """JSON Schema 호환 설정 검증기

    JSON Schema 형식의 스키마를 사용하여 설정을 검증합니다.
    """

    def __init__(self, schema: Dict[str, Any]) -> None:
        """SchemaValidator 생성자

        Args:
            schema: JSON Schema 형식의 검증 스키마
        """
        self.schema = schema

    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """설정 데이터 검증"""
        result = ValidationResult()

        try:
            # JSON Schema 검증 시도

            jsonschema.validate(config_data, self.schema)
        except ImportError:
            # jsonschema 라이브러리가 없으면 기본 검증 수행
            result = self._basic_validate(config_data)
        except Exception as e:
            result.add_error(f"스키마 검증 실패: {str(e)}")

        return result

    def _basic_validate(self, config_data: ConfigDict) -> ValidationResult:
        """기본 검증 (jsonschema 없을 때)"""
        result = ValidationResult()

        # 기본적인 타입과 필수 필드 검증
        if self.schema.get("type") == "object":
            if not isinstance(config_data, dict):
                result.add_error("설정 데이터는 객체여야 합니다")
                return result

            # 필수 필드 확인
            required = self.schema.get("required", [])
            for field in required:
                if field not in config_data:
                    result.add_error(f"필수 필드가 없습니다: {field}")

            # 속성 타입 검증
            properties = self.schema.get("properties", {})
            for field, field_schema in properties.items():
                if field in config_data:
                    field_result = self._validate_field(config_data[field], field_schema, field)
                    if not field_result.is_valid:
                        result.errors.extend(field_result.errors)
                        # 필드 검증 실패 시 전체 결과를 실패로 표시
                        result.is_valid = False

        return result

    def _validate_field(
        self, value: Any, field_schema: Dict[str, Any], field_name: str
    ) -> ValidationResult:
        """개별 필드 검증"""
        result = ValidationResult()

        expected_type = field_schema.get("type")
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                result.add_error(f"필드 '{field_name}'는 문자열이어야 합니다")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                result.add_error(f"필드 '{field_name}'는 숫자여야 합니다")
            elif expected_type == "integer" and not isinstance(value, int):
                result.add_error(f"필드 '{field_name}'는 정수여야 합니다")
            elif expected_type == "boolean" and not isinstance(value, bool):
                result.add_error(f"필드 '{field_name}'는 불린값이어야 합니다")
            elif expected_type == "array" and not isinstance(value, list):
                result.add_error(f"필드 '{field_name}'는 배열이어야 합니다")
            elif expected_type == "object" and not isinstance(value, dict):
                result.add_error(f"필드 '{field_name}'는 객체여야 합니다")

        # 범위 검증
        if isinstance(value, (int, float)):
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            if minimum is not None and value < minimum:
                result.add_error(
                    f"필드 '{field_name}'의 값이 최솟값보다 작습니다: {value} < {minimum}"
                )
            if maximum is not None and value > maximum:
                result.add_error(
                    f"필드 '{field_name}'의 값이 최댓값보다 큽니다: {value} > {maximum}"
                )

        return result


class LLMConfigValidator(IConfigValidator):
    """LLM 설정 검증기"""

    def __init__(self) -> None:
        self.required_fields = {
            "api_key",
            "base_url",
            "model",
            "temperature",
            "max_tokens",
            "top_k",
        }
        self.url_pattern = re.compile(
            r"^https?://"  # http:// 또는 https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # 도메인
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # 포트
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """LLM 설정 검증"""
        result = ValidationResult()

        # 필수 필드 확인
        for field in self.required_fields:
            if field not in config_data:
                result.add_error(f"LLM 필수 필드가 없습니다: {field}")

        # API 키 검증
        if "api_key" in config_data:
            api_key = config_data["api_key"]
            if not api_key or api_key == "your-api-key-here":
                result.add_error("유효한 API 키를 설정해주세요")

        # URL 검증
        if "base_url" in config_data:
            base_url = config_data["base_url"]
            if not self.url_pattern.match(str(base_url)):
                result.add_error(f"잘못된 URL 형식: {base_url}")

        # 온도 검증
        if "temperature" in config_data:
            temp = config_data["temperature"]
            try:
                temp_float = float(temp)
                if not (0.0 <= temp_float <= 2.0):
                    result.add_error(f"temperature는 0.0~2.0 사이여야 합니다: {temp}")
            except (ValueError, TypeError):
                result.add_error(f"temperature는 숫자여야 합니다: {temp}")

        # 토큰 수 검증
        if "max_tokens" in config_data:
            max_tokens = config_data["max_tokens"]
            try:
                tokens_int = int(max_tokens)
                if tokens_int <= 0:
                    result.add_error(f"max_tokens는 양수여야 합니다: {max_tokens}")
            except (ValueError, TypeError):
                result.add_error(f"max_tokens는 정수여야 합니다: {max_tokens}")

        # top_k 검증
        if "top_k" in config_data:
            top_k = config_data["top_k"]
            try:
                top_k_int = int(top_k)
                if top_k_int <= 0:
                    result.add_error(f"top_k는 양수여야 합니다: {top_k}")
            except (ValueError, TypeError):
                result.add_error(f"top_k는 정수여야 합니다: {top_k}")

        return result


class MCPConfigValidator(IConfigValidator):
    """MCP 설정 검증기"""

    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """MCP 설정 검증"""
        result = ValidationResult()

        # 기본 구조 확인
        if "mcpServers" not in config_data:
            result.add_error("mcpServers 섹션이 없습니다")
            return result

        servers = config_data["mcpServers"]
        if not isinstance(servers, dict):
            result.add_error("mcpServers는 객체여야 합니다")
            return result

        # 각 서버 설정 검증
        for server_name, server_config in servers.items():
            if not isinstance(server_config, dict):
                result.add_error(f"서버 설정이 객체가 아닙니다: {server_name}")
                continue

            # 필수 필드 확인
            if "command" not in server_config:
                result.add_error(f"서버 '{server_name}'에 command 필드가 없습니다")

            if "args" in server_config:
                args = server_config["args"]
                if not isinstance(args, list):
                    result.add_error(f"서버 '{server_name}'의 args는 배열이어야 합니다")

        # 기본 서버 검증
        if "defaultServer" in config_data:
            default_server = config_data["defaultServer"]
            if default_server and default_server not in servers:
                result.add_error(f"기본 서버가 존재하지 않습니다: {default_server}")

        return result


class GitHubConfigValidator(IConfigValidator):
    """GitHub 설정 검증기"""

    def __init__(self) -> None:
        self.repo_pattern = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")

    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """GitHub 설정 검증"""
        result = ValidationResult()

        # 저장소 목록 검증
        if "repositories" in config_data:
            repositories = config_data["repositories"]
            if isinstance(repositories, str):
                # 쉼표로 구분된 문자열인 경우
                repo_list = [repo.strip() for repo in repositories.split(",") if repo.strip()]
            elif isinstance(repositories, list):
                repo_list = repositories
            else:
                result.add_error("repositories는 문자열 또는 배열이어야 합니다")
                return result

            for repo in repo_list:
                if not self.repo_pattern.match(repo):
                    result.add_error(f"잘못된 저장소 형식: {repo} (예: owner/repo)")

        # 웹훅 설정 검증
        if "webhook_enabled" in config_data:
            webhook_enabled = config_data["webhook_enabled"]
            if isinstance(webhook_enabled, str):
                if webhook_enabled.lower() not in ("true", "false"):
                    result.add_error(f"webhook_enabled는 true/false여야 합니다: {webhook_enabled}")

        if "webhook_port" in config_data:
            webhook_port = config_data["webhook_port"]
            try:
                port_int = int(webhook_port)
                if not (1 <= port_int <= 65535):
                    result.add_error(f"webhook_port는 1~65535 사이여야 합니다: {webhook_port}")
            except (ValueError, TypeError):
                result.add_error(f"webhook_port는 정수여야 합니다: {webhook_port}")

        return result


class CompositeValidator(IConfigValidator):
    """복합 검증기

    여러 검증기를 조합하여 사용할 수 있습니다.
    """

    def __init__(self, validators: List[IConfigValidator]):
        """CompositeValidator 생성자

        Args:
            validators: 검증기 목록
        """
        self.validators = validators

    def validate(self, config_data: ConfigDict) -> ValidationResult:
        """모든 검증기로 검증"""
        result = ValidationResult()

        for validator in self.validators:
            validator_result = validator.validate(config_data)
            if not validator_result.is_valid:
                result.errors.extend(validator_result.errors)
                result.is_valid = False

        return result

    def add_validator(self, validator: IConfigValidator) -> None:
        """검증기 추가"""
        self.validators.append(validator)

    def remove_validator(self, validator: IConfigValidator) -> None:
        """검증기 제거"""
        if validator in self.validators:
            self.validators.remove(validator)


# 편의 함수들
def create_llm_validator() -> LLMConfigValidator:
    """LLM 검증기 생성"""
    return LLMConfigValidator()


def create_mcp_validator() -> MCPConfigValidator:
    """MCP 검증기 생성"""
    return MCPConfigValidator()


def create_github_validator() -> GitHubConfigValidator:
    """GitHub 검증기 생성"""
    return GitHubConfigValidator()


def create_schema_validator(schema: Dict[str, Any]) -> SchemaValidator:
    """스키마 검증기 생성"""
    return SchemaValidator(schema)


def create_composite_validator(*validators: IConfigValidator) -> CompositeValidator:
    """복합 검증기 생성"""
    return CompositeValidator(list(validators))
