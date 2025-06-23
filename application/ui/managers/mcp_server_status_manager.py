from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem


class MCPServerStatusManager:
    """MCP 서버 상태 표시를 담당하는 클래스"""

    def __init__(self, server_status_tree, tool_details_text, log_manager):
        self.server_status_tree = server_status_tree
        self.tool_details_text = tool_details_text
        self.log_manager = log_manager

        # 서버 상태 아이템 클릭 이벤트 연결
        self.server_status_tree.itemClicked.connect(self._on_server_selected)

    def update_server_status(self, server_data):
        """서버 상태 UI 업데이트"""
        self.server_status_tree.clear()

        for server_name, data in server_data.items():
            config = data["config"]
            status = data["status"]

            item = QTreeWidgetItem(self.server_status_tree)
            item.setText(0, server_name)

            # 상태 표시
            if config.enabled and status.connected:
                item.setText(1, "🟢 연결됨")
                item.setData(0, Qt.UserRole, "connected")
            elif config.enabled and not status.connected:
                item.setText(1, "🔴 연결 실패")
                item.setData(0, Qt.UserRole, "failed")
                # 오류 메시지가 있으면 툴팁에 표시
                if status.error_message:
                    item.setToolTip(1, f"오류: {status.error_message}")
            else:
                item.setText(1, "⚫ 비활성화")
                item.setData(0, Qt.UserRole, "disabled")
                item.setToolTip(
                    1,
                    "이 서버는 비활성화되어 있습니다. mcp.json에서 enabled를 true로 설정하세요.",
                )

            # 도구 수
            tools_count = len(status.tools) if status.tools else 0
            item.setText(2, str(tools_count))

            # 서버 세부 정보 저장
            item.setData(0, Qt.UserRole + 1, data)

            # 하위 항목: 도구, 리소스, 프롬프트
            if status.connected:
                self._add_server_sub_items(item, status)

        # 모든 항목 확장
        self.server_status_tree.expandAll()

        # 컬럼 크기 자동 조정
        for i in range(3):
            self.server_status_tree.resizeColumnToContents(i)

    def _add_server_sub_items(self, parent_item, status):
        """서버 하위 항목 추가 (도구, 리소스, 프롬프트)"""
        # 도구
        if status.tools:
            tools_item = QTreeWidgetItem(parent_item)
            tools_item.setText(0, f"📦 도구 ({len(status.tools)}개)")
            for tool in status.tools:
                tool_item = QTreeWidgetItem(tools_item)
                tool_item.setText(0, tool.get("name", "Unknown"))
                description = tool.get("description", "")
                if len(description) > 50:
                    description = description[:50] + "..."
                tool_item.setText(1, description)

        # 리소스
        if status.resources:
            resources_item = QTreeWidgetItem(parent_item)
            resources_item.setText(0, f"📁 리소스 ({len(status.resources)}개)")
            for resource in status.resources:
                resource_item = QTreeWidgetItem(resources_item)
                resource_item.setText(0, resource.get("name", "Unknown"))
                resource_item.setText(1, resource.get("description", ""))

        # 프롬프트
        if status.prompts:
            prompts_item = QTreeWidgetItem(parent_item)
            prompts_item.setText(0, f"💬 프롬프트 ({len(status.prompts)}개)")
            for prompt in status.prompts:
                prompt_item = QTreeWidgetItem(prompts_item)
                prompt_item.setText(0, prompt.get("name", "Unknown"))
                prompt_item.setText(1, prompt.get("description", ""))

    def _on_server_selected(self, item, _column):
        """서버 선택 시 호출"""
        server_data = item.data(0, Qt.UserRole + 1)
        if server_data:
            self._show_server_details(server_data)

    def _show_server_details(self, server_data):
        """서버 세부정보 표시"""
        config = server_data["config"]
        status = server_data["status"]
        name = server_data["name"]

        details = f"""
=== 서버 정보: {name} ===

📋 기본 설정:
  • 명령어: {config.command}
  • 인수: {' '.join(config.args) if config.args else '없음'}
  • 활성화: {'✅ 예' if config.enabled else '❌ 아니오'}
  • 설명: {config.description or '설명 없음'}

🔌 연결 상태:
  • 상태: {'🟢 연결됨' if status.connected else '🔴 연결 실패'}
  • 도구 수: {len(status.tools)}개
  • 리소스 수: {len(status.resources)}개  
  • 프롬프트 수: {len(status.prompts)}개

🌍 환경변수:
"""

        if config.env:
            for key, value in config.env.items():
                # 민감한 정보는 일부 숨김
                if any(
                    sensitive in key.lower() for sensitive in ["token", "key", "secret"]
                ):
                    if len(value) > 8:
                        masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                    else:
                        masked_value = "*" * len(value)
                    details += f"  • {key}: {masked_value}\n"
                else:
                    details += f"  • {key}: {value}\n"
        else:
            details += "  • 없음\n"

        if status.error_message:
            details += f"\n❌ 오류 메시지:\n  {status.error_message}\n"

        self.tool_details_text.setPlainText(details)

        # 로그에 선택 기록
        self.log_manager.add_log(f"📋 서버 '{name}' 세부정보 표시됨")
