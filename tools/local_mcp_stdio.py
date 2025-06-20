#!/usr/bin/env python3
"""
시간 관련 MCP 서버
현재 시간, GMT 시간, 로컬 시간을 반환하는 도구들을 제공합니다.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="Time Server",
    description="A server for time-related operations",
    version="1.0.0",
)

TRANSPORT = "stdio"


@app.tool()
def get_current_time() -> dict:
    """
    현재 시간을 ISO 8601 형식으로 반환합니다.

    Returns:
        dict: 현재 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_current_time()
        {'result': '현재 시간: 2024-01-15T14:30:45.123456'}
    """
    try:
        now = datetime.now()
        return {"result": f"현재 시간: {now.isoformat()}"}
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_gmt_time() -> dict:
    """
    현재 GMT(UTC) 시간을 반환합니다.

    Returns:
        dict: GMT 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_gmt_time()
        {'result': 'GMT 시간: 2024-01-15 05:30:45 UTC'}
    """
    try:
        utc_now = datetime.now(timezone.utc)
        return {"result": f"GMT 시간: {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}"}
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_local_time(timezone_name: Optional[str] = None) -> dict:
    """
    현재 로컬 시간을 반환합니다.

    Args:
        timezone_name: 타임존 이름 (예: Asia/Seoul, America/New_York).
                      기본값은 None으로 시스템 로컬 타임존을 사용합니다.

    Returns:
        dict: 로컬 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_local_time()
        {'result': '로컬 시간: 2024-01-15 14:30:45'}
        >>> get_local_time("Asia/Seoul")
        {'result': 'Asia/Seoul 시간: 2024-01-15 23:30:45 KST'}
    """
    try:
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
                local_time = datetime.now(tz)
                return {
                    "result": f"{timezone_name} 시간: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                }
            except Exception as e:
                return {"error": f"타임존 오류: {str(e)}"}
        else:
            local_time = datetime.now()
            return {"result": f"로컬 시간: {local_time.strftime('%Y-%m-%d %H:%M:%S')}"}
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_time_in_timezone(timezone_name: str) -> dict:
    """
    지정된 타임존의 현재 시간을 반환합니다.

    Args:
        timezone_name: 타임존 이름 (예: Asia/Seoul, America/New_York, Europe/London)

    Returns:
        dict: 지정된 타임존의 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_time_in_timezone("Asia/Seoul")
        {'result': 'Asia/Seoul 시간: 2024-01-15 23:30:45 KST'}
        >>> get_time_in_timezone("America/New_York")
        {'result': 'America/New_York 시간: 2024-01-15 09:30:45 EST'}
    """
    try:
        tz = ZoneInfo(timezone_name)
        tz_time = datetime.now(tz)
        return {
            "result": f"{timezone_name} 시간: {tz_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        }
    except Exception as e:
        return {"error": f"타임존 오류: {str(e)}"}


@app.tool()
def list_common_timezones() -> dict:
    """
    자주 사용되는 타임존 목록을 반환합니다.

    Returns:
        dict: 자주 사용되는 타임존들의 목록

    Examples:
        >>> list_common_timezones()
        {'result': ['UTC', 'Asia/Seoul', 'Asia/Tokyo', ...]}
    """
    try:
        common_timezones = [
            "UTC",
            "Asia/Seoul",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Australia/Sydney",
            "Australia/Melbourne",
        ]
        return {"result": common_timezones}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    app.run(transport="stdio")
