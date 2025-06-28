#!/usr/bin/env python3
"""
Web Search MCP Server
URL 크롤링을 수행하고 결과를 제공하는 도구를 제공합니다.
사용자가 특정 URL을 전달하면 해당 URL의 내용을 크롤링하여 반환합니다.
"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 web_search_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "web_search_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("WEB_SEARCH_LOG_LEVEL", "WARNING").upper()
log_level_int = getattr(logging, log_level, logging.WARNING)

logging.basicConfig(
    level=log_level_int,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path),
              logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# INFO 레벨 로그는 환경 변수가 DEBUG나 INFO로 설정된 경우에만 출력
if log_level_int <= logging.INFO:
    logger.info("Web Search MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Web Search Server",
    description="A server for URL crawling operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class CrawlResult:
    """크롤링 결과를 담는 데이터 클래스"""

    url: str
    title: str
    content: str
    html: str
    timestamp: str
    published_date: str = ""
    content_type: str = "article"
    metadata: Dict = None


class WebCrawlerService:
    """웹 크롤링 서비스 클래스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def crawl_url(self, url: str, timeout: int = 10) -> Optional[CrawlResult]:
        """지정된 URL을 크롤링하고 결과를 반환합니다.

        Args:
            url: 크롤링할 URL
            timeout: 요청 타임아웃 (초)

        Returns:
            CrawlResult: 크롤링 결과 객체 또는 None (실패 시)
        """
        try:
            if not url or not url.startswith(("http://", "https://")):
                logger.error("유효하지 않은 URL: %s", url)
                return None

            # URL 요청
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # 제목 추출
            title = self._extract_title(soup)

            # 본문 내용 추출
            content, published_date = self._extract_content(soup)

            # 메타데이터 추출
            metadata = self._extract_metadata(soup)

            # 콘텐츠 타입 추정
            content_type = self._determine_content_type(url, soup)

            # 결과 생성
            result = CrawlResult(
                url=url,
                title=title,
                content=content,
                html=response.text,
                timestamp=datetime.now().isoformat(),
                published_date=published_date,
                content_type=content_type,
                metadata=metadata
            )

            return result

        except Exception as e:
            logger.error("URL 크롤링 중 오류 발생: %s - %s", url, str(e))
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """HTML에서 제목을 추출합니다."""
        # 1. title 태그에서 추출
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # 2. h1 태그에서 추출
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.string:
            return h1_tag.string.strip()

        # 3. 메타 태그에서 추출
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        return "제목 없음"

    def _extract_content(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """HTML에서 본문 내용과 발행일을 추출합니다.

        Returns:
            tuple: (content, published_date)
        """
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "advertisement"]):
            tag.decompose()

        # 본문 내용 추출 시도 (여러 패턴)
        content = ""

        # 1. 주요 콘텐츠 선택자들
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
                longest_element = max(
                    elements, key=lambda x: len(x.get_text()))
                content = longest_element.get_text(
                    separator=' ', strip=True)
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

        # 내용 정리 (연속된 공백/줄바꿈 정리)
        if content:
            content = re.sub(r'\s+', ' ', content).strip()

        return content, published_date

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """HTML에서 메타데이터를 추출합니다."""
        metadata = {}

        # Open Graph 메타데이터
        og_tags = soup.find_all("meta", property=re.compile(r'^og:'))
        for tag in og_tags:
            property_name = tag.get("property", "").replace("og:", "")
            if property_name and tag.get("content"):
                metadata[property_name] = tag["content"]

        # Twitter 카드 메타데이터
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r'^twitter:')})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            if name and tag.get("content"):
                metadata[f"twitter_{name}"] = tag["content"]

        # 기본 메타데이터
        basic_meta = ["description", "keywords", "author"]
        for name in basic_meta:
            meta_tag = soup.find("meta", attrs={"name": name})
            if meta_tag and meta_tag.get("content"):
                metadata[name] = meta_tag["content"]

        return metadata

    def _determine_content_type(self, url: str, soup: BeautifulSoup) -> str:
        """URL과 HTML 내용을 기반으로 콘텐츠 타입을 추정합니다."""
        # URL 기반 추정
        domain = url.split("//")[-1].split("/")[0].lower()
        
        if any(keyword in domain for keyword in ["news", "뉴스"]):
            return "news"
        elif any(keyword in domain for keyword in ["blog", "블로그"]):
            return "blog"
        
        # 메타 태그 기반 추정
        og_type = soup.find("meta", property="og:type")
        if og_type and og_type.get("content"):
            og_content = og_type["content"].lower()
            if "article" in og_content:
                return "article"
            elif "blog" in og_content:
                return "blog"
            elif "news" in og_content:
                return "news"
            else:
                return og_content
                
        return "article"  # 기본값


# 전역 서비스 인스턴스
web_crawler = WebCrawlerService()


@app.tool()
def crawl_url(url: str, timeout: int = 10) -> dict:
    """
    지정된 URL을 크롤링하고 내용을 반환합니다.

    Args:
        url: 크롤링할 URL
        timeout: 요청 타임아웃 (초)

    Returns:
        dict: 크롤링 결과를 포함한 딕셔너리

    Examples:
        >>> crawl_url("https://example.com")
        {'result': {'url': 'https://example.com', 'title': '...', ...}}
    """
    try:
        if not url:
            return {"error": "URL을 입력해주세요."}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # URL 크롤링 수행
        result = web_crawler.crawl_url(url, timeout)

        if not result:
            return {"error": f"URL 크롤링에 실패했습니다: {url}"}

        # 결과 포맷팅
        return {
            "result": {
                "url": result.url,
                "title": result.title,
                "content": result.content,
                "content_length": len(result.content),
                "published_date": result.published_date,
                "content_type": result.content_type,
                "timestamp": result.timestamp,
                "metadata": result.metadata,
            }
        }

    except Exception as e:
        return {"error": f"URL 크롤링 중 오류 발생: {str(e)}"}


@app.tool()
def crawl_url_with_html(url: str, timeout: int = 10) -> dict:
    """
    지정된 URL을 크롤링하고 HTML을 포함한 내용을 반환합니다.

    Args:
        url: 크롤링할 URL
        timeout: 요청 타임아웃 (초)

    Returns:
        dict: HTML을 포함한 크롤링 결과를 포함한 딕셔너리
    """
    try:
        if not url:
            return {"error": "URL을 입력해주세요."}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # URL 크롤링 수행
        result = web_crawler.crawl_url(url, timeout)

        if not result:
            return {"error": f"URL 크롤링에 실패했습니다: {url}"}

        # 결과 포맷팅 (HTML 포함)
        return {
            "result": {
                "url": result.url,
                "title": result.title,
                "content": result.content,
                "html": result.html,
                "content_length": len(result.content),
                "html_length": len(result.html),
                "published_date": result.published_date,
                "content_type": result.content_type,
                "timestamp": result.timestamp,
                "metadata": result.metadata,
            }
        }

    except Exception as e:
        return {"error": f"URL 크롤링 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    웹 크롤링 도구 정보를 반환합니다.

    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Web Crawler",
                "description": "URL 크롤링을 수행하는 도구",
                "tools": [
                    {"name": "crawl_url", "description": "URL을 크롤링하고 내용을 반환합니다"},
                    {"name": "crawl_url_with_html", "description": "URL을 크롤링하고 HTML을 포함한 내용을 반환합니다"},
                ],
                "usage_examples": [
                    {"command": "crawl_url('https://example.com')", "description": "example.com 웹사이트 크롤링"},
                    {"command": "crawl_url_with_html('https://example.com')", "description": "HTML을 포함한 크롤링 결과 반환"},
                ]
            }
        }

    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("web_search.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise