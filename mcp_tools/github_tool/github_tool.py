#!/usr/bin/env python3
"""
GitHub API MCP Server
GitHub REST API를 통해 다양한 정보를 조회하고 결과를 제공하는 도구를 제공합니다.
코드 리뷰 활동 분석을 위한 다양한 기능을 포함합니다.
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
# 프로젝트 루트에 github_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "github_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("GITHUB_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("GitHub Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="GitHub API Server",
    description="A server for GitHub API operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
GITHUB_API_URL = "https://api.github.com"
USER_AGENT = "GitHub-API-MCP-Tool/1.0"


@dataclass
class GitHubUser:
    """GitHub 사용자 정보를 담는 데이터 클래스"""
    login: str
    id: int
    name: str = ""
    email: str = ""
    bio: str = ""
    company: str = ""
    location: str = ""
    avatar_url: str = ""
    html_url: str = ""
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class GitHubRepository:
    """GitHub 저장소 정보를 담는 데이터 클래스"""
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    description: str = ""
    html_url: str = ""
    language: str = ""
    default_branch: str = "main"
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    stargazers_count: int = 0
    watchers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0


@dataclass
class GitHubPullRequest:
    """GitHub PR 정보를 담는 데이터 클래스"""
    id: int
    number: int
    title: str
    state: str
    html_url: str
    user: GitHubUser
    body: str = ""
    created_at: str = ""
    updated_at: str = ""
    closed_at: str = ""
    merged_at: str = ""
    head: Dict = field(default_factory=dict)
    base: Dict = field(default_factory=dict)
    comments: int = 0
    review_comments: int = 0
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    merged: bool = False
    mergeable: bool = True
    draft: bool = False


@dataclass
class GitHubIssue:
    """GitHub 이슈 정보를 담는 데이터 클래스"""
    id: int
    number: int
    title: str
    state: str
    html_url: str
    user: GitHubUser
    body: str = ""
    created_at: str = ""
    updated_at: str = ""
    closed_at: str = ""
    comments: int = 0
    labels: List[Dict] = field(default_factory=list)
    assignees: List[Dict] = field(default_factory=list)
    milestone: Dict = field(default_factory=dict)
    pull_request: Dict = field(default_factory=dict)


@dataclass
class GitHubComment:
    """GitHub 코멘트 정보를 담는 데이터 클래스"""
    id: int
    body: str
    user: GitHubUser
    created_at: str
    updated_at: str
    html_url: str = ""
    path: str = ""  # 인라인 코멘트의 경우 파일 경로
    position: int = None  # 인라인 코멘트의 경우 위치
    line: int = None  # 인라인 코멘트의 경우 라인 번호
    commit_id: str = ""  # 인라인 코멘트의 경우 커밋 ID


@dataclass
class GitHubBranch:
    """GitHub 브랜치 정보를 담는 데이터 클래스"""
    name: str
    commit: Dict
    protected: bool = False
    protection: Dict = field(default_factory=dict)


@dataclass
class GitHubCommit:
    """GitHub 커밋 정보를 담는 데이터 클래스"""
    sha: str
    commit: Dict
    author: Dict
    committer: Dict
    html_url: str = ""
    parents: List[Dict] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


@dataclass
class GitHubFile:
    """GitHub 파일 변경 정보를 담는 데이터 클래스"""
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str = ""
    blob_url: str = ""
    raw_url: str = ""
    contents_url: str = ""


class GitHubAPIService:
    """GitHub API 서비스 클래스"""

    def __init__(self, token: str = None):
        """
        GitHub API 서비스 초기화
        
        Args:
            token: GitHub API 토큰 (없으면 환경 변수에서 가져옴)
        """
        self.token = token or os.getenv("GITHUB_API_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github.v3+json",
        })
        
        if self.token:
            self.session.headers.update({
                "Authorization": f"token {self.token}"
            })
        
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0

    def _make_request(self, method: str, url: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        GitHub API 요청을 수행합니다.
        
        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE)
            url: API 엔드포인트 URL
            params: URL 파라미터
            data: 요청 데이터
            
        Returns:
            Dict: API 응답 데이터
        """
        try:
            # Rate limit 확인 및 대기
            if self.rate_limit_remaining <= 1:
                wait_time = max(0, self.rate_limit_reset - time.time())
                if wait_time > 0:
                    logger.warning(f"GitHub API 속도 제한에 도달했습니다. {wait_time:.1f}초 대기 중...")
                    time.sleep(wait_time + 1)  # 여유있게 1초 추가
            
            # API 요청
            if not url.startswith("http"):
                url = f"{GITHUB_API_URL}/{url.lstrip('/')}"
                
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # Rate limit 정보 업데이트
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 5000))
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))
            
            # 응답 확인
            response.raise_for_status()
            
            # 페이지네이션 링크 확인
            pagination = {}
            if "Link" in response.headers:
                links = response.headers["Link"].split(",")
                for link in links:
                    if 'rel="next"' in link:
                        pagination["next"] = link.split(";")[0].strip(" <>")
                    elif 'rel="last"' in link:
                        pagination["last"] = link.split(";")[0].strip(" <>")
            
            # JSON 응답 반환
            result = response.json() if response.content else {}
            
            # 페이지네이션 정보 추가
            if pagination:
                if isinstance(result, list):
                    return {"items": result, "pagination": pagination}
                elif isinstance(result, dict):
                    result["pagination"] = pagination
                    return result
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API 요청 중 오류 발생: {e}")
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
            logger.error(f"GitHub API 요청 중 예외 발생: {e}")
            return {"error": str(e)}

    def get_user(self, username: str) -> Optional[GitHubUser]:
        """
        GitHub 사용자 정보를 가져옵니다.
        
        Args:
            username: GitHub 사용자명
            
        Returns:
            GitHubUser: 사용자 정보 객체 또는 None (실패 시)
        """
        try:
            response = self._make_request("GET", f"users/{username}")
            
            if "error" in response:
                return None
                
            return GitHubUser(
                login=response.get("login", ""),
                id=response.get("id", 0),
                name=response.get("name", ""),
                email=response.get("email", ""),
                bio=response.get("bio", ""),
                company=response.get("company", ""),
                location=response.get("location", ""),
                avatar_url=response.get("avatar_url", ""),
                html_url=response.get("html_url", ""),
                public_repos=response.get("public_repos", 0),
                followers=response.get("followers", 0),
                following=response.get("following", 0),
                created_at=response.get("created_at", ""),
                updated_at=response.get("updated_at", "")
            )
        except Exception as e:
            logger.error(f"사용자 정보 가져오기 중 오류 발생: {e}")
            return None

    def get_repository(self, owner: str, repo: str) -> Optional[GitHubRepository]:
        """
        GitHub 저장소 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            
        Returns:
            GitHubRepository: 저장소 정보 객체 또는 None (실패 시)
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}")
            
            if "error" in response:
                return None
                
            # 소유자 정보 파싱
            owner_data = response.get("owner", {})
            owner_obj = GitHubUser(
                login=owner_data.get("login", ""),
                id=owner_data.get("id", 0),
                avatar_url=owner_data.get("avatar_url", ""),
                html_url=owner_data.get("html_url", "")
            )
                
            return GitHubRepository(
                id=response.get("id", 0),
                name=response.get("name", ""),
                full_name=response.get("full_name", ""),
                owner=owner_obj,
                description=response.get("description", ""),
                html_url=response.get("html_url", ""),
                language=response.get("language", ""),
                default_branch=response.get("default_branch", "main"),
                created_at=response.get("created_at", ""),
                updated_at=response.get("updated_at", ""),
                pushed_at=response.get("pushed_at", ""),
                stargazers_count=response.get("stargazers_count", 0),
                watchers_count=response.get("watchers_count", 0),
                forks_count=response.get("forks_count", 0),
                open_issues_count=response.get("open_issues_count", 0)
            )
        except Exception as e:
            logger.error(f"저장소 정보 가져오기 중 오류 발생: {e}")
            return None

    def list_pull_requests(self, owner: str, repo: str, state: str = "all", per_page: int = 30) -> List[GitHubPullRequest]:
        """
        GitHub 저장소의 PR 목록을 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            state: PR 상태 (open, closed, all)
            per_page: 페이지당 결과 수
            
        Returns:
            List[GitHubPullRequest]: PR 목록
        """
        try:
            params = {
                "state": state,
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params=params)
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            pull_requests = []
            for item in items:
                # 사용자 정보 파싱
                user_data = item.get("user", {})
                user_obj = GitHubUser(
                    login=user_data.get("login", ""),
                    id=user_data.get("id", 0),
                    avatar_url=user_data.get("avatar_url", ""),
                    html_url=user_data.get("html_url", "")
                )
                
                pr = GitHubPullRequest(
                    id=item.get("id", 0),
                    number=item.get("number", 0),
                    title=item.get("title", ""),
                    state=item.get("state", ""),
                    html_url=item.get("html_url", ""),
                    user=user_obj,
                    body=item.get("body", ""),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    closed_at=item.get("closed_at", ""),
                    merged_at=item.get("merged_at", ""),
                    head=item.get("head", {}),
                    base=item.get("base", {}),
                    comments=item.get("comments", 0),
                    review_comments=item.get("review_comments", 0),
                    commits=item.get("commits", 0),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    changed_files=item.get("changed_files", 0),
                    merged=item.get("merged", False),
                    mergeable=item.get("mergeable", True),
                    draft=item.get("draft", False)
                )
                pull_requests.append(pr)
                
            return pull_requests
        except Exception as e:
            logger.error(f"PR 목록 가져오기 중 오류 발생: {e}")
            return []

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> Optional[GitHubPullRequest]:
        """
        GitHub 저장소의 특정 PR 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            pr_number: PR 번호
            
        Returns:
            GitHubPullRequest: PR 정보 객체 또는 None (실패 시)
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls/{pr_number}")
            
            if "error" in response:
                return None
                
            # 사용자 정보 파싱
            user_data = response.get("user", {})
            user_obj = GitHubUser(
                login=user_data.get("login", ""),
                id=user_data.get("id", 0),
                avatar_url=user_data.get("avatar_url", ""),
                html_url=user_data.get("html_url", "")
            )
            
            return GitHubPullRequest(
                id=response.get("id", 0),
                number=response.get("number", 0),
                title=response.get("title", ""),
                state=response.get("state", ""),
                html_url=response.get("html_url", ""),
                user=user_obj,
                body=response.get("body", ""),
                created_at=response.get("created_at", ""),
                updated_at=response.get("updated_at", ""),
                closed_at=response.get("closed_at", ""),
                merged_at=response.get("merged_at", ""),
                head=response.get("head", {}),
                base=response.get("base", {}),
                comments=response.get("comments", 0),
                review_comments=response.get("review_comments", 0),
                commits=response.get("commits", 0),
                additions=response.get("additions", 0),
                deletions=response.get("deletions", 0),
                changed_files=response.get("changed_files", 0),
                merged=response.get("merged", False),
                mergeable=response.get("mergeable", True),
                draft=response.get("draft", False)
            )
        except Exception as e:
            logger.error(f"PR 정보 가져오기 중 오류 발생: {e}")
            return None

    def list_issues(self, owner: str, repo: str, state: str = "all", per_page: int = 30) -> List[GitHubIssue]:
        """
        GitHub 저장소의 이슈 목록을 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            state: 이슈 상태 (open, closed, all)
            per_page: 페이지당 결과 수
            
        Returns:
            List[GitHubIssue]: 이슈 목록
        """
        try:
            params = {
                "state": state,
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues", params=params)
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            issues = []
            for item in items:
                # PR인 경우 건너뛰기 (PR은 이슈이기도 함)
                if "pull_request" in item:
                    continue
                    
                # 사용자 정보 파싱
                user_data = item.get("user", {})
                user_obj = GitHubUser(
                    login=user_data.get("login", ""),
                    id=user_data.get("id", 0),
                    avatar_url=user_data.get("avatar_url", ""),
                    html_url=user_data.get("html_url", "")
                )
                
                issue = GitHubIssue(
                    id=item.get("id", 0),
                    number=item.get("number", 0),
                    title=item.get("title", ""),
                    state=item.get("state", ""),
                    html_url=item.get("html_url", ""),
                    user=user_obj,
                    body=item.get("body", ""),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    closed_at=item.get("closed_at", ""),
                    comments=item.get("comments", 0),
                    labels=item.get("labels", []),
                    assignees=item.get("assignees", []),
                    milestone=item.get("milestone", {}),
                    pull_request=item.get("pull_request", {})
                )
                issues.append(issue)
                
            return issues
        except Exception as e:
            logger.error(f"이슈 목록 가져오기 중 오류 발생: {e}")
            return []

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[GitHubIssue]:
        """
        GitHub 저장소의 특정 이슈 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            issue_number: 이슈 번호
            
        Returns:
            GitHubIssue: 이슈 정보 객체 또는 None (실패 시)
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues/{issue_number}")
            
            if "error" in response:
                return None
                
            # 사용자 정보 파싱
            user_data = response.get("user", {})
            user_obj = GitHubUser(
                login=user_data.get("login", ""),
                id=user_data.get("id", 0),
                avatar_url=user_data.get("avatar_url", ""),
                html_url=user_data.get("html_url", "")
            )
            
            return GitHubIssue(
                id=response.get("id", 0),
                number=response.get("number", 0),
                title=response.get("title", ""),
                state=response.get("state", ""),
                html_url=response.get("html_url", ""),
                user=user_obj,
                body=response.get("body", ""),
                created_at=response.get("created_at", ""),
                updated_at=response.get("updated_at", ""),
                closed_at=response.get("closed_at", ""),
                comments=response.get("comments", 0),
                labels=response.get("labels", []),
                assignees=response.get("assignees", []),
                milestone=response.get("milestone", {}),
                pull_request=response.get("pull_request", {})
            )
        except Exception as e:
            logger.error(f"이슈 정보 가져오기 중 오류 발생: {e}")
            return None

    def get_pr_inline_comments(self, owner: str, repo: str, pr_number: int) -> List[GitHubComment]:
        """
        PR에 등록된 인라인 코멘트를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            pr_number: PR 번호
            
        Returns:
            List[GitHubComment]: 인라인 코멘트 목록
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls/{pr_number}/comments")
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            comments = []
            for item in items:
                # 사용자 정보 파싱
                user_data = item.get("user", {})
                user_obj = GitHubUser(
                    login=user_data.get("login", ""),
                    id=user_data.get("id", 0),
                    avatar_url=user_data.get("avatar_url", ""),
                    html_url=user_data.get("html_url", "")
                )
                
                comment = GitHubComment(
                    id=item.get("id", 0),
                    body=item.get("body", ""),
                    user=user_obj,
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    html_url=item.get("html_url", ""),
                    path=item.get("path", ""),
                    position=item.get("position"),
                    line=item.get("line"),
                    commit_id=item.get("commit_id", "")
                )
                comments.append(comment)
                
            return comments
        except Exception as e:
            logger.error(f"PR 인라인 코멘트 가져오기 중 오류 발생: {e}")
            return []

    def get_pr_issue_comments(self, owner: str, repo: str, pr_number: int) -> List[GitHubComment]:
        """
        PR에 등록된 이슈 코멘트를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            pr_number: PR 번호
            
        Returns:
            List[GitHubComment]: 이슈 코멘트 목록
        """
        try:
            # PR은 이슈이기도 하므로 이슈 코멘트 API 사용
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues/{pr_number}/comments")
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            comments = []
            for item in items:
                # 사용자 정보 파싱
                user_data = item.get("user", {})
                user_obj = GitHubUser(
                    login=user_data.get("login", ""),
                    id=user_data.get("id", 0),
                    avatar_url=user_data.get("avatar_url", ""),
                    html_url=user_data.get("html_url", "")
                )
                
                comment = GitHubComment(
                    id=item.get("id", 0),
                    body=item.get("body", ""),
                    user=user_obj,
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    html_url=item.get("html_url", "")
                )
                comments.append(comment)
                
            return comments
        except Exception as e:
            logger.error(f"PR 이슈 코멘트 가져오기 중 오류 발생: {e}")
            return []

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[GitHubComment]:
        """
        이슈에 등록된 코멘트를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            issue_number: 이슈 번호
            
        Returns:
            List[GitHubComment]: 코멘트 목록
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues/{issue_number}/comments")
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            comments = []
            for item in items:
                # 사용자 정보 파싱
                user_data = item.get("user", {})
                user_obj = GitHubUser(
                    login=user_data.get("login", ""),
                    id=user_data.get("id", 0),
                    avatar_url=user_data.get("avatar_url", ""),
                    html_url=user_data.get("html_url", "")
                )
                
                comment = GitHubComment(
                    id=item.get("id", 0),
                    body=item.get("body", ""),
                    user=user_obj,
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    html_url=item.get("html_url", "")
                )
                comments.append(comment)
                
            return comments
        except Exception as e:
            logger.error(f"이슈 코멘트 가져오기 중 오류 발생: {e}")
            return []

    def list_branches(self, owner: str, repo: str) -> List[GitHubBranch]:
        """
        저장소의 브랜치 목록을 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            
        Returns:
            List[GitHubBranch]: 브랜치 목록
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/branches")
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            branches = []
            for item in items:
                branch = GitHubBranch(
                    name=item.get("name", ""),
                    commit=item.get("commit", {}),
                    protected=item.get("protected", False),
                    protection=item.get("protection", {})
                )
                branches.append(branch)
                
            return branches
        except Exception as e:
            logger.error(f"브랜치 목록 가져오기 중 오류 발생: {e}")
            return []

    def list_commits(self, owner: str, repo: str, branch: str = None, per_page: int = 30) -> List[GitHubCommit]:
        """
        저장소의 커밋 목록을 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            branch: 브랜치 이름 (None이면 기본 브랜치)
            per_page: 페이지당 결과 수
            
        Returns:
            List[GitHubCommit]: 커밋 목록
        """
        try:
            params = {
                "per_page": per_page
            }
            
            if branch:
                params["sha"] = branch
                
            response = self._make_request("GET", f"repos/{owner}/{repo}/commits", params=params)
            
            if "error" in response:
                return []
                
            # 응답 형식에 따라 처리
            items = response if isinstance(response, list) else response.get("items", [])
            
            commits = []
            for item in items:
                commit = GitHubCommit(
                    sha=item.get("sha", ""),
                    commit=item.get("commit", {}),
                    author=item.get("author", {}),
                    committer=item.get("committer", {}),
                    html_url=item.get("html_url", ""),
                    parents=item.get("parents", [])
                )
                commits.append(commit)
                
            return commits
        except Exception as e:
            logger.error(f"커밋 목록 가져오기 중 오류 발생: {e}")
            return []

    def get_commit(self, owner: str, repo: str, commit_sha: str) -> Optional[GitHubCommit]:
        """
        특정 커밋 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            commit_sha: 커밋 SHA
            
        Returns:
            GitHubCommit: 커밋 정보 객체 또는 None (실패 시)
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/commits/{commit_sha}")
            
            if "error" in response:
                return None
                
            return GitHubCommit(
                sha=response.get("sha", ""),
                commit=response.get("commit", {}),
                author=response.get("author", {}),
                committer=response.get("committer", {}),
                html_url=response.get("html_url", ""),
                parents=response.get("parents", []),
                stats=response.get("stats", {})
            )
        except Exception as e:
            logger.error(f"커밋 정보 가져오기 중 오류 발생: {e}")
            return None

    def get_commit_files(self, owner: str, repo: str, commit_sha: str) -> List[GitHubFile]:
        """
        특정 커밋의 변경 파일 목록을 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            commit_sha: 커밋 SHA
            
        Returns:
            List[GitHubFile]: 변경 파일 목록
        """
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}/commits/{commit_sha}")
            
            if "error" in response:
                return []
                
            files_data = response.get("files", [])
            
            files = []
            for file_data in files_data:
                file = GitHubFile(
                    filename=file_data.get("filename", ""),
                    status=file_data.get("status", ""),
                    additions=file_data.get("additions", 0),
                    deletions=file_data.get("deletions", 0),
                    changes=file_data.get("changes", 0),
                    patch=file_data.get("patch", ""),
                    blob_url=file_data.get("blob_url", ""),
                    raw_url=file_data.get("raw_url", ""),
                    contents_url=file_data.get("contents_url", "")
                )
                files.append(file)
                
            return files
        except Exception as e:
            logger.error(f"커밋 파일 목록 가져오기 중 오류 발생: {e}")
            return []

    def get_pr_statistics(self, owner: str, repo: str, pr_number: int) -> Dict:
        """
        PR의 통계 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            pr_number: PR 번호
            
        Returns:
            Dict: PR 통계 정보
        """
        try:
            # PR 정보 가져오기
            pr = self.get_pull_request(owner, repo, pr_number)
            if not pr:
                return {"error": "PR 정보를 가져올 수 없습니다."}
                
            # PR 인라인 코멘트 가져오기
            inline_comments = self.get_pr_inline_comments(owner, repo, pr_number)
            
            # PR 이슈 코멘트 가져오기
            issue_comments = self.get_pr_issue_comments(owner, repo, pr_number)
            
            # 통계 계산
            reviewers = set()
            for comment in inline_comments + issue_comments:
                reviewers.add(comment.user.login)
                
            # PR 작성자 제외
            if pr.user.login in reviewers:
                reviewers.remove(pr.user.login)
                
            # 파일별 코멘트 수 계산
            file_comments = {}
            for comment in inline_comments:
                if comment.path:
                    if comment.path not in file_comments:
                        file_comments[comment.path] = 0
                    file_comments[comment.path] += 1
            
            # 결과 반환
            return {
                "pr_number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "merged_at": pr.merged_at,
                "closed_at": pr.closed_at,
                "author": pr.user.login,
                "reviewers": list(reviewers),
                "reviewer_count": len(reviewers),
                "commits": pr.commits,
                "changed_files": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "inline_comments": len(inline_comments),
                "issue_comments": len(issue_comments),
                "total_comments": len(inline_comments) + len(issue_comments),
                "file_comments": file_comments,
                "most_commented_files": sorted(file_comments.items(), key=lambda x: x[1], reverse=True)[:5] if file_comments else []
            }
        except Exception as e:
            logger.error(f"PR 통계 정보 가져오기 중 오류 발생: {e}")
            return {"error": str(e)}

    def get_user_activity(self, owner: str, repo: str, username: str) -> Dict:
        """
        특정 사용자의 저장소 활동 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            username: GitHub 사용자명
            
        Returns:
            Dict: 사용자 활동 정보
        """
        try:
            # 사용자가 작성한 PR 목록
            authored_prs = []
            params = {
                "state": "all",
                "per_page": 100,
                "creator": username
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params=params)
            if not "error" in response:
                items = response if isinstance(response, list) else response.get("items", [])
                for item in items:
                    authored_prs.append({
                        "number": item.get("number", 0),
                        "title": item.get("title", ""),
                        "state": item.get("state", ""),
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", ""),
                        "html_url": item.get("html_url", "")
                    })
            
            # 사용자가 작성한 이슈 목록
            authored_issues = []
            params = {
                "state": "all",
                "per_page": 100,
                "creator": username
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues", params=params)
            if not "error" in response:
                items = response if isinstance(response, list) else response.get("items", [])
                for item in items:
                    # PR이 아닌 이슈만 추가
                    if "pull_request" not in item:
                        authored_issues.append({
                            "number": item.get("number", 0),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "html_url": item.get("html_url", "")
                        })
            
            # 사용자가 리뷰한 PR 목록 (코멘트를 남긴 PR)
            reviewed_prs = set()
            
            # 모든 PR 목록 가져오기
            params = {
                "state": "all",
                "per_page": 100
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params=params)
            if not "error" in response:
                items = response if isinstance(response, list) else response.get("items", [])
                for item in items:
                    pr_number = item.get("number", 0)
                    
                    # PR 인라인 코멘트 확인
                    inline_comments = self.get_pr_inline_comments(owner, repo, pr_number)
                    for comment in inline_comments:
                        if comment.user.login == username:
                            reviewed_prs.add(pr_number)
                            break
                    
                    # 이미 리뷰한 것으로 확인되면 다음 PR로
                    if pr_number in reviewed_prs:
                        continue
                        
                    # PR 이슈 코멘트 확인
                    issue_comments = self.get_pr_issue_comments(owner, repo, pr_number)
                    for comment in issue_comments:
                        if comment.user.login == username:
                            reviewed_prs.add(pr_number)
                            break
            
            # 결과 반환
            return {
                "username": username,
                "repository": f"{owner}/{repo}",
                "authored_prs_count": len(authored_prs),
                "authored_prs": authored_prs[:10],  # 최근 10개만 반환
                "authored_issues_count": len(authored_issues),
                "authored_issues": authored_issues[:10],  # 최근 10개만 반환
                "reviewed_prs_count": len(reviewed_prs),
                "reviewed_prs": list(reviewed_prs)[:10]  # 최근 10개만 반환
            }
        except Exception as e:
            logger.error(f"사용자 활동 정보 가져오기 중 오류 발생: {e}")
            return {"error": str(e)}

    def analyze_code_review_patterns(self, owner: str, repo: str, pr_count: int = 30) -> Dict:
        """
        저장소의 코드 리뷰 패턴을 분석합니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            pr_count: 분석할 PR 수
            
        Returns:
            Dict: 코드 리뷰 패턴 분석 결과
        """
        try:
            # 최근 PR 목록 가져오기
            params = {
                "state": "all",
                "per_page": pr_count,
                "sort": "updated",
                "direction": "desc"
            }
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params=params)
            if "error" in response:
                return {"error": "PR 목록을 가져올 수 없습니다."}
                
            items = response if isinstance(response, list) else response.get("items", [])
            
            # 분석 데이터 초기화
            total_prs = len(items)
            merged_prs = 0
            closed_without_merge = 0
            open_prs = 0
            prs_with_comments = 0
            total_comments = 0
            total_inline_comments = 0
            total_issue_comments = 0
            total_reviewers = 0
            reviewer_counts = {}
            author_counts = {}
            time_to_first_review = []
            time_to_merge = []
            
            # PR별 분석
            for item in items:
                pr_number = item.get("number", 0)
                state = item.get("state", "")
                merged = item.get("merged", False)
                author = item.get("user", {}).get("login", "")
                
                # PR 상태 카운트
                if state == "open":
                    open_prs += 1
                elif merged:
                    merged_prs += 1
                else:
                    closed_without_merge += 1
                    
                # 작성자 카운트
                if author not in author_counts:
                    author_counts[author] = 0
                author_counts[author] += 1
                
                # PR 인라인 코멘트 분석
                inline_comments = self.get_pr_inline_comments(owner, repo, pr_number)
                total_inline_comments += len(inline_comments)
                
                # PR 이슈 코멘트 분석
                issue_comments = self.get_pr_issue_comments(owner, repo, pr_number)
                total_issue_comments += len(issue_comments)
                
                # 코멘트가 있는 PR 카운트
                if inline_comments or issue_comments:
                    prs_with_comments += 1
                    
                # 리뷰어 분석
                reviewers = set()
                for comment in inline_comments + issue_comments:
                    reviewer = comment.user.login
                    if reviewer != author:  # 작성자 제외
                        reviewers.add(reviewer)
                        if reviewer not in reviewer_counts:
                            reviewer_counts[reviewer] = 0
                        reviewer_counts[reviewer] += 1
                
                total_reviewers += len(reviewers)
                
                # 첫 리뷰까지 시간 계산
                if inline_comments or issue_comments:
                    created_at = datetime.fromisoformat(item.get("created_at", "").replace("Z", "+00:00"))
                    
                    # 모든 코멘트 시간 정렬
                    all_comments = inline_comments + issue_comments
                    if all_comments:
                        comment_times = [datetime.fromisoformat(c.created_at.replace("Z", "+00:00")) for c in all_comments if c.user.login != author]
                        if comment_times:
                            first_comment_time = min(comment_times)
                            review_time = (first_comment_time - created_at).total_seconds() / 3600  # 시간 단위
                            time_to_first_review.append(review_time)
                
                # 머지까지 시간 계산
                if merged:
                    created_at = datetime.fromisoformat(item.get("created_at", "").replace("Z", "+00:00"))
                    merged_at = datetime.fromisoformat(item.get("merged_at", "").replace("Z", "+00:00"))
                    merge_time = (merged_at - created_at).total_seconds() / 3600  # 시간 단위
                    time_to_merge.append(merge_time)
            
            # 총 코멘트 수
            total_comments = total_inline_comments + total_issue_comments
            
            # 평균 계산
            avg_comments_per_pr = total_comments / total_prs if total_prs > 0 else 0
            avg_reviewers_per_pr = total_reviewers / total_prs if total_prs > 0 else 0
            avg_time_to_first_review = sum(time_to_first_review) / len(time_to_first_review) if time_to_first_review else 0
            avg_time_to_merge = sum(time_to_merge) / len(time_to_merge) if time_to_merge else 0
            
            # 상위 리뷰어 및 작성자
            top_reviewers = sorted(reviewer_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 결과 반환
            return {
                "repository": f"{owner}/{repo}",
                "analyzed_prs": total_prs,
                "pr_status": {
                    "open": open_prs,
                    "merged": merged_prs,
                    "closed_without_merge": closed_without_merge,
                    "merge_rate": merged_prs / (merged_prs + closed_without_merge) * 100 if (merged_prs + closed_without_merge) > 0 else 0
                },
                "review_stats": {
                    "prs_with_comments": prs_with_comments,
                    "prs_with_comments_percent": prs_with_comments / total_prs * 100 if total_prs > 0 else 0,
                    "total_comments": total_comments,
                    "inline_comments": total_inline_comments,
                    "issue_comments": total_issue_comments,
                    "avg_comments_per_pr": avg_comments_per_pr,
                    "avg_reviewers_per_pr": avg_reviewers_per_pr
                },
                "time_stats": {
                    "avg_time_to_first_review_hours": avg_time_to_first_review,
                    "avg_time_to_merge_hours": avg_time_to_merge
                },
                "top_reviewers": top_reviewers,
                "top_authors": top_authors
            }
        except Exception as e:
            logger.error(f"코드 리뷰 패턴 분석 중 오류 발생: {e}")
            return {"error": str(e)}

    def get_repository_activity(self, owner: str, repo: str, days: int = 30) -> Dict:
        """
        저장소의 최근 활동 정보를 가져옵니다.
        
        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            days: 최근 일수
            
        Returns:
            Dict: 저장소 활동 정보
        """
        try:
            # 저장소 정보 가져오기
            repository = self.get_repository(owner, repo)
            if not repository:
                return {"error": "저장소 정보를 가져올 수 없습니다."}
                
            # 최근 커밋 목록
            commits = self.list_commits(owner, repo, per_page=100)
            
            # 최근 PR 목록
            params = {
                "state": "all",
                "per_page": 100,
                "sort": "updated",
                "direction": "desc"
            }
            
            pr_response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params=params)
            prs = pr_response if isinstance(pr_response, list) else pr_response.get("items", [])
            
            # 최근 이슈 목록
            params = {
                "state": "all",
                "per_page": 100,
                "sort": "updated",
                "direction": "desc"
            }
            
            issue_response = self._make_request("GET", f"repos/{owner}/{repo}/issues", params=params)
            issues = []
            if not "error" in issue_response:
                items = issue_response if isinstance(issue_response, list) else issue_response.get("items", [])
                for item in items:
                    # PR이 아닌 이슈만 추가
                    if "pull_request" not in item:
                        issues.append(item)
            
            # 브랜치 목록
            branches = self.list_branches(owner, repo)
            
            # 결과 반환
            return {
                "repository": {
                    "name": repository.name,
                    "full_name": repository.full_name,
                    "description": repository.description,
                    "default_branch": repository.default_branch,
                    "stars": repository.stargazers_count,
                    "forks": repository.forks_count,
                    "open_issues": repository.open_issues_count,
                    "created_at": repository.created_at,
                    "updated_at": repository.updated_at,
                    "pushed_at": repository.pushed_at
                },
                "activity": {
                    "recent_commits": len(commits),
                    "recent_prs": len(prs),
                    "recent_issues": len(issues),
                    "branch_count": len(branches)
                },
                "recent_commits": [
                    {
                        "sha": commit.sha[:7],
                        "message": commit.commit.get("message", "").split("\n")[0],
                        "author": commit.commit.get("author", {}).get("name", ""),
                        "date": commit.commit.get("author", {}).get("date", "")
                    }
                    for commit in commits[:10]  # 최근 10개만 반환
                ],
                "recent_prs": [
                    {
                        "number": pr.get("number", 0),
                        "title": pr.get("title", ""),
                        "state": pr.get("state", ""),
                        "user": pr.get("user", {}).get("login", ""),
                        "created_at": pr.get("created_at", ""),
                        "updated_at": pr.get("updated_at", "")
                    }
                    for pr in prs[:10]  # 최근 10개만 반환
                ],
                "recent_issues": [
                    {
                        "number": issue.get("number", 0),
                        "title": issue.get("title", ""),
                        "state": issue.get("state", ""),
                        "user": issue.get("user", {}).get("login", ""),
                        "created_at": issue.get("created_at", ""),
                        "updated_at": issue.get("updated_at", "")
                    }
                    for issue in issues[:10]  # 최근 10개만 반환
                ],
                "branches": [
                    {
                        "name": branch.name,
                        "last_commit": branch.commit.get("sha", "")[:7]
                    }
                    for branch in branches
                ]
            }
        except Exception as e:
            logger.error(f"저장소 활동 정보 가져오기 중 오류 발생: {e}")
            return {"error": str(e)}


# 전역 서비스 인스턴스
github_api = GitHubAPIService()


@app.tool()
def get_user_info(username: str) -> dict:
    """
    GitHub 사용자 정보를 가져옵니다.
    
    Args:
        username: GitHub 사용자명
        
    Returns:
        dict: 사용자 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_user_info("octocat")
        {'result': {'login': 'octocat', 'name': 'The Octocat', ...}}
    """
    try:
        if not username:
            return {"error": "사용자명을 입력해주세요."}
            
        # 사용자 정보 가져오기
        user = github_api.get_user(username)
        
        if not user:
            return {"error": f"사용자 정보를 가져올 수 없습니다: {username}"}
            
        # 결과 포맷팅
        return {
            "result": {
                "login": user.login,
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "bio": user.bio,
                "company": user.company,
                "location": user.location,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
        
    except Exception as e:
        return {"error": f"사용자 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def list_repository_prs(owner: str, repo: str, state: str = "all", max_results: int = 30) -> dict:
    """
    GitHub 저장소의 PR 목록을 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        state: PR 상태 (open, closed, all)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: PR 목록을 포함한 딕셔너리
        
    Examples:
        >>> list_repository_prs("octocat", "Hello-World")
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'prs': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if state not in ["open", "closed", "all"]:
            return {"error": "유효한 상태가 아닙니다. open, closed, all 중 하나를 선택하세요."}
            
        # PR 목록 가져오기
        prs = github_api.list_pull_requests(owner, repo, state, max_results)
        
        # 결과 포맷팅
        formatted_prs = []
        for pr in prs[:max_results]:
            formatted_prs.append({
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "user": pr.user.login,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "closed_at": pr.closed_at,
                "merged_at": pr.merged_at,
                "html_url": pr.html_url,
                "comments": pr.comments,
                "review_comments": pr.review_comments,
                "commits": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "draft": pr.draft
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "state": state,
                "count": len(formatted_prs),
                "prs": formatted_prs
            }
        }
        
    except Exception as e:
        return {"error": f"PR 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def list_repository_issues(owner: str, repo: str, state: str = "all", max_results: int = 30) -> dict:
    """
    GitHub 저장소의 이슈 목록을 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        state: 이슈 상태 (open, closed, all)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 이슈 목록을 포함한 딕셔너리
        
    Examples:
        >>> list_repository_issues("octocat", "Hello-World")
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'issues': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if state not in ["open", "closed", "all"]:
            return {"error": "유효한 상태가 아닙니다. open, closed, all 중 하나를 선택하세요."}
            
        # 이슈 목록 가져오기
        issues = github_api.list_issues(owner, repo, state, max_results)
        
        # 결과 포맷팅
        formatted_issues = []
        for issue in issues[:max_results]:
            formatted_issues.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "user": issue.user.login,
                "created_at": issue.created_at,
                "updated_at": issue.updated_at,
                "closed_at": issue.closed_at,
                "html_url": issue.html_url,
                "comments": issue.comments,
                "labels": [label.get("name", "") for label in issue.labels]
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "state": state,
                "count": len(formatted_issues),
                "issues": formatted_issues
            }
        }
        
    except Exception as e:
        return {"error": f"이슈 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pr_inline_comments(owner: str, repo: str, pr_number: int) -> dict:
    """
    PR에 등록된 인라인 코멘트를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        pr_number: PR 번호
        
    Returns:
        dict: 인라인 코멘트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_pr_inline_comments("octocat", "Hello-World", 1)
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'pr_number': 1, 'comments': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not pr_number or pr_number <= 0:
            return {"error": "유효한 PR 번호를 입력해주세요."}
            
        # 인라인 코멘트 가져오기
        comments = github_api.get_pr_inline_comments(owner, repo, pr_number)
        
        # 결과 포맷팅
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment.id,
                "user": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "html_url": comment.html_url,
                "path": comment.path,
                "position": comment.position,
                "line": comment.line,
                "commit_id": comment.commit_id
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "count": len(formatted_comments),
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        return {"error": f"PR 인라인 코멘트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pr_issue_comments(owner: str, repo: str, pr_number: int) -> dict:
    """
    PR에 등록된 이슈 코멘트를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        pr_number: PR 번호
        
    Returns:
        dict: 이슈 코멘트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_pr_issue_comments("octocat", "Hello-World", 1)
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'pr_number': 1, 'comments': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not pr_number or pr_number <= 0:
            return {"error": "유효한 PR 번호를 입력해주세요."}
            
        # 이슈 코멘트 가져오기
        comments = github_api.get_pr_issue_comments(owner, repo, pr_number)
        
        # 결과 포맷팅
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment.id,
                "user": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "html_url": comment.html_url
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "count": len(formatted_comments),
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        return {"error": f"PR 이슈 코멘트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_issue_comments(owner: str, repo: str, issue_number: int) -> dict:
    """
    이슈에 등록된 코멘트를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        issue_number: 이슈 번호
        
    Returns:
        dict: 코멘트 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_issue_comments("octocat", "Hello-World", 1)
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'issue_number': 1, 'comments': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not issue_number or issue_number <= 0:
            return {"error": "유효한 이슈 번호를 입력해주세요."}
            
        # 이슈 코멘트 가져오기
        comments = github_api.get_issue_comments(owner, repo, issue_number)
        
        # 결과 포맷팅
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment.id,
                "user": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "html_url": comment.html_url
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "count": len(formatted_comments),
                "comments": formatted_comments
            }
        }
        
    except Exception as e:
        return {"error": f"이슈 코멘트 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_branch_status(owner: str, repo: str) -> dict:
    """
    저장소의 브랜치 현황을 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        
    Returns:
        dict: 브랜치 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_branch_status("octocat", "Hello-World")
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'branches': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        # 브랜치 목록 가져오기
        branches = github_api.list_branches(owner, repo)
        
        # 저장소 정보 가져오기
        repository = github_api.get_repository(owner, repo)
        default_branch = repository.default_branch if repository else "main"
        
        # 결과 포맷팅
        formatted_branches = []
        for branch in branches:
            formatted_branches.append({
                "name": branch.name,
                "is_default": branch.name == default_branch,
                "protected": branch.protected,
                "last_commit": {
                    "sha": branch.commit.get("sha", ""),
                    "url": branch.commit.get("url", "")
                }
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "default_branch": default_branch,
                "count": len(formatted_branches),
                "branches": formatted_branches
            }
        }
        
    except Exception as e:
        return {"error": f"브랜치 현황 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_branch_commits(owner: str, repo: str, branch: str = None, max_results: int = 30) -> dict:
    """
    브랜치별 커밋 리스트를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        branch: 브랜치 이름 (None이면 기본 브랜치)
        max_results: 반환할 최대 결과 수
        
    Returns:
        dict: 커밋 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_branch_commits("octocat", "Hello-World", "main")
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'branch': 'main', 'commits': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        # 브랜치가 없으면 기본 브랜치 사용
        if not branch:
            repository = github_api.get_repository(owner, repo)
            branch = repository.default_branch if repository else "main"
            
        # 커밋 목록 가져오기
        commits = github_api.list_commits(owner, repo, branch, max_results)
        
        # 결과 포맷팅
        formatted_commits = []
        for commit in commits[:max_results]:
            formatted_commits.append({
                "sha": commit.sha,
                "html_url": commit.html_url,
                "message": commit.commit.get("message", ""),
                "author": {
                    "name": commit.commit.get("author", {}).get("name", ""),
                    "email": commit.commit.get("author", {}).get("email", ""),
                    "date": commit.commit.get("author", {}).get("date", "")
                },
                "committer": {
                    "name": commit.commit.get("committer", {}).get("name", ""),
                    "email": commit.commit.get("committer", {}).get("email", ""),
                    "date": commit.commit.get("committer", {}).get("date", "")
                }
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "count": len(formatted_commits),
                "commits": formatted_commits
            }
        }
        
    except Exception as e:
        return {"error": f"브랜치 커밋 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_commit_files(owner: str, repo: str, commit_sha: str) -> dict:
    """
    커밋별 변경 파일 리스트를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        commit_sha: 커밋 SHA
        
    Returns:
        dict: 변경 파일 목록을 포함한 딕셔너리
        
    Examples:
        >>> get_commit_files("octocat", "Hello-World", "6dcb09b5b57875f334f61aebed695e2e4193db5e")
        {'result': {'owner': 'octocat', 'repo': 'Hello-World', 'commit_sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e', 'files': [...]}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not commit_sha:
            return {"error": "커밋 SHA를 입력해주세요."}
            
        # 커밋 정보 가져오기
        commit = github_api.get_commit(owner, repo, commit_sha)
        
        if not commit:
            return {"error": f"커밋 정보를 가져올 수 없습니다: {commit_sha}"}
            
        # 변경 파일 목록 가져오기
        files = github_api.get_commit_files(owner, repo, commit_sha)
        
        # 결과 포맷팅
        formatted_files = []
        for file in files:
            formatted_files.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "blob_url": file.blob_url,
                "raw_url": file.raw_url,
                "patch": file.patch[:1000] if file.patch else ""  # 패치가 너무 길면 잘라냄
            })
            
        return {
            "result": {
                "owner": owner,
                "repo": repo,
                "commit_sha": commit_sha,
                "commit_message": commit.commit.get("message", ""),
                "stats": {
                    "additions": commit.stats.get("additions", 0),
                    "deletions": commit.stats.get("deletions", 0),
                    "total": commit.stats.get("total", 0)
                },
                "count": len(formatted_files),
                "files": formatted_files
            }
        }
        
    except Exception as e:
        return {"error": f"커밋 파일 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pr_statistics(owner: str, repo: str, pr_number: int) -> dict:
    """
    PR의 통계 정보를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        pr_number: PR 번호
        
    Returns:
        dict: PR 통계 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_pr_statistics("octocat", "Hello-World", 1)
        {'result': {'pr_number': 1, 'title': '...', 'reviewers': [...], ...}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not pr_number or pr_number <= 0:
            return {"error": "유효한 PR 번호를 입력해주세요."}
            
        # PR 통계 정보 가져오기
        stats = github_api.get_pr_statistics(owner, repo, pr_number)
        
        if "error" in stats:
            return {"error": stats["error"]}
            
        # 결과 반환
        return {
            "result": stats
        }
        
    except Exception as e:
        return {"error": f"PR 통계 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_user_activity(owner: str, repo: str, username: str) -> dict:
    """
    특정 사용자의 저장소 활동 정보를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        username: GitHub 사용자명
        
    Returns:
        dict: 사용자 활동 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_user_activity("octocat", "Hello-World", "octocat")
        {'result': {'username': 'octocat', 'authored_prs_count': 5, ...}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if not username:
            return {"error": "사용자명을 입력해주세요."}
            
        # 사용자 활동 정보 가져오기
        activity = github_api.get_user_activity(owner, repo, username)
        
        if "error" in activity:
            return {"error": activity["error"]}
            
        # 결과 반환
        return {
            "result": activity
        }
        
    except Exception as e:
        return {"error": f"사용자 활동 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def analyze_code_review_patterns(owner: str, repo: str, pr_count: int = 30) -> dict:
    """
    저장소의 코드 리뷰 패턴을 분석합니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        pr_count: 분석할 PR 수
        
    Returns:
        dict: 코드 리뷰 패턴 분석 결과를 포함한 딕셔너리
        
    Examples:
        >>> analyze_code_review_patterns("octocat", "Hello-World")
        {'result': {'repository': 'octocat/Hello-World', 'analyzed_prs': 30, ...}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if pr_count <= 0:
            return {"error": "분석할 PR 수는 1 이상이어야 합니다."}
            
        # 코드 리뷰 패턴 분석
        patterns = github_api.analyze_code_review_patterns(owner, repo, pr_count)
        
        if "error" in patterns:
            return {"error": patterns["error"]}
            
        # 결과 반환
        return {
            "result": patterns
        }
        
    except Exception as e:
        return {"error": f"코드 리뷰 패턴 분석 중 오류 발생: {str(e)}"}


@app.tool()
def get_repository_activity(owner: str, repo: str, days: int = 30) -> dict:
    """
    저장소의 최근 활동 정보를 가져옵니다.
    
    Args:
        owner: 저장소 소유자
        repo: 저장소 이름
        days: 최근 일수
        
    Returns:
        dict: 저장소 활동 정보를 포함한 딕셔너리
        
    Examples:
        >>> get_repository_activity("octocat", "Hello-World")
        {'result': {'repository': {...}, 'activity': {...}, ...}}
    """
    try:
        if not owner or not repo:
            return {"error": "저장소 소유자와 이름을 입력해주세요."}
            
        if days <= 0:
            return {"error": "일수는 1 이상이어야 합니다."}
            
        # 저장소 활동 정보 가져오기
        activity = github_api.get_repository_activity(owner, repo, days)
        
        if "error" in activity:
            return {"error": activity["error"]}
            
        # 결과 반환
        return {
            "result": activity
        }
        
    except Exception as e:
        return {"error": f"저장소 활동 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    GitHub API 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "GitHub API Tool",
                "description": "GitHub REST API를 통해 다양한 정보를 조회하는 도구",
                "auth_status": "인증됨" if github_api.token else "인증되지 않음",
                "rate_limit_remaining": github_api.rate_limit_remaining,
                "tools": [
                    {"name": "get_user_info", "description": "GitHub 사용자 정보를 가져옵니다"},
                    {"name": "list_repository_prs", "description": "GitHub 저장소의 PR 목록을 가져옵니다"},
                    {"name": "list_repository_issues", "description": "GitHub 저장소의 이슈 목록을 가져옵니다"},
                    {"name": "get_pr_inline_comments", "description": "PR에 등록된 인라인 코멘트를 가져옵니다"},
                    {"name": "get_pr_issue_comments", "description": "PR에 등록된 이슈 코멘트를 가져옵니다"},
                    {"name": "get_issue_comments", "description": "이슈에 등록된 코멘트를 가져옵니다"},
                    {"name": "get_branch_status", "description": "저장소의 브랜치 현황을 가져옵니다"},
                    {"name": "get_branch_commits", "description": "브랜치별 커밋 리스트를 가져옵니다"},
                    {"name": "get_commit_files", "description": "커밋별 변경 파일 리스트를 가져옵니다"},
                    {"name": "get_pr_statistics", "description": "PR의 통계 정보를 가져옵니다"},
                    {"name": "get_user_activity", "description": "특정 사용자의 저장소 활동 정보를 가져옵니다"},
                    {"name": "analyze_code_review_patterns", "description": "저장소의 코드 리뷰 패턴을 분석합니다"},
                    {"name": "get_repository_activity", "description": "저장소의 최근 활동 정보를 가져옵니다"}
                ],
                "usage_examples": [
                    {"command": "get_user_info('octocat')", "description": "octocat 사용자 정보 가져오기"},
                    {"command": "list_repository_prs('octocat', 'Hello-World')", "description": "Hello-World 저장소의 PR 목록 가져오기"},
                    {"command": "get_pr_inline_comments('octocat', 'Hello-World', 1)", "description": "PR #1의 인라인 코멘트 가져오기"},
                    {"command": "analyze_code_review_patterns('octocat', 'Hello-World')", "description": "Hello-World 저장소의 코드 리뷰 패턴 분석"}
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
        logger.error("github_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise