#!/usr/bin/env python3
"""
Bitbucket API를 사용한 코드 리뷰 MCP 서버
PR 리스트 조회, 댓글 확인, 미승인 코드 반영 확인 등 코드 리뷰 활동을 위한 도구들을 제공합니다.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="Bitbucket Code Review Server",
    description="A server for Bitbucket code review operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# Bitbucket API 설정
API_KEY = os.getenv("BITBUCKET_API_KEY", "")
BASE_URL = "https://api.bitbucket.org/2.0"
WORKSPACE = os.getenv("BITBUCKET_WORKSPACE", "")


@dataclass
class PullRequest:
    """PR 정보를 담는 데이터 클래스"""
    id: int
    title: str
    description: str
    author: str
    source_branch: str
    destination_branch: str
    state: str
    created_on: datetime
    updated_on: datetime
    comment_count: int
    task_count: int
    url: str
    reviewers: List[str]
    is_approved: bool


class BitbucketService:
    """Bitbucket API 서비스 클래스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def get_pull_requests(self, workspace: str, repo_slug: str, state: str = "OPEN") -> Optional[List[Dict[str, Any]]]:
        """특정 저장소의 PR 목록을 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests"
            params = {
                "state": state,
                "pagelen": 50  # 한 페이지당 결과 수
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("values", [])
        except Exception:
            return None
    
    def get_pull_request(self, workspace: str, repo_slug: str, pr_id: int) -> Optional[Dict[str, Any]]:
        """특정 PR의 상세 정보를 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def get_pull_request_comments(self, workspace: str, repo_slug: str, pr_id: int) -> Optional[List[Dict[str, Any]]]:
        """특정 PR의 댓글을 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/comments"
            params = {"pagelen": 100}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("values", [])
        except Exception:
            return None
    
    def get_pull_request_activity(self, workspace: str, repo_slug: str, pr_id: int) -> Optional[List[Dict[str, Any]]]:
        """특정 PR의 활동 내역(승인, 댓글 등)을 가져옵니다."""
        if not self.api_key:
            return None
            
        try:
            url = f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/activity"
            params = {"pagelen": 100}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("values", [])
        except Exception:
            return None
    
    def parse_pull_request(self, pr_data: Dict[str, Any], activities: List[Dict[str, Any]]) -> PullRequest:
        """PR 데이터를 PullRequest 객체로 변환합니다."""
        # 승인 여부 확인
        is_approved = False
        for activity in activities:
            if activity.get("approval") and activity.get("approval").get("date"):
                is_approved = True
                break
        
        # 리뷰어 목록
        reviewers = []
        for reviewer in pr_data.get("reviewers", []):
            if reviewer.get("user") and reviewer.get("user").get("display_name"):
                reviewers.append(reviewer["user"]["display_name"])
        
        return PullRequest(
            id=pr_data["id"],
            title=pr_data["title"],
            description=pr_data.get("description", ""),
            author=pr_data["author"]["display_name"] if pr_data.get("author") else "Unknown",
            source_branch=pr_data["source"]["branch"]["name"],
            destination_branch=pr_data["destination"]["branch"]["name"],
            state=pr_data["state"],
            created_on=datetime.fromisoformat(pr_data["created_on"].replace("Z", "+00:00")),
            updated_on=datetime.fromisoformat(pr_data["updated_on"].replace("Z", "+00:00")),
            comment_count=pr_data.get("comment_count", 0),
            task_count=pr_data.get("task_count", 0),
            url=pr_data["links"]["html"]["href"],
            reviewers=reviewers,
            is_approved=is_approved
        )


# 전역 서비스 인스턴스
bitbucket_service = BitbucketService(API_KEY)


@app.tool()
def list_pull_requests(workspace: str = WORKSPACE, repo_slug: str = "", state: str = "OPEN") -> dict:
    """
    지정된 저장소의 PR 목록을 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        state: PR 상태 (OPEN, MERGED, DECLINED, SUPERSEDED)

    Returns:
        dict: PR 목록 정보를 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다. BITBUCKET_API_KEY 환경변수를 설정해주세요."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        # PR 목록 가져오기
        prs_data = bitbucket_service.get_pull_requests(workspace, repo_slug, state)
        if not prs_data:
            return {"error": "PR 목록을 가져올 수 없습니다."}
        
        # 간단한 PR 정보 목록 생성
        prs_info = []
        for pr in prs_data:
            pr_info = {
                "id": pr["id"],
                "title": pr["title"],
                "author": pr["author"]["display_name"] if pr.get("author") else "Unknown",
                "source": pr["source"]["branch"]["name"],
                "destination": pr["destination"]["branch"]["name"],
                "created_on": pr["created_on"],
                "updated_on": pr["updated_on"],
                "comment_count": pr.get("comment_count", 0),
                "url": pr["links"]["html"]["href"]
            }
            prs_info.append(pr_info)
        
        return {
            "result": {
                "repository": f"{workspace}/{repo_slug}",
                "state": state,
                "count": len(prs_info),
                "pull_requests": prs_info
            }
        }
        
    except Exception as e:
        return {"error": f"PR 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_pull_request_details(workspace: str = WORKSPACE, repo_slug: str = "", pr_id: int = 0) -> dict:
    """
    지정된 PR의 상세 정보를 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        pr_id: PR ID

    Returns:
        dict: PR 상세 정보를 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        if not pr_id:
            return {"error": "PR ID가 지정되지 않았습니다."}
        
        # PR 정보 가져오기
        pr_data = bitbucket_service.get_pull_request(workspace, repo_slug, pr_id)
        if not pr_data:
            return {"error": f"PR #{pr_id}를 찾을 수 없습니다."}
        
        # PR 활동 내역 가져오기
        activities = bitbucket_service.get_pull_request_activity(workspace, repo_slug, pr_id)
        if activities is None:
            return {"error": "PR 활동 내역을 가져올 수 없습니다."}
        
        # PR 정보 파싱
        pr_info = bitbucket_service.parse_pull_request(pr_data, activities)
        
        result = {
            "id": pr_info.id,
            "title": pr_info.title,
            "description": pr_info.description,
            "author": pr_info.author,
            "source_branch": pr_info.source_branch,
            "destination_branch": pr_info.destination_branch,
            "state": pr_info.state,
            "created_on": pr_info.created_on.isoformat(),
            "updated_on": pr_info.updated_on.isoformat(),
            "comment_count": pr_info.comment_count,
            "task_count": pr_info.task_count,
            "url": pr_info.url,
            "reviewers": pr_info.reviewers,
            "is_approved": pr_info.is_approved,
            "age_days": (datetime.now() - pr_info.created_on).days
        }
        
        return {"result": result}
        
    except Exception as e:
        return {"error": f"PR 상세 정보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_pull_request_comments(workspace: str = WORKSPACE, repo_slug: str = "", pr_id: int = 0) -> dict:
    """
    지정된 PR의 댓글 목록을 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        pr_id: PR ID

    Returns:
        dict: PR 댓글 목록을 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        if not pr_id:
            return {"error": "PR ID가 지정되지 않았습니다."}
        
        # 댓글 목록 가져오기
        comments = bitbucket_service.get_pull_request_comments(workspace, repo_slug, pr_id)
        if comments is None:
            return {"error": "댓글 목록을 가져올 수 없습니다."}
        
        # 댓글 정보 정리
        comments_info = []
        for comment in comments:
            comment_info = {
                "id": comment["id"],
                "content": comment["content"]["raw"],
                "author": comment["user"]["display_name"] if comment.get("user") else "Unknown",
                "created_on": comment["created_on"],
                "updated_on": comment["updated_on"],
                "deleted": comment.get("deleted", False)
            }
            comments_info.append(comment_info)
        
        return {
            "result": {
                "pull_request_id": pr_id,
                "repository": f"{workspace}/{repo_slug}",
                "count": len(comments_info),
                "comments": comments_info
            }
        }
        
    except Exception as e:
        return {"error": f"댓글 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def find_my_assigned_prs(workspace: str = WORKSPACE, username: str = "") -> dict:
    """
    특정 사용자가 리뷰어로 할당된 PR 목록을 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        username: Bitbucket 사용자 이름

    Returns:
        dict: 할당된 PR 목록을 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not username:
            return {"error": "사용자 이름이 지정되지 않았습니다."}
        
        # 워크스페이스의 저장소 목록 가져오기
        url = f"{BASE_URL}/workspaces/{workspace}/repositories"
        params = {"pagelen": 100}
        response = bitbucket_service.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        repositories = response.json().get("values", [])
        
        # 각 저장소의 PR 중 사용자가 리뷰어로 할당된 PR 찾기
        assigned_prs = []
        
        for repo in repositories:
            repo_slug = repo["slug"]
            prs_data = bitbucket_service.get_pull_requests(workspace, repo_slug, "OPEN")
            
            if not prs_data:
                continue
            
            for pr in prs_data:
                is_reviewer = False
                for reviewer in pr.get("reviewers", []):
                    if reviewer.get("user") and reviewer.get("user").get("username") == username:
                        is_reviewer = True
                        break
                
                if is_reviewer:
                    assigned_prs.append({
                        "id": pr["id"],
                        "title": pr["title"],
                        "repository": repo_slug,
                        "author": pr["author"]["display_name"] if pr.get("author") else "Unknown",
                        "created_on": pr["created_on"],
                        "url": pr["links"]["html"]["href"]
                    })
        
        return {
            "result": {
                "username": username,
                "count": len(assigned_prs),
                "assigned_pull_requests": assigned_prs
            }
        }
        
    except Exception as e:
        return {"error": f"할당된 PR 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def find_unapproved_prs(workspace: str = WORKSPACE, repo_slug: str = "", days: int = 7) -> dict:
    """
    지정된 기간 동안 승인되지 않은 PR 목록을 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        days: 검색할 기간(일) (기본값: 7)

    Returns:
        dict: 승인되지 않은 PR 목록을 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        # PR 목록 가져오기
        prs_data = bitbucket_service.get_pull_requests(workspace, repo_slug, "OPEN")
        if not prs_data:
            return {"error": "PR 목록을 가져올 수 없습니다."}
        
        # 승인되지 않은 PR 찾기
        unapproved_prs = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for pr in prs_data:
            pr_id = pr["id"]
            created_on = datetime.fromisoformat(pr["created_on"].replace("Z", "+00:00"))
            
            # 지정된 기간보다 오래된 PR만 확인
            if created_on > cutoff_date:
                continue
            
            # PR 활동 내역 가져오기
            activities = bitbucket_service.get_pull_request_activity(workspace, repo_slug, pr_id)
            if activities is None:
                continue
            
            # 승인 여부 확인
            is_approved = False
            for activity in activities:
                if activity.get("approval") and activity.get("approval").get("date"):
                    is_approved = True
                    break
            
            if not is_approved:
                unapproved_prs.append({
                    "id": pr_id,
                    "title": pr["title"],
                    "author": pr["author"]["display_name"] if pr.get("author") else "Unknown",
                    "created_on": pr["created_on"],
                    "age_days": (datetime.now() - created_on).days,
                    "url": pr["links"]["html"]["href"]
                })
        
        return {
            "result": {
                "repository": f"{workspace}/{repo_slug}",
                "period_days": days,
                "count": len(unapproved_prs),
                "unapproved_pull_requests": unapproved_prs
            }
        }
        
    except Exception as e:
        return {"error": f"승인되지 않은 PR 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def find_stale_prs(workspace: str = WORKSPACE, repo_slug: str = "", days: int = 30) -> dict:
    """
    지정된 기간 동안 병합되지 않은 오래된 PR 목록을 반환합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        days: 검색할 기간(일) (기본값: 30)

    Returns:
        dict: 오래된 PR 목록을 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        # PR 목록 가져오기
        prs_data = bitbucket_service.get_pull_requests(workspace, repo_slug, "OPEN")
        if not prs_data:
            return {"error": "PR 목록을 가져올 수 없습니다."}
        
        # 오래된 PR 찾기
        stale_prs = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for pr in prs_data:
            created_on = datetime.fromisoformat(pr["created_on"].replace("Z", "+00:00"))
            
            # 지정된 기간보다 오래된 PR 찾기
            if created_on < cutoff_date:
                stale_prs.append({
                    "id": pr["id"],
                    "title": pr["title"],
                    "author": pr["author"]["display_name"] if pr.get("author") else "Unknown",
                    "created_on": pr["created_on"],
                    "age_days": (datetime.now() - created_on).days,
                    "url": pr["links"]["html"]["href"]
                })
        
        # 생성일 기준으로 정렬 (오래된 순)
        stale_prs.sort(key=lambda x: x["age_days"], reverse=True)
        
        return {
            "result": {
                "repository": f"{workspace}/{repo_slug}",
                "period_days": days,
                "count": len(stale_prs),
                "stale_pull_requests": stale_prs
            }
        }
        
    except Exception as e:
        return {"error": f"오래된 PR 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def analyze_review_comments(workspace: str = WORKSPACE, repo_slug: str = "", pr_id: int = 0) -> dict:
    """
    특정 PR의 리뷰 댓글을 분석합니다.

    Args:
        workspace: Bitbucket 워크스페이스 (기본값: 환경변수에서 설정)
        repo_slug: 저장소 이름
        pr_id: PR ID

    Returns:
        dict: 리뷰 댓글 분석 결과를 포함한 딕셔너리
    """
    try:
        if not API_KEY:
            return {"error": "Bitbucket API 키가 설정되지 않았습니다."}
        
        if not workspace:
            return {"error": "워크스페이스가 지정되지 않았습니다."}
        
        if not repo_slug:
            return {"error": "저장소 이름이 지정되지 않았습니다."}
        
        if not pr_id:
            return {"error": "PR ID가 지정되지 않았습니다."}
        
        # 댓글 목록 가져오기
        comments = bitbucket_service.get_pull_request_comments(workspace, repo_slug, pr_id)
        if comments is None:
            return {"error": "댓글 목록을 가져올 수 없습니다."}
        
        # 댓글 분석
        comment_count = len(comments)
        authors = {}
        comment_lengths = []
        
        for comment in comments:
            author = comment["user"]["display_name"] if comment.get("user") else "Unknown"
            content = comment["content"]["raw"]
            
            # 작성자별 댓글 수 집계
            if author in authors:
                authors[author] += 1
            else:
                authors[author] = 1
            
            # 댓글 길이 저장
            comment_lengths.append(len(content))
        
        # 분석 결과
        avg_length = sum(comment_lengths) / comment_count if comment_count > 0 else 0
        
        # 작성자별 댓글 수 정렬
        authors_sorted = [{"author": author, "comment_count": count} for author, count in authors.items()]
        authors_sorted.sort(key=lambda x: x["comment_count"], reverse=True)
        
        return {
            "result": {
                "pull_request_id": pr_id,
                "repository": f"{workspace}/{repo_slug}",
                "total_comments": comment_count,
                "unique_commenters": len(authors),
                "average_comment_length": round(avg_length, 1),
                "commenters_by_activity": authors_sorted
            }
        }
        
    except Exception as e:
        return {"error": f"리뷰 댓글 분석 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    app.run(transport=TRANSPORT)
