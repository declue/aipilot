#!/usr/bin/env python3
"""
DuckDuckGo Search MCP Server
웹 검색을 수행하고 결과를 제공하는 도구들을 제공합니다.
DuckDuckGo 검색 엔진을 사용하여 프라이버시를 보호하면서 검색 결과를 얻을 수 있습니다.
"""

import logging
import os
import sys
from pathlib import Path

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 duckduckgo_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "duckduckgo_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

logger.info(f"DuckDuckGo MCP 서버 프로세스 시작 (PID: {os.getpid()})")
logger.info(f"Python Executable: {sys.executable}")
logger.info(f"sys.path: {sys.path}")
# --- 로깅 설정 끝 ---

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

error_msg = ""

try:
    from duckduckgo_search import DDGS  # type: ignore
    DUCKDUCKGO_SEARCH_AVAILABLE = True
    logger.debug("duckduckgo_search 라이브러리 (DDGS) 임포트 성공")
except ImportError as e:  # pragma: no cover – 라이브러리가 없으면 스크래핑 방식으로 대체
    DDGS = None  # type: ignore
    error_msg += f"duckduckgo_search 라이브러리가 없습니다: {e}\n"
    logger.error(f"duckduckgo_search 라이브러리 임포트 실패: {e}")
    DUCKDUCKGO_SEARCH_AVAILABLE = False
except Exception as e:
    DDGS = None  # type: ignore
    error_msg += f"duckduckgo_search 라이브러리 임포트 중 오류: {e}\n"
    logger.error(f"duckduckgo_search 라이브러리 임포트 중 예상치 못한 오류: {e}")
    DUCKDUCKGO_SEARCH_AVAILABLE = False

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
    full_content: str = ""  # 웹페이지 본문 내용
    published_date: str = ""  # 발행일
    content_type: str = "article"  # 콘텐츠 타입 (article, news, blog 등)


class DuckDuckGoService:
    """DuckDuckGo 검색 서비스 클래스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://duckduckgo.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-GPC": "1",
            }
        )

    def search(
        self,
        query: str,
        region: str = "kr-kr",
        safe_search: str = "moderate",
        time_period: str = None,
    ) -> List[SearchResult]:
        """DuckDuckGo에서 검색을 수행합니다.

        1. `duckduckgo_search` 라이브러리가 설치되어 있는 경우 → 해당 라이브러리를 우선 사용합니다.
        2. 라이브러리가 없거나, 예외가 발생한 경우 → 기존 HTML 스크래핑 방식으로 폴백합니다.
        """

        # 1️⃣ 라이브러리 기반 검색 (권장) -------------------------------------------------
        if DUCKDUCKGO_SEARCH_AVAILABLE and DDGS is not None:
            try:
                # 라이브러리 파라미터 매핑
                timelimit = self._get_time_period_param(time_period) if time_period else None

                # DDGS 인스턴스 생성 및 검색 수행 (더 많은 결과 요청)
                with DDGS() as ddgs:
                    raw_results = ddgs.text(
                        keywords=query,
                        region=region,
                        safesearch=safe_search,
                        timelimit=timelimit,
                        max_results=500,  # 더 많은 결과 요청
                    )

                parsed: List[SearchResult] = []
                for i, item in enumerate(raw_results or []):
                    # 라이브러리 결과 필드 매핑
                    title = item.get("title") or item.get("heading", "")
                    url = item.get("href") or item.get("url", "")
                    description = item.get("body", "") or item.get("snippet", "")
                    if url and not url.startswith(("http://", "https://")):
                        url = "https://" + url

                    source = url.split("//")[-1].split("/")[0] if url else ""
                    
                    # 본문 크롤링 (상위 20개 결과만, 성능 고려)
                    full_content = ""
                    published_date = ""
                    if i < 20 and url:  # 상위 20개만 크롤링
                        try:
                            full_content, published_date = self._extract_article_content(url)
                            logger.info(f"본문 크롤링 성공: {url[:50]}... ({len(full_content)}자)")
                        except Exception as e:
                            logger.debug(f"본문 크롤링 실패: {url} - {e}")
                    
                    # 콘텐츠 타입 추정
                    content_type = "article"
                    if any(keyword in source.lower() for keyword in ["news", "뉴스"]):
                        content_type = "news"
                    elif any(keyword in source.lower() for keyword in ["blog", "블로그"]):
                        content_type = "blog"

                    parsed.append(
                        SearchResult(
                            title=title,
                            url=url,
                            description=description,
                            source=source,
                            timestamp=datetime.now().isoformat(),
                            full_content=full_content,
                            published_date=published_date,
                            content_type=content_type,
                        )
                    )

                # 라이브러리 결과가 있다면 즉시 반환
                if parsed:
                    return parsed

                # 결과가 없고 글로벌(region="wt-wt")이 아닌 경우 → 글로벌 지역으로 한번 더 시도
                if region != "wt-wt":
                    try:
                        with DDGS() as ddgs:
                            raw_results = ddgs.text(
                                keywords=query,
                                region="wt-wt",
                                safesearch=safe_search,
                                timelimit=timelimit,
                                max_results=250,
                            )
                        for i, item in enumerate(raw_results or []):
                            title = item.get("title") or item.get("heading", "")
                            url = item.get("href") or item.get("url", "")
                            description = item.get("body", "") or item.get("snippet", "")
                            if url and not url.startswith(("http://", "https://")):
                                url = "https://" + url
                            source = url.split("//")[-1].split("/")[0] if url else ""
                            
                            # 본문 크롤링 (상위 10개만)
                            full_content = ""
                            published_date = ""
                            if i < 10 and url:
                                try:
                                    full_content, published_date = self._extract_article_content(url)
                                except Exception:
                                    pass
                            
                            content_type = "article"
                            if any(keyword in source.lower() for keyword in ["news", "뉴스"]):
                                content_type = "news"
                            
                            parsed.append(
                                SearchResult(
                                    title=title,
                                    url=url,
                                    description=description,
                                    source=source,
                                    timestamp=datetime.now().isoformat(),
                                    full_content=full_content,
                                    published_date=published_date,
                                    content_type=content_type,
                                )
                            )
                        if parsed:
                            return parsed
                    except Exception:
                        pass

            except Exception:
                # 라이브러리 사용 중 오류 → 로그 후 스크래핑 방식으로 폴백
                pass

        # 2️⃣ HTML 스크래핑 방식 -----------------------------------------------------------
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
            results: List[SearchResult] = []
            

            # 검색 결과 추출
            for i, result in enumerate(soup.select(".result")):
                try:
                    title_elem = result.select_one(".result__title")
                    url_elem = result.select_one(".result__url")
                    anchor_elem = result.select_one("a.result__a")
                    desc_elem = result.select_one(".result__snippet")

                    if title_elem and (url_elem or anchor_elem):
                        title = title_elem.get_text(strip=True)
                        url = ""
                        if url_elem:
                            url = url_elem.get_text(strip=True)
                        elif anchor_elem and anchor_elem.has_attr("href"):
                            url = anchor_elem["href"]

                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url

                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        source = url.split("//")[-1].split("/")[0]
                        
                        # 본문 크롤링 (상위 15개만)
                        full_content = ""
                        published_date = ""
                        if i < 15 and url:
                            try:
                                full_content, published_date = self._extract_article_content(url)
                            except Exception:
                                pass
                        
                        content_type = "article"
                        if any(keyword in source.lower() for keyword in ["news", "뉴스"]):
                            content_type = "news"

                        results.append(
                            SearchResult(
                                title=title,
                                url=url,
                                description=description,
                                source=source,
                                timestamp=datetime.now().isoformat(),
                                full_content=full_content,
                                published_date=published_date,
                                content_type=content_type,
                            )
                        )
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
        time_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
        return time_map.get(time_period.lower(), "")

    def _extract_article_content(self, url: str, max_chars: int = 2000) -> tuple[str, str]:
        """웹페이지에서 본문 내용을 추출합니다.
        
        Returns:
            tuple: (full_content, published_date)
        """
        try:
            if not url or not url.startswith(("http://", "https://")):
                return "", ""
            
            # 타임아웃을 짧게 설정하여 빠른 응답 보장
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 불필요한 태그 제거
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "advertisement"]):
                tag.decompose()
            
            # 본문 내용 추출 시도 (여러 패턴)
            content = ""
            
            # 1. 주요 뉴스 사이트의 본문 선택자들
            content_selectors = [
                "article", ".article-content", ".news-content", ".post-content",
                ".entry-content", ".main-content", ".article-body", ".story-body",
                ".content", ".post", ".news-article", "main", "[role='main']",
                ".article", ".news", ".story", ".text-content"
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # 가장 긴 텍스트를 가진 요소 선택
                    longest_element = max(elements, key=lambda x: len(x.get_text()))
                    content = longest_element.get_text(separator=' ', strip=True)
                    if len(content) > 200:  # 충분한 내용이 있으면 사용
                        break
            
            # 2. 메타태그에서 description 추출 (본문이 없을 경우)
            if len(content) < 200:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    content = meta_desc["content"]
                else:
                    # 3. body 태그에서 직접 추출
                    body = soup.find("body")
                    if body:
                        content = body.get_text(separator=' ', strip=True)
            
            # 발행일 추출
            published_date = ""
            date_selectors = [
                'time[datetime]', '.date', '.published', '.publish-date',
                '.article-date', '.news-date', '[datetime]', '.timestamp'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    if date_elem.get('datetime'):
                        published_date = date_elem['datetime']
                    else:
                        published_date = date_elem.get_text(strip=True)
                    break
            
            # 내용 정리 및 길이 제한
            if content:
                # 연속된 공백/줄바꿈 정리
                content = re.sub(r'\s+', ' ', content).strip()
                # 길이 제한
                if len(content) > max_chars:
                    content = content[:max_chars] + "..."
            
            return content, published_date
            
        except Exception as e:
            logger.debug(f"본문 추출 실패 ({url}): {e}")
            return "", ""


# 전역 서비스 인스턴스
ddg_service = DuckDuckGoService()


@app.tool()
def search_web(
    query: str, region: str = "kr-kr", safe_search: str = "moderate", max_results: int = 20
) -> dict:
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

        # 결과 포맷팅 (풍부한 데이터 포함)
        formatted_results = []
        for result in limited_results:
            formatted_results.append(
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                    "source": result.source,
                    "full_content": result.full_content,
                    "published_date": result.published_date,
                    "content_type": result.content_type,
                    "content_length": len(result.full_content),
                }
            )

        return {
            "result": {
                "query": query,
                "region": region,
                "safe_search": safe_search,
                "count": len(formatted_results),
                "results": formatted_results,
                "error": error_msg,
                "total_content_chars": sum(len(r.full_content) for r in limited_results),
            }
        }

    except Exception as e:
        return {"error": f"검색 중 오류 발생: {str(e)}"}


@app.tool()
def search_with_time_filter(
    query: str, time_period: str = "week", region: str = "kr-kr", max_results: int = 20
) -> dict:
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
            return {
                "error": "유효한 시간 필터가 아닙니다. day, week, month, year 중 하나를 선택하세요."
            }

        # 검색 수행
        results = ddg_service.search(query, region, "moderate", time_period)

        # 결과 제한
        limited_results = results[:max_results]

        # 결과 포맷팅 (풍부한 데이터 포함)
        formatted_results = []
        for result in limited_results:
            formatted_results.append(
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                    "source": result.source,
                    "full_content": result.full_content,
                    "published_date": result.published_date,
                    "content_type": result.content_type,
                    "content_length": len(result.full_content),
                }
            )

        return {
            "result": {
                "query": query,
                "time_period": time_period,
                "region": region,
                "count": len(formatted_results),
                "results": formatted_results,
                "total_content_chars": sum(len(r.full_content) for r in limited_results),
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
        params = {"q": query, "kl": "kr-kr", "type": "list"}

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
                "suggestions": formatted_suggestions,
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
        params = {"q": query, "iax": "images", "ia": "images"}

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
        image_params = {"q": query, "o": "json", "vqd": vqd, "p": 1}

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
                formatted_results.append(
                    {
                        "title": result.get("title", ""),
                        "image_url": result.get("image", ""),
                        "source_url": result.get("url", ""),
                        "width": result.get("width", 0),
                        "height": result.get("height", 0),
                        "source": result.get("source", ""),
                    }
                )

        return {
            "result": {"query": query, "count": len(formatted_results), "images": formatted_results}
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
            "au-en": "호주",
        }

        # 세이프서치 설정
        safe_search_options = {
            "strict": "엄격 (성인 콘텐츠 필터링)",
            "moderate": "보통 (기본값)",
            "off": "끄기 (필터링 없음)",
        }

        # 시간 필터 옵션
        time_filters = {
            "day": "지난 24시간",
            "week": "지난 1주일",
            "month": "지난 1개월",
            "year": "지난 1년",
        }

        return {
            "result": {
                "name": "DuckDuckGo Search",
                "description": "DuckDuckGo 검색 엔진을 사용한 웹 검색 도구",
                "available_regions": regions,
                "safe_search_options": safe_search_options,
                "time_filters": time_filters,
                "tools": [
                    {"name": "search_web", "description": "기본 웹 검색"},
                    {"name": "search_with_time_filter", "description": "시간 필터를 적용한 검색"},
                    {"name": "get_search_suggestions", "description": "검색어 자동 완성 제안"},
                    {"name": "search_images", "description": "이미지 검색"},
                ],
            }
        }

    except Exception as e:
        return {"error": f"검색 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("duckduckgo.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise
