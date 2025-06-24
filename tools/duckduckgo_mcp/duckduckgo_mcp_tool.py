#!/usr/bin/env python3
"""
DuckDuckGo Search MCP Server
웹 검색을 수행하고 결과를 제공하는 도구들을 제공합니다.
DuckDuckGo 검색 엔진을 사용하여 프라이버시를 보호하면서 검색 결과를 얻을 수 있습니다.
"""

import os
import json
import re
import html
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="DuckDuckGo Search Server",
    description="A server for web search operations using DuckDuckGo",
    version="1.0.0",
)

TRANSPORT = "stdio"

# DuckDuckGo 설정
BASE_URL = "https://duckduckgo.com"
SEARCH_URL = "https://duckduckgo.com/html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class SearchResult:
    """검색 결과를 담는 데이터 클래스"""
    title: str
    url: str
    description: str
    source: str
    timestamp: str


class DuckDuckGoService:
    """DuckDuckGo 검색 서비스 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://duckduckgo.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-GPC": "1",
        })
    
    def search(self, query: str, region: str = "kr-kr", safe_search: str = "moderate", time_period: str = None) -> List[SearchResult]:
        """DuckDuckGo에서 검색을 수행합니다."""
        try:
            # 검색 파라미터 설정
            params = {
                "q": query,
                "kl": region,  # 지역 설정
                "kp": self._get_safe_search_param(safe_search),  # 세이프서치 설정
                "kaf": "1",  # 자동 완성 비활성화
                "kac": "-1",  # 자동 제안 비활성화
            }
            
            # 시간 필터 추가
            if time_period:
                params["df"] = self._get_time_period_param(time_period)
            
            # 검색 요청
            response = self.session.get(SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # 검색 결과 추출
            for result in soup.select(".result"):
                try:
                    title_elem = result.select_one(".result__title")
                    url_elem = result.select_one(".result__url")
                    desc_elem = result.select_one(".result__snippet")
                    
                    if title_elem and url_elem:
                        title = title_elem.get_text(strip=True)
                        url = url_elem.get_text(strip=True)
                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url
                        
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        source = url.split("//")[-1].split("/")[0]
                        
                        results.append(SearchResult(
                            title=title,
                            url=url,
                            description=description,
                            source=source,
                            timestamp=datetime.now().isoformat()
                        ))
                except Exception:
                    continue
            
            return results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []
    
    def _get_safe_search_param(self, safe_search: str) -> str:
        """세이프서치 파라미터를 변환합니다."""
        if safe_search.lower() == "strict":
            return "1"  # 엄격
        elif safe_search.lower() == "off":
            return "-2"  # 끄기
        else:
            return "0"  # 보통 (기본값)
    
    def _get_time_period_param(self, time_period: str) -> str:
        """시간 필터 파라미터를 변환합니다."""
        time_map = {
            "day": "d",
            "week": "w",
            "month": "m",
            "year": "y"
        }
        return time_map.get(time_period.lower(), "")


# 전역 서비스 인스턴스
ddg_service = DuckDuckGoService()


@app.tool()
def search_web(query: str, region: str = "kr-kr", safe_search: str = "moderate", max_results: int = 10) -> dict:
    """
    웹 검색을 수행합니다.

    Args:
        query: 검색할 쿼리
        region: 검색 지역 (예: kr-kr, us-en, wt-wt)
        safe_search: 세이프서치 설정 (strict, moderate, off)
        max_results: 반환할 최대 결과 수

    Returns:
        dict: 검색 결과를 포함한 딕셔너리

    Examples:
        >>> search_web("파이썬 프로그래밍")
        {'result': {'query': '파이썬 프로그래밍', 'results': [...]}}
    """
    try:
        if not query:
            return {"error": "검색어를 입력해주세요."}
        
        # 검색 수행
        results = ddg_service.search(query, region, safe_search)
        
        # 결과 제한
        limited_results = results[:max_results]
        
        # 결과 포맷팅
        formatted_results = []
        for result in limited_results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "description": result.description,
                "source": result.source
            })
        
        return {
            "result": {
                "query": query,
                "region": region,
                "safe_search": safe_search,
                "count": len(formatted_results),
                "results": formatted_results
            }
        }
        
    except Exception as e:
        return {"error": f"검색 중 오류 발생: {str(e)}"}


@app.tool()
def search_with_time_filter(query: str, time_period: str = "week", region: str = "kr-kr", max_results: int = 10) -> dict:
    """
    특정 기간 내의 결과만 검색합니다.

    Args:
        query: 검색할 쿼리
        time_period: 검색 기간 (day, week, month, year)
        region: 검색 지역 (예: kr-kr, us-en, wt-wt)
        max_results: 반환할 최대 결과 수

    Returns:
        dict: 검색 결과를 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "검색어를 입력해주세요."}
        
        if time_period not in ["day", "week", "month", "year"]:
            return {"error": "유효한 시간 필터가 아닙니다. day, week, month, year 중 하나를 선택하세요."}
        
        # 검색 수행
        results = ddg_service.search(query, region, "moderate", time_period)
        
        # 결과 제한
        limited_results = results[:max_results]
        
        # 결과 포맷팅
        formatted_results = []
        for result in limited_results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "description": result.description,
                "source": result.source
            })
        
        return {
            "result": {
                "query": query,
                "time_period": time_period,
                "region": region,
                "count": len(formatted_results),
                "results": formatted_results
            }
        }
        
    except Exception as e:
        return {"error": f"검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_search_suggestions(query: str) -> dict:
    """
    검색어 자동 완성 제안을 가져옵니다.

    Args:
        query: 검색 쿼리

    Returns:
        dict: 검색어 제안을 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "검색어를 입력해주세요."}
        
        # 자동 완성 API 요청
        url = f"{BASE_URL}/ac/"
        params = {
            "q": query,
            "kl": "kr-kr",
            "type": "list"
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        suggestions = response.json()
        
        # 결과 포맷팅
        formatted_suggestions = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict) and "phrase" in suggestion:
                formatted_suggestions.append(suggestion["phrase"])
        
        return {
            "result": {
                "query": query,
                "count": len(formatted_suggestions),
                "suggestions": formatted_suggestions
            }
        }
        
    except Exception as e:
        return {"error": f"검색 제안을 가져오는 중 오류 발생: {str(e)}"}


@app.tool()
def search_images(query: str, max_results: int = 10) -> dict:
    """
    이미지 검색을 수행합니다.

    Args:
        query: 검색할 쿼리
        max_results: 반환할 최대 결과 수

    Returns:
        dict: 이미지 검색 결과를 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "검색어를 입력해주세요."}
        
        # 이미지 검색 파라미터 설정
        params = {
            "q": query,
            "iax": "images",
            "ia": "images"
        }
        
        # 검색 요청
        response = ddg_service.session.get(f"{BASE_URL}/", params=params, timeout=10)
        response.raise_for_status()
        
        # 이미지 데이터 추출 시도
        vqd_match = re.search(r'vqd="([^"]+)"', response.text)
        if not vqd_match:
            return {"error": "이미지 검색 토큰을 찾을 수 없습니다."}
        
        vqd = vqd_match.group(1)
        
        # 이미지 API 요청
        image_api_url = f"{BASE_URL}/i.js"
        image_params = {
            "q": query,
            "o": "json",
            "vqd": vqd,
            "p": 1
        }
        
        image_response = ddg_service.session.get(image_api_url, params=image_params, timeout=10)
        image_response.raise_for_status()
        
        try:
            image_data = image_response.json()
            results = image_data.get("results", [])
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 대체 방법
            return {"error": "이미지 결과를 파싱할 수 없습니다."}
        
        # 결과 제한 및 포맷팅
        formatted_results = []
        for result in results[:max_results]:
            if "image" in result and "url" in result:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "image_url": result.get("image", ""),
                    "source_url": result.get("url", ""),
                    "width": result.get("width", 0),
                    "height": result.get("height", 0),
                    "source": result.get("source", "")
                })
        
        return {
            "result": {
                "query": query,
                "count": len(formatted_results),
                "images": formatted_results
            }
        }
        
    except Exception as e:
        return {"error": f"이미지 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_search_info() -> dict:
    """
    검색 도구 정보와 사용 가능한 지역 설정을 반환합니다.

    Returns:
        dict: 검색 도구 정보를 포함한 딕셔너리
    """
    try:
        # 지역 설정 목록
        regions = {
            "wt-wt": "전 세계 (기본값)",
            "kr-kr": "대한민국",
            "us-en": "미국 (영어)",
            "uk-en": "영국 (영어)",
            "jp-jp": "일본",
            "cn-zh": "중국",
            "de-de": "독일",
            "fr-fr": "프랑스",
            "es-es": "스페인",
            "it-it": "이탈리아",
            "ru-ru": "러시아",
            "ca-en": "캐나다 (영어)",
            "ca-fr": "캐나다 (프랑스어)",
            "au-en": "호주"
        }
        
        # 세이프서치 설정
        safe_search_options = {
            "strict": "엄격 (성인 콘텐츠 필터링)",
            "moderate": "보통 (기본값)",
            "off": "끄기 (필터링 없음)"
        }
        
        # 시간 필터 옵션
        time_filters = {
            "day": "지난 24시간",
            "week": "지난 1주일",
            "month": "지난 1개월",
            "year": "지난 1년"
        }
        
        return {
            "result": {
                "name": "DuckDuckGo Search",
                "description": "DuckDuckGo 검색 엔진을 사용한 웹 검색 도구",
                "available_regions": regions,
                "safe_search_options": safe_search_options,
                "time_filters": time_filters,
                "tools": [
                    {
                        "name": "search_web",
                        "description": "기본 웹 검색"
                    },
                    {
                        "name": "search_with_time_filter",
                        "description": "시간 필터를 적용한 검색"
                    },
                    {
                        "name": "get_search_suggestions",
                        "description": "검색어 자동 완성 제안"
                    },
                    {
                        "name": "search_images",
                        "description": "이미지 검색"
                    }
                ]
            }
        }
        
    except Exception as e:
        return {"error": f"검색 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    app.run(transport=TRANSPORT)