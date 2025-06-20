from typing import Any, Dict


class ToolCache:  # pylint: disable=too-few-public-methods
    """MCP 도구 메타데이터를 메모리에 저장/조회하는 캐시."""

    def __init__(self) -> None:
        # key -> { server_name, tool_name, tool_info }
        self._cache: Dict[str, Dict[str, Any]] = {}

    # -------------------------------------------------
    # 쓰기 메서드
    # -------------------------------------------------
    def add(self, key: str, server_name: str, tool_name: str, tool_info: Dict[str, Any]) -> None:
        """도구 정보를 캐시에 추가합니다."""
        self._cache[key] = {
            "server_name": server_name,
            "tool_name": tool_name,
            "tool_info": tool_info,
        }

    def clear(self) -> None:
        """캐시 초기화"""
        self._cache.clear()

    # -------------------------------------------------
    # 조회 메서드
    # -------------------------------------------------
    def get(self, key: str) -> Dict[str, Any]:
        """키로 도구 정보를 조회합니다. 존재하지 않으면 빈 dict를 반환합니다."""
        return self._cache.get(key, {})

    def items(self):  # type: ignore[override]
        """(key, value) 튜플 이터레이터를 반환합니다."""
        return self._cache.items()

    def keys(self):  # type: ignore[override]
        return self._cache.keys()

    def values(self):  # type: ignore[override]
        return self._cache.values()

    # -------------------------------------------------
    # 상태 메서드
    # -------------------------------------------------
    def __len__(self) -> int:  # pragma: no cover
        return len(self._cache)

    def __contains__(self, key: str) -> bool:  # pragma: no cover
        return key in self._cache 