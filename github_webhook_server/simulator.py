import hashlib
import hmac
import json
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk
from typing import Any, Dict

import requests


class GitHubWebhookSimulator:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GitHub Webhook 시뮬레이터")
        self.root.geometry("1000x800")
        
        # Webhook URL 설정
        self.webhook_url = "http://localhost:8000/webhook"
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        
        self.setup_ui()
        
    def setup_ui(self) -> None:
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # type: ignore
        
        # 서버 설정 섹션
        server_frame = ttk.LabelFrame(main_frame, text="서버 설정", padding="10")
        server_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))  # type: ignore
        
        ttk.Label(server_frame, text="Webhook URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(server_frame, width=50)
        self.url_entry.insert(0, self.webhook_url)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))  # type: ignore
        
        # Repository 설정 섹션
        repo_frame = ttk.LabelFrame(main_frame, text="Repository 설정", padding="10")
        repo_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))  # type: ignore
        
        ttk.Label(repo_frame, text="Organization:").grid(row=0, column=0, sticky=tk.W)
        self.org_entry = ttk.Entry(repo_frame, width=30)
        self.org_entry.insert(0, "example-org")
        self.org_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 10))  # type: ignore
        
        ttk.Label(repo_frame, text="Repository:").grid(row=0, column=2, sticky=tk.W)
        self.repo_entry = ttk.Entry(repo_frame, width=30)
        self.repo_entry.insert(0, "example-repo")
        self.repo_entry.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(5, 0))  # type: ignore
        
        # 이벤트 선택 섹션
        event_frame = ttk.LabelFrame(main_frame, text="이벤트 선택", padding="10")
        event_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))  # type: ignore
        
        # 이벤트 카테고리
        self.event_category = tk.StringVar(value="actions")
        ttk.Label(event_frame, text="카테고리:").grid(row=0, column=0, sticky=tk.W)
        
        category_frame = ttk.Frame(event_frame)
        category_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 10))  # type: ignore
        
        ttk.Radiobutton(category_frame, text="GitHub Actions", 
                       variable=self.event_category, value="actions",
                       command=self.update_event_types).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(category_frame, text="Pull Request", 
                       variable=self.event_category, value="pull_request",
                       command=self.update_event_types).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Radiobutton(category_frame, text="Issues", 
                       variable=self.event_category, value="issues",
                       command=self.update_event_types).grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # 이벤트 타입 선택
        ttk.Label(event_frame, text="이벤트 타입:").grid(row=2, column=0, sticky=tk.W)
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(event_frame, textvariable=self.event_type_var, 
                                           state="readonly", width=30)
        self.event_type_combo.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 10))  # type: ignore
        
        # 액션 선택
        ttk.Label(event_frame, text="액션:").grid(row=4, column=0, sticky=tk.W)
        self.action_var = tk.StringVar()
        self.action_combo = ttk.Combobox(event_frame, textvariable=self.action_var, 
                                       state="readonly", width=30)
        self.action_combo.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(5, 10))  # type: ignore
        
        # 추가 설정
        ttk.Label(event_frame, text="추가 설정:").grid(row=6, column=0, sticky=tk.W)
        
        additional_frame = ttk.Frame(event_frame)
        additional_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(5, 10))  # type: ignore
        
        self.pr_number_var = tk.StringVar(value="1")
        ttk.Label(additional_frame, text="PR/Issue 번호:").grid(row=0, column=0, sticky=tk.W)
        self.pr_number_entry = ttk.Entry(additional_frame, textvariable=self.pr_number_var, width=10)
        self.pr_number_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # 실행 버튼
        ttk.Button(event_frame, text="Webhook 시뮬레이션 실행", 
                  command=self.send_webhook).grid(row=8, column=0, pady=(10, 0))
        
        # 로그 섹션
        log_frame = ttk.LabelFrame(main_frame, text="실행 로그", padding="10")
        log_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))  # type: ignore
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=50, height=25)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # type: ignore
        
        # 로그 지우기 버튼
        ttk.Button(log_frame, text="로그 지우기", 
                  command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # 그리드 설정
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        server_frame.columnconfigure(1, weight=1)
        repo_frame.columnconfigure(1, weight=1)
        repo_frame.columnconfigure(3, weight=1)
        event_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 초기 이벤트 타입 업데이트
        self.update_event_types()
        
    def update_event_types(self) -> None:
        """선택된 카테고리에 따라 이벤트 타입 업데이트"""
        category = self.event_category.get()
        
        if category == "actions":
            event_types = ["workflow_run", "workflow_job"]
        elif category == "pull_request":
            event_types = ["pull_request", "pull_request_review", "pull_request_review_comment"]
        else:  # issues
            event_types = ["issues", "issue_comment"]
            
        self.event_type_combo['values'] = event_types
        if event_types:
            self.event_type_var.set(event_types[0])
            self.update_actions()
        
        self.event_type_combo.bind('<<ComboboxSelected>>', lambda e: self.update_actions())
        
    def update_actions(self) -> None:
        """선택된 이벤트 타입에 따라 액션 업데이트"""
        event_type = self.event_type_var.get()
        
        actions_map = {
            "workflow_run": ["requested", "completed", "in_progress"],
            "workflow_job": ["queued", "in_progress", "completed"],
            "pull_request": ["opened", "closed", "synchronize", "reopened", "edited"],
            "pull_request_review": ["submitted", "edited", "dismissed"],
            "pull_request_review_comment": ["created", "edited", "deleted"],
            "issues": ["opened", "closed", "edited", "deleted", "reopened"],
            "issue_comment": ["created", "edited", "deleted"]
        }
        
        actions = actions_map.get(event_type, [])
        self.action_combo['values'] = actions
        if actions:
            self.action_var.set(actions[0])
            
    def generate_signature(self, payload_body: bytes) -> str:
        """GitHub webhook 서명 생성"""
        if not self.webhook_secret:
            return ""
            
        hash_object = hmac.new(
            self.webhook_secret.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        return "sha256=" + hash_object.hexdigest()
        
    def generate_payload(self, event_type: str, action: str) -> Dict[str, Any]:
        """이벤트 타입과 액션에 따른 페이로드 생성"""
        org_name = self.org_entry.get().strip()
        repo_name = self.repo_entry.get().strip()
        full_repo_name = f"{org_name}/{repo_name}" if org_name else repo_name
        pr_number = int(self.pr_number_var.get() or "1")
        
        base_repo = {
            "id": 123456789,
            "name": repo_name,
            "full_name": full_repo_name,
            "owner": {
                "login": org_name or "user",
                "type": "Organization" if org_name else "User"
            },
            "private": False,
            "html_url": f"https://github.com/{full_repo_name}",
            "default_branch": "main"
        }
        
        user = {
            "login": "testuser",
            "id": 12345,
            "type": "User",
            "html_url": "https://github.com/testuser"
        }
        
        if event_type == "workflow_run":
            return {
                "action": action,
                "workflow_run": {
                    "id": 987654321,
                    "name": "CI",
                    "head_branch": "main",
                    "head_sha": "abc123def456",
                    "status": "completed" if action == "completed" else "in_progress",
                    "conclusion": "success" if action == "completed" else None,
                    "workflow_id": 12345,
                    "run_number": 42,
                    "created_at": datetime.now().isoformat() + "Z",
                    "updated_at": datetime.now().isoformat() + "Z",
                    "html_url": f"https://github.com/{full_repo_name}/actions/runs/987654321"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        elif event_type == "workflow_job":
            return {
                "action": action,
                "workflow_job": {
                    "id": 111222333,
                    "run_id": 987654321,
                    "name": "build",
                    "status": "completed" if action == "completed" else action,
                    "conclusion": "success" if action == "completed" else None,
                    "started_at": datetime.now().isoformat() + "Z",
                    "completed_at": datetime.now().isoformat() + "Z" if action == "completed" else None,
                    "html_url": f"https://github.com/{full_repo_name}/runs/111222333"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        elif event_type == "pull_request":
            return {
                "action": action,
                "number": pr_number,
                "pull_request": {
                    "id": 555666777,
                    "number": pr_number,
                    "title": f"테스트 Pull Request #{pr_number}",
                    "body": "테스트용 PR입니다.",
                    "state": "closed" if action == "closed" else "open",
                    "merged": action == "closed",
                    "head": {
                        "label": f"{org_name}:feature-branch",
                        "ref": "feature-branch",
                        "sha": "xyz789abc123"
                    },
                    "base": {
                        "label": f"{org_name}:main",
                        "ref": "main",
                        "sha": "main123abc456"
                    },
                    "user": user,
                    "created_at": datetime.now().isoformat() + "Z",
                    "updated_at": datetime.now().isoformat() + "Z",
                    "html_url": f"https://github.com/{full_repo_name}/pull/{pr_number}"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        elif event_type == "pull_request_review":
            return {
                "action": action,
                "review": {
                    "id": 888999111,
                    "user": user,
                    "body": "테스트 리뷰 코멘트입니다.",
                    "state": "approved",
                    "html_url": f"https://github.com/{full_repo_name}/pull/{pr_number}#pullrequestreview-888999111",
                    "submitted_at": datetime.now().isoformat() + "Z"
                },
                "pull_request": {
                    "id": 555666777,
                    "number": pr_number,
                    "title": f"테스트 Pull Request #{pr_number}",
                    "html_url": f"https://github.com/{full_repo_name}/pull/{pr_number}"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        elif event_type == "issues":
            return {
                "action": action,
                "issue": {
                    "id": 333444555,
                    "number": pr_number,
                    "title": f"테스트 Issue #{pr_number}",
                    "body": "테스트용 이슈입니다.",
                    "state": "closed" if action == "closed" else "open",
                    "user": user,
                    "created_at": datetime.now().isoformat() + "Z",
                    "updated_at": datetime.now().isoformat() + "Z",
                    "html_url": f"https://github.com/{full_repo_name}/issues/{pr_number}"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        elif event_type == "issue_comment":
            return {
                "action": action,
                "issue": {
                    "id": 333444555,
                    "number": pr_number,
                    "title": f"테스트 Issue #{pr_number}",
                    "html_url": f"https://github.com/{full_repo_name}/issues/{pr_number}"
                },
                "comment": {
                    "id": 777888999,
                    "user": user,
                    "body": "테스트 코멘트입니다.",
                    "created_at": datetime.now().isoformat() + "Z",
                    "updated_at": datetime.now().isoformat() + "Z",
                    "html_url": f"https://github.com/{full_repo_name}/issues/{pr_number}#issuecomment-777888999"
                },
                "repository": base_repo,
                "organization": {"login": org_name} if org_name else None,
                "sender": user
            }
            
        # 기본값 (알 수 없는 이벤트)
        return {
            "action": action,
            "repository": base_repo,
            "organization": {"login": org_name} if org_name else None,
            "sender": user
        }
        
    def send_webhook(self) -> None:
        """Webhook 전송"""
        def send_in_thread() -> None:
            try:
                event_type = self.event_type_var.get()
                action = self.action_var.get()
                webhook_url = self.url_entry.get().strip()
                
                if not event_type or not action:
                    self.log_message("❌ 이벤트 타입과 액션을 선택해주세요.")
                    return
                    
                if not webhook_url:
                    self.log_message("❌ Webhook URL을 입력해주세요.")
                    return
                
                # 페이로드 생성
                payload = self.generate_payload(event_type, action)
                payload_json = json.dumps(payload, indent=2)
                payload_bytes = payload_json.encode('utf-8')
                
                # 서명 생성
                signature = self.generate_signature(payload_bytes)
                
                # 헤더 설정
                headers = {
                    "Content-Type": "application/json",
                    "X-GitHub-Event": event_type,
                    "X-GitHub-Delivery": f"test-delivery-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    "User-Agent": "GitHub-Hookshot/test"
                }
                
                if signature:
                    headers["X-Hub-Signature-256"] = signature
                
                self.log_message(f"🚀 Webhook 전송 시작...")
                self.log_message(f"   URL: {webhook_url}")
                self.log_message(f"   Event: {event_type}")
                self.log_message(f"   Action: {action}")
                self.log_message(f"   Organization: {self.org_entry.get() or 'N/A'}")
                self.log_message(f"   Repository: {self.repo_entry.get()}")
                
                # HTTP 요청 전송
                response = requests.post(
                    webhook_url,
                    data=payload_bytes,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.log_message(f"✅ Webhook 전송 성공! (Status: {response.status_code})")
                    try:
                        response_data = response.json()
                        self.log_message(f"   응답: {response_data.get('message', 'N/A')}")
                        if 'saved_file' in response_data:
                            self.log_message(f"   저장된 파일: {response_data['saved_file']}")
                    except:
                        pass
                else:
                    self.log_message(f"❌ Webhook 전송 실패! (Status: {response.status_code})")
                    self.log_message(f"   응답: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                self.log_message("❌ 연결 실패! 서버가 실행 중인지 확인해주세요.")
            except requests.exceptions.Timeout:
                self.log_message("❌ 요청 시간 초과!")
            except Exception as e:
                self.log_message(f"❌ 오류 발생: {str(e)}")
                
        # 별도 스레드에서 실행
        thread = threading.Thread(target=send_in_thread)
        thread.daemon = True
        thread.start()
        
    def log_message(self, message: str) -> None:
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self) -> None:
        """로그 지우기"""
        self.log_text.delete(1.0, tk.END)


def main() -> None:
    root = tk.Tk()
    app = GitHubWebhookSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
