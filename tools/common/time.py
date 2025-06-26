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
    현재 날짜와 시간을 모두 포함하여 반환합니다. 완전한 날짜와 시간 정보가 필요할 때 사용하세요.

    Returns:
        dict: 현재 날짜와 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_current_time()
        {'result': '2024년 1월 15일 월요일 오후 2시 30분 45초'}
    """
    try:
        now = datetime.now()
        
        # 요일 이름 매핑
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday_name = weekdays[now.weekday()]
        
        # 오전/오후 구분
        if now.hour < 12:
            period = "오전"
            hour_12 = now.hour if now.hour > 0 else 12
        else:
            period = "오후"
            hour_12 = now.hour - 12 if now.hour > 12 else 12
        
        # 사용자 친화적인 형식으로 포맷
        formatted_time = f"{now.year}년 {now.month}월 {now.day}일 {weekday_name} {period} {hour_12}시 {now.minute}분 {now.second}초"
        
        return {
            "result": formatted_time,
            "iso_format": now.isoformat(),  # 필요시 ISO 형식도 제공
            "timestamp": now.timestamp()    # 타임스탬프도 제공
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_current_date() -> dict:
    """
    🗓️ 현재 날짜 정보 전용 도구입니다.
    
    ⚠️ CRITICAL: 이 도구는 오늘의 정확한 날짜를 제공합니다.
    - "오늘", "날짜", "몇일", "며칠" 관련 질문에 사용하세요
    - 절대 추측하지 말고 이 도구를 사용하여 정확한 날짜를 확인하세요
    - 현재 날짜가 필요한 모든 상황에서 이 도구를 사용해야 합니다

    Returns:
        dict: 현재 날짜 정보를 포함한 딕셔너리

    Examples:
        >>> get_current_date()
        {'result': '2024년 1월 15일 월요일'}
    """
    try:
        now = datetime.now()
        
        # 요일 이름 매핑
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday_name = weekdays[now.weekday()]
        
        # 날짜 포맷
        formatted_date = f"{now.year}년 {now.month}월 {now.day}일 {weekday_name}"
        
        return {
            "result": formatted_date,
            "iso_date": now.date().isoformat()  # ISO 날짜 형식도 제공
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_time_only() -> dict:
    """
    현재 시간만 반환합니다. 시간 정보만 필요할 때 사용하세요.

    Returns:
        dict: 현재 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_time_only()
        {'result': '오후 2시 30분 45초'}
    """
    try:
        now = datetime.now()
        
        # 오전/오후 구분
        if now.hour < 12:
            period = "오전"
            hour_12 = now.hour if now.hour > 0 else 12
        else:
            period = "오후"
            hour_12 = now.hour - 12 if now.hour > 12 else 12
        
        # 시간 포맷
        formatted_time = f"{period} {hour_12}시 {now.minute}분 {now.second}초"
        
        return {
            "result": formatted_time,
            "24_hour_format": f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_gmt_time() -> dict:
    """
    현재 GMT(UTC) 시간을 사용자 친화적인 형식으로 반환합니다.

    Returns:
        dict: GMT 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_gmt_time()
        {'result': 'GMT: 2024년 1월 15일 월요일 오전 5시 30분 45초 (UTC)'}
    """
    try:
        utc_now = datetime.now(timezone.utc)
        
        # 요일 이름 매핑
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday_name = weekdays[utc_now.weekday()]
        
        # 오전/오후 구분
        if utc_now.hour < 12:
            period = "오전"
            hour_12 = utc_now.hour if utc_now.hour > 0 else 12
        else:
            period = "오후"
            hour_12 = utc_now.hour - 12 if utc_now.hour > 12 else 12
        
        # GMT 시간 포맷
        formatted_gmt = f"GMT: {utc_now.year}년 {utc_now.month}월 {utc_now.day}일 {weekday_name} {period} {hour_12}시 {utc_now.minute}분 {utc_now.second}초 (UTC)"
        
        return {
            "result": formatted_gmt,
            "iso_format": utc_now.isoformat(),
            "standard_format": utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_local_time(timezone_name: Optional[str] = None) -> dict:
    """
    현재 로컬 시간을 사용자 친화적인 형식으로 반환합니다.

    Args:
        timezone_name: 타임존 이름 (예: Asia/Seoul, America/New_York).
                      기본값은 None으로 시스템 로컬 타임존을 사용합니다.

    Returns:
        dict: 로컬 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_local_time()
        {'result': '로컬 시간: 2024년 1월 15일 월요일 오후 2시 30분 45초'}
        >>> get_local_time("Asia/Seoul")
        {'result': 'Asia/Seoul: 2024년 1월 15일 월요일 오후 11시 30분 45초 (KST)'}
    """
    try:
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
                local_time = datetime.now(tz)
                
                # 요일 이름 매핑
                weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                weekday_name = weekdays[local_time.weekday()]
                
                # 오전/오후 구분
                if local_time.hour < 12:
                    period = "오전"
                    hour_12 = local_time.hour if local_time.hour > 0 else 12
                else:
                    period = "오후"
                    hour_12 = local_time.hour - 12 if local_time.hour > 12 else 12
                
                # 타임존 시간 포맷
                tz_abbr = local_time.strftime('%Z')
                formatted_time = f"{timezone_name}: {local_time.year}년 {local_time.month}월 {local_time.day}일 {weekday_name} {period} {hour_12}시 {local_time.minute}분 {local_time.second}초"
                if tz_abbr:
                    formatted_time += f" ({tz_abbr})"
                
                return {
                    "result": formatted_time,
                    "iso_format": local_time.isoformat(),
                    "standard_format": local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                }
            except Exception as e:
                return {"error": f"타임존 오류: {str(e)}"}
        else:
            local_time = datetime.now()
            
            # 요일 이름 매핑
            weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            weekday_name = weekdays[local_time.weekday()]
            
            # 오전/오후 구분
            if local_time.hour < 12:
                period = "오전"
                hour_12 = local_time.hour if local_time.hour > 0 else 12
            else:
                period = "오후"
                hour_12 = local_time.hour - 12 if local_time.hour > 12 else 12
            
            # 로컬 시간 포맷
            formatted_time = f"로컬 시간: {local_time.year}년 {local_time.month}월 {local_time.day}일 {weekday_name} {period} {hour_12}시 {local_time.minute}분 {local_time.second}초"
            
            return {
                "result": formatted_time,
                "iso_format": local_time.isoformat(),
                "standard_format": local_time.strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        return {"error": str(e)}


@app.tool()
def get_time_in_timezone(timezone_name: str) -> dict:
    """
    지정된 타임존의 현재 시간을 사용자 친화적인 형식으로 반환합니다.

    Args:
        timezone_name: 타임존 이름 (예: Asia/Seoul, America/New_York, Europe/London)

    Returns:
        dict: 지정된 타임존의 시간 정보를 포함한 딕셔너리

    Examples:
        >>> get_time_in_timezone("Asia/Seoul")
        {'result': 'Asia/Seoul: 2024년 1월 15일 월요일 오후 11시 30분 45초 (KST)'}
        >>> get_time_in_timezone("America/New_York")
        {'result': 'America/New_York: 2024년 1월 15일 월요일 오전 9시 30분 45초 (EST)'}
    """
    try:
        tz = ZoneInfo(timezone_name)
        tz_time = datetime.now(tz)
        
        # 요일 이름 매핑
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        weekday_name = weekdays[tz_time.weekday()]
        
        # 오전/오후 구분
        if tz_time.hour < 12:
            period = "오전"
            hour_12 = tz_time.hour if tz_time.hour > 0 else 12
        else:
            period = "오후"
            hour_12 = tz_time.hour - 12 if tz_time.hour > 12 else 12
        
        # 타임존 시간 포맷
        tz_abbr = tz_time.strftime('%Z')
        formatted_time = f"{timezone_name}: {tz_time.year}년 {tz_time.month}월 {tz_time.day}일 {weekday_name} {period} {hour_12}시 {tz_time.minute}분 {tz_time.second}초"
        if tz_abbr:
            formatted_time += f" ({tz_abbr})"
        
        return {
            "result": formatted_time,
            "iso_format": tz_time.isoformat(),
            "standard_format": tz_time.strftime('%Y-%m-%d %H:%M:%S %Z')
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
