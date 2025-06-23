from typing import Any, Dict


class ToolConverter:  # pylint: disable=too-few-public-methods
    """MCP → OpenAI 변환 유틸리티 (SRP)"""

    @staticmethod
    def convert_schema(mcp_schema: Dict[str, Any]) -> Dict[str, Any]:
        """MCP JSON 스키마를 OpenAI 함수 호출용 JSON 스키마로 변환합니다.

        - 스키마가 비어있으면 기본적으로 query 문자열 하나를 요구합니다.
        - type: object 이고 properties 필드가 있으면 해당 스키마를 그대로 사용합니다.
        - 그 외에는 단일 문자열 입력을 받도록 변환합니다.
        """
        if not mcp_schema:
            return {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "요청 내용 또는 검색어",
                    }
                },
                "required": ["query"],
            }

        if mcp_schema.get("type") == "object" and "properties" in mcp_schema:
            return mcp_schema

        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "도구에 전달할 입력 데이터",
                }
            },
            "required": ["input"],
        }

    # ------------------------------------------------------------------
    @staticmethod
    def enhance_description(server_name: str, tool_name: str, description: str) -> str:
        """도구 설명을 개선하여 AI가 언제 사용해야 할지 더 명확하게 해줍니다."""
        enhanced = f"[{server_name.upper()}] {description}"

        # GitHub 관련 도구인 경우 추가 안내
        if "github" in server_name.lower() or "git" in tool_name.lower():
            enhanced += " (GitHub 관련 질문 시 우선 사용)"
        return enhanced
