#!/usr/bin/env python3
"""
Confluence API MCP Server
Confluence REST API를 통해 페이지를 검색하고 다양한 정보를 조회하는 도구를 제공합니다.
LLM을 통한 Confluence의 다양한 데이터를 가져오는 읽기 전용 도구입니다.
"""

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import requests
from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 confluence_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "confluence_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("CONFLUENCE_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Confluence Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Confluence API Server",
    description="A server for Confluence API operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
USER_AGENT = "Confluence-API-MCP-Tool/1.0"


@dataclass
class ConfluenceUser:
    """Confluence 사용자 정보를 담는 데이터 클래스"""
    account_id: str
    display_name: str
    email: str = ""
    active: bool = True
    avatar_url: str = ""
    time_zone: str = ""
    locale: str = ""


@dataclass
class ConfluenceSpace:
    """Confluence 스페이스 정보를 담는 데이터 클래스"""
    id: str
    key: str
    name: str
    type: str  # personal, global 등
    description: str = ""
    homepage_id: str = ""
    created_date: str = ""
    created_by: ConfluenceUser = None
    status: str = "current"


@dataclass
class ConfluencePageVersion:
    """Confluence 페이지 버전 정보를 담는 데이터 클래스"""
    number: int
    when: str
    message: str = ""
    by: ConfluenceUser = None


@dataclass
class ConfluencePage:
    """Confluence 페이지 정보를 담는 데이터 클래스"""
    id: str
    title: str
    space_key: str
    version: ConfluencePageVersion = None
    status: str = "current"
    type: str = "page"  # page, blogpost 등
    created_date: str = ""
    created_by: ConfluenceUser = None
    last_updated: str = ""
    last_updated_by: ConfluenceUser = None
    content: str = ""
    body: Dict = field(default_factory=dict)
    ancestors: List[Dict] = field(default_factory=list)
    children: List[Dict] = field(default_factory=list)
    descendants: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    labels: List[Dict] = field(default_factory=list)


@dataclass
class ConfluenceSearchResult:
    """Confluence 검색 결과를 담는 데이터 클래스"""
    total: int
    start: int
    limit: int
    size: int
    results: List[ConfluencePage] = field(default_factory=list)


@dataclass
class ConfluenceAttachment:
    """Confluence 첨부 파일 정보를 담는 데이터 클래스"""
    id: str
    title: str
    filename: str
    media_type: str
    file_size: int
    created: str
    creator: ConfluenceUser = None
    comment: str = ""
    download_url: str = ""


@dataclass
class ConfluenceComment:
    """Confluence 코멘트 정보를 담는 데이터 클래스"""
    id: str
    type: str  # comment, page 등
    content: str
    created: str
    updated: str
    author: ConfluenceUser = None
    parent_id: str = ""
    parent_type: str = ""
    container_id: str = ""
    container_type: str = ""


class ConfluenceAPIService:
    """Confluence API 서비스 클래스"""

    def __init__(self, base_url: str = None, username: str = None, api_token: str = None):
        """
        Confluence API 서비스 초기화
        
        Args:
            base_url: Confluence 인스턴스 URL (없으면 환경 변수에서 가져옴)
            username: Confluence 사용자명 (없으면 환경 변수에서 가져옴)
            api_token: Confluence API 토큰 (없으면 환경 변수에서 가져옴)
        """
        self.base_url = base_url or os.getenv("CONFLUENCE_BASE_URL", "")
        self.username = username or os.getenv("CONFLUENCE_USERNAME", "")
        self.api_token = api_token or os.getenv("CONFLUENCE_API_TOKEN", "")
        
        if not self.base_url:
            logger.warning("Confluence 인스턴스 URL이 설정되지 않았습니다.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        
        # 기본 인증 설정
        if self.username and self.api_token:
            self.session.auth = (self.username, self.api_token)
        else:
            logger.warning("Confluence 인증 정보가 설정되지 않았습니다. 인증이 필요한 API 호출은 실패할 수 있습니다.")

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        Confluence API 요청을 수행합니다.
        
        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE)
            endpoint: API 엔드포인트 경로
            params: URL 파라미터
            data: 요청 데이터
            
        Returns:
            Dict: API 응답 데이터
        """
        try:
            # API 요청 URL 구성
            url = f"{self.base_url.rstrip('/')}/rest/api/{endpoint.lstrip('/')}"
            
            # API 요청 수행
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # 응답 확인
            response.raise_for_status()
            
            # JSON 응답 반환
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Confluence API 요청 중 오류 발생: {e}")
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_message = f"HTTP 오류 {status_code}"
                
                try:
                    error_data = e.response.json()
                    if "message" in error_data:
                        error_message = f"{error_message}: {error_data['message']}"
                except:
                    pass
                
                logger.error(error_message)
                return {"error": error_message}
            
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Confluence API 요청 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_content(self, content_id: str, expand: List[str] = None) -> Optional[ConfluencePage]:
        """
        콘텐츠 ID로 콘텐츠 정보를 가져옵니다.
        
        Args:
            content_id: 콘텐츠 ID
            expand: 확장할 필드 목록
            
        Returns:
            ConfluencePage: 페이지 정보 객체 또는 None (실패 시)
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space", "ancestors", "children.page", "metadata", "history"]
            
            # 콘텐츠 요청 파라미터
            params = {
                "expand": ",".join(expand)
            }
            
            # 콘텐츠 API 호출
            response = self._make_request("GET", f"content/{content_id}", params=params)
            
            if "error" in response:
                logger.error(f"콘텐츠 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 페이지 정보 파싱
            page = self._parse_page(response)
            return page
            
        except Exception as e:
            logger.error(f"콘텐츠 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_page_by_title(self, space_key: str, title: str, expand: List[str] = None) -> Optional[ConfluencePage]:
        """
        스페이스 키와 제목으로 페이지 정보를 가져옵니다.
        
        Args:
            space_key: 스페이스 키
            title: 페이지 제목
            expand: 확장할 필드 목록
            
        Returns:
            ConfluencePage: 페이지 정보 객체 또는 None (실패 시)
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space", "ancestors", "children.page", "metadata"]
            
            # 콘텐츠 요청 파라미터
            params = {
                "spaceKey": space_key,
                "title": title,
                "expand": ",".join(expand)
            }
            
            # 콘텐츠 API 호출
            response = self._make_request("GET", "content", params=params)
            
            if "error" in response:
                logger.error(f"페이지 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 결과 확인
            results = response.get("results", [])
            if not results:
                logger.warning(f"페이지를 찾을 수 없습니다: {space_key}/{title}")
                return None
            
            # 첫 번째 결과 파싱
            page = self._parse_page(results[0])
            return page
            
        except Exception as e:
            logger.error(f"페이지 정보 가져오기 중 예외 발생: {e}")
            return None

    def search_content(self, cql: str, start: int = 0, limit: int = 25, expand: List[str] = None) -> ConfluenceSearchResult:
        """
        CQL을 사용하여 콘텐츠를 검색합니다.
        
        Args:
            cql: CQL 검색 쿼리
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            expand: 확장할 필드 목록
            
        Returns:
            ConfluenceSearchResult: 검색 결과 객체
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space"]
            
            # 검색 요청 파라미터
            params = {
                "cql": cql,
                "start": start,
                "limit": limit,
                "expand": ",".join(expand)
            }
            
            # 검색 API 호출
            response = self._make_request("GET", "content/search", params=params)
            
            if "error" in response:
                logger.error(f"콘텐츠 검색 중 오류: {response['error']}")
                return ConfluenceSearchResult(total=0, start=0, limit=0, size=0)
            
            # 검색 결과 파싱
            results = []
            for result_data in response.get("results", []):
                page = self._parse_page(result_data)
                results.append(page)
            
            # 검색 결과 객체 생성
            search_result = ConfluenceSearchResult(
                total=response.get("totalSize", 0),
                start=response.get("start", 0),
                limit=response.get("limit", 0),
                size=response.get("size", 0),
                results=results
            )
            
            return search_result
            
        except Exception as e:
            logger.error(f"콘텐츠 검색 중 예외 발생: {e}")
            return ConfluenceSearchResult(total=0, start=0, limit=0, size=0)

    def get_space(self, space_key: str, expand: List[str] = None) -> Optional[ConfluenceSpace]:
        """
        스페이스 키로 스페이스 정보를 가져옵니다.
        
        Args:
            space_key: 스페이스 키
            expand: 확장할 필드 목록
            
        Returns:
            ConfluenceSpace: 스페이스 정보 객체 또는 None (실패 시)
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["description", "homepage", "metadata"]
            
            # 스페이스 요청 파라미터
            params = {
                "spaceKey": space_key,
                "expand": ",".join(expand)
            }
            
            # 스페이스 API 호출
            response = self._make_request("GET", "space", params=params)
            
            if "error" in response:
                logger.error(f"스페이스 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 결과 확인
            results = response.get("results", [])
            if not results:
                logger.warning(f"스페이스를 찾을 수 없습니다: {space_key}")
                return None
            
            # 첫 번째 결과 파싱
            space_data = results[0]
            
            # 생성자 정보 파싱
            creator = None
            if "createdBy" in space_data:
                creator_data = space_data.get("createdBy", {})
                creator = ConfluenceUser(
                    account_id=creator_data.get("accountId", ""),
                    display_name=creator_data.get("displayName", ""),
                    email=creator_data.get("email", ""),
                    avatar_url=creator_data.get("profilePicture", {}).get("path", "")
                )
            
            # 스페이스 객체 생성
            space = ConfluenceSpace(
                id=space_data.get("id", ""),
                key=space_data.get("key", ""),
                name=space_data.get("name", ""),
                type=space_data.get("type", ""),
                description=space_data.get("description", {}).get("plain", {}).get("value", ""),
                homepage_id=space_data.get("homepage", {}).get("id", ""),
                created_date=space_data.get("created", ""),
                created_by=creator,
                status=space_data.get("status", "current")
            )
            
            return space
            
        except Exception as e:
            logger.error(f"스페이스 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_spaces(self, start: int = 0, limit: int = 25, type: str = None, status: str = "current") -> List[ConfluenceSpace]:
        """
        스페이스 목록을 가져옵니다.
        
        Args:
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            type: 스페이스 타입 (global, personal)
            status: 스페이스 상태 (current, archived)
            
        Returns:
            List[ConfluenceSpace]: 스페이스 목록
        """
        try:
            # 스페이스 요청 파라미터
            params = {
                "start": start,
                "limit": limit,
                "status": status,
                "expand": "description,homepage"
            }
            
            if type:
                params["type"] = type
            
            # 스페이스 API 호출
            response = self._make_request("GET", "space", params=params)
            
            if "error" in response:
                logger.error(f"스페이스 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 스페이스 목록 파싱
            spaces = []
            for space_data in response.get("results", []):
                # 생성자 정보 파싱
                creator = None
                if "createdBy" in space_data:
                    creator_data = space_data.get("createdBy", {})
                    creator = ConfluenceUser(
                        account_id=creator_data.get("accountId", ""),
                        display_name=creator_data.get("displayName", ""),
                        email=creator_data.get("email", ""),
                        avatar_url=creator_data.get("profilePicture", {}).get("path", "")
                    )
                
                # 스페이스 객체 생성
                space = ConfluenceSpace(
                    id=space_data.get("id", ""),
                    key=space_data.get("key", ""),
                    name=space_data.get("name", ""),
                    type=space_data.get("type", ""),
                    description=space_data.get("description", {}).get("plain", {}).get("value", ""),
                    homepage_id=space_data.get("homepage", {}).get("id", ""),
                    created_date=space_data.get("created", ""),
                    created_by=creator,
                    status=space_data.get("status", "current")
                )
                spaces.append(space)
            
            return spaces
            
        except Exception as e:
            logger.error(f"스페이스 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_space_content(self, space_key: str, content_type: str = "page", start: int = 0, limit: int = 25, expand: List[str] = None) -> List[ConfluencePage]:
        """
        스페이스의 콘텐츠 목록을 가져옵니다.
        
        Args:
            space_key: 스페이스 키
            content_type: 콘텐츠 타입 (page, blogpost, comment, attachment)
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            expand: 확장할 필드 목록
            
        Returns:
            List[ConfluencePage]: 콘텐츠 목록
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space"]
            
            # 콘텐츠 요청 파라미터
            params = {
                "spaceKey": space_key,
                "type": content_type,
                "start": start,
                "limit": limit,
                "expand": ",".join(expand),
                "status": "current"
            }
            
            # 콘텐츠 API 호출
            response = self._make_request("GET", "content", params=params)
            
            if "error" in response:
                logger.error(f"스페이스 콘텐츠 가져오기 중 오류: {response['error']}")
                return []
            
            # 콘텐츠 목록 파싱
            pages = []
            for page_data in response.get("results", []):
                page = self._parse_page(page_data)
                pages.append(page)
            
            return pages
            
        except Exception as e:
            logger.error(f"스페이스 콘텐츠 가져오기 중 예외 발생: {e}")
            return []

    def get_page_children(self, page_id: str, start: int = 0, limit: int = 25, expand: List[str] = None) -> List[ConfluencePage]:
        """
        페이지의 하위 페이지 목록을 가져옵니다.
        
        Args:
            page_id: 페이지 ID
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            expand: 확장할 필드 목록
            
        Returns:
            List[ConfluencePage]: 하위 페이지 목록
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space"]
            
            # 하위 페이지 요청 파라미터
            params = {
                "start": start,
                "limit": limit,
                "expand": ",".join(expand)
            }
            
            # 하위 페이지 API 호출
            response = self._make_request("GET", f"content/{page_id}/child/page", params=params)
            
            if "error" in response:
                logger.error(f"하위 페이지 가져오기 중 오류: {response['error']}")
                return []
            
            # 하위 페이지 목록 파싱
            pages = []
            for page_data in response.get("results", []):
                page = self._parse_page(page_data)
                pages.append(page)
            
            return pages
            
        except Exception as e:
            logger.error(f"하위 페이지 가져오기 중 예외 발생: {e}")
            return []

    def get_page_attachments(self, page_id: str, start: int = 0, limit: int = 25, expand: List[str] = None) -> List[ConfluenceAttachment]:
        """
        페이지의 첨부 파일 목록을 가져옵니다.
        
        Args:
            page_id: 페이지 ID
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            expand: 확장할 필드 목록
            
        Returns:
            List[ConfluenceAttachment]: 첨부 파일 목록
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["version", "container"]
            
            # 첨부 파일 요청 파라미터
            params = {
                "start": start,
                "limit": limit,
                "expand": ",".join(expand)
            }
            
            # 첨부 파일 API 호출
            response = self._make_request("GET", f"content/{page_id}/child/attachment", params=params)
            
            if "error" in response:
                logger.error(f"첨부 파일 가져오기 중 오류: {response['error']}")
                return []
            
            # 첨부 파일 목록 파싱
            attachments = []
            for attachment_data in response.get("results", []):
                # 생성자 정보 파싱
                creator = None
                if "by" in attachment_data.get("version", {}):
                    creator_data = attachment_data.get("version", {}).get("by", {})
                    creator = ConfluenceUser(
                        account_id=creator_data.get("accountId", ""),
                        display_name=creator_data.get("displayName", ""),
                        email=creator_data.get("email", ""),
                        avatar_url=creator_data.get("profilePicture", {}).get("path", "")
                    )
                
                # 첨부 파일 객체 생성
                attachment = ConfluenceAttachment(
                    id=attachment_data.get("id", ""),
                    title=attachment_data.get("title", ""),
                    filename=attachment_data.get("title", ""),
                    media_type=attachment_data.get("metadata", {}).get("mediaType", ""),
                    file_size=attachment_data.get("extensions", {}).get("fileSize", 0),
                    created=attachment_data.get("version", {}).get("when", ""),
                    creator=creator,
                    comment=attachment_data.get("metadata", {}).get("comment", ""),
                    download_url=f"{self.base_url}/download/attachments/{page_id}/{attachment_data.get('title', '')}"
                )
                attachments.append(attachment)
            
            return attachments
            
        except Exception as e:
            logger.error(f"첨부 파일 가져오기 중 예외 발생: {e}")
            return []

    def get_page_comments(self, page_id: str, start: int = 0, limit: int = 25, depth: str = "all") -> List[ConfluenceComment]:
        """
        페이지의 코멘트 목록을 가져옵니다.
        
        Args:
            page_id: 페이지 ID
            start: 결과 시작 인덱스
            limit: 최대 결과 수
            depth: 코멘트 깊이 (root, all)
            
        Returns:
            List[ConfluenceComment]: 코멘트 목록
        """
        try:
            # 코멘트 요청 파라미터
            params = {
                "start": start,
                "limit": limit,
                "depth": depth,
                "expand": "body.storage,version"
            }
            
            # 코멘트 API 호출
            response = self._make_request("GET", f"content/{page_id}/child/comment", params=params)
            
            if "error" in response:
                logger.error(f"코멘트 가져오기 중 오류: {response['error']}")
                return []
            
            # 코멘트 목록 파싱
            comments = []
            for comment_data in response.get("results", []):
                # 작성자 정보 파싱
                author = None
                if "by" in comment_data.get("version", {}):
                    author_data = comment_data.get("version", {}).get("by", {})
                    author = ConfluenceUser(
                        account_id=author_data.get("accountId", ""),
                        display_name=author_data.get("displayName", ""),
                        email=author_data.get("email", ""),
                        avatar_url=author_data.get("profilePicture", {}).get("path", "")
                    )
                
                # 코멘트 내용 추출
                content = ""
                if "body" in comment_data and "storage" in comment_data["body"]:
                    content = comment_data["body"]["storage"].get("value", "")
                
                # 코멘트 객체 생성
                comment = ConfluenceComment(
                    id=comment_data.get("id", ""),
                    type=comment_data.get("type", "comment"),
                    content=content,
                    created=comment_data.get("version", {}).get("when", ""),
                    updated=comment_data.get("version", {}).get("when", ""),
                    author=author,
                    parent_id=comment_data.get("ancestors", [{}])[-1].get("id", "") if comment_data.get("ancestors") else "",
                    parent_type=comment_data.get("ancestors", [{}])[-1].get("type", "") if comment_data.get("ancestors") else "",
                    container_id=page_id,
                    container_type="page"
                )
                comments.append(comment)
            
            return comments
            
        except Exception as e:
            logger.error(f"코멘트 가져오기 중 예외 발생: {e}")
            return []

    def get_content_by_id(self, content_id: str, expand: List[str] = None) -> Optional[Union[ConfluencePage, ConfluenceComment, ConfluenceAttachment]]:
        """
        콘텐츠 ID로 콘텐츠를 가져옵니다.
        
        Args:
            content_id: 콘텐츠 ID
            expand: 확장할 필드 목록
            
        Returns:
            Union[ConfluencePage, ConfluenceComment, ConfluenceAttachment]: 콘텐츠 객체 또는 None (실패 시)
        """
        try:
            # 기본 확장 필드 설정
            if expand is None:
                expand = ["body.storage", "version", "space", "ancestors", "children.page", "metadata"]
            
            # 콘텐츠 요청 파라미터
            params = {
                "expand": ",".join(expand)
            }
            
            # 콘텐츠 API 호출
            response = self._make_request("GET", f"content/{content_id}", params=params)
            
            if "error" in response:
                logger.error(f"콘텐츠 가져오기 중 오류: {response['error']}")
                return None
            
            # 콘텐츠 타입에 따라 파싱
            content_type = response.get("type", "")
            
            if content_type == "page" or content_type == "blogpost":
                return self._parse_page(response)
            elif content_type == "comment":
                return self._parse_comment(response)
            elif content_type == "attachment":
                return self._parse_attachment(response)
            else:
                logger.warning(f"지원되지 않는 콘텐츠 타입: {content_type}")
                return None
            
        except Exception as e:
            logger.error(f"콘텐츠 가져오기 중 예외 발생: {e}")
            return None

    def _parse_page(self, page_data: Dict) -> ConfluencePage:
        """
        페이지 데이터를 파싱하여 ConfluencePage 객체로 변환합니다.
        
        Args:
            page_data: Confluence API에서 반환된 페이지 데이터
            
        Returns:
            ConfluencePage: 파싱된 페이지 객체
        """
        try:
            # 버전 정보 파싱
            version = None
            if "version" in page_data:
                version_data = page_data.get("version", {})
                
                # 작성자 정보 파싱
                by = None
                if "by" in version_data:
                    by_data = version_data.get("by", {})
                    by = ConfluenceUser(
                        account_id=by_data.get("accountId", ""),
                        display_name=by_data.get("displayName", ""),
                        email=by_data.get("email", ""),
                        avatar_url=by_data.get("profilePicture", {}).get("path", "")
                    )
                
                version = ConfluencePageVersion(
                    number=version_data.get("number", 0),
                    when=version_data.get("when", ""),
                    message=version_data.get("message", ""),
                    by=by
                )
            
            # 생성자 정보 파싱
            created_by = None
            if "createdBy" in page_data:
                created_by_data = page_data.get("createdBy", {})
                created_by = ConfluenceUser(
                    account_id=created_by_data.get("accountId", ""),
                    display_name=created_by_data.get("displayName", ""),
                    email=created_by_data.get("email", ""),
                    avatar_url=created_by_data.get("profilePicture", {}).get("path", "")
                )
            
            # 최종 수정자 정보 파싱
            last_updated_by = None
            if "lastUpdatedBy" in page_data:
                last_updated_by_data = page_data.get("lastUpdatedBy", {})
                last_updated_by = ConfluenceUser(
                    account_id=last_updated_by_data.get("accountId", ""),
                    display_name=last_updated_by_data.get("displayName", ""),
                    email=last_updated_by_data.get("email", ""),
                    avatar_url=last_updated_by_data.get("profilePicture", {}).get("path", "")
                )
            
            # 콘텐츠 추출
            content = ""
            if "body" in page_data and "storage" in page_data["body"]:
                content = page_data["body"]["storage"].get("value", "")
            
            # 페이지 객체 생성
            page = ConfluencePage(
                id=page_data.get("id", ""),
                title=page_data.get("title", ""),
                space_key=page_data.get("space", {}).get("key", ""),
                version=version,
                status=page_data.get("status", "current"),
                type=page_data.get("type", "page"),
                created_date=page_data.get("created", ""),
                created_by=created_by,
                last_updated=page_data.get("lastUpdated", ""),
                last_updated_by=last_updated_by,
                content=content,
                body=page_data.get("body", {}),
                ancestors=page_data.get("ancestors", []),
                children=page_data.get("children", {}),
                descendants=page_data.get("descendants", {}),
                metadata=page_data.get("metadata", {}),
                labels=page_data.get("metadata", {}).get("labels", {}).get("results", [])
            )
            
            return page
            
        except Exception as e:
            logger.error(f"페이지 데이터 파싱 중 예외 발생: {e}")
            # 최소한의 페이지 객체 반환
            return ConfluencePage(
                id=page_data.get("id", ""),
                title=page_data.get("title", ""),
                space_key=page_data.get("space", {}).get("key", "")
            )

    def _parse_comment(self, comment_data: Dict) -> ConfluenceComment:
        """
        코멘트 데이터를 파싱하여 ConfluenceComment 객체로 변환합니다.
        
        Args:
            comment_data: Confluence API에서 반환된 코멘트 데이터
            
        Returns:
            ConfluenceComment: 파싱된 코멘트 객체
        """
        try:
            # 작성자 정보 파싱
            author = None
            if "version" in comment_data and "by" in comment_data["version"]:
                author_data = comment_data["version"]["by"]
                author = ConfluenceUser(
                    account_id=author_data.get("accountId", ""),
                    display_name=author_data.get("displayName", ""),
                    email=author_data.get("email", ""),
                    avatar_url=author_data.get("profilePicture", {}).get("path", "")
                )
            
            # 콘텐츠 추출
            content = ""
            if "body" in comment_data and "storage" in comment_data["body"]:
                content = comment_data["body"]["storage"].get("value", "")
            
            # 코멘트 객체 생성
            comment = ConfluenceComment(
                id=comment_data.get("id", ""),
                type=comment_data.get("type", "comment"),
                content=content,
                created=comment_data.get("version", {}).get("when", ""),
                updated=comment_data.get("version", {}).get("when", ""),
                author=author,
                parent_id=comment_data.get("ancestors", [{}])[-1].get("id", "") if comment_data.get("ancestors") else "",
                parent_type=comment_data.get("ancestors", [{}])[-1].get("type", "") if comment_data.get("ancestors") else "",
                container_id=comment_data.get("container", {}).get("id", ""),
                container_type=comment_data.get("container", {}).get("type", "")
            )
            
            return comment
            
        except Exception as e:
            logger.error(f"코멘트 데이터 파싱 중 예외 발생: {e}")
            # 최소한의 코멘트 객체 반환
            return ConfluenceComment(
                id=comment_data.get("id", ""),
                type=comment_data.get("type", "comment"),
                content="",
                created="",
                updated=""
            )

    def _parse_attachment(self, attachment_data: Dict) -> ConfluenceAttachment:
        """
        첨부 파일 데이터를 파싱하여 ConfluenceAttachment 객체로 변환합니다.
        
        Args:
            attachment_data: Confluence API에서 반환된 첨부 파일 데이터
            
        Returns:
            ConfluenceAttachment: 파싱된 첨부 파일 객체
        """
        try:
            # 생성자 정보 파싱
            creator = None
            if "version" in attachment_data and "by" in attachment_data["version"]:
                creator_data = attachment_data["version"]["by"]
                creator = ConfluenceUser(
                    account_id=creator_data.get("accountId", ""),
                    display_name=creator_data.get("displayName", ""),
                    email=creator_data.get("email", ""),
                    avatar_url=creator_data.get("profilePicture", {}).get("path", "")
                )
            
            # 첨부 파일 객체 생성
            attachment = ConfluenceAttachment(
                id=attachment_data.get("id", ""),
                title=attachment_data.get("title", ""),
                filename=attachment_data.get("title", ""),
                media_type=attachment_data.get("metadata", {}).get("mediaType", ""),
                file_size=attachment_data.get("extensions", {}).get("fileSize", 0),
                created=attachment_data.get("version", {}).get("when", ""),
                creator=creator,
                comment=attachment_data.get("metadata", {}).get("comment", ""),
                download_url=f"{self.base_url}/download/attachments/{attachment_data.get('container', {}).get('id', '')}/{attachment_data.get('title', '')}"
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"첨부 파일 데이터 파싱 중 예외 발생: {e}")
            # 최소한의 첨부 파일 객체 반환
            return ConfluenceAttachment(
                id=attachment_data.get("id", ""),
                title=attachment_data.get("title", ""),
                filename=attachment_data.get("title", ""),
                media_type="",
                file_size=0,
                created=""
            )


# 전역 서비스 인스턴스
confluence_api = ConfluenceAPIService()


@app.tool()
def search_content(cql: str, max_results: int = 20) -> dict:
    """
    CQL을 사용하여 Confluence 콘텐츠를 검색합니다.
    
    Args:
        cql: CQL 검색 쿼리 (예: "space = 'SPACE' AND type = 'page'")
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 검색 결과를 포함한 딕셔너리
        
    Examples:
        >>> search_content("space = 'SPACE' AND type = 'page'")
        {'result': {'total': 10, 'results': [...]}}
    """
    try:
        if not cql:
            return {"error": "CQL 쿼리를 입력해주세요."}
            
        # 콘텐츠 검색
        search_result = confluence_api.search_content(cql, limit=max_results)
        
        # 결과 포맷팅
        formatted_results = []
        for page in search_result.results:
            formatted_result = {
                "id": page.id,
                "title": page.title,
                "space_key": page.space_key,
                "type": page.type,
                "created_date": page.created_date,
                "last_updated": page.last_updated,
                "created_by": page.created_by.display_name if page.created_by else None,
                "content_preview": page.content[:200] + "..." if len(page.content) > 200 else page.content
            }
            formatted_results.append(formatted_result)
            
        return {
            "result": {
                "cql": cql,
                "total": search_result.total,
                "returned": len(formatted_results),
                "results": formatted_results
            }
        }
        
    except Exception as e:
        return {"error": f"콘텐츠 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_page_content(page_id: str = None, space_key: str = None, title: str = None) -> dict:
    """
    페이지 ID 또는 스페이스 키와 제목으로 페이지 내용을 가져옵니다.
    
    Args:
        page_id: 페이지 ID
        space_key: 스페이스 키 (page_id가 없을 경우 필요)
        title: 페이지 제목 (page_id가 없을 경우 필요)
        
    Returns:
        dict: 페이지 내용을 포함한 딕셔너리
        
    Examples:
        >>> get_page_content(page_id="123456")
        {'result': {'id': '123456', 'title': '...', 'content': '...'}}
        >>> get_page_content(space_key="SPACE", title="Home")
        {'result': {'id': '123456', 'title': 'Home', 'content': '...'}}
    """
    try:
        page = None
        
        # 페이지 ID로 조회
        if page_id:
            page = confluence_api.get_content(page_id)
        # 스페이스 키와 제목으로 조회
        elif space_key and title:
            page = confluence_api.get_page_by_title(space_key, title)
        else:
            return {"error": "페이지 ID 또는 스페이스 키와 제목을 입력해주세요."}
        
        if not page:
            return {"error": "페이지를 찾을 수 없습니다."}
            
        # 결과 포맷팅
        result = {
            "id": page.id,
            "title": page.title,
            "space_key": page.space_key,
            "content": page.content,
            "version": {
                "number": page.version.number if page.version else None,
                "when": page.version.when if page.version else None,
                "by": page.version.by.display_name if page.version and page.version.by else None
            },
            "created_date": page.created_date,
            "last_updated": page.last_updated,
            "created_by": page.created_by.display_name if page.created_by else None,
            "last_updated_by": page.last_updated_by.display_name if page.last_updated_by else None,
            "ancestors": [{"id": ancestor.get("id"), "title": ancestor.get("title")} for ancestor in page.ancestors],
            "labels": [label.get("name") for label in page.labels]
        }
            
        return {
            "result": result
        }
        
    except Exception as e:
        return {"error": f"페이지 내용 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_space_info(space_key: str) -> dict:
    """
    스페이스 키로 스페이스 정보를 가져옵니다.
    
    Args:
        space_key: 스페이스 키
        
    Returns:
        dict: 스페이스 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_space_info("SPACE")
        {'result': {'key': 'SPACE', 'name': '...', ...}}
    """
    try:
        if not space_key:
            return {"error": "스페이스 키를 입력해주세요."}
            
        # 스페이스 정보 가져오기
        space = confluence_api.get_space(space_key)
        
        if not space:
            return {"error": f"스페이스를 찾을 수 없습니다: {space_key}"}
            
        # 결과 포맷팅
        result = {
            "key": space.key,
            "name": space.name,
            "type": space.type,
            "description": space.description,
            "homepage_id": space.homepage_id,
            "created_date": space.created_date,
            "created_by": space.created_by.display_name if space.created_by else None,
            "status": space.status
        }
            
        return {
            "result": result
        }
        
    except Exception as e:
        return {"error": f"스페이스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_space_pages(space_key: str, max_results: int = 20) -> dict:
    """
    스페이스의 페이지 목록을 가져옵니다.
    
    Args:
        space_key: 스페이스 키
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 페이지 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_space_pages("SPACE")
        {'result': {'space_key': 'SPACE', 'pages': [...]}}
    """
    try:
        if not space_key:
            return {"error": "스페이스 키를 입력해주세요."}
            
        # 페이지 목록 가져오기
        pages = confluence_api.get_space_content(space_key, content_type="page", limit=max_results)
        
        # 결과 포맷팅
        formatted_pages = []
        for page in pages:
            formatted_page = {
                "id": page.id,
                "title": page.title,
                "created_date": page.created_date,
                "last_updated": page.last_updated,
                "created_by": page.created_by.display_name if page.created_by else None,
                "version": page.version.number if page.version else None,
                "has_children": bool(page.children.get("page", {}).get("results", [])) if page.children else False
            }
            formatted_pages.append(formatted_page)
            
        return {
            "result": {
                "space_key": space_key,
                "count": len(formatted_pages),
                "pages": formatted_pages
            }
        }
        
    except Exception as e:
        return {"error": f"스페이스 페이지 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_page_children_info(page_id: str, max_results: int = 20) -> dict:
    """
    페이지의 하위 페이지 목록을 가져옵니다.
    
    Args:
        page_id: 페이지 ID
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 하위 페이지 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_page_children_info("123456")
        {'result': {'page_id': '123456', 'children': [...]}}
    """
    try:
        if not page_id:
            return {"error": "페이지 ID를 입력해주세요."}
            
        # 하위 페이지 목록 가져오기
        children = confluence_api.get_page_children(page_id, limit=max_results)
        
        # 결과 포맷팅
        formatted_children = []
        for child in children:
            formatted_child = {
                "id": child.id,
                "title": child.title,
                "created_date": child.created_date,
                "last_updated": child.last_updated,
                "created_by": child.created_by.display_name if child.created_by else None,
                "version": child.version.number if child.version else None
            }
            formatted_children.append(formatted_child)
            
        return {
            "result": {
                "page_id": page_id,
                "count": len(formatted_children),
                "children": formatted_children
            }
        }
        
    except Exception as e:
        return {"error": f"하위 페이지 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_page_attachments_info(page_id: str, max_results: int = 20) -> dict:
    """
    페이지의 첨부 파일 목록을 가져옵니다.
    
    Args:
        page_id: 페이지 ID
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 첨부 파일 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_page_attachments_info("123456")
        {'result': {'page_id': '123456', 'attachments': [...]}}
    """
    try:
        if not page_id:
            return {"error": "페이지 ID를 입력해주세요."}
            
        # 첨부 파일 목록 가져오기
        attachments = confluence_api.get_page_attachments(page_id, limit=max_results)
        
        # 결과 포맷팅
        formatted_attachments = []
        for attachment in attachments:
            formatted_attachment = {
                "id": attachment.id,
                "title": attachment.title,
                "filename": attachment.filename,
                "media_type": attachment.media_type,
                "file_size": attachment.file_size,
                "created": attachment.created,
                "creator": attachment.creator.display_name if attachment.creator else None,
                "comment": attachment.comment,
                "download_url": attachment.download_url
            }
            formatted_attachments.append(formatted_attachment)
            
        return {
            "result": {
                "page_id": page_id,
                "count": len(formatted_attachments),
                "attachments": formatted_attachments
            }
        }
        
    except Exception as e:
        return {"error": f"첨부 파일 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_page_comments_info(page_id: str, max_results: int = 20) -> dict:
    """
    페이지의 코멘트 목록을 가져옵니다.
    
    Args:
        page_id: 페이지 ID
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 코멘트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_page_comments_info("123456")
        {'result': {'page_id': '123456', 'comments': [...]}}
    """
    try:
        if not page_id:
            return {"error": "페이지 ID를 입력해주세요."}
            
        # 코멘트 목록 가져오기
        comments = confluence_api.get_page_comments(page_id, limit=max_results)
        
        # 결과 포맷팅
        formatted_comments = []
        for comment in comments:
            formatted_comment = {
                "id": comment.id,
                "content": comment.content,
                "created": comment.created,
                "updated": comment.updated,
                "author": comment.author.display_name if comment.author else None,
                "parent_id": comment.parent_id
            }
            formatted_comments.append(formatted_comment)
            
        return {
            "result": {
                "page_id": page_id,
                "count": len(formatted_comments),
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        return {"error": f"코멘트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_spaces(max_results: int = 20, type: str = None) -> dict:
    """
    스페이스 목록을 가져옵니다.
    
    Args:
        max_results: 반환할 최대 결과 수
        type: 스페이스 타입 (global, personal)
        
    Returns:
        dict: 스페이스 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_spaces(type="global")
        {'result': {'spaces': [...]}}
    """
    try:
        # 스페이스 목록 가져오기
        spaces = confluence_api.get_spaces(limit=max_results, type=type)
        
        # 결과 포맷팅
        formatted_spaces = []
        for space in spaces:
            formatted_space = {
                "key": space.key,
                "name": space.name,
                "type": space.type,
                "description": space.description,
                "created_date": space.created_date,
                "created_by": space.created_by.display_name if space.created_by else None
            }
            formatted_spaces.append(formatted_space)
            
        return {
            "result": {
                "type_filter": type,
                "count": len(formatted_spaces),
                "spaces": formatted_spaces
            }
        }
        
    except Exception as e:
        return {"error": f"스페이스 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_content_by_label(label: str, space_key: str = None, max_results: int = 20) -> dict:
    """
    라벨로 콘텐츠를 검색합니다.
    
    Args:
        label: 라벨 이름
        space_key: 스페이스 키 (선택 사항)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 검색 결과를 포함한 딕셔너리
        
    Examples:
        >>> get_content_by_label("documentation", space_key="SPACE")
        {'result': {'label': 'documentation', 'results': [...]}}
    """
    try:
        if not label:
            return {"error": "라벨을 입력해주세요."}
            
        # CQL 쿼리 구성
        cql = f"label = '{label}'"
        if space_key:
            cql += f" AND space = '{space_key}'"
            
        # 콘텐츠 검색
        search_result = confluence_api.search_content(cql, limit=max_results)
        
        # 결과 포맷팅
        formatted_results = []
        for page in search_result.results:
            formatted_result = {
                "id": page.id,
                "title": page.title,
                "space_key": page.space_key,
                "type": page.type,
                "created_date": page.created_date,
                "last_updated": page.last_updated,
                "created_by": page.created_by.display_name if page.created_by else None
            }
            formatted_results.append(formatted_result)
            
        return {
            "result": {
                "label": label,
                "space_key": space_key,
                "total": search_result.total,
                "returned": len(formatted_results),
                "results": formatted_results
            }
        }
        
    except Exception as e:
        return {"error": f"라벨로 콘텐츠 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    Confluence API 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Confluence API Tool",
                "description": "Confluence REST API를 통해 페이지를 검색하고 다양한 정보를 조회하는 도구",
                "auth_status": "인증됨" if confluence_api.username and confluence_api.api_token else "인증되지 않음",
                "base_url": confluence_api.base_url or "설정되지 않음",
                "tools": [
                    {"name": "search_content", "description": "CQL을 사용하여 Confluence 콘텐츠를 검색합니다"},
                    {"name": "get_page_content", "description": "페이지 ID 또는 스페이스 키와 제목으로 페이지 내용을 가져옵니다"},
                    {"name": "get_space_info", "description": "스페이스 정보를 가져옵니다"},
                    {"name": "get_space_pages", "description": "스페이스의 페이지 목록을 가져옵니다"},
                    {"name": "get_page_children_info", "description": "페이지의 하위 페이지 목록을 가져옵니다"},
                    {"name": "get_page_attachments_info", "description": "페이지의 첨부 파일 목록을 가져옵니다"},
                    {"name": "get_page_comments_info", "description": "페이지의 코멘트 목록을 가져옵니다"},
                    {"name": "get_spaces", "description": "스페이스 목록을 가져옵니다"},
                    {"name": "get_content_by_label", "description": "라벨로 콘텐츠를 검색합니다"}
                ],
                "usage_examples": [
                    {"command": "search_content(\"space = 'SPACE' AND type = 'page'\")", "description": "SPACE 스페이스의 모든 페이지 검색"},
                    {"command": "get_page_content(space_key=\"SPACE\", title=\"Home\")", "description": "SPACE 스페이스의 Home 페이지 내용 가져오기"},
                    {"command": "get_space_pages(\"SPACE\")", "description": "SPACE 스페이스의 모든 페이지 목록 가져오기"},
                    {"command": "get_page_comments_info(\"123456\")", "description": "ID가 123456인 페이지의 코멘트 가져오기"}
                ],
                "authentication": {
                    "required": True,
                    "method": "Basic Authentication (username/API token)",
                    "environment_variables": [
                        "CONFLUENCE_BASE_URL - Confluence 인스턴스 URL",
                        "CONFLUENCE_USERNAME - Confluence 사용자명 또는 이메일",
                        "CONFLUENCE_API_TOKEN - Confluence API 토큰"
                    ]
                },
                "cql_examples": [
                    "space = 'SPACE' AND type = 'page'",
                    "space = 'SPACE' AND title ~ 'Home'",
                    "space = 'SPACE' AND label = 'documentation'",
                    "creator = 'admin' AND created > '2023-01-01'",
                    "lastmodified > now('-30d')"
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
        logger.error("confluence_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise