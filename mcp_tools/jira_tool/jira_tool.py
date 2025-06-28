#!/usr/bin/env python3
"""
Jira API MCP Server
Jira REST API를 통해 이슈를 검색하고 다양한 정보를 조회하는 도구를 제공합니다.
LLM을 통한 Jira의 다양한 데이터를 가져오는 읽기 전용 도구입니다.
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
# 프로젝트 루트에 jira_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "jira_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("JIRA_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Jira Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Jira API Server",
    description="A server for Jira API operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
USER_AGENT = "Jira-API-MCP-Tool/1.0"


@dataclass
class JiraUser:
    """Jira 사용자 정보를 담는 데이터 클래스"""
    account_id: str
    display_name: str
    email: str = ""
    active: bool = True
    avatar_url: str = ""
    time_zone: str = ""
    locale: str = ""


@dataclass
class JiraProject:
    """Jira 프로젝트 정보를 담는 데이터 클래스"""
    id: str
    key: str
    name: str
    description: str = ""
    lead: JiraUser = None
    url: str = ""
    category: str = ""
    project_type: str = ""
    simplified: bool = False
    style: str = ""
    is_private: bool = False


@dataclass
class JiraIssueType:
    """Jira 이슈 타입 정보를 담는 데이터 클래스"""
    id: str
    name: str
    description: str = ""
    icon_url: str = ""
    subtask: bool = False


@dataclass
class JiraStatus:
    """Jira 상태 정보를 담는 데이터 클래스"""
    id: str
    name: str
    description: str = ""
    category_name: str = ""
    color_name: str = ""
    status_category: str = ""


@dataclass
class JiraPriority:
    """Jira 우선순위 정보를 담는 데이터 클래스"""
    id: str
    name: str
    description: str = ""
    icon_url: str = ""


@dataclass
class JiraComment:
    """Jira 코멘트 정보를 담는 데이터 클래스"""
    id: str
    body: str
    author: JiraUser
    created: str
    updated: str
    jsd_public: bool = False
    visibility: Dict = field(default_factory=dict)


@dataclass
class JiraIssue:
    """Jira 이슈 정보를 담는 데이터 클래스"""
    id: str
    key: str
    summary: str
    description: str = ""
    project: JiraProject = None
    issue_type: JiraIssueType = None
    status: JiraStatus = None
    priority: JiraPriority = None
    assignee: JiraUser = None
    reporter: JiraUser = None
    created: str = ""
    updated: str = ""
    resolved: str = ""
    due_date: str = ""
    labels: List[str] = field(default_factory=list)
    components: List[Dict] = field(default_factory=list)
    fix_versions: List[Dict] = field(default_factory=list)
    affect_versions: List[Dict] = field(default_factory=list)
    comment_count: int = 0
    votes: int = 0
    watches: int = 0
    time_estimate: int = 0
    time_spent: int = 0
    original_estimate: int = 0
    remaining_estimate: int = 0
    custom_fields: Dict = field(default_factory=dict)


@dataclass
class JiraSearchResult:
    """Jira 검색 결과를 담는 데이터 클래스"""
    total: int
    start_at: int
    max_results: int
    issues: List[JiraIssue] = field(default_factory=list)


class JiraAPIService:
    """Jira API 서비스 클래스"""

    def __init__(self, base_url: str = None, username: str = None, api_token: str = None):
        """
        Jira API 서비스 초기화
        
        Args:
            base_url: Jira 인스턴스 URL (없으면 환경 변수에서 가져옴)
            username: Jira 사용자명 (없으면 환경 변수에서 가져옴)
            api_token: Jira API 토큰 (없으면 환경 변수에서 가져옴)
        """
        self.base_url = base_url or os.getenv("JIRA_BASE_URL", "")
        self.username = username or os.getenv("JIRA_USERNAME", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        
        if not self.base_url:
            logger.warning("Jira 인스턴스 URL이 설정되지 않았습니다.")
        
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
            logger.warning("Jira 인증 정보가 설정되지 않았습니다. 인증이 필요한 API 호출은 실패할 수 있습니다.")

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        Jira API 요청을 수행합니다.
        
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
            url = f"{self.base_url.rstrip('/')}/rest/api/3/{endpoint.lstrip('/')}"
            
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
            logger.error(f"Jira API 요청 중 오류 발생: {e}")
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_message = f"HTTP 오류 {status_code}"
                
                try:
                    error_data = e.response.json()
                    if "errorMessages" in error_data and error_data["errorMessages"]:
                        error_message = f"{error_message}: {error_data['errorMessages'][0]}"
                    elif "message" in error_data:
                        error_message = f"{error_message}: {error_data['message']}"
                except:
                    pass
                
                logger.error(error_message)
                return {"error": error_message}
            
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Jira API 요청 중 예외 발생: {e}")
            return {"error": str(e)}

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 50, fields: List[str] = None) -> JiraSearchResult:
        """
        JQL을 사용하여 이슈를 검색합니다.
        
        Args:
            jql: JQL 검색 쿼리
            start_at: 결과 시작 인덱스
            max_results: 최대 결과 수
            fields: 반환할 필드 목록
            
        Returns:
            JiraSearchResult: 검색 결과 객체
        """
        try:
            # 기본 필드 설정
            if fields is None:
                fields = [
                    "summary", "description", "status", "priority", "issuetype", 
                    "assignee", "reporter", "created", "updated", "resolutiondate", 
                    "duedate", "labels", "components", "fixVersions", "versions",
                    "comment", "votes", "watches", "timeestimate", "timespent",
                    "timeoriginalestimate", "timetracking", "project"
                ]
            
            # 검색 요청 파라미터
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ",".join(fields),
                "expand": "names,schema"
            }
            
            # 검색 API 호출
            response = self._make_request("GET", "search", params=params)
            
            if "error" in response:
                logger.error(f"이슈 검색 중 오류: {response['error']}")
                return JiraSearchResult(total=0, start_at=0, max_results=0)
            
            # 검색 결과 파싱
            issues = []
            for issue_data in response.get("issues", []):
                issue = self._parse_issue(issue_data)
                issues.append(issue)
            
            # 검색 결과 객체 생성
            search_result = JiraSearchResult(
                total=response.get("total", 0),
                start_at=response.get("startAt", 0),
                max_results=response.get("maxResults", 0),
                issues=issues
            )
            
            return search_result
            
        except Exception as e:
            logger.error(f"이슈 검색 중 예외 발생: {e}")
            return JiraSearchResult(total=0, start_at=0, max_results=0)

    def get_issue(self, issue_key: str, fields: List[str] = None) -> Optional[JiraIssue]:
        """
        이슈 키로 이슈 정보를 가져옵니다.
        
        Args:
            issue_key: 이슈 키 (예: PROJECT-123)
            fields: 반환할 필드 목록
            
        Returns:
            JiraIssue: 이슈 정보 객체 또는 None (실패 시)
        """
        try:
            # 기본 필드 설정
            if fields is None:
                fields = [
                    "summary", "description", "status", "priority", "issuetype", 
                    "assignee", "reporter", "created", "updated", "resolutiondate", 
                    "duedate", "labels", "components", "fixVersions", "versions",
                    "comment", "votes", "watches", "timeestimate", "timespent",
                    "timeoriginalestimate", "timetracking", "project"
                ]
            
            # 이슈 요청 파라미터
            params = {
                "fields": ",".join(fields),
                "expand": "names,schema"
            }
            
            # 이슈 API 호출
            response = self._make_request("GET", f"issue/{issue_key}", params=params)
            
            if "error" in response:
                logger.error(f"이슈 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 이슈 정보 파싱
            issue = self._parse_issue(response)
            return issue
            
        except Exception as e:
            logger.error(f"이슈 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_issue_comments(self, issue_key: str, start_at: int = 0, max_results: int = 50) -> List[JiraComment]:
        """
        이슈의 코멘트를 가져옵니다.
        
        Args:
            issue_key: 이슈 키 (예: PROJECT-123)
            start_at: 결과 시작 인덱스
            max_results: 최대 결과 수
            
        Returns:
            List[JiraComment]: 코멘트 목록
        """
        try:
            # 코멘트 요청 파라미터
            params = {
                "startAt": start_at,
                "maxResults": max_results,
                "expand": "renderedBody"
            }
            
            # 코멘트 API 호출
            response = self._make_request("GET", f"issue/{issue_key}/comment", params=params)
            
            if "error" in response:
                logger.error(f"이슈 코멘트 가져오기 중 오류: {response['error']}")
                return []
            
            # 코멘트 목록 파싱
            comments = []
            for comment_data in response.get("comments", []):
                # 작성자 정보 파싱
                author_data = comment_data.get("author", {})
                author = JiraUser(
                    account_id=author_data.get("accountId", ""),
                    display_name=author_data.get("displayName", ""),
                    email=author_data.get("emailAddress", ""),
                    active=author_data.get("active", True),
                    avatar_url=author_data.get("avatarUrls", {}).get("48x48", "")
                )
                
                # 코멘트 객체 생성
                comment = JiraComment(
                    id=comment_data.get("id", ""),
                    body=comment_data.get("body", ""),
                    author=author,
                    created=comment_data.get("created", ""),
                    updated=comment_data.get("updated", ""),
                    jsd_public=comment_data.get("jsdPublic", False),
                    visibility=comment_data.get("visibility", {})
                )
                comments.append(comment)
            
            return comments
            
        except Exception as e:
            logger.error(f"이슈 코멘트 가져오기 중 예외 발생: {e}")
            return []

    def get_project(self, project_key: str) -> Optional[JiraProject]:
        """
        프로젝트 키로 프로젝트 정보를 가져옵니다.
        
        Args:
            project_key: 프로젝트 키 (예: PROJECT)
            
        Returns:
            JiraProject: 프로젝트 정보 객체 또는 None (실패 시)
        """
        try:
            # 프로젝트 API 호출
            response = self._make_request("GET", f"project/{project_key}")
            
            if "error" in response:
                logger.error(f"프로젝트 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 프로젝트 리드 정보 파싱
            lead_data = response.get("lead", {})
            lead = JiraUser(
                account_id=lead_data.get("accountId", ""),
                display_name=lead_data.get("displayName", ""),
                email=lead_data.get("emailAddress", ""),
                active=lead_data.get("active", True),
                avatar_url=lead_data.get("avatarUrls", {}).get("48x48", "")
            )
            
            # 프로젝트 객체 생성
            project = JiraProject(
                id=response.get("id", ""),
                key=response.get("key", ""),
                name=response.get("name", ""),
                description=response.get("description", ""),
                lead=lead,
                url=response.get("url", ""),
                category=response.get("projectCategory", {}).get("name", ""),
                project_type=response.get("projectTypeKey", ""),
                simplified=response.get("simplified", False),
                style=response.get("style", ""),
                is_private=response.get("isPrivate", False)
            )
            
            return project
            
        except Exception as e:
            logger.error(f"프로젝트 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_user(self, account_id: str = None, username: str = None) -> Optional[JiraUser]:
        """
        사용자 정보를 가져옵니다.
        
        Args:
            account_id: 사용자 계정 ID
            username: 사용자명 (이메일 또는 사용자명)
            
        Returns:
            JiraUser: 사용자 정보 객체 또는 None (실패 시)
        """
        try:
            # 파라미터 검증
            if not account_id and not username:
                logger.error("사용자 정보를 가져오기 위해 account_id 또는 username이 필요합니다.")
                return None
            
            # 사용자 요청 파라미터
            params = {}
            if account_id:
                params["accountId"] = account_id
            elif username:
                params["username"] = username
            
            # 사용자 API 호출
            response = self._make_request("GET", "user", params=params)
            
            if "error" in response:
                logger.error(f"사용자 정보 가져오기 중 오류: {response['error']}")
                return None
            
            # 사용자 객체 생성
            user = JiraUser(
                account_id=response.get("accountId", ""),
                display_name=response.get("displayName", ""),
                email=response.get("emailAddress", ""),
                active=response.get("active", True),
                avatar_url=response.get("avatarUrls", {}).get("48x48", ""),
                time_zone=response.get("timeZone", ""),
                locale=response.get("locale", "")
            )
            
            return user
            
        except Exception as e:
            logger.error(f"사용자 정보 가져오기 중 예외 발생: {e}")
            return None

    def get_issue_types(self, project_key: str = None) -> List[JiraIssueType]:
        """
        이슈 타입 목록을 가져옵니다.
        
        Args:
            project_key: 프로젝트 키 (특정 프로젝트의 이슈 타입만 가져올 경우)
            
        Returns:
            List[JiraIssueType]: 이슈 타입 목록
        """
        try:
            # API 엔드포인트 결정
            endpoint = f"project/{project_key}/issuetypes" if project_key else "issuetype"
            
            # 이슈 타입 API 호출
            response = self._make_request("GET", endpoint)
            
            if "error" in response:
                logger.error(f"이슈 타입 가져오기 중 오류: {response['error']}")
                return []
            
            # 응답 형식에 따라 처리
            issue_types_data = response if isinstance(response, list) else []
            
            # 이슈 타입 목록 파싱
            issue_types = []
            for issue_type_data in issue_types_data:
                issue_type = JiraIssueType(
                    id=issue_type_data.get("id", ""),
                    name=issue_type_data.get("name", ""),
                    description=issue_type_data.get("description", ""),
                    icon_url=issue_type_data.get("iconUrl", ""),
                    subtask=issue_type_data.get("subtask", False)
                )
                issue_types.append(issue_type)
            
            return issue_types
            
        except Exception as e:
            logger.error(f"이슈 타입 가져오기 중 예외 발생: {e}")
            return []

    def get_statuses(self, project_key: str = None) -> List[JiraStatus]:
        """
        상태 목록을 가져옵니다.
        
        Args:
            project_key: 프로젝트 키 (특정 프로젝트의 상태만 가져올 경우)
            
        Returns:
            List[JiraStatus]: 상태 목록
        """
        try:
            # API 엔드포인트 결정
            endpoint = f"project/{project_key}/statuses" if project_key else "status"
            
            # 상태 API 호출
            response = self._make_request("GET", endpoint)
            
            if "error" in response:
                logger.error(f"상태 가져오기 중 오류: {response['error']}")
                return []
            
            # 응답 형식에 따라 처리
            statuses_data = []
            if project_key:
                # 프로젝트별 상태는 이슈 타입별로 그룹화되어 있음
                for issue_type_statuses in response:
                    for status_data in issue_type_statuses.get("statuses", []):
                        statuses_data.append(status_data)
            else:
                statuses_data = response if isinstance(response, list) else []
            
            # 중복 제거 (ID 기준)
            unique_statuses = {}
            for status_data in statuses_data:
                status_id = status_data.get("id", "")
                if status_id and status_id not in unique_statuses:
                    unique_statuses[status_id] = status_data
            
            # 상태 목록 파싱
            statuses = []
            for status_data in unique_statuses.values():
                status_category = status_data.get("statusCategory", {})
                status = JiraStatus(
                    id=status_data.get("id", ""),
                    name=status_data.get("name", ""),
                    description=status_data.get("description", ""),
                    category_name=status_category.get("name", ""),
                    color_name=status_category.get("colorName", ""),
                    status_category=status_category.get("key", "")
                )
                statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"상태 가져오기 중 예외 발생: {e}")
            return []

    def get_priorities(self) -> List[JiraPriority]:
        """
        우선순위 목록을 가져옵니다.
        
        Returns:
            List[JiraPriority]: 우선순위 목록
        """
        try:
            # 우선순위 API 호출
            response = self._make_request("GET", "priority")
            
            if "error" in response:
                logger.error(f"우선순위 가져오기 중 오류: {response['error']}")
                return []
            
            # 응답 형식에 따라 처리
            priorities_data = response if isinstance(response, list) else []
            
            # 우선순위 목록 파싱
            priorities = []
            for priority_data in priorities_data:
                priority = JiraPriority(
                    id=priority_data.get("id", ""),
                    name=priority_data.get("name", ""),
                    description=priority_data.get("description", ""),
                    icon_url=priority_data.get("iconUrl", "")
                )
                priorities.append(priority)
            
            return priorities
            
        except Exception as e:
            logger.error(f"우선순위 가져오기 중 예외 발생: {e}")
            return []

    def get_projects(self, recent: bool = False, max_results: int = 50) -> List[JiraProject]:
        """
        프로젝트 목록을 가져옵니다.
        
        Args:
            recent: 최근 프로젝트만 가져올지 여부
            max_results: 최대 결과 수
            
        Returns:
            List[JiraProject]: 프로젝트 목록
        """
        try:
            # API 엔드포인트 결정
            endpoint = "project/recent" if recent else "project"
            
            # 프로젝트 요청 파라미터
            params = {
                "maxResults": max_results
            }
            
            # 프로젝트 API 호출
            response = self._make_request("GET", endpoint, params=params)
            
            if "error" in response:
                logger.error(f"프로젝트 목록 가져오기 중 오류: {response['error']}")
                return []
            
            # 응답 형식에 따라 처리
            projects_data = response if isinstance(response, list) else []
            
            # 프로젝트 목록 파싱
            projects = []
            for project_data in projects_data:
                # 프로젝트 리드 정보 파싱
                lead_data = project_data.get("lead", {})
                lead = JiraUser(
                    account_id=lead_data.get("accountId", ""),
                    display_name=lead_data.get("displayName", ""),
                    email=lead_data.get("emailAddress", ""),
                    active=lead_data.get("active", True),
                    avatar_url=lead_data.get("avatarUrls", {}).get("48x48", "")
                )
                
                # 프로젝트 객체 생성
                project = JiraProject(
                    id=project_data.get("id", ""),
                    key=project_data.get("key", ""),
                    name=project_data.get("name", ""),
                    description=project_data.get("description", ""),
                    lead=lead,
                    url=project_data.get("url", ""),
                    category=project_data.get("projectCategory", {}).get("name", ""),
                    project_type=project_data.get("projectTypeKey", ""),
                    simplified=project_data.get("simplified", False),
                    style=project_data.get("style", ""),
                    is_private=project_data.get("isPrivate", False)
                )
                projects.append(project)
            
            return projects
            
        except Exception as e:
            logger.error(f"프로젝트 목록 가져오기 중 예외 발생: {e}")
            return []

    def _parse_issue(self, issue_data: Dict) -> JiraIssue:
        """
        이슈 데이터를 파싱하여 JiraIssue 객체로 변환합니다.
        
        Args:
            issue_data: Jira API에서 반환된 이슈 데이터
            
        Returns:
            JiraIssue: 파싱된 이슈 객체
        """
        try:
            # 필드 데이터 추출
            fields = issue_data.get("fields", {})
            
            # 프로젝트 정보 파싱
            project_data = fields.get("project", {})
            project = JiraProject(
                id=project_data.get("id", ""),
                key=project_data.get("key", ""),
                name=project_data.get("name", "")
            )
            
            # 이슈 타입 정보 파싱
            issue_type_data = fields.get("issuetype", {})
            issue_type = JiraIssueType(
                id=issue_type_data.get("id", ""),
                name=issue_type_data.get("name", ""),
                description=issue_type_data.get("description", ""),
                icon_url=issue_type_data.get("iconUrl", ""),
                subtask=issue_type_data.get("subtask", False)
            )
            
            # 상태 정보 파싱
            status_data = fields.get("status", {})
            status_category = status_data.get("statusCategory", {})
            status = JiraStatus(
                id=status_data.get("id", ""),
                name=status_data.get("name", ""),
                description=status_data.get("description", ""),
                category_name=status_category.get("name", ""),
                color_name=status_category.get("colorName", ""),
                status_category=status_category.get("key", "")
            )
            
            # 우선순위 정보 파싱
            priority_data = fields.get("priority", {})
            priority = None
            if priority_data:
                priority = JiraPriority(
                    id=priority_data.get("id", ""),
                    name=priority_data.get("name", ""),
                    description=priority_data.get("description", ""),
                    icon_url=priority_data.get("iconUrl", "")
                )
            
            # 담당자 정보 파싱
            assignee_data = fields.get("assignee", {})
            assignee = None
            if assignee_data:
                assignee = JiraUser(
                    account_id=assignee_data.get("accountId", ""),
                    display_name=assignee_data.get("displayName", ""),
                    email=assignee_data.get("emailAddress", ""),
                    active=assignee_data.get("active", True),
                    avatar_url=assignee_data.get("avatarUrls", {}).get("48x48", "")
                )
            
            # 보고자 정보 파싱
            reporter_data = fields.get("reporter", {})
            reporter = None
            if reporter_data:
                reporter = JiraUser(
                    account_id=reporter_data.get("accountId", ""),
                    display_name=reporter_data.get("displayName", ""),
                    email=reporter_data.get("emailAddress", ""),
                    active=reporter_data.get("active", True),
                    avatar_url=reporter_data.get("avatarUrls", {}).get("48x48", "")
                )
            
            # 코멘트 수 파싱
            comment_count = 0
            comment_data = fields.get("comment", {})
            if comment_data:
                comment_count = comment_data.get("total", 0)
            
            # 투표 수 파싱
            votes = 0
            votes_data = fields.get("votes", {})
            if votes_data:
                votes = votes_data.get("votes", 0)
            
            # 워치 수 파싱
            watches = 0
            watches_data = fields.get("watches", {})
            if watches_data:
                watches = watches_data.get("watchCount", 0)
            
            # 시간 추정치 파싱
            time_estimate = fields.get("timeestimate", 0) or 0
            time_spent = fields.get("timespent", 0) or 0
            original_estimate = fields.get("timeoriginalestimate", 0) or 0
            
            # 남은 시간 추정치 파싱
            remaining_estimate = time_estimate
            time_tracking = fields.get("timetracking", {})
            if time_tracking:
                remaining_estimate = time_tracking.get("remainingEstimateSeconds", time_estimate)
            
            # 커스텀 필드 파싱
            custom_fields = {}
            for field_name, field_value in fields.items():
                if field_name.startswith("customfield_") and field_value is not None:
                    custom_fields[field_name] = field_value
            
            # 이슈 객체 생성
            issue = JiraIssue(
                id=issue_data.get("id", ""),
                key=issue_data.get("key", ""),
                summary=fields.get("summary", ""),
                description=fields.get("description", ""),
                project=project,
                issue_type=issue_type,
                status=status,
                priority=priority,
                assignee=assignee,
                reporter=reporter,
                created=fields.get("created", ""),
                updated=fields.get("updated", ""),
                resolved=fields.get("resolutiondate", ""),
                due_date=fields.get("duedate", ""),
                labels=fields.get("labels", []),
                components=[comp.get("name", "") for comp in fields.get("components", [])],
                fix_versions=[ver.get("name", "") for ver in fields.get("fixVersions", [])],
                affect_versions=[ver.get("name", "") for ver in fields.get("versions", [])],
                comment_count=comment_count,
                votes=votes,
                watches=watches,
                time_estimate=time_estimate,
                time_spent=time_spent,
                original_estimate=original_estimate,
                remaining_estimate=remaining_estimate,
                custom_fields=custom_fields
            )
            
            return issue
            
        except Exception as e:
            logger.error(f"이슈 데이터 파싱 중 예외 발생: {e}")
            # 최소한의 이슈 객체 반환
            return JiraIssue(
                id=issue_data.get("id", ""),
                key=issue_data.get("key", ""),
                summary=issue_data.get("fields", {}).get("summary", "")
            )


# 전역 서비스 인스턴스
jira_api = JiraAPIService()


@app.tool()
def search_issues(jql: str, max_results: int = 20) -> dict:
    """
    JQL을 사용하여 Jira 이슈를 검색합니다.
    
    Args:
        jql: JQL 검색 쿼리 (예: "project = PROJECT AND status = 'In Progress'")
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 검색 결과를 포함한 딕셔너리
        
    Examples:
        >>> search_issues("project = PROJECT AND status = 'In Progress'")
        {'result': {'total': 10, 'issues': [...]}}
    """
    try:
        if not jql:
            return {"error": "JQL 쿼리를 입력해주세요."}
            
        # 이슈 검색
        search_result = jira_api.search_issues(jql, max_results=max_results)
        
        # 결과 포맷팅
        formatted_issues = []
        for issue in search_result.issues:
            formatted_issue = {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status.name if issue.status else None,
                "priority": issue.priority.name if issue.priority else None,
                "issue_type": issue.issue_type.name if issue.issue_type else None,
                "assignee": issue.assignee.display_name if issue.assignee else None,
                "reporter": issue.reporter.display_name if issue.reporter else None,
                "created": issue.created,
                "updated": issue.updated,
                "project": issue.project.key if issue.project else None,
                "comment_count": issue.comment_count,
                "labels": issue.labels
            }
            formatted_issues.append(formatted_issue)
            
        return {
            "result": {
                "jql": jql,
                "total": search_result.total,
                "returned": len(formatted_issues),
                "issues": formatted_issues
            }
        }
        
    except Exception as e:
        return {"error": f"이슈 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_issue_details(issue_key: str) -> dict:
    """
    이슈 키로 이슈의 상세 정보를 가져옵니다.
    
    Args:
        issue_key: 이슈 키 (예: PROJECT-123)
        
    Returns:
        dict: 이슈 상세 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_issue_details("PROJECT-123")
        {'result': {'key': 'PROJECT-123', 'summary': '...', ...}}
    """
    try:
        if not issue_key:
            return {"error": "이슈 키를 입력해주세요."}
            
        # 이슈 정보 가져오기
        issue = jira_api.get_issue(issue_key)
        
        if not issue:
            return {"error": f"이슈를 찾을 수 없습니다: {issue_key}"}
            
        # 결과 포맷팅
        result = {
            "key": issue.key,
            "summary": issue.summary,
            "description": issue.description,
            "status": {
                "name": issue.status.name if issue.status else None,
                "category": issue.status.status_category if issue.status else None
            },
            "priority": {
                "name": issue.priority.name if issue.priority else None,
                "icon_url": issue.priority.icon_url if issue.priority else None
            },
            "issue_type": {
                "name": issue.issue_type.name if issue.issue_type else None,
                "icon_url": issue.issue_type.icon_url if issue.issue_type else None,
                "subtask": issue.issue_type.subtask if issue.issue_type else False
            },
            "project": {
                "key": issue.project.key if issue.project else None,
                "name": issue.project.name if issue.project else None
            },
            "assignee": {
                "display_name": issue.assignee.display_name if issue.assignee else None,
                "email": issue.assignee.email if issue.assignee else None
            },
            "reporter": {
                "display_name": issue.reporter.display_name if issue.reporter else None,
                "email": issue.reporter.email if issue.reporter else None
            },
            "dates": {
                "created": issue.created,
                "updated": issue.updated,
                "resolved": issue.resolved,
                "due_date": issue.due_date
            },
            "labels": issue.labels,
            "components": issue.components,
            "fix_versions": issue.fix_versions,
            "affect_versions": issue.affect_versions,
            "comment_count": issue.comment_count,
            "votes": issue.votes,
            "watches": issue.watches,
            "time_tracking": {
                "original_estimate": issue.original_estimate,
                "time_spent": issue.time_spent,
                "remaining_estimate": issue.remaining_estimate
            }
        }
            
        return {
            "result": result
        }
        
    except Exception as e:
        return {"error": f"이슈 상세 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_issue_comments(issue_key: str, max_results: int = 50) -> dict:
    """
    이슈의 코멘트를 가져옵니다.
    
    Args:
        issue_key: 이슈 키 (예: PROJECT-123)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 코멘트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_issue_comments("PROJECT-123")
        {'result': {'issue_key': 'PROJECT-123', 'comments': [...]}}
    """
    try:
        if not issue_key:
            return {"error": "이슈 키를 입력해주세요."}
            
        # 코멘트 가져오기
        comments = jira_api.get_issue_comments(issue_key, max_results=max_results)
        
        # 결과 포맷팅
        formatted_comments = []
        for comment in comments:
            formatted_comment = {
                "id": comment.id,
                "body": comment.body,
                "author": {
                    "display_name": comment.author.display_name,
                    "email": comment.author.email
                },
                "created": comment.created,
                "updated": comment.updated,
                "jsd_public": comment.jsd_public
            }
            formatted_comments.append(formatted_comment)
            
        return {
            "result": {
                "issue_key": issue_key,
                "count": len(formatted_comments),
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        return {"error": f"이슈 코멘트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_project_info(project_key: str) -> dict:
    """
    프로젝트 정보를 가져옵니다.
    
    Args:
        project_key: 프로젝트 키 (예: PROJECT)
        
    Returns:
        dict: 프로젝트 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_project_info("PROJECT")
        {'result': {'key': 'PROJECT', 'name': '...', ...}}
    """
    try:
        if not project_key:
            return {"error": "프로젝트 키를 입력해주세요."}
            
        # 프로젝트 정보 가져오기
        project = jira_api.get_project(project_key)
        
        if not project:
            return {"error": f"프로젝트를 찾을 수 없습니다: {project_key}"}
            
        # 결과 포맷팅
        result = {
            "key": project.key,
            "name": project.name,
            "description": project.description,
            "lead": {
                "display_name": project.lead.display_name if project.lead else None,
                "email": project.lead.email if project.lead else None
            },
            "url": project.url,
            "category": project.category,
            "project_type": project.project_type,
            "simplified": project.simplified,
            "style": project.style,
            "is_private": project.is_private
        }
            
        return {
            "result": result
        }
        
    except Exception as e:
        return {"error": f"프로젝트 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_project_issues(project_key: str, status: str = None, max_results: int = 20) -> dict:
    """
    프로젝트의 이슈 목록을 가져옵니다.
    
    Args:
        project_key: 프로젝트 키 (예: PROJECT)
        status: 이슈 상태 필터 (예: "In Progress")
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 이슈 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_project_issues("PROJECT", status="In Progress")
        {'result': {'project_key': 'PROJECT', 'issues': [...]}}
    """
    try:
        if not project_key:
            return {"error": "프로젝트 키를 입력해주세요."}
            
        # JQL 쿼리 구성
        jql = f"project = {project_key}"
        if status:
            jql += f" AND status = '{status}'"
        jql += " ORDER BY updated DESC"
            
        # 이슈 검색
        search_result = jira_api.search_issues(jql, max_results=max_results)
        
        # 결과 포맷팅
        formatted_issues = []
        for issue in search_result.issues:
            formatted_issue = {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status.name if issue.status else None,
                "priority": issue.priority.name if issue.priority else None,
                "issue_type": issue.issue_type.name if issue.issue_type else None,
                "assignee": issue.assignee.display_name if issue.assignee else None,
                "created": issue.created,
                "updated": issue.updated
            }
            formatted_issues.append(formatted_issue)
            
        return {
            "result": {
                "project_key": project_key,
                "status_filter": status,
                "total": search_result.total,
                "returned": len(formatted_issues),
                "issues": formatted_issues
            }
        }
        
    except Exception as e:
        return {"error": f"프로젝트 이슈 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_user_issues(username: str, project_key: str = None, max_results: int = 20) -> dict:
    """
    사용자에게 할당된 이슈 목록을 가져옵니다.
    
    Args:
        username: 사용자명 또는 이메일
        project_key: 프로젝트 키 필터 (선택 사항)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 이슈 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_user_issues("user@example.com", project_key="PROJECT")
        {'result': {'username': 'user@example.com', 'issues': [...]}}
    """
    try:
        if not username:
            return {"error": "사용자명을 입력해주세요."}
            
        # JQL 쿼리 구성
        jql = f"assignee = '{username}'"
        if project_key:
            jql += f" AND project = {project_key}"
        jql += " ORDER BY updated DESC"
            
        # 이슈 검색
        search_result = jira_api.search_issues(jql, max_results=max_results)
        
        # 결과 포맷팅
        formatted_issues = []
        for issue in search_result.issues:
            formatted_issue = {
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status.name if issue.status else None,
                "priority": issue.priority.name if issue.priority else None,
                "issue_type": issue.issue_type.name if issue.issue_type else None,
                "project": issue.project.key if issue.project else None,
                "created": issue.created,
                "updated": issue.updated
            }
            formatted_issues.append(formatted_issue)
            
        return {
            "result": {
                "username": username,
                "project_filter": project_key,
                "total": search_result.total,
                "returned": len(formatted_issues),
                "issues": formatted_issues
            }
        }
        
    except Exception as e:
        return {"error": f"사용자 이슈 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_recent_projects(max_results: int = 10) -> dict:
    """
    최근 프로젝트 목록을 가져옵니다.
    
    Args:
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 프로젝트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_recent_projects()
        {'result': {'projects': [...]}}
    """
    try:
        # 최근 프로젝트 가져오기
        projects = jira_api.get_projects(recent=True, max_results=max_results)
        
        # 결과 포맷팅
        formatted_projects = []
        for project in projects:
            formatted_project = {
                "key": project.key,
                "name": project.name,
                "description": project.description,
                "lead": project.lead.display_name if project.lead else None,
                "category": project.category,
                "project_type": project.project_type
            }
            formatted_projects.append(formatted_project)
            
        return {
            "result": {
                "count": len(formatted_projects),
                "projects": formatted_projects
            }
        }
        
    except Exception as e:
        return {"error": f"최근 프로젝트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_issue_types_and_statuses(project_key: str = None) -> dict:
    """
    이슈 타입과 상태 목록을 가져옵니다.
    
    Args:
        project_key: 프로젝트 키 (특정 프로젝트의 이슈 타입과 상태만 가져올 경우)
        
    Returns:
        dict: 이슈 타입과 상태 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_issue_types_and_statuses("PROJECT")
        {'result': {'issue_types': [...], 'statuses': [...]}}
    """
    try:
        # 이슈 타입 가져오기
        issue_types = jira_api.get_issue_types(project_key)
        
        # 상태 가져오기
        statuses = jira_api.get_statuses(project_key)
        
        # 우선순위 가져오기
        priorities = jira_api.get_priorities()
        
        # 결과 포맷팅
        formatted_issue_types = []
        for issue_type in issue_types:
            formatted_issue_type = {
                "id": issue_type.id,
                "name": issue_type.name,
                "description": issue_type.description,
                "subtask": issue_type.subtask
            }
            formatted_issue_types.append(formatted_issue_type)
            
        formatted_statuses = []
        for status in statuses:
            formatted_status = {
                "id": status.id,
                "name": status.name,
                "category": status.status_category,
                "category_name": status.category_name,
                "color_name": status.color_name
            }
            formatted_statuses.append(formatted_status)
            
        formatted_priorities = []
        for priority in priorities:
            formatted_priority = {
                "id": priority.id,
                "name": priority.name,
                "description": priority.description
            }
            formatted_priorities.append(formatted_priority)
            
        return {
            "result": {
                "project_key": project_key,
                "issue_types": {
                    "count": len(formatted_issue_types),
                    "items": formatted_issue_types
                },
                "statuses": {
                    "count": len(formatted_statuses),
                    "items": formatted_statuses
                },
                "priorities": {
                    "count": len(formatted_priorities),
                    "items": formatted_priorities
                }
            }
        }
        
    except Exception as e:
        return {"error": f"이슈 타입과 상태 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    Jira API 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Jira API Tool",
                "description": "Jira REST API를 통해 이슈를 검색하고 다양한 정보를 조회하는 도구",
                "auth_status": "인증됨" if jira_api.username and jira_api.api_token else "인증되지 않음",
                "base_url": jira_api.base_url or "설정되지 않음",
                "tools": [
                    {"name": "search_issues", "description": "JQL을 사용하여 Jira 이슈를 검색합니다"},
                    {"name": "get_issue_details", "description": "이슈 키로 이슈의 상세 정보를 가져옵니다"},
                    {"name": "get_issue_comments", "description": "이슈의 코멘트를 가져옵니다"},
                    {"name": "get_project_info", "description": "프로젝트 정보를 가져옵니다"},
                    {"name": "get_project_issues", "description": "프로젝트의 이슈 목록을 가져옵니다"},
                    {"name": "get_user_issues", "description": "사용자에게 할당된 이슈 목록을 가져옵니다"},
                    {"name": "get_recent_projects", "description": "최근 프로젝트 목록을 가져옵니다"},
                    {"name": "get_issue_types_and_statuses", "description": "이슈 타입과 상태 목록을 가져옵니다"}
                ],
                "usage_examples": [
                    {"command": "search_issues(\"project = PROJECT AND status = 'In Progress'\")", "description": "진행 중인 이슈 검색"},
                    {"command": "get_issue_details(\"PROJECT-123\")", "description": "이슈 상세 정보 가져오기"},
                    {"command": "get_issue_comments(\"PROJECT-123\")", "description": "이슈 코멘트 가져오기"},
                    {"command": "get_project_issues(\"PROJECT\", status=\"Done\")", "description": "완료된 프로젝트 이슈 가져오기"}
                ],
                "authentication": {
                    "required": True,
                    "method": "Basic Authentication (username/API token)",
                    "environment_variables": [
                        "JIRA_BASE_URL - Jira 인스턴스 URL",
                        "JIRA_USERNAME - Jira 사용자명 또는 이메일",
                        "JIRA_API_TOKEN - Jira API 토큰"
                    ]
                }
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
        logger.error("jira_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise