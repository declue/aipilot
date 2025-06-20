import logging
import threading
import time
import random
from typing import Any, Dict, List, Optional
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from application.util.logger import setup_logger
from application.config.config_manager import ConfigManager

logger = setup_logger("webhook_client") or logging.getLogger("webhook_client")

# 전역 설정 변수
SESSION_SOCKET_TIMEOUT = 5  # 기본 타임아웃 5초
SESSION_VERIFY = False  # SSL 인증 활성화


class WebhookClient:
    """Webhook API 서버와 통신하는 클라이언트"""

    def __init__(
        self,
        webhook_server_url: str,
        client_name: str,
        client_description: str = "",
        poll_interval: int = 10,  # 10초 간격으로 polling
    ):
        self.webhook_server_url = webhook_server_url.rstrip("/")
        self.client_name = client_name
        self.client_description = client_description
        self.poll_interval = poll_interval

        self.client_id: Optional[int] = None
        self.is_polling = False
        self.polling_thread: Optional[threading.Thread] = None
        # 설정은 나중에 초기화 시점에 로드
        self.config_manager: Optional[ConfigManager] = None
        self.interested_orgs: List[str] = []
        self.interested_repos: List[str] = []
        self.api_server_url = "http://127.0.0.1:8001"  # 기본값

        # HTTP 세션 설정 (재시도 로직 포함)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def initialize_config(self) -> bool:
        """설정 초기화 - 별도 메서드로 분리하여 나중에 호출"""
        try:
            if not self.config_manager:
                self.config_manager = ConfigManager()
                self.config_manager.load_config()

            # app.config에서 repositories 설정 읽기
            self.interested_orgs, self.interested_repos = self._parse_repositories_config()

            # API 서버 URL 설정
            host = self.config_manager.get_config_value("API", "host", "127.0.0.1") or "127.0.0.1"
            port = self.config_manager.get_config_value("API", "port", "8001") or "8001"
            self.api_server_url = f"http://{host}:{port}"

            return True
        except Exception as e:
            logger.error(f"설정 초기화 실패: {e}")
            return False

    def _parse_repositories_config(self) -> tuple[List[str], List[str]]:
        """app.config의 repositories 설정을 파싱하여 orgs와 repos로 분리"""
        if not self.config_manager:
            return [], []

        repositories_str = self.config_manager.get_config_value("GITHUB", "repositories", "") or ""

        if not repositories_str:
            logger.info("GITHUB repositories 설정이 비어있습니다.")
            return [], []

        orgs = []
        repos = []

        # 쉼표로 구분하여 각 항목 처리
        for item in repositories_str.split(","):
            item = item.strip()
            if not item:
                continue

            # "/" 포함되어 있으면 repository (owner/repo 형태)
            if "/" in item:
                repos.append(item)
                # 조직도 추가 (중복 제거는 나중에)
                org = item.split("/")[0]
                if org not in orgs:
                    orgs.append(org)
            else:
                # "/" 없으면 organization
                if item not in orgs:
                    orgs.append(item)

        logger.info(f"관심 조직: {orgs}")
        logger.info(f"관심 저장소: {repos}")

        return orgs, repos

    def _group_messages_by_type(self, messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """이벤트 타입별로 메시지를 그룹핑"""
        grouped = defaultdict(list)

        for message in messages:
            event_type = message.get("event_type", "unknown")
            # GitHub Actions 관련 이벤트들을 별도로 그룹핑
            if event_type in ["workflow_run", "workflow_job", "check_run", "check_suite"]:
                grouped["github_actions"].append(message)
            else:
                grouped[event_type].append(message)

        return dict(grouped)

    def _create_grouped_summary(self, grouped_messages: Dict[str, List[Dict[str, Any]]]) -> str:
        """그룹핑된 메시지들을 요약하여 문자열로 반환"""
        summary_parts: list[str] = []

        for event_type, messages in grouped_messages.items():
            count = len(messages)

            if event_type == "github_actions":
                # GitHub Actions 이벤트 세부 분석
                workflow_summary = self._summarize_workflow_events(messages)
                summary_parts.append(f"🔄 GitHub Actions: {workflow_summary}")

            elif event_type == "push":
                repos = set(msg.get("repo_name", "") for msg in messages)
                summary_parts.append(f"🚀 Push 이벤트 {count}개 (저장소: {', '.join(repos)})")

            elif event_type == "pull_request":
                actions: defaultdict[str, int] = defaultdict(int)
                repos = set()
                for msg in messages:
                    action = msg.get("payload", {}).get("action", "unknown")
                    actions[action] += 1
                    repos.add(msg.get("repo_name", ""))

                action_summary = ", ".join([f"{action} {cnt}개" for action, cnt in actions.items()])
                summary_parts.append(f"📝 Pull Request: {action_summary} (저장소: {', '.join(repos)})")

            elif event_type == "issues":
                actions: defaultdict[str, int] = defaultdict(int)
                repos = set()
                for msg in messages:
                    action = msg.get("payload", {}).get("action", "unknown")
                    actions[action] += 1
                    repos.add(msg.get("repo_name", ""))

                action_summary = ", ".join([f"{action} {cnt}개" for action, cnt in actions.items()])
                summary_parts.append(f"🐛 Issues: {action_summary} (저장소: {', '.join(repos)})")

            else:
                repos = set(msg.get("repo_name", "") for msg in messages)
                summary_parts.append(f"📢 {event_type}: {count}개 (저장소: {', '.join(repos)})")

        return "\n".join(summary_parts)

    def _summarize_workflow_events(self, messages: List[Dict[str, Any]]) -> str:
        """GitHub Actions 워크플로우 이벤트들을 요약"""
        workflows: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0, "in_progress": 0})
        repos = set()

        for msg in messages:
            repo_name = msg.get("repo_name", "")
            repos.add(repo_name)

            payload = msg.get("payload", {})
            workflow_run = payload.get("workflow_run", {})
            conclusion = workflow_run.get("conclusion", "")
            status = workflow_run.get("status", "")

            workflow_name = workflow_run.get("name", "Unknown")

            if conclusion == "success":
                workflows[workflow_name]["success"] += 1
            elif conclusion == "failure":
                workflows[workflow_name]["failure"] += 1
            elif status == "in_progress":
                workflows[workflow_name]["in_progress"] += 1

        workflow_summaries = []
        for workflow_name, stats in workflows.items():
            parts = []
            if stats["success"]:
                parts.append(f"성공 {stats['success']}개")
            if stats["failure"]:
                parts.append(f"실패 {stats['failure']}개")
            if stats["in_progress"]:
                parts.append(f"진행중 {stats['in_progress']}개")

            workflow_summaries.append(f"{workflow_name} ({', '.join(parts)})")

        return f"{', '.join(workflow_summaries)} (저장소: {', '.join(repos)})"

    async def _generate_llm_summary(self, messages: List[Dict[str, Any]]) -> tuple[str, str]:
        """LLM을 사용하여 메시지들을 요약"""
        try:
            from application.llm.llm_agent import LLMAgent
            from application.llm.mcp.mcp_tool_manager import MCPToolManager

            # MCP 도구 관리자 초기화 (None으로 설정하여 기본 응답만 사용)
            mcp_tool_manager = None

            # LLM 에이전트 초기화
            llm_agent = LLMAgent(self.config_manager, mcp_tool_manager)

            # 메시지 정보를 텍스트로 변환
            message_details = []
            for i, msg in enumerate(messages, 1):
                event_type = msg.get("event_type", "unknown")
                repo_name = msg.get("repo_name", "Unknown")
                org_name = msg.get("org_name", "")
                timestamp = msg.get("timestamp", "")
                payload = msg.get("payload", {})

                # 각 이벤트의 주요 정보 추출
                if event_type == "push":
                    commits = payload.get("commits", [])
                    commit_count = len(commits)
                    message_details.append(f"{i}. Push 이벤트 - {repo_name} (커밋 {commit_count}개)")

                elif event_type == "pull_request":
                    action = payload.get("action", "unknown")
                    pr_title = payload.get("pull_request", {}).get("title", "")
                    message_details.append(f"{i}. Pull Request {action} - {repo_name}: {pr_title}")

                elif event_type == "issues":
                    action = payload.get("action", "unknown")
                    issue_title = payload.get("issue", {}).get("title", "")
                    message_details.append(f"{i}. Issue {action} - {repo_name}: {issue_title}")

                elif event_type in ["workflow_run", "workflow_job", "check_run", "check_suite"]:
                    if event_type == "workflow_run":
                        workflow_run = payload.get("workflow_run", {})
                        workflow_name = workflow_run.get("name", "Unknown")
                        conclusion = workflow_run.get("conclusion", "진행중")
                        message_details.append(f"{i}. GitHub Actions 워크플로우 - {repo_name}: {workflow_name} ({conclusion})")
                    elif event_type == "workflow_job":
                        job = payload.get("workflow_job", {})
                        job_name = job.get("name", "Unknown")
                        conclusion = job.get("conclusion", "진행중")
                        message_details.append(f"{i}. GitHub Actions 잡 - {repo_name}: {job_name} ({conclusion})")
                    elif event_type == "check_run":
                        check_run = payload.get("check_run", {})
                        check_name = check_run.get("name", "Unknown")
                        conclusion = check_run.get("conclusion", "진행중")
                        message_details.append(f"{i}. GitHub 체크 - {repo_name}: {check_name} ({conclusion})")
                    else:
                        message_details.append(f"{i}. GitHub Actions 이벤트 - {repo_name}: {event_type}")

                elif event_type == "release":
                    release = payload.get("release", {})
                    tag_name = release.get("tag_name", "")
                    message_details.append(f"{i}. 릴리즈 - {repo_name}: {tag_name}")

                else:
                    message_details.append(f"{i}. {event_type} - {repo_name}")

            # LLM에게 요약 요청
            prompt = f"""
다음은 GitHub 웹훅 이벤트들의 목록입니다. 이 이벤트들을 친근하고 구어체로 요약해주세요.
요약할 때 다음 사항들을 반드시 지켜주세요:

1. 모든 이벤트의 내용이 누락되지 않도록 해주세요
2. 같은 타입의 이벤트들은 그룹핑해서 설명해주세요
3. 친근하고 구어체 톤으로 작성해주세요
4. 이모지를 적절히 사용해주세요
5. 제목(title)과 내용(content)을 분리해서 생각해주세요

총 {len(messages)}개의 이벤트가 있습니다:

{chr(10).join(message_details)}

응답 형식:
제목: [친근한 요약 제목]
내용: [상세한 요약 내용]
"""

            # LLM 응답 생성
            response = await llm_agent.generate_response(prompt)

            # 응답에서 제목과 내용 분리
            lines = response.strip().split('\n')
            title = "📬 GitHub 활동 요약"
            content = response

            for line in lines:
                if line.startswith("제목:"):
                    title = line.replace("제목:", "").strip()
                elif line.startswith("내용:"):
                    # 내용 부분만 추출
                    content_start = response.find("내용:")
                    if content_start >= 0:
                        content = response[content_start + 3:].strip()
                    break

            return title, content

        except Exception as e:
            logger.error(f"LLM 요약 생성 실패: {e}")
            # 폴백: 기본 그룹핑 요약 사용
            grouped = self._group_messages_by_type(messages)
            basic_summary = self._create_grouped_summary(grouped)

            return (
                f"📬 GitHub 활동 요약 ({len(messages)}개 이벤트)",
                f"최근 GitHub에서 {len(messages)}개의 이벤트가 발생했어요!\n\n{basic_summary}\n\n* LLM 요약을 사용할 수 없어 기본 요약을 제공했습니다."
            )

    def _send_pr_html_dialog(self, message: Dict[str, Any]) -> bool:
        """Pull Request Open 이벤트를 HTML 다이얼로그로 전송"""
        try:
            payload = message.get("payload", {})
            pr = payload.get("pull_request", {})
            repo_name = message.get("repo_name", "Unknown")
            org_name = message.get("org_name", "")

            # 상세한 디버그 로그 추가
            logger.info(f"=== PR HTML 다이얼로그 디버그 시작 ===")
            logger.info(f"원본 메시지 키들: {list(message.keys()) if message else '메시지 없음'}")
            logger.info(f"페이로드 키들: {list(payload.keys()) if payload else '페이로드 없음'}")
            logger.info(f"PR 키들: {list(pr.keys()) if pr else 'PR 데이터 없음'}")
            logger.info(f"저장소: {repo_name}, 조직: {org_name}")

            # PR 정보 추출 및 디버깅
            pr_title = pr.get("title", "제목 없음") if pr else "제목 없음"
            pr_number = str(pr.get("number", "")) if pr and pr.get("number") else "번호 없음"
            pr_author = pr.get("user", {}).get("login", "누군가") if pr else "누군가"
            pr_body = pr.get("body") or "" if pr else ""
            pr_url = pr.get("html_url", "") if pr else ""

            logger.info(f"추출된 정보 - 제목: '{pr_title}', 번호: '{pr_number}', 작성자: '{pr_author}', URL: '{pr_url}'")
            
            # 브랜치 정보 (안전하게)
            base_branch = pr.get("base", {}).get("ref", "main") if pr else "main"
            head_branch = pr.get("head", {}).get("ref", "feature") if pr else "feature"
            
            # 변경 통계 (안전하게)
            additions = pr.get("additions", 0) if pr else 0
            deletions = pr.get("deletions", 0) if pr else 0
            changed_files = pr.get("changed_files", 0) if pr else 0
            
            # PR 작성자 아바타
            author_avatar = pr.get("user", {}).get("avatar_url", "") if pr else ""
            
            # 라벨 정보
            labels = pr.get("labels", []) if pr else []
            label_html = ""
            if labels:
                label_items = []
                for label in labels:
                    label_name = label.get("name", "")
                    label_color = label.get("color", "666666")
                    if label_name:  # 라벨 이름이 있을 때만 추가
                        label_items.append(f'<span class="label" style="background-color: #{label_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 4px;">{label_name}</span>')
                if label_items:
                    label_html = '<div style="margin: 8px 0;">' + ''.join(label_items) + '</div>'

            # PR 본문 미리보기 (최대 150자로 줄임)
            body_preview = ""
            if pr_body and pr_body.strip():
                clean_body = pr_body.replace('\r\n', '\n').replace('\r', '\n').strip()
                if len(clean_body) > 150:
                    body_preview = clean_body[:150] + "..."
                else:
                    body_preview = clean_body
                # HTML 이스케이프
                body_preview = body_preview.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')

            # 디버그 로그
            logger.debug(f"PR 정보 - 제목: {pr_title}, 번호: {pr_number}, URL: {pr_url}")

            # 최소 필수 데이터 검증
            if pr_title == "제목 없음" and pr_number == "번호 없음" and not pr_url:
                logger.warning("PR 데이터가 부족하여 기본 알림으로 대체합니다.")
                # 기본 친숙한 메시지로 돌아가기
                title, content = self._create_friendly_message(message)
                if content and content.strip():
                    url = f"{self.api_server_url}/notifications/info"
                    notification_data = {
                        "title": title or "새 PR 알림",
                        "message": content,
                        "duration": 5000,
                        "priority": "normal",
                    }
                    response = self.session.post(url, json=notification_data, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
                    response.raise_for_status()
                    logger.info(f"기본 알림으로 전송 완료: {title}")
                return True

            # HTML 다이얼로그 생성 (더 컴팩트하게)
            # 아바타 이미지 HTML 생성
            avatar_html = f'<img src="{author_avatar}" style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.3);" onerror="this.style.display=\'none\'" />' if author_avatar else '<div style="width: 32px; height: 32px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px;">👤</div>'
            
            # PR 설명 섹션 HTML 생성
            description_html = f'''
                <!-- PR 설명 -->
                <div style="background: #f9fafb; border-radius: 6px; padding: 12px; margin-bottom: 16px; border-left: 3px solid #3b82f6;">
                    <h4 style="margin: 0 0 6px 0; color: #374151; font-size: 13px; font-weight: 600;">📝 설명</h4>
                    <div style="color: #6b7280; font-size: 12px; line-height: 1.4;">{body_preview}</div>
                </div>
                ''' if body_preview else ''
            
            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 12px; max-width: 520px;">
                <!-- 헤더 -->
                <div style="text-align: center; margin-bottom: 12px;">
                    <div style="font-size: 24px; margin-bottom: 4px;">🎉</div>
                    <h2 style="color: #1f2937; margin: 0; font-size: 18px; font-weight: 600;">새로운 Pull Request</h2>
                    <p style="color: #6b7280; margin: 4px 0 0 0; font-size: 13px;">코드 리뷰가 필요합니다!</p>
                </div>

                <!-- PR 정보 카드 -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; padding: 12px; margin-bottom: 12px; color: white; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);">
                    <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px;">
                        {avatar_html}
                        <div style="flex: 1;">
                            <h3 style="margin: 0 0 3px 0; font-size: 15px; font-weight: 600; line-height: 1.2;">{pr_title}</h3>
                            <p style="margin: 0; opacity: 0.9; font-size: 12px;">#{pr_number} by <strong>{pr_author}</strong></p>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 8px; margin-bottom: 6px;">
                        <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;"><strong>📁 {repo_name}</strong></div>
                        <div style="font-size: 11px; opacity: 0.8;">{base_branch} ← {head_branch}</div>
                    </div>
                    
                    {label_html}
                </div>

                <!-- 통계 정보 -->
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                    <div style="background: #f3f4f6; border-radius: 5px; padding: 8px; text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; color: #059669;">+{additions}</div>
                        <div style="font-size: 10px; color: #6b7280;">추가</div>
                    </div>
                    <div style="background: #f3f4f6; border-radius: 5px; padding: 8px; text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; color: #dc2626;">-{deletions}</div>
                        <div style="font-size: 10px; color: #6b7280;">삭제</div>
                    </div>
                    <div style="background: #f3f4f6; border-radius: 5px; padding: 8px; text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; color: #7c3aed;">{changed_files}</div>
                        <div style="font-size: 10px; color: #6b7280;">파일</div>
                    </div>
                </div>

                {description_html}

                <!-- 액션 링크들 -->
                <div style="display: flex; gap: 12px; justify-content: center; margin-top: 16px;">
                    <a href="{pr_url}" target="_blank" rel="noopener noreferrer" style="
                        display: inline-block;
                        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        color: white;
                        text-decoration: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 600;
                        text-align: center;
                        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
                        transition: all 0.2s ease;
                    " onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 12px rgba(16, 185, 129, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(16, 185, 129, 0.3)'">
                        🚀 PR 보러가기
                    </a>
                    <a href="javascript:void(0)" onclick="window.close && window.close(); return false;" style="
                        display: inline-block;
                        background: #f3f4f6;
                        color: #6b7280;
                        text-decoration: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 600;
                        text-align: center;
                        transition: all 0.2s ease;
                    " onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'">
                        나중에
                    </a>
                </div>

                <!-- 동기부여 메시지 -->
                <div style="text-align: center; margin-top: 12px; padding: 10px; background: linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%); border-radius: 5px;">
                    <div style="font-size: 12px; margin-bottom: 2px;">💪</div>
                    <p style="margin: 0; color: #92400e; font-size: 11px; font-weight: 500;">코드 리뷰로 팀의 코드 품질을 높여보세요!</p>
                </div>
            </div>

            <script>
                document.addEventListener('keydown', function(event) {{
                    if (event.key === 'Escape') {{
                        if (window && window.close) {{
                            window.close();
                        }}
                    }}
                }});
            </script>
            """

            # 채팅에 표시할 간단한 메시지 생성
            newline = "\n"
            chat_message = f"🎉 새로운 Pull Request가 열렸어요!{newline}{newline}**{pr_title}** (#{pr_number}){newline}작성자: {pr_author}{newline}저장소: {repo_name}{newline}{newline}코드 리뷰가 필요합니다! 📝"

            # HTML 다이얼로그 전송 (높이 최적화)
            url = f"{self.api_server_url}/notifications/dialog/html"
            dialog_data = {
                "title": f"🎉 새 PR: {pr_title}",
                "html_message": html_content,  # html_content -> html_message로 변경
                "message": chat_message,  # 채팅에 표시할 메시지
                "notification_type": "info",
                "width": 550,
                "height": 380 if body_preview else 340,  # 더 작은 높이로 조정
                "duration": 0  # 자동으로 닫히지 않음
            }

            response = self.session.post(url, json=dialog_data, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            response.raise_for_status()

            logger.info(f"PR HTML 다이얼로그 전송 성공: {pr_title} (#{pr_number}) - URL: {pr_url}")
            logger.info(f"=== PR HTML 다이얼로그 디버그 종료 ===")
            return True

        except Exception as e:
            logger.error(f"PR HTML 다이얼로그 전송 실패: {e}")
            logger.error(f"=== PR HTML 다이얼로그 디버그 종료 (오류) ===")
            return False

    def register_client(self) -> bool:
        """webhook 서버에 클라이언트 등록"""
        try:
            url = f"{self.webhook_server_url}/clients"
            data = {
                "name": self.client_name,
                "description": self.client_description,
                "interested_orgs": self.interested_orgs,
                "interested_repos": self.interested_repos,
            }

            response = self.session.post(url, json=data, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            response.raise_for_status()

            result = response.json()
            self.client_id = result.get("id")

            logger.info(
                f"Webhook 클라이언트 등록 성공: {self.client_name} (ID: {self.client_id})"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.warning(f"클라이언트 등록 실패 (webhook 서버 연결 불가): {e}")
            return False

    def poll_messages(self) -> List[Dict[str, Any]]:
        """새로운 메시지를 polling"""
        if not self.client_id:
            logger.error("클라이언트 ID가 없습니다. 먼저 등록해주세요.")
            return []

        try:
            url = f"{self.webhook_server_url}/poll/{self.client_id}"
            response = self.session.get(url, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            response.raise_for_status()

            result = response.json()
            messages = result.get("messages", [])

            if messages:
                logger.info(f"새로운 메시지 {len(messages)}개 수신")

            return messages

        except requests.exceptions.RequestException as e:
            logger.debug(f"메시지 polling 실패 (일시적): {e}")
            return []

    def _create_friendly_message(self, message: Dict[str, Any]) -> tuple[str, str]:
        """메시지를 친숙하고 구어체 스타일로 가공"""
        event_type = message.get("event_type", "unknown")
        org_name = message.get("org_name", "")
        repo_name = message.get("repo_name", "")
        payload = message.get("payload", {})
        action = payload.get("action", "")
        sender = payload.get("sender", {}).get("login", "누군가")

        # 이벤트별 친숙한 메시지 생성
        if event_type == "push":
            # 푸시 이벤트에서 추가 정보 추출
            commits = payload.get("commits", [])
            commit_count = len(commits)
            branch = payload.get("ref", "").replace("refs/heads/", "")
            pusher = payload.get("pusher", {}).get("name", sender)
            
            # 푸시 정보
            head_commit = payload.get("head_commit", {})
            before = payload.get("before", "")
            after = payload.get("after", "")
            compare_url = payload.get("compare", "")
            
            # 푸시 통계 (head_commit에서 추출)
            added_files = head_commit.get("added", []) if head_commit else []
            removed_files = head_commit.get("removed", []) if head_commit else []
            modified_files = head_commit.get("modified", []) if head_commit else []
            
            # 파일 변경 통계
            files_stats = []
            if added_files:
                files_stats.append(f"추가 {len(added_files)}개")
            if modified_files:
                files_stats.append(f"수정 {len(modified_files)}개")
            if removed_files:
                files_stats.append(f"삭제 {len(removed_files)}개")
            
            files_stats_text = f"파일: {', '.join(files_stats)}" if files_stats else ""
            
            # 강제 푸시 여부 확인
            is_force_push = payload.get("forced", False)
            force_text = " (강제 푸시)" if is_force_push else ""

            commit_messages = []
            commit_authors = set()
            for i, commit in enumerate(commits[:3]):  # 최대 3개까지만 표시
                commit_msg = commit.get("message", "").split("\n")[0][:50]  # 첫 줄만, 최대 50자
                commit_author = commit.get("author", {}).get("name", "")
                commit_id = commit.get("id", "")
                commit_short = commit_id[:7] if commit_id else ""
                
                if commit_author:
                    commit_authors.add(commit_author)
                
                commit_line = f"- {commit_msg}"
                if commit_short:
                    commit_line += f" ({commit_short})"
                if commit_author and commit_author != pusher:
                    commit_line += f" by {commit_author}"
                
                commit_messages.append(commit_line)

            if len(commits) > 3:
                commit_messages.append(f"- ... 그 외 {len(commits) - 3}개 커밋")
                
            # 다중 작성자 정보
            authors_text = ""
            if len(commit_authors) > 1:
                authors_text = f" (작성자: {', '.join(list(commit_authors)[:3])}{'...' if len(commit_authors) > 3 else ''})"

            titles = [
                f"🚀 {pusher}님이 {branch} 브랜치에 푸시했어요!{force_text}",
                f"📦 {branch} 브랜치에 {commit_count}개의 새 커밋!{force_text}",
                f"✨ {pusher}님의 {commit_count}개 커밋이 도착했어요!{force_text}",
                f"🎯 {branch} 브랜치가 업데이트 됐어요!{force_text}"
            ]
            messages = [
                f"{pusher}님이 {repo_name}의 {branch} 브랜치에 {commit_count}개의 새 커밋을 올렸어요!{force_text} 🤔{authors_text}" + (f"\n{files_stats_text}" if files_stats_text else ""),
                f"따끈따끈한 {commit_count}개의 새 코드가 {repo_name}의 {branch} 브랜치에 도착했습니다!{force_text} 👀{authors_text}" + (f"\n{files_stats_text}" if files_stats_text else ""),
                f"{repo_name}의 {branch} 브랜치가 {pusher}님에 의해 업데이트 됐어요~{force_text} 확인해보실래요? 😊{authors_text}" + (f"\n{files_stats_text}" if files_stats_text else ""),
                f"{pusher}님이 {repo_name}의 {branch} 브랜치에 열심히 코딩한 흔적을 남겼어요!{force_text} 💪{authors_text}" + (f"\n{files_stats_text}" if files_stats_text else "")
            ]

            # 커밋 메시지가 있으면 추가
            if commit_messages:
                for i in range(len(messages)):
                    messages[i] += "\n\n📝 커밋 내용:\n" + "\n".join(commit_messages)
                    
            # 비교 URL이 있으면 추가
            if compare_url:
                for i in range(len(messages)):
                    messages[i] += f"\n\n🔗 변경사항 보기: {compare_url}"

        elif event_type == "pull_request":
            # PR 정보 추출
            pr = payload.get("pull_request", {})
            pr_title = pr.get("title", "제목 없음")
            pr_number = pr.get("number", "")
            pr_author = pr.get("user", {}).get("login", sender)
            pr_body = pr.get("body", "")
            pr_body_preview = pr_body[:100] + "..." if pr_body and len(pr_body) > 100 else pr_body

            # 브랜치 정보
            base_branch = pr.get("base", {}).get("ref", "")
            head_branch = pr.get("head", {}).get("ref", "")

            # 변경 통계
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            changed_files = pr.get("changed_files", 0)

            if action == "opened":
                titles = [
                    f"🔥 {pr_author}님이 새 PR을 열었어요: {pr_title}",
                    f"📝 리뷰 요청: {pr_title}",
                    f"🎉 새 PR #{pr_number}: {pr_title}",
                    f"👥 {pr_author}님의 코드 리뷰 요청: {pr_title}"
                ]
                messages = [
                    f"와! {pr_author}님이 {repo_name}에 새로운 PR을 올렸어요! 제목: \"{pr_title}\" 🙋‍♂️\n\n{base_branch} ← {head_branch} | 파일 {changed_files}개 변경 (+{additions}, -{deletions})",
                    f"{pr_author}님이 {repo_name}에 멋진 코드를 들고 나타났습니다! PR #{pr_number}: \"{pr_title}\" 👨‍💻\n\n{base_branch} ← {head_branch} | 파일 {changed_files}개 변경 (+{additions}, -{deletions})",
                    f"{repo_name}에서 {pr_author}님의 PR \"{pr_title}\"에 대한 코드 리뷰가 필요해요~ 함께 봐주실래요? 🤝\n\n{base_branch} ← {head_branch} | 파일 {changed_files}개 변경 (+{additions}, -{deletions})",
                    f"새로운 PR #{pr_number}이 {repo_name}에서 여러분을 기다리고 있어요! {pr_author}님이 작성한 \"{pr_title}\" 😎\n\n{base_branch} ← {head_branch} | 파일 {changed_files}개 변경 (+{additions}, -{deletions})"
                ]

                # PR 설명이 있으면 추가
                if pr_body_preview:
                    for i in range(len(messages)):
                        messages[i] += f"\n\nPR 설명: {pr_body_preview}"

            elif action == "closed":
                # 머지 여부 확인
                merged = pr.get("merged", False)

                if merged:
                    titles = [
                        f"✅ PR 머지 완료: {pr_title}",
                        f"🎊 {pr_author}님의 PR이 머지됐어요!",
                        f"🏆 PR #{pr_number} 머지 성공!",
                        f"📋 {pr_title} - 코드베이스에 합류!"
                    ]
                    messages = [
                        f"축하해요! {pr_author}님의 PR \"{pr_title}\"이 {repo_name}에 성공적으로 머지됐어요! 🎉\n\n{base_branch} ← {head_branch} | 파일 {changed_files}개 변경 (+{additions}, -{deletions})",
                        f"또 하나의 멋진 작업이 {repo_name}에 합류했어요! {pr_author}님의 \"{pr_title}\" PR이 머지됐습니다! 👏\n\n{base_branch} ← {head_branch}",
                        f"{repo_name}의 {base_branch} 브랜치가 {pr_author}님의 코드로 한층 더 발전했어요! PR \"{pr_title}\" 머지 완료! 💪",
                        f"PR 머지 완료! {pr_author}님의 \"{pr_title}\"이 {repo_name}의 {base_branch} 브랜치에 반영됐어요! ✨"
                    ]
                else:
                    titles = [
                        f"❌ PR 닫힘: {pr_title}",
                        f"🚫 PR #{pr_number} 종료",
                        f"📕 {pr_author}님의 PR이 닫혔어요",
                        f"🔒 PR 닫힘: {pr_title}"
                    ]
                    messages = [
                        f"{repo_name}의 PR \"{pr_title}\"이 머지 없이 닫혔어요. 다음 기회에! 🤔",
                        f"{pr_author}님의 PR #{pr_number}이 {repo_name}에서 종료됐어요. 머지되지 않았습니다. 👀",
                        f"{repo_name}에서 PR \"{pr_title}\"이 닫혔어요. 머지 없이 종료되었습니다. 🙏",
                        f"PR 닫힘 알림! {pr_author}님의 \"{pr_title}\"이 머지 없이 종료됐어요. 💻"
                    ]
            else:
                titles = [f"📌 PR #{pr_number} 업데이트: {action}"]
                messages = [f"{repo_name}의 PR \"{pr_title}\"에 {action} 액션이 일어났어요! {pr_author}님의 PR #{pr_number}입니다."]

        elif event_type == "issues":
            # 이슈 정보 추출
            issue = payload.get("issue", {})
            issue_title = issue.get("title", "제목 없음")
            issue_number = issue.get("number", "")
            issue_author = issue.get("user", {}).get("login", sender)
            issue_body = issue.get("body", "")
            issue_body_preview = issue_body[:100] + "..." if issue_body and len(issue_body) > 100 else issue_body

            # 라벨 정보
            labels = issue.get("labels", [])
            label_names = [label.get("name", "") for label in labels]
            label_text = f"라벨: {', '.join(label_names)}" if label_names else ""

            # 담당자 정보
            assignees = issue.get("assignees", [])
            assignee_names = [assignee.get("login", "") for assignee in assignees]
            assignee_text = f"담당자: {', '.join(assignee_names)}" if assignee_names else ""

            if action == "opened":
                titles = [
                    f"🐛 새 이슈 #{issue_number}: {issue_title}",
                    f"❗ {issue_author}님의 이슈 리포트: {issue_title}",
                    f"🚨 새 이슈 등록: {issue_title}",
                    f"📋 #{issue_number} 이슈가 생성됐어요!"
                ]
                messages = [
                    f"어라? {issue_author}님이 {repo_name}에 새로운 이슈를 등록했어요! 🔍\n\n제목: \"{issue_title}\" (#{issue_number})",
                    f"{issue_author}님이 {repo_name}에서 문제를 발견했나봐요~ 확인해보세요! 👀\n\n\"{issue_title}\" (#{issue_number})",
                    f"{repo_name}에 {issue_author}님이 새 이슈를 올렸어요. 개발자님의 도움이 필요해요! 🙏\n\n\"{issue_title}\" (#{issue_number})",
                    f"이슈 알림! {issue_author}님이 등록한 \"{issue_title}\"이 {repo_name}에서 여러분을 기다리고 있어요! 💻 (#{issue_number})"
                ]

                # 이슈 본문이 있으면 추가
                if issue_body_preview:
                    for i in range(len(messages)):
                        messages[i] += f"\n\n내용: {issue_body_preview}"

                # 라벨이나 담당자 정보가 있으면 추가
                extra_details = []
                if label_text:
                    extra_details.append(label_text)
                if assignee_text:
                    extra_details.append(assignee_text)

                if extra_details:
                    for i in range(len(messages)):
                        messages[i] += "\n\n" + " | ".join(extra_details)

            elif action == "closed":
                # 이슈를 닫은 사람 정보 (가능하면)
                closer = payload.get("sender", {}).get("login", "누군가")

                titles = [
                    f"🎯 이슈 해결 완료: #{issue_number}",
                    f"✨ {closer}님이 이슈를 해결했어요!",
                    f"🏅 이슈 #{issue_number} 종료: {issue_title}",
                    f"📝 이슈 클리어: {issue_title}"
                ]
                messages = [
                    f"대단해요! {repo_name}의 이슈 \"{issue_title}\"이 {closer}님에 의해 깔끔하게 해결됐어요! 🎉 (#{issue_number})",
                    f"또 하나의 문제가 {repo_name}에서 사라졌네요! {closer}님이 \"{issue_title}\" 이슈를 닫았습니다. 👍",
                    f"{repo_name}가 더 안정적이 됐어요! {closer}님이 이슈 #{issue_number} \"{issue_title}\"을 해결했습니다! 🙌",
                    f"이슈 해결 완료! {closer}님 덕분에 {repo_name}의 \"{issue_title}\" 문제가 해결됐어요! ⭐"
                ]

                # 라벨 정보가 있으면 추가
                if label_text:
                    for i in range(len(messages)):
                        messages[i] += f"\n\n{label_text}"

            else:
                titles = [f"🔄 이슈 #{issue_number} 업데이트: {action}"]
                messages = [f"{repo_name}의 이슈 \"{issue_title}\"에 {action} 액션이 일어났어요! {issue_author}님이 작성한 이슈 #{issue_number}입니다."]

                # 라벨이나 담당자 변경 시 추가 정보
                if action == "labeled" or action == "unlabeled":
                    label = payload.get("label", {}).get("name", "")
                    if label:
                        messages[0] += f"\n\n{action}된 라벨: {label}"
                        messages[0] += f"\n\n현재 라벨: {', '.join(label_names)}"

                elif action == "assigned" or action == "unassigned":
                    assignee = payload.get("assignee", {}).get("login", "")
                    if assignee:
                        assignee_action = "할당된" if action == "assigned" else "해제된"
                        messages[0] += f"\n\n👤 {assignee_action} 담당자: {assignee}"
                        if assignee_names:
                            messages[0] += f"\n현재 담당자: {', '.join(assignee_names)}"
                            
                # 마일스톤 변경 시 추가 정보
                elif action == "milestoned" or action == "demilestoned":
                    milestone = payload.get("milestone", {})
                    milestone_title = milestone.get("title", "") if milestone else ""
                    if milestone_title:
                        milestone_action = "설정된" if action == "milestoned" else "해제된"
                        messages[0] += f"\n\n🎯 {milestone_action} 마일스톤: {milestone_title}"

        elif event_type == "pull_request_review":
            # PR 리뷰 정보 추출
            review = payload.get("review", {})
            pr = payload.get("pull_request", {})
            review_body = review.get("body", "")
            review_state = review.get("state", "")
            reviewer = review.get("user", {}).get("login", sender)
            review_html_url = review.get("html_url", "")
            
            # PR 정보
            pr_title = pr.get("title", "")
            pr_number = pr.get("number", "")
            pr_author = pr.get("user", {}).get("login", "")
            
            # 브랜치 정보
            base_branch = pr.get("base", {}).get("ref", "")
            head_branch = pr.get("head", {}).get("ref", "")
            
            # PR 통계
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            changed_files = pr.get("changed_files", 0)
            
            # 리뷰 상태별 이모지와 텍스트
            if review_state == "approved":
                state_emoji = "✅"
                state_text = "승인"
                state_description = "코드가 승인되었어요!"
            elif review_state == "changes_requested":
                state_emoji = "🔄"
                state_text = "변경 요청"
                state_description = "개선사항이 요청되었어요"
            elif review_state == "commented":
                state_emoji = "💬"
                state_text = "코멘트"
                state_description = "리뷰 의견을 남겼어요"
            else:
                state_emoji = "📝"
                state_text = "리뷰"
                state_description = "리뷰를 남겼어요"

            # 리뷰 본문 미리보기
            review_preview = ""
            if review_body and review_body.strip():
                clean_review = review_body.replace('\r\n', '\n').replace('\r', '\n').strip()
                if len(clean_review) > 120:
                    review_preview = clean_review[:120] + "..."
                else:
                    review_preview = clean_review

            titles = [
                f"{state_emoji} {reviewer}님의 PR 리뷰: {state_text}",
                f"📋 PR #{pr_number} 리뷰 완료: {state_text}",
                f"{state_emoji} {pr_title} - 리뷰 {state_text}",
                f"👀 {reviewer}님이 코드 리뷰를 완료했어요!"
            ]
            
            branch_info = f"{base_branch} ← {head_branch}" if base_branch and head_branch else ""
            stats_info = f"파일 {changed_files}개 변경 (+{additions}, -{deletions})" if changed_files > 0 else ""
            
            messages = [
                f"{reviewer}님이 {repo_name}의 PR #{pr_number}에 {state_text} 리뷰를 남겼어요! {state_emoji}\n\nPR: {pr_title}\n작성자: {pr_author}\n{state_description}" + (f"\n\n{branch_info}" if branch_info else "") + (f"\n{stats_info}" if stats_info else ""),
                f"코드 리뷰 완료! {reviewer}님이 {repo_name}의 \"{pr_title}\"에 {state_text} 의견을 주셨어요! {state_emoji}\n\n{state_description}" + (f"\n작성자: {pr_author}" if pr_author else "") + (f"\n{branch_info}" if branch_info else ""),
                f"{repo_name}의 PR #{pr_number}이 {reviewer}님에 의해 리뷰되었어요! 상태: {state_text} {state_emoji}\n\nPR: {pr_title}" + (f"\n작성자: {pr_author}" if pr_author else "") + (f"\n{stats_info}" if stats_info else ""),
                f"팀워크! {reviewer}님이 {repo_name}의 \"{pr_title}\" PR을 꼼꼼히 리뷰해주셨어요! {state_emoji} ({state_text})" + (f"\n\n작성자: {pr_author}" if pr_author else "") + (f"\n{branch_info}" if branch_info else "")
            ]

            # 리뷰 내용이 있으면 추가
            if review_preview:
                for i in range(len(messages)):
                    messages[i] += f"\n\n💭 리뷰 내용:\n\"{review_preview}\""
                    
            # 리뷰 URL이 있으면 추가
            if review_html_url:
                for i in range(len(messages)):
                    messages[i] += f"\n\n🔗 리뷰 보기: {review_html_url}"

        elif event_type == "pull_request_review_comment":
            # PR 리뷰 코멘트 정보 추출
            comment = payload.get("comment", {})
            pr = payload.get("pull_request", {})
            comment_body = comment.get("body", "")
            commenter = comment.get("user", {}).get("login", sender)
            comment_html_url = comment.get("html_url", "")
            comment_id = comment.get("id", "")
            
            # PR 정보
            pr_title = pr.get("title", "")
            pr_number = pr.get("number", "")
            pr_author = pr.get("user", {}).get("login", "")
            
            # 브랜치 정보
            base_branch = pr.get("base", {}).get("ref", "")
            head_branch = pr.get("head", {}).get("ref", "")
            
            # 파일 및 라인 정보
            file_path = comment.get("path", "")
            line_number = comment.get("line") or comment.get("original_line", "")
            position = comment.get("position", "")
            original_position = comment.get("original_position", "")
            
            # 인라인 코멘트 vs 일반 코멘트 구분
            is_inline = bool(file_path and line_number)
            comment_type = "인라인 코멘트" if is_inline else "리뷰 코멘트"
            
            # 커밋 정보
            commit_id = comment.get("commit_id", "")
            commit_short = commit_id[:7] if commit_id else ""
            
            # 코멘트 본문 미리보기
            comment_preview = ""
            if comment_body and comment_body.strip():
                clean_comment = comment_body.replace('\r\n', '\n').replace('\r', '\n').strip()
                if len(clean_comment) > 100:
                    comment_preview = clean_comment[:100] + "..."
                else:
                    comment_preview = clean_comment

            # 파일명만 추출 (경로가 길면)
            file_name = file_path.split("/")[-1] if file_path else "파일"
            
            titles = [
                f"💬 {commenter}님의 {comment_type}",
                f"📝 PR #{pr_number}에 새 {comment_type}",
                f"🔍 {file_name}에 리뷰 의견" if is_inline else f"🔍 PR #{pr_number}에 리뷰 의견",
                f"💭 {commenter}님이 코드에 의견을 남겼어요!"
            ]
            
            branch_info = f"{base_branch} ← {head_branch}" if base_branch and head_branch else ""
            
            messages = [
                f"{commenter}님이 {repo_name}의 PR #{pr_number}에 {comment_type}를 남겼어요! 💬\n\nPR: {pr_title}" + (f"\n작성자: {pr_author}" if pr_author else "") + (f"\n{branch_info}" if branch_info else ""),
                f"{comment_type} 도착! {commenter}님이 {repo_name}의 \"{pr_title}\"에 의견을 주셨어요! 👀" + (f"\n작성자: {pr_author}" if pr_author else ""),
                f"{repo_name}의 PR #{pr_number}에 {commenter}님의 새로운 {comment_type}가 있어요! 📝\n\nPR: {pr_title}" + (f"\n작성자: {pr_author}" if pr_author else ""),
                f"세심한 리뷰! {commenter}님이 {repo_name}의 \"{pr_title}\" 코드에 피드백을 남겼어요! 🔍" + (f"\n\n{branch_info}" if branch_info else "")
            ]

            # 파일 위치 정보 추가 (인라인 코멘트인 경우)
            if is_inline:
                location_info = f"📁 {file_path}"
                if line_number:
                    location_info += f" (라인 {line_number})"
                if position:
                    location_info += f" [위치: {position}]"
                if commit_short:
                    location_info += f" (커밋: {commit_short})"
                
                for i in range(len(messages)):
                    messages[i] += f"\n\n{location_info}"

            # 코멘트 내용이 있으면 추가
            if comment_preview:
                for i in range(len(messages)):
                    messages[i] += f"\n\n💭 코멘트:\n\"{comment_preview}\""
                    
            # 코멘트 URL이 있으면 추가
            if comment_html_url:
                for i in range(len(messages)):
                    messages[i] += f"\n\n🔗 코멘트 보기: {comment_html_url}"

        elif event_type == "release":
            # 릴리즈 정보 추출
            release = payload.get("release", {})
            tag_name = release.get("tag_name", "")
            release_name = release.get("name", tag_name)
            release_body = release.get("body", "")
            release_body_preview = release_body[:150] + "..." if release_body and len(release_body) > 150 else release_body

            # 릴리즈 작성자
            author = release.get("author", {}).get("login", sender)

            # 릴리즈 유형 (정식 출시 vs 프리릴리즈)
            is_prerelease = release.get("prerelease", False)
            release_type = "프리릴리즈" if is_prerelease else "정식 릴리즈"

            # 릴리즈 생성 시간
            created_at = release.get("created_at", "")

            titles = [
                f"🎉 {repo_name} {release_name} 출시!",
                f"🚀 {tag_name} 버전 업데이트!",
                f"📦 {repo_name} {release_type}: {release_name}",
                f"✨ 새 릴리즈: {release_name} ({tag_name})"
            ]
            messages = [
                f"와우! {author}님이 {repo_name}의 새 버전 {release_name}을 출시했어요! 🌟\n\n태그: {tag_name} | {release_type}",
                f"축하합니다! {repo_name}가 {author}님에 의해 {release_name} 버전으로 업그레이드됐어요! 🎊\n\n태그: {tag_name} | {release_type}",
                f"{repo_name}의 개발팀이 {tag_name} 태그로 {release_name} 릴리즈를 선보였어요! 👨‍💻\n\n{release_type} | 작성자: {author}",
                f"새로운 기능과 개선사항이 {repo_name}의 {release_name} 버전에 담겨 도착했어요! 확인해보세요! 🔥\n\n태그: {tag_name} | {release_type}"
            ]

            # 릴리즈 노트가 있으면 추가
            if release_body_preview:
                for i in range(len(messages)):
                    messages[i] += f"\n\n릴리즈 노트:\n{release_body_preview}"

        elif event_type == "star":
            # 스타를 준 사용자 정보
            stargazer = sender

            # 현재 스타 수 (가능한 경우)
            stargazers_count = payload.get("repository", {}).get("stargazers_count", "")
            star_count_text = f"현재 스타 {stargazers_count}개" if stargazers_count else ""

            titles = [
                f"⭐ {stargazer}님이 스타를 주셨어요!",
                f"🌟 {repo_name}에 새 스타!",
                f"✨ {stargazer}님이 인정한 프로젝트!",
                f"🎯 {stargazer}님의 스타 감사합니다!"
            ]
            messages = [
                f"오예! {stargazer}님이 {repo_name}에 스타를 주셨어요! ⭐ {star_count_text}",
                f"{stargazer}님이 {repo_name}에 스타를 눌러줬네요! 인기 프로젝트가 되어가고 있어요! 🌟 {star_count_text}",
                f"{repo_name}의 매력에 {stargazer}님이 빠졌나봐요! 스타 감사합니다! 😊 {star_count_text}",
                f"스타 하나 추가! {stargazer}님 덕분에 {repo_name}가 점점 더 빛나고 있어요! ✨ {star_count_text}"
            ]

        elif event_type == "fork":
            # 포크한 사용자 정보
            forker = sender

            # 포크된 저장소 정보
            forkee = payload.get("forkee", {})
            fork_full_name = forkee.get("full_name", "")

            # 현재 포크 수 (가능한 경우)
            forks_count = payload.get("repository", {}).get("forks_count", "")
            fork_count_text = f"현재 포크 {forks_count}개" if forks_count else ""

            titles = [
                f"🍴 {forker}님이 {repo_name}를 포크했어요!",
                f"🌿 {forker}님의 새 포크 생성!",
                f"🔀 {repo_name}가 {forker}님에 의해 포크됐어요!",
                f"📋 {forker}님의 포크 알림!"
            ]
            messages = [
                f"{forker}님이 {repo_name}를 포크했어요! 프로젝트가 더 널리 퍼져나가고 있네요! 🌱" + (f"\n\n포크: {fork_full_name}" if fork_full_name else "") + (f"\n\n{fork_count_text}" if fork_count_text else ""),
                f"와! {forker}님이 {repo_name}를 자신의 계정으로 포크했어요! 🤝" + (f"\n\n포크: {fork_full_name}" if fork_full_name else "") + (f"\n\n{fork_count_text}" if fork_count_text else ""),
                f"{repo_name}의 코드가 {forker}님에 의해 새로운 곳에서 활용될 예정이에요! 기대돼요! 🚀" + (f"\n\n포크: {fork_full_name}" if fork_full_name else "") + (f"\n\n{fork_count_text}" if fork_count_text else ""),
                f"포크 알림! {forker}님이 {repo_name}를 포크하여 오픈소스의 힘을 보여주고 있어요! 💪" + (f"\n\n포크: {fork_full_name}" if fork_full_name else "") + (f"\n\n{fork_count_text}" if fork_count_text else "")
            ]

        elif event_type == "watch":
            # 구독한 사용자 정보
            watcher = sender

            # 현재 구독자 수 (가능한 경우)
            watchers_count = payload.get("repository", {}).get("watchers_count", "")
            watch_count_text = f"현재 구독자 {watchers_count}명" if watchers_count else ""

            titles = [
                f"👀 {watcher}님이 {repo_name}를 구독했어요!",
                f"🔔 {watcher}님이 알림 설정을 했어요!",
                f"👥 {watcher}님이 새 팔로워로 추가됐어요!",
                f"📺 {watcher}님의 구독 알림!"
            ]
            messages = [
                f"{watcher}님이 {repo_name}를 지켜보기 시작했어요! 👀 {watch_count_text}",
                f"{watcher}님이 {repo_name}의 소식을 받아보고 싶어해요! 관심 감사합니다! 😊 {watch_count_text}",
                f"{repo_name}의 팬이 한 명 더 늘었네요! {watcher}님이 구독을 시작했어요! 계속 좋은 코드 부탁해요! 👍 {watch_count_text}",
                f"구독 알림! {watcher}님 덕분에 {repo_name}가 더 많은 사람들에게 알려지고 있어요! 🌟 {watch_count_text}"
            ]
            
        elif event_type == "issue_comment":
            # 이슈/PR 코멘트 정보 추출
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            comment_body = comment.get("body", "")
            commenter = comment.get("user", {}).get("login", sender)
            comment_html_url = comment.get("html_url", "")
            
            # 이슈/PR 정보
            issue_title = issue.get("title", "")
            issue_number = issue.get("number", "")
            issue_author = issue.get("user", {}).get("login", "")
            is_pull_request = "pull_request" in issue  # PR인지 이슈인지 구분
            
            # 이슈/PR 상태
            issue_state = issue.get("state", "")
            
            # 코멘트 본문 미리보기
            comment_preview = ""
            if comment_body and comment_body.strip():
                clean_comment = comment_body.replace('\r\n', '\n').replace('\r', '\n').strip()
                if len(clean_comment) > 120:
                    comment_preview = clean_comment[:120] + "..."
                else:
                    comment_preview = clean_comment
            
            # 이슈/PR 구분
            item_type = "PR" if is_pull_request else "이슈"
            emoji = "🔄" if is_pull_request else "🐛"
            
            titles = [
                f"💬 {commenter}님의 {item_type} 코멘트",
                f"📝 {item_type} #{issue_number}에 새 코멘트",
                f"🗨️ {commenter}님이 의견을 남겼어요!",
                f"💭 {item_type} 토론 참여!"
            ]
            
            messages = [
                f"{commenter}님이 {repo_name}의 {item_type} #{issue_number}에 코멘트를 남겼어요! 💬\n\n{emoji} {item_type}: {issue_title}" + (f"\n작성자: {issue_author}" if issue_author else "") + (f"\n상태: {issue_state}" if issue_state else ""),
                f"{item_type} 코멘트 도착! {commenter}님이 {repo_name}의 \"{issue_title}\"에 의견을 주셨어요! 👀" + (f"\n작성자: {issue_author}" if issue_author else ""),
                f"{repo_name}의 {item_type} #{issue_number}에 {commenter}님의 새로운 코멘트가 있어요! 📝\n\n{emoji} {issue_title}" + (f"\n작성자: {issue_author}" if issue_author else ""),
                f"활발한 토론! {commenter}님이 {repo_name}의 \"{issue_title}\" {item_type}에 참여했어요! 🗣️" + (f"\n상태: {issue_state}" if issue_state else "")
            ]
            
            # 코멘트 내용이 있으면 추가
            if comment_preview:
                for i in range(len(messages)):
                    messages[i] += f"\n\n💭 코멘트:\n\"{comment_preview}\""
                    
            # 코멘트 URL이 있으면 추가
            if comment_html_url:
                for i in range(len(messages)):
                    messages[i] += f"\n\n🔗 코멘트 보기: {comment_html_url}"
                    
        elif event_type == "create":
            # 브랜치/태그 생성 이벤트
            ref = payload.get("ref", "")
            ref_type = payload.get("ref_type", "")
            creator = sender
            master_branch = payload.get("master_branch", "")
            
            # 타입별 이모지와 텍스트
            if ref_type == "branch":
                type_emoji = "🌿"
                type_text = "브랜치"
            elif ref_type == "tag":
                type_emoji = "🏷️"
                type_text = "태그"
            else:
                type_emoji = "📝"
                type_text = ref_type or "항목"
            
            titles = [
                f"{type_emoji} {creator}님이 새 {type_text}를 만들었어요!",
                f"✨ {repo_name}에 새 {type_text}: {ref}",
                f"🎉 {type_text} 생성: {ref}",
                f"🚀 {creator}님의 새 {type_text} 등장!"
            ]
            
            messages = [
                f"{creator}님이 {repo_name}에 새로운 {type_text} '{ref}'를 만들었어요! {type_emoji}" + (f"\n기준 브랜치: {master_branch}" if master_branch else ""),
                f"새로운 {type_text}가 {repo_name}에 등장했네요! '{ref}' {type_emoji}\n생성자: {creator}" + (f"\n기준: {master_branch}" if master_branch else ""),
                f"{repo_name}의 {type_text} '{ref}'가 {creator}님에 의해 생성됐어요! 개발이 활발해지고 있어요! 💪",
                f"{type_text} 생성 알림! {creator}님이 {repo_name}에 '{ref}'를 만들었어요! {type_emoji}" + (f"\n\n기준 브랜치: {master_branch}" if master_branch else "")
            ]
            
        elif event_type == "delete":
            # 브랜치/태그 삭제 이벤트
            ref = payload.get("ref", "")
            ref_type = payload.get("ref_type", "")
            deleter = sender
            
            # 타입별 이모지와 텍스트
            if ref_type == "branch":
                type_emoji = "🗑️"
                type_text = "브랜치"
            elif ref_type == "tag":
                type_emoji = "🏷️"
                type_text = "태그"
            else:
                type_emoji = "❌"
                type_text = ref_type or "항목"
            
            titles = [
                f"{type_emoji} {deleter}님이 {type_text}를 삭제했어요",
                f"🗑️ {repo_name}에서 {type_text} 삭제: {ref}",
                f"❌ {type_text} 제거: {ref}",
                f"🧹 {deleter}님의 정리 작업"
            ]
            
            messages = [
                f"{deleter}님이 {repo_name}의 {type_text} '{ref}'를 삭제했어요! {type_emoji}\n\n정리 작업이 진행되고 있네요!",
                f"{repo_name}에서 {type_text} '{ref}'가 제거됐어요! 🗑️\n삭제자: {deleter}",
                f"{type_text} 삭제 알림! {deleter}님이 {repo_name}의 '{ref}'를 정리했어요! 🧹",
                f"코드베이스 정리! {deleter}님이 {repo_name}에서 {type_text} '{ref}'를 삭제했어요! ✨"
            ]
            
        elif event_type == "commit_comment":
            # 커밋 코멘트 이벤트
            comment = payload.get("comment", {})
            comment_body = comment.get("body", "")
            commenter = comment.get("user", {}).get("login", sender)
            comment_html_url = comment.get("html_url", "")
            commit_id = comment.get("commit_id", "")
            commit_short = commit_id[:7] if commit_id else ""
            
            # 파일 및 라인 정보 (있는 경우)
            file_path = comment.get("path", "")
            line_number = comment.get("line", "")
            position = comment.get("position", "")
            
            # 코멘트 본문 미리보기
            comment_preview = ""
            if comment_body and comment_body.strip():
                clean_comment = comment_body.replace('\r\n', '\n').replace('\r', '\n').strip()
                if len(clean_comment) > 100:
                    comment_preview = clean_comment[:100] + "..."
                else:
                    comment_preview = clean_comment
            
            # 파일명만 추출 (경로가 길면)
            file_name = file_path.split("/")[-1] if file_path else ""
            
            titles = [
                f"💬 {commenter}님의 커밋 코멘트",
                f"📝 {commit_short} 커밋에 새 코멘트",
                f"🔍 커밋 리뷰 의견",
                f"💭 {commenter}님이 커밋에 의견을 남겼어요!"
            ]
            
            messages = [
                f"{commenter}님이 {repo_name}의 커밋 {commit_short}에 코멘트를 남겼어요! 💬",
                f"커밋 코멘트 도착! {commenter}님이 {repo_name}의 커밋에 의견을 주셨어요! 👀\n\n커밋: {commit_short}",
                f"{repo_name}의 커밋 {commit_short}에 {commenter}님의 새로운 코멘트가 있어요! 📝",
                f"코드 리뷰! {commenter}님이 {repo_name}의 커밋에 피드백을 남겼어요! 🔍\n\n커밋: {commit_short}"
            ]
            
            # 파일 위치 정보 추가 (있는 경우)
            if file_path:
                location_info = f"📁 {file_path}"
                if line_number:
                    location_info += f" (라인 {line_number})"
                if position:
                    location_info += f" [위치: {position}]"
                
                for i in range(len(messages)):
                    messages[i] += f"\n\n{location_info}"
            
            # 코멘트 내용이 있으면 추가
            if comment_preview:
                for i in range(len(messages)):
                    messages[i] += f"\n\n💭 코멘트:\n\"{comment_preview}\""
                    
            # 코멘트 URL이 있으면 추가
            if comment_html_url:
                for i in range(len(messages)):
                    messages[i] += f"\n\n🔗 코멘트 보기: {comment_html_url}"
                    
        elif event_type == "gollum":
            # 위키 업데이트 이벤트
            pages = payload.get("pages", [])
            editor = sender
            
            if not pages:
                titles = [f"📚 {editor}님이 위키를 수정했어요!"]
                messages = [f"{editor}님이 {repo_name}의 위키를 업데이트했어요! 📚"]
            else:
                # 페이지별 정보 추출
                page_summaries = []
                for page in pages[:3]:  # 최대 3개까지만 표시
                    page_title = page.get("title", "")
                    page_action = page.get("action", "")
                    page_html_url = page.get("html_url", "")
                    
                    action_emoji = "✏️" if page_action == "edited" else "📄" if page_action == "created" else "🔄"
                    action_text = "수정" if page_action == "edited" else "생성" if page_action == "created" else page_action
                    
                    page_summaries.append(f"{action_emoji} {page_title} ({action_text})")
                
                if len(pages) > 3:
                    page_summaries.append(f"... 그 외 {len(pages) - 3}개 페이지")
                
                titles = [
                    f"📚 {editor}님이 위키를 업데이트했어요!",
                    f"📖 {repo_name} 위키 수정",
                    f"✏️ 위키 편집: {len(pages)}개 페이지",
                    f"📝 {editor}님의 위키 작업"
                ]
                
                messages = [
                    f"{editor}님이 {repo_name}의 위키를 업데이트했어요! 📚\n\n" + "\n".join(page_summaries),
                    f"위키 업데이트 알림! {editor}님이 {repo_name}에서 {len(pages)}개의 위키 페이지를 수정했어요! 📖\n\n" + "\n".join(page_summaries),
                    f"{repo_name}의 문서가 {editor}님에 의해 개선됐어요! 더 나은 문서화! 💪\n\n" + "\n".join(page_summaries),
                    f"지식 공유! {editor}님이 {repo_name}의 위키를 풍성하게 만들어주셨어요! ✨\n\n" + "\n".join(page_summaries)
                ]
                
        elif event_type == "milestone":
            # 마일스톤 이벤트
            milestone = payload.get("milestone", {})
            milestone_title = milestone.get("title", "")
            milestone_number = milestone.get("number", "")
            milestone_state = milestone.get("state", "")
            milestone_description = milestone.get("description", "")
            due_date = milestone.get("due_on", "")
            
            # 마일스톤 통계
            open_issues = milestone.get("open_issues", 0)
            closed_issues = milestone.get("closed_issues", 0)
            total_issues = open_issues + closed_issues
            
            # 액션별 처리
            if action == "created":
                action_emoji = "🎯"
                action_text = "생성"
            elif action == "closed":
                action_emoji = "🏁"
                action_text = "완료"
            elif action == "opened":
                action_emoji = "🔄"
                action_text = "재오픈"
            else:
                action_emoji = "📊"
                action_text = action or "업데이트"
            
            titles = [
                f"{action_emoji} 마일스톤 {action_text}: {milestone_title}",
                f"🎯 마일스톤 #{milestone_number} {action_text}",
                f"📊 {repo_name} 마일스톤 업데이트",
                f"🚀 프로젝트 진척도 알림"
            ]
            
            progress_info = ""
            if total_issues > 0:
                progress_percent = int((closed_issues / total_issues) * 100)
                progress_info = f"\n진행률: {progress_percent}% ({closed_issues}/{total_issues} 완료)"
            
            messages = [
                f"{sender}님이 {repo_name}의 마일스톤을 {action_text}했어요! {action_emoji}\n\n🎯 마일스톤: {milestone_title}" + progress_info + (f"\n마감일: {due_date}" if due_date else ""),
                f"마일스톤 {action_text} 알림! {repo_name}의 '{milestone_title}' 마일스톤이 {action_text}됐어요! 📊" + progress_info,
                f"프로젝트 관리! {sender}님이 {repo_name}의 마일스톤 #{milestone_number}을 {action_text}했어요! 🎯\n\n제목: {milestone_title}" + progress_info,
                f"팀워크! {repo_name}의 '{milestone_title}' 마일스톤이 {action_text}됐어요! 🚀" + progress_info + (f"\n\n마감일: {due_date}" if due_date else "")
            ]
            
            # 마일스톤 설명이 있으면 추가
            if milestone_description:
                description_preview = milestone_description[:100] + "..." if len(milestone_description) > 100 else milestone_description
                for i in range(len(messages)):
                    messages[i] += f"\n\n📝 설명: {description_preview}"

        elif event_type in ["workflow_run", "workflow_job", "check_run", "check_suite"]:
            # GitHub Actions 관련 이벤트 처리
            if event_type == "workflow_run":
                # 워크플로우 실행 정보 추출
                workflow_run = payload.get("workflow_run", {})
                workflow_name = workflow_run.get("name", "Unknown")
                workflow_id = workflow_run.get("id", "")
                status = workflow_run.get("status", "unknown")
                conclusion = workflow_run.get("conclusion", "진행중")

                # 워크플로우 URL
                html_url = workflow_run.get("html_url", "")

                # 워크플로우 실행자
                actor = payload.get("sender", {}).get("login", sender)

                # 브랜치 정보
                head_branch = workflow_run.get("head_branch", "")
                branch_info = f"브랜치: {head_branch}" if head_branch else ""

                # 상태에 따른 이모지 선택
                status_emoji = "🟢" if conclusion == "success" else "🔴" if conclusion == "failure" else "🟡" if status == "in_progress" else "⚪"

                titles = [
                    f"{status_emoji} 워크플로우 실행: {workflow_name}",
                    f"{status_emoji} GitHub Actions: {workflow_name} ({conclusion})",
                    f"{status_emoji} {repo_name}의 워크플로우 {conclusion}",
                    f"{status_emoji} CI/CD 알림: {workflow_name}"
                ]

                messages = [
                    f"{repo_name}의 '{workflow_name}' 워크플로우가 {conclusion} 상태로 실행됐어요! {status_emoji}\n\n실행자: {actor}" + (f"\n\n{branch_info}" if branch_info else ""),
                    f"{actor}님이 실행한 {repo_name}의 '{workflow_name}' 워크플로우가 {conclusion} 상태입니다. {status_emoji}" + (f"\n\n{branch_info}" if branch_info else ""),
                    f"{repo_name}의 CI/CD 파이프라인 '{workflow_name}'이 {conclusion} 상태로 완료됐어요! {status_emoji}\n\n실행자: {actor}" + (f"\n\n{branch_info}" if branch_info else ""),
                    f"GitHub Actions 알림: {repo_name}의 '{workflow_name}' 워크플로우 상태는 {conclusion}입니다. {status_emoji}\n\n실행자: {actor}" + (f"\n\n{branch_info}" if branch_info else "")
                ]

                # URL이 있으면 추가
                if html_url:
                    for i in range(len(messages)):
                        messages[i] += f"\n\n자세히 보기: {html_url}"

            elif event_type == "workflow_job":
                # 워크플로우 잡 정보 추출
                job = payload.get("workflow_job", {})
                job_name = job.get("name", "Unknown")
                job_id = job.get("id", "")
                status = job.get("status", "unknown")
                conclusion = job.get("conclusion", "진행중")

                # 워크플로우 URL
                html_url = job.get("html_url", "")

                # 상태에 따른 이모지 선택
                status_emoji = "🟢" if conclusion == "success" else "🔴" if conclusion == "failure" else "🟡" if status == "in_progress" else "⚪"

                titles = [
                    f"{status_emoji} 작업 실행: {job_name}",
                    f"{status_emoji} GitHub Actions 작업: {job_name} ({conclusion})",
                    f"{status_emoji} {repo_name}의 작업 {conclusion}",
                    f"{status_emoji} CI/CD 작업 알림: {job_name}"
                ]

                messages = [
                    f"{repo_name}의 '{job_name}' 작업이 {conclusion} 상태로 실행됐어요! {status_emoji}",
                    f"{repo_name}의 '{job_name}' 작업이 {conclusion} 상태입니다. {status_emoji}",
                    f"{repo_name}의 CI/CD 작업 '{job_name}'이 {conclusion} 상태로 완료됐어요! {status_emoji}",
                    f"GitHub Actions 작업 알림: {repo_name}의 '{job_name}' 상태는 {conclusion}입니다. {status_emoji}"
                ]

                # URL이 있으면 추가
                if html_url:
                    for i in range(len(messages)):
                        messages[i] += f"\n\n자세히 보기: {html_url}"

            elif event_type == "check_run":
                # 체크 런 정보 추출
                check_run = payload.get("check_run", {})
                check_name = check_run.get("name", "Unknown")
                status = check_run.get("status", "unknown")
                conclusion = check_run.get("conclusion", "진행중")

                # 체크 URL
                html_url = check_run.get("html_url", "")

                # 상태에 따른 이모지 선택
                status_emoji = "🟢" if conclusion == "success" else "🔴" if conclusion == "failure" else "🟡" if status == "in_progress" else "⚪"

                titles = [
                    f"{status_emoji} 체크 실행: {check_name}",
                    f"{status_emoji} GitHub 체크: {check_name} ({conclusion})",
                    f"{status_emoji} {repo_name}의 체크 {conclusion}",
                    f"{status_emoji} 코드 체크 알림: {check_name}"
                ]

                messages = [
                    f"{repo_name}의 '{check_name}' 체크가 {conclusion} 상태로 실행됐어요! {status_emoji}",
                    f"{repo_name}의 '{check_name}' 체크가 {conclusion} 상태입니다. {status_emoji}",
                    f"{repo_name}의 코드 체크 '{check_name}'이 {conclusion} 상태로 완료됐어요! {status_emoji}",
                    f"GitHub 체크 알림: {repo_name}의 '{check_name}' 상태는 {conclusion}입니다. {status_emoji}"
                ]

                # URL이 있으면 추가
                if html_url:
                    for i in range(len(messages)):
                        messages[i] += f"\n\n자세히 보기: {html_url}"

            else:  # check_suite
                # 체크 스위트 정보 추출
                check_suite = payload.get("check_suite", {})
                status = check_suite.get("status", "unknown")
                conclusion = check_suite.get("conclusion", "진행중")

                # 상태에 따른 이모지 선택
                status_emoji = "🟢" if conclusion == "success" else "🔴" if conclusion == "failure" else "🟡" if status == "in_progress" else "⚪"

                titles = [
                    f"{status_emoji} 체크 스위트 실행",
                    f"{status_emoji} GitHub 체크 스위트 ({conclusion})",
                    f"{status_emoji} {repo_name}의 체크 스위트 {conclusion}",
                    f"{status_emoji} 코드 체크 스위트 알림"
                ]

                messages = [
                    f"{repo_name}의 체크 스위트가 {conclusion} 상태로 실행됐어요! {status_emoji}",
                    f"{repo_name}의 체크 스위트가 {conclusion} 상태입니다. {status_emoji}",
                    f"{repo_name}의 코드 체크 스위트가 {conclusion} 상태로 완료됐어요! {status_emoji}",
                    f"GitHub 체크 스위트 알림: {repo_name}의 상태는 {conclusion}입니다. {status_emoji}"
                ]

        else:
            # 기본 메시지 - 가능한 정보 추출 시도
            # 이벤트 발생자
            actor = sender

            # 액션 정보 (있는 경우)
            action_info = f"액션: {action}" if action else ""

            # 페이로드에서 유용한 정보 추출 시도
            payload_preview = ""
            important_keys = ["id", "name", "title", "state", "description", "url", "html_url"]
            extracted_info = []

            for key in important_keys:
                if key in payload and payload[key]:
                    extracted_info.append(f"{key}: {payload[key]}")

            if extracted_info:
                payload_preview = "\n\n" + "\n".join(extracted_info)

            titles = [
                f"📢 {event_type} 이벤트 발생!",
                f"🔔 {actor}님의 {event_type} 알림!",
                f"📬 {repo_name}의 {event_type} 업데이트!",
                f"🎯 {event_type} 액션 발생!"
            ]
            messages = [
                f"{actor}님이 {repo_name}에서 {event_type} 이벤트를 발생시켰어요!" + (f"\n\n{action_info}" if action_info else "") + payload_preview,
                f"{repo_name}의 {event_type} 소식을 전해드려요! 발생자: {actor}" + (f"\n\n{action_info}" if action_info else "") + payload_preview,
                f"어? {repo_name}에서 {actor}님이 {event_type} 이벤트를 발생시켰어요!" + (f"\n\n{action_info}" if action_info else "") + payload_preview,
                f"{repo_name}가 {actor}님에 의해 활발하게 움직이고 있어요! 이벤트: {event_type}" + (f"\n\n{action_info}" if action_info else "") + payload_preview
            ]

        # 랜덤하게 선택
        title = random.choice(titles)
        base_message = random.choice(messages)

        # 추가 정보가 있으면 덧붙이기
        extra_info = []
        if org_name:
            extra_info.append(f"조직: {org_name}")
        if action and action not in base_message:
            extra_info.append(f"액션: {action}")

        # 시간 정보를 친숙하게 표현
        timestamp = message.get("timestamp", "")
        if timestamp:
            extra_info.append(f"방금 전에 일어난 일이에요! ⏰")

        # 최종 메시지 구성
        final_message = base_message
        if extra_info:
            final_message += "\n\n" + " | ".join(extra_info)

        return title, final_message

    def send_notification_to_self(self, message: Dict[str, Any]) -> bool:
        """수신된 메시지를 자기 자신의 API로 전달"""
        try:
            # 필터링 체크
            should_show_system, should_show_bubble = self._should_show_notification(message)
            if not should_show_system and not should_show_bubble:
                logger.debug(f"필터링으로 인해 알림 건너뜀: {message.get('event_type', 'unknown')}")
                return True

            # Pull Request Open 이벤트는 HTML 다이얼로그로 처리
            if (message.get("event_type") == "pull_request" and 
                message.get("payload", {}).get("action") == "opened"):
                return self._send_pr_html_dialog(message)

            # 친숙한 메시지로 변환
            title, content = self._create_friendly_message(message)

            # 빈 메시지 체크
            if not content or not content.strip():
                logger.warning(f"빈 메시지 내용으로 인해 알림 건너뜀: {title}")
                return True

            # 자기 자신의 API로 알림 전송 (시스템 알림인 경우)
            if should_show_system:
                url = f"{self.api_server_url}/notifications/info"
                notification_data = {
                    "title": title or "알림",  # 제목도 빈 값 방지
                    "message": content,
                    "duration": 5000,  # 5초 표시
                    "priority": "normal",
                    "show_bubble": should_show_bubble,  # 버블 표시 여부 전달
                }

                response = self.session.post(url, json=notification_data, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
                response.raise_for_status()

                logger.info(f"알림 전송 성공: {title}")
            else:
                logger.debug(f"시스템 알림 비활성화로 건너뜀: {title}")

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"알림 전송 실패: {e}")
            return False

    def _should_show_notification(self, message: Dict[str, Any]) -> tuple[bool, bool]:
        """메시지가 필터링 조건에 따라 표시되어야 하는지 확인"""
        try:
            # 설정 로드
            if not self.config_manager:
                return True, True  # 설정이 없으면 기본적으로 표시

            settings_json = self.config_manager.get_config_value("GITHUB", "notification_settings", "{}")
            if not settings_json:
                return True, True  # 설정이 없으면 기본적으로 표시

            import json
            try:
                settings = json.loads(settings_json)
            except json.JSONDecodeError:
                return True, True  # 파싱 오류시 기본적으로 표시

            # 전역 활성화 확인
            if not settings.get("enabled", True):
                return False, False

            # 이벤트 정보 추출
            event_type = message.get("event_type", "")
            payload = message.get("payload", {})
            action = payload.get("action", "")

            # 이벤트별 설정 확인
            events_settings = settings.get("events", {})
            
            # 이벤트 타입 매핑
            event_key = self._map_event_type(event_type, action, payload)
            if not event_key or event_key not in events_settings:
                return True, True  # 매핑되지 않은 이벤트는 기본적으로 표시

            event_config = events_settings[event_key]
            
            # 이벤트 활성화 확인
            if not event_config.get("enabled", True):
                return False, False

            # 액션별 필터링
            if event_config.get("actions") and action:
                if not event_config["actions"].get(action, False):
                    return False, False

            # 커스텀 필터링
            if not self._check_custom_filters(event_key, event_config, message):
                return False, False

            # 시스템 알림과 채팅 버블 설정 반환
            show_system = event_config.get("show_system_notification", True)
            show_bubble = event_config.get("show_chat_bubble", True)
            
            return show_system, show_bubble

        except Exception as e:
            logger.error(f"필터링 확인 중 오류: {e}")
            return True, True  # 오류시 기본적으로 표시

    def _map_event_type(self, event_type: str, action: str, payload: Dict[str, Any]) -> str:
        """이벤트 타입을 설정 키로 매핑"""
        if event_type == "push":
            return "push"
        elif event_type == "pull_request":
            return "pull_request"
        elif event_type == "issues":
            return "issues"
        elif event_type == "release":
            return "release"
        elif event_type in ["workflow_run", "workflow_job"]:
            return "workflow"
        elif event_type in ["check_run", "check_suite"]:
            return "workflow"  # 체크도 워크플로우로 분류
        elif event_type in ["star", "fork", "watch", "create", "delete"]:
            return "repository"
        else:
            return None

    def _check_custom_filters(self, event_key: str, event_config: Dict[str, Any], message: Dict[str, Any]) -> bool:
        """커스텀 필터링 조건 확인"""
        try:
            payload = message.get("payload", {})
            
            if event_key == "push":
                # 커밋 수 필터링
                commits = payload.get("commits", [])
                commit_count = len(commits)
                min_commits = event_config.get("min_commits", 1)
                max_commits = event_config.get("max_commits", 50)
                
                if commit_count < min_commits or commit_count > max_commits:
                    return False

                # 브랜치 필터링
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
                
                exclude_branches = event_config.get("exclude_branches", [])
                include_branches = event_config.get("include_branches", [])
                
                if exclude_branches and branch in exclude_branches:
                    return False
                if include_branches and branch not in include_branches:
                    return False

            elif event_key == "release":
                # 프리릴리즈/드래프트 필터링
                release = payload.get("release", {})
                is_prerelease = release.get("prerelease", False)
                is_draft = release.get("draft", False)
                
                if is_prerelease and not event_config.get("include_prerelease", True):
                    return False
                if is_draft and not event_config.get("include_draft", False):
                    return False

            elif event_key == "workflow":
                # 워크플로우 상태/결론 필터링
                if message.get("event_type") in ["workflow_run", "workflow_job"]:
                    workflow_run = payload.get("workflow_run", {}) or payload.get("workflow_job", {})
                    status = workflow_run.get("status", "")
                    conclusion = workflow_run.get("conclusion", "")
                    
                    # 액션 설정에서 상태별 확인
                    actions = event_config.get("actions", {})
                    if status and not actions.get(status, False):
                        return False
                    if conclusion and not actions.get(conclusion, False):
                        return False

            return True

        except Exception as e:
            logger.error(f"커스텀 필터링 확인 중 오류: {e}")
            return True  # 오류시 기본적으로 표시

    def _polling_loop(self):
        """백그라운드에서 실행되는 polling 루프"""
        logger.info("Webhook polling 시작")
        first_poll = True

        while self.is_polling:
            try:
                messages = self.poll_messages()

                if not messages:
                    # 메시지가 없으면 다음 polling까지 대기
                    time.sleep(self.poll_interval)
                    continue

                # 첫 번째 polling이거나 메시지가 많을 때 요약 처리
                should_summarize = first_poll and len(messages) >= 3  # 3개 이상이면 요약

                if should_summarize:
                    logger.info(f"메시지 {len(messages)}개를 요약하여 처리합니다.")
                    self._process_messages_with_summary_sync(messages)
                else:
                    # 개별 메시지 처리
                    for message in messages:
                        self.send_notification_to_self(message)

                first_poll = False

                # 다음 polling까지 대기
                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Polling 루프에서 오류 발생: {e}")
                time.sleep(self.poll_interval)

        logger.info("Webhook polling 종료")

    def _process_messages_with_summary_sync(self, messages: List[Dict[str, Any]]):
        """메시지들을 요약하여 처리 (동기 버전)"""
        try:
            import asyncio

            # 새로운 이벤트 루프에서 비동기 처리 실행
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._run_async_summary, messages)
                        future.result(timeout=30)  # 30초 타임아웃
                else:
                    loop.run_until_complete(self._process_messages_with_summary(messages))
            except RuntimeError:
                # 새로운 이벤트 루프 생성하여 실행
                asyncio.run(self._process_messages_with_summary(messages))

        except Exception as e:
            logger.error(f"요약 처리 실패: {e}")
            # 폴백: 개별 메시지 처리
            logger.info("폴백으로 개별 메시지 처리를 수행합니다.")
            for message in messages:
                self.send_notification_to_self(message)

    def _run_async_summary(self, messages: List[Dict[str, Any]]):
        """별도 스레드에서 비동기 요약 실행"""
        import asyncio
        asyncio.run(self._process_messages_with_summary(messages))

    async def _process_messages_with_summary(self, messages: List[Dict[str, Any]]):
        """메시지들을 요약하여 처리"""
        try:
            # 먼저 "요약 중" 알림 전송
            preparing_title = "🔄 GitHub 활동 정리 중..."
            preparing_message = f"와! GitHub에서 {len(messages)}개의 새로운 활동이 있었네요! 🎉\n\n잠시만 기다려주세요, 모든 내용을 정리해서 알려드릴게요~ 📝✨"

            url = f"{self.api_server_url}/notifications/info"
            preparing_notification = {
                "title": preparing_title,
                "message": preparing_message,
                "duration": 3000,  # 3초 표시
                "priority": "normal",
            }

            # 준비 중 알림 전송
            try:
                response = self.session.post(url, json=preparing_notification, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
                response.raise_for_status()
                logger.info(f"요약 준비 알림 전송 성공: {len(messages)}개 메시지 요약 시작")
            except Exception as e:
                logger.warning(f"요약 준비 알림 전송 실패: {e}")

            # LLM 요약 시도
            title, content = await self._generate_llm_summary(messages)

            # 요약된 내용으로 최종 알림 전송
            final_notification = {
                "title": title,
                "message": content,
                "duration": 8000,  # 8초 표시 (내용이 많으므로)
                "priority": "high",  # 요약 메시지는 높은 우선순위
            }

            response = self.session.post(url, json=final_notification, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            response.raise_for_status()

            logger.info(f"최종 요약 알림 전송 성공: {title} ({len(messages)}개 메시지 요약)")

        except Exception as e:
            logger.error(f"요약 처리 실패: {e}")
            # 폴백: 개별 메시지 처리
            logger.info("폴백으로 개별 메시지 처리를 수행합니다.")

            # 실패 알림도 전송
            try:
                error_notification = {
                    "title": "⚠️ 요약 처리 실패",
                    "message": f"아이고, GitHub 활동 요약 중 문제가 생겨서 개별 알림으로 전환할게요! 😅\n\n총 {len(messages)}개의 메시지를 하나씩 보내드려요~",
                    "duration": 4000,
                    "priority": "normal",
                }
                self.session.post(url, json=error_notification, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            except:
                pass  # 실패 알림 전송도 실패하면 무시

            for message in messages:
                self.send_notification_to_self(message)

    def start_polling(self) -> bool:
        """백그라운드 polling 시작"""
        if self.is_polling:
            logger.warning("이미 polling이 실행 중입니다.")
            return False

        # 설정 초기화
        if not self.config_manager:
            if not self.initialize_config():
                logger.error("설정 초기화에 실패했습니다.")
                return False

        # 클라이언트 등록
        if not self.client_id:
            if not self.register_client():
                logger.error("클라이언트 등록에 실패했습니다.")
                return False

        self.is_polling = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()

        logger.info("백그라운드 polling 시작")
        return True

    def stop_polling(self):
        """백그라운드 polling 중지"""
        if not self.is_polling:
            logger.warning("Polling이 실행 중이 아닙니다.")
            return

        self.is_polling = False

        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)

        logger.info("백그라운드 polling 중지")

    def get_client_info(self) -> Optional[Dict[str, Any]]:
        """클라이언트 정보 조회"""
        if not self.client_id:
            return None

        try:
            url = f"{self.webhook_server_url}/clients/{self.client_id}"
            response = self.session.get(url, timeout=SESSION_SOCKET_TIMEOUT, verify=SESSION_VERIFY)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"클라이언트 정보 조회 실패: {e}")
            return None

    def __del__(self):
        """소멸자에서 polling 정리"""
        if self.is_polling:
            self.stop_polling() 
