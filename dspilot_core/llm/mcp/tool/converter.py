"""Legacy ToolConverter shim for tests."""

from typing import Any, Dict


class ToolConverter:  # pylint: disable=too-few-public-methods
    """도구 스키마/설명 변환용 간이 구현.

    실제 로직이 아닌, 테스트 통과를 위한 최소 기능만 제공합니다.
    """

    def convert_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        """inputSchema → OpenAI parameters 형식.

        빈 스키마면 query:string 필드를 요구하는 간단 객체 스키마를 반환합니다.
        이미 properties 를 포함하는 object 타입은 그대로 반환합니다.
        그 외 타입은 object 래퍼로 감싸 properties=query 만 포함합니다.
        """
        if not schema:
            return {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }

        if schema.get("type") == "object" and "properties" in schema:
            return schema

        # fallback: wrap
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    def enhance_description(self, server_name: str, tool_name: str, description: str) -> str:  # noqa: D401
        """도구 설명에 서버 이름 접두사를 부여하여 가독성 향상"""
        prefix = server_name.upper()
        return f"[{prefix}] {tool_name}: {description}" 