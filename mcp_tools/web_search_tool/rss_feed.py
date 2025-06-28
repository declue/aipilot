#!/usr/bin/env python3
"""
RSS Feed MCP Server
RSS 피드를 처리하고 결과를 제공하는 도구를 제공합니다.
사용자가 RSS 피드 URL을 전달하면 해당 피드의 내용을 가져오거나 검색할 수 있습니다.
"""

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError as e:
    FEEDPARSER_AVAILABLE = False
    error_msg = f"feedparser 라이브러리가 없습니다: {e}\n"
    print(error_msg)

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 rss_feed_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "rss_feed_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("RSS_FEED_LOG_LEVEL", "WARNING").upper()
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
    logger.info("RSS Feed MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="RSS Feed Server",
    description="A server for RSS feed processing operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class RSSFeedItem:
    """RSS 피드 항목을 담는 데이터 클래스"""

    title: str
    link: str
    description: str
    published: str
    content: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    guid: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RSSFeedResult:
    """RSS 피드 결과를 담는 데이터 클래스"""

    feed_url: str
    feed_title: str
    feed_description: str
    feed_link: str
    items: List[RSSFeedItem] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RSSFeedService:
    """RSS 피드 서비스 클래스"""

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

    def fetch_feed(self, feed_url: str, timeout: int = 10) -> Optional[RSSFeedResult]:
        """RSS 피드를 가져오고 결과를 반환합니다.

        Args:
            feed_url: RSS 피드 URL
            timeout: 요청 타임아웃 (초)

        Returns:
            RSSFeedResult: RSS 피드 결과 객체 또는 None (실패 시)
        """
        try:
            if not feed_url or not feed_url.startswith(("http://", "https://")):
                logger.error("유효하지 않은 피드 URL: %s", feed_url)
                return None

            if not FEEDPARSER_AVAILABLE:
                # feedparser가 없는 경우 직접 요청 및 파싱 시도
                return self._fetch_feed_without_feedparser(feed_url, timeout)

            # feedparser를 사용하여 피드 파싱
            feed = feedparser.parse(feed_url)
            
            if feed.get('bozo_exception'):
                logger.warning("피드 파싱 경고: %s", feed.bozo_exception)
            
            # 피드 정보 추출
            feed_info = feed.get('feed', {})
            feed_title = feed_info.get('title', '제목 없음')
            feed_description = feed_info.get('description', feed_info.get('subtitle', '설명 없음'))
            feed_link = feed_info.get('link', feed_url)
            
            # 피드 항목 추출
            items = []
            for entry in feed.get('entries', []):
                # 본문 내용 추출 시도
                content = ""
                if 'content' in entry and entry['content']:
                    for content_item in entry['content']:
                        if content_item.get('type') == 'text/html':
                            content = content_item.get('value', '')
                            break
                
                if not content and 'summary' in entry:
                    content = entry.get('summary', '')
                
                # HTML 태그 제거
                if content:
                    content = self._clean_html(content)
                
                # 발행일 처리
                published = ""
                if 'published' in entry:
                    published = entry['published']
                elif 'updated' in entry:
                    published = entry['updated']
                
                # 저자 정보 추출
                author = ""
                if 'author' in entry:
                    author = entry['author']
                elif 'authors' in entry and entry['authors']:
                    author = entry['authors'][0].get('name', '')
                
                # 카테고리 추출
                categories = []
                if 'tags' in entry:
                    categories = [tag.get('term', '') for tag in entry['tags']]
                elif 'categories' in entry:
                    categories = entry['categories']
                
                item = RSSFeedItem(
                    title=entry.get('title', '제목 없음'),
                    link=entry.get('link', ''),
                    description=entry.get('summary', ''),
                    published=published,
                    content=content,
                    author=author,
                    categories=categories,
                    guid=entry.get('id', entry.get('link', '')),
                )
                items.append(item)
            
            return RSSFeedResult(
                feed_url=feed_url,
                feed_title=feed_title,
                feed_description=feed_description,
                feed_link=feed_link,
                items=items,
            )
            
        except Exception as e:
            logger.error("RSS 피드 가져오기 중 오류 발생: %s - %s", feed_url, str(e))
            return None

    def _fetch_feed_without_feedparser(self, feed_url: str, timeout: int) -> Optional[RSSFeedResult]:
        """feedparser 없이 RSS 피드를 가져오고 결과를 반환합니다."""
        try:
            # URL 요청
            response = self.session.get(feed_url, timeout=timeout)
            response.raise_for_status()
            
            # XML 파싱
            soup = BeautifulSoup(response.text, "xml")
            if not soup.find('rss') and not soup.find('feed'):
                logger.error("유효한 RSS/Atom 피드가 아닙니다: %s", feed_url)
                return None
            
            # 피드 정보 추출
            feed_title = ""
            feed_description = ""
            feed_link = ""
            
            # RSS 형식 확인
            if soup.find('rss'):
                channel = soup.find('channel')
                if channel:
                    feed_title = channel.find('title').text if channel.find('title') else '제목 없음'
                    feed_description = channel.find('description').text if channel.find('description') else '설명 없음'
                    feed_link = channel.find('link').text if channel.find('link') else feed_url
                    
                    # 피드 항목 추출
                    items = []
                    for item_elem in channel.find_all('item'):
                        title = item_elem.find('title').text if item_elem.find('title') else '제목 없음'
                        link = item_elem.find('link').text if item_elem.find('link') else ''
                        description = item_elem.find('description').text if item_elem.find('description') else ''
                        published = item_elem.find('pubDate').text if item_elem.find('pubDate') else ''
                        
                        # 본문 내용 추출
                        content = ""
                        content_encoded = item_elem.find('content:encoded')
                        if content_encoded:
                            content = content_encoded.text
                        else:
                            content = description
                        
                        # HTML 태그 제거
                        content = self._clean_html(content)
                        description = self._clean_html(description)
                        
                        # 저자 정보 추출
                        author = item_elem.find('author').text if item_elem.find('author') else ''
                        
                        # 카테고리 추출
                        categories = [cat.text for cat in item_elem.find_all('category')]
                        
                        # GUID 추출
                        guid = item_elem.find('guid').text if item_elem.find('guid') else link
                        
                        item = RSSFeedItem(
                            title=title,
                            link=link,
                            description=description,
                            published=published,
                            content=content,
                            author=author,
                            categories=categories,
                            guid=guid,
                        )
                        items.append(item)
            
            # Atom 형식 확인
            elif soup.find('feed'):
                feed = soup.find('feed')
                feed_title = feed.find('title').text if feed.find('title') else '제목 없음'
                feed_description = feed.find('subtitle').text if feed.find('subtitle') else '설명 없음'
                
                # Atom에서는 link가 여러 개일 수 있음
                feed_link_elem = feed.find('link', rel='alternate') or feed.find('link')
                feed_link = feed_link_elem.get('href', feed_url) if feed_link_elem else feed_url
                
                # 피드 항목 추출
                items = []
                for entry in feed.find_all('entry'):
                    title = entry.find('title').text if entry.find('title') else '제목 없음'
                    
                    # Atom에서는 link가 여러 개일 수 있음
                    link_elem = entry.find('link', rel='alternate') or entry.find('link')
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    # 설명 및 내용 추출
                    description = entry.find('summary').text if entry.find('summary') else ''
                    content_elem = entry.find('content')
                    content = content_elem.text if content_elem else description
                    
                    # HTML 태그 제거
                    content = self._clean_html(content)
                    description = self._clean_html(description)
                    
                    # 발행일 처리
                    published = ""
                    if entry.find('published'):
                        published = entry.find('published').text
                    elif entry.find('updated'):
                        published = entry.find('updated').text
                    
                    # 저자 정보 추출
                    author = ""
                    author_elem = entry.find('author')
                    if author_elem and author_elem.find('name'):
                        author = author_elem.find('name').text
                    
                    # 카테고리 추출
                    categories = [cat.get('term', '') for cat in entry.find_all('category')]
                    
                    # ID 추출
                    guid = entry.find('id').text if entry.find('id') else link
                    
                    item = RSSFeedItem(
                        title=title,
                        link=link,
                        description=description,
                        published=published,
                        content=content,
                        author=author,
                        categories=categories,
                        guid=guid,
                    )
                    items.append(item)
            
            return RSSFeedResult(
                feed_url=feed_url,
                feed_title=feed_title,
                feed_description=feed_description,
                feed_link=feed_link,
                items=items,
            )
            
        except Exception as e:
            logger.error("feedparser 없이 RSS 피드 가져오기 중 오류 발생: %s - %s", feed_url, str(e))
            return None

    def search_feed(self, feed_url: str, query: str, timeout: int = 10) -> Optional[RSSFeedResult]:
        """RSS 피드에서 검색을 수행하고 결과를 반환합니다.

        Args:
            feed_url: RSS 피드 URL
            query: 검색 쿼리
            timeout: 요청 타임아웃 (초)

        Returns:
            RSSFeedResult: 검색 결과를 포함한 RSS 피드 결과 객체 또는 None (실패 시)
        """
        try:
            # 피드 가져오기
            feed_result = self.fetch_feed(feed_url, timeout)
            if not feed_result:
                return None
            
            # 검색어가 없으면 전체 피드 반환
            if not query:
                return feed_result
            
            # 검색어를 소문자로 변환
            query_lower = query.lower()
            
            # 검색 결과 필터링
            filtered_items = []
            for item in feed_result.items:
                # 제목, 설명, 내용에서 검색
                if (query_lower in item.title.lower() or
                    query_lower in item.description.lower() or
                    query_lower in item.content.lower()):
                    filtered_items.append(item)
            
            # 검색 결과 생성
            search_result = RSSFeedResult(
                feed_url=feed_result.feed_url,
                feed_title=feed_result.feed_title,
                feed_description=feed_result.feed_description,
                feed_link=feed_result.feed_link,
                items=filtered_items,
            )
            
            return search_result
            
        except Exception as e:
            logger.error("RSS 피드 검색 중 오류 발생: %s - %s", feed_url, str(e))
            return None

    def _clean_html(self, html_content: str) -> str:
        """HTML 태그를 제거하고 텍스트만 추출합니다."""
        if not html_content:
            return ""
        
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 불필요한 태그 제거
        for tag in soup(["script", "style"]):
            tag.decompose()
        
        # 텍스트 추출
        text = soup.get_text(separator=' ', strip=True)
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


# 전역 서비스 인스턴스
rss_service = RSSFeedService()


@app.tool()
def get_rss_feed(feed_url: str, max_items: int = 20) -> dict:
    """
    RSS 피드를 가져오고 내용을 반환합니다.

    Args:
        feed_url: RSS 피드 URL
        max_items: 반환할 최대 항목 수

    Returns:
        dict: RSS 피드 결과를 포함한 딕셔너리

    Examples:
        >>> get_rss_feed("https://news.google.com/rss")
        {'result': {'feed_url': 'https://news.google.com/rss', 'feed_title': '...', ...}}
    """
    try:
        if not feed_url:
            return {"error": "RSS 피드 URL을 입력해주세요."}

        if not feed_url.startswith(("http://", "https://")):
            feed_url = "https://" + feed_url

        # RSS 피드 가져오기
        result = rss_service.fetch_feed(feed_url)

        if not result:
            return {"error": f"RSS 피드를 가져오는데 실패했습니다: {feed_url}"}

        # 결과 제한
        limited_items = result.items[:max_items]

        # 결과 포맷팅
        formatted_items = []
        for item in limited_items:
            formatted_items.append({
                "title": item.title,
                "link": item.link,
                "description": item.description,
                "published": item.published,
                "content": item.content,
                "author": item.author,
                "categories": item.categories,
                "guid": item.guid,
            })

        return {
            "result": {
                "feed_url": result.feed_url,
                "feed_title": result.feed_title,
                "feed_description": result.feed_description,
                "feed_link": result.feed_link,
                "item_count": len(formatted_items),
                "items": formatted_items,
                "timestamp": result.timestamp,
            }
        }

    except Exception as e:
        return {"error": f"RSS 피드 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def search_rss_feed(feed_url: str, query: str, max_items: int = 20) -> dict:
    """
    RSS 피드에서 검색을 수행하고 결과를 반환합니다.

    Args:
        feed_url: RSS 피드 URL
        query: 검색 쿼리
        max_items: 반환할 최대 항목 수

    Returns:
        dict: 검색 결과를 포함한 딕셔너리

    Examples:
        >>> search_rss_feed("https://news.google.com/rss", "코로나")
        {'result': {'feed_url': 'https://news.google.com/rss', 'query': '코로나', ...}}
    """
    try:
        if not feed_url:
            return {"error": "RSS 피드 URL을 입력해주세요."}

        if not feed_url.startswith(("http://", "https://")):
            feed_url = "https://" + feed_url

        # RSS 피드 검색
        result = rss_service.search_feed(feed_url, query)

        if not result:
            return {"error": f"RSS 피드 검색에 실패했습니다: {feed_url}"}

        # 결과 제한
        limited_items = result.items[:max_items]

        # 결과 포맷팅
        formatted_items = []
        for item in limited_items:
            formatted_items.append({
                "title": item.title,
                "link": item.link,
                "description": item.description,
                "published": item.published,
                "content": item.content,
                "author": item.author,
                "categories": item.categories,
                "guid": item.guid,
            })

        return {
            "result": {
                "feed_url": result.feed_url,
                "feed_title": result.feed_title,
                "query": query,
                "match_count": len(formatted_items),
                "items": formatted_items,
                "timestamp": result.timestamp,
            }
        }

    except Exception as e:
        return {"error": f"RSS 피드 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_feed_content(feed_url: str, item_index: int = 0) -> dict:
    """
    RSS 피드의 특정 항목 내용을 가져옵니다.

    Args:
        feed_url: RSS 피드 URL
        item_index: 가져올 항목의 인덱스 (0부터 시작)

    Returns:
        dict: 항목 내용을 포함한 딕셔너리

    Examples:
        >>> get_feed_content("https://news.google.com/rss", 0)
        {'result': {'title': '...', 'content': '...', ...}}
    """
    try:
        if not feed_url:
            return {"error": "RSS 피드 URL을 입력해주세요."}

        if not feed_url.startswith(("http://", "https://")):
            feed_url = "https://" + feed_url

        # RSS 피드 가져오기
        result = rss_service.fetch_feed(feed_url)

        if not result:
            return {"error": f"RSS 피드를 가져오는데 실패했습니다: {feed_url}"}

        # 항목 인덱스 확인
        if item_index < 0 or item_index >= len(result.items):
            return {"error": f"유효하지 않은 항목 인덱스입니다: {item_index}. 유효한 범위: 0-{len(result.items)-1}"}

        # 항목 가져오기
        item = result.items[item_index]

        return {
            "result": {
                "feed_title": result.feed_title,
                "title": item.title,
                "link": item.link,
                "published": item.published,
                "content": item.content,
                "author": item.author,
                "categories": item.categories,
                "timestamp": result.timestamp,
            }
        }

    except Exception as e:
        return {"error": f"RSS 피드 항목 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    RSS 피드 도구 정보를 반환합니다.

    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "RSS Feed Processor",
                "description": "RSS 피드를 처리하는 도구",
                "feedparser_available": FEEDPARSER_AVAILABLE,
                "tools": [
                    {"name": "get_rss_feed", "description": "RSS 피드를 가져오고 내용을 반환합니다"},
                    {"name": "search_rss_feed", "description": "RSS 피드에서 검색을 수행하고 결과를 반환합니다"},
                    {"name": "get_feed_content", "description": "RSS 피드의 특정 항목 내용을 가져옵니다"},
                ],
                "usage_examples": [
                    {"command": "get_rss_feed('https://news.google.com/rss')", "description": "Google 뉴스 RSS 피드 가져오기"},
                    {"command": "search_rss_feed('https://news.google.com/rss', '코로나')", "description": "'코로나' 관련 뉴스 검색"},
                    {"command": "get_feed_content('https://news.google.com/rss', 0)", "description": "첫 번째 뉴스 항목의 내용 가져오기"},
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
        logger.error("rss_feed.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise