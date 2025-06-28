"""
Utility functions for the webhook server.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from loguru import logger
from werkzeug.utils import secure_filename

from webhook.config import DATA_DIR, GITHUB_WEBHOOK_SECRET


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify the GitHub webhook signature.
    
    Args:
        payload_body: The raw request body
        signature_header: The X-Hub-Signature-256 header value
        
    Returns:
        bool: True if the signature is valid, False otherwise
    """
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning(
            "GITHUB_WEBHOOK_SECRET이 설정되지 않았습니다. 서명 검증을 건너뜁니다."
        )
        return True

    if not signature_header:
        return False

    hash_object = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def extract_org_repo_info(
    payload: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract organization and repository information from the webhook payload.
    
    Args:
        payload: The webhook payload
        
    Returns:
        Tuple[Optional[str], Optional[str]]: The organization name and repository name
    """
    org_name = None
    repo_name = None

    # Repository 정보 추출
    if "repository" in payload:
        repo_info = payload["repository"]
        repo_name = repo_info.get("full_name") or repo_info.get("name")

        # Organization 정보 추출
        if "owner" in repo_info:
            owner = repo_info["owner"]
            if owner.get("type") == "Organization":
                org_name = owner.get("login")

    # Organization 직접 추출 (organization 이벤트의 경우)
    if "organization" in payload:
        org_name = payload["organization"].get("login")

    return org_name, repo_name


def save_webhook_data(
    payload: Dict[str, Any], event_type: str
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Save webhook data to a file and return org/repo information.
    
    Args:
        payload: The webhook payload
        event_type: The GitHub event type
        
    Returns:
        Tuple[str, Optional[str], Optional[str]]: The filepath, organization name, and repository name
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지

    # 파일명 생성 (이벤트 타입과 타임스탬프 포함)
    sanitized_event_type = secure_filename(event_type)
    filename = f"{sanitized_event_type}_{timestamp}.json"
    filepath = os.path.normpath(DATA_DIR / filename)

    # Ensure the filepath is within the DATA_DIR
    if not str(filepath).startswith(str(DATA_DIR)):
        raise ValueError("Invalid file path: potential directory traversal detected")

    # org/repo 정보 추출
    org_name, repo_name = extract_org_repo_info(payload)

    # 저장할 데이터 구성
    webhook_data = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "org_name": org_name,
        "repo_name": repo_name,
        "payload": payload,
    }

    # JSON 파일로 저장
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(webhook_data, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Webhook 데이터가 저장되었습니다: {filepath} (org: {org_name}, repo: {repo_name})"
    )
    return str(filepath), org_name, repo_name


def message_matches_client_interest(
    webhook_data: Dict[str, Any], interested_orgs: list, interested_repos: list
) -> bool:
    """
    Check if a webhook message matches a client's interests.
    
    Args:
        webhook_data: The webhook data
        interested_orgs: List of organizations the client is interested in
        interested_repos: List of repositories the client is interested in
        
    Returns:
        bool: True if the message matches the client's interests, False otherwise
    """
    org_name = webhook_data.get("org_name")
    repo_name = webhook_data.get("repo_name")

    # 관심 있는 조직이나 저장소가 설정되지 않았다면 모든 메시지에 관심
    if not interested_orgs and not interested_repos:
        return True

    # 조직 매칭
    if org_name and interested_orgs:
        if org_name in interested_orgs:
            return True

    # 저장소 매칭 (full_name 또는 repository name)
    if repo_name and interested_repos:
        if repo_name in interested_repos:
            return True
        # full_name에서 repository name만 추출해서 비교
        if "/" in repo_name:
            simple_repo_name = repo_name.split("/")[-1]
            if simple_repo_name in interested_repos:
                return True

    return False