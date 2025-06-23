import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem


class MCPToolsManager:
    """MCP 도구 표시를 담당하는 클래스"""

    def __init__(self, tools_tree, tool_details_text, log_manager):
        self.tools_tree = tools_tree
        self.tool_details_text = tool_details_text
        self.log_manager = log_manager

        # 도구 아이템 클릭 이벤트 연결
        self.tools_tree.itemClicked.connect(self._on_tool_selected)

    def update_tools(self, tools_data):
        """도구 UI 업데이트"""
        self.tools_tree.clear()

        # 서버별로 그룹화
        server_groups = self._group_tools_by_server(tools_data)

        # 서버별 그룹 생성
        for server_name, tools in server_groups.items():
            server_item = QTreeWidgetItem(self.tools_tree)
            server_item.setText(0, f"📋 {server_name.upper()}")
            server_item.setText(1, f"{len(tools)}개 도구")
            server_item.setText(2, server_name)

            # 도구들 추가
            for tool in tools:
                tool_item = QTreeWidgetItem(server_item)
                tool_item.setText(0, tool["name"])

                description = tool["description"]
                if len(description) > 60:
                    description = description[:60] + "..."
                tool_item.setText(1, description)
                tool_item.setText(2, server_name)

                # 도구 데이터 저장
                tool_item.setData(0, Qt.UserRole, tool)

        # 모든 항목 확장
        self.tools_tree.expandAll()

        # 컬럼 크기 자동 조정
        for i in range(3):
            self.tools_tree.resizeColumnToContents(i)

    def _group_tools_by_server(self, tools_data):
        """도구를 서버별로 그룹화"""
        server_groups = {}

        for tool in tools_data:
            func_info = tool.get("function", {})
            tool_name = func_info.get("name", "Unknown")
            description = func_info.get("description", "")

            # 서버명 추출 (tool_name에서 prefix 제거)
            if "_" in tool_name:
                server_name = tool_name.split("_")[0]
                actual_tool_name = "_".join(tool_name.split("_")[1:])
            else:
                server_name = "unknown"
                actual_tool_name = tool_name

            if server_name not in server_groups:
                server_groups[server_name] = []

            server_groups[server_name].append(
                {
                    "name": actual_tool_name,
                    "full_name": tool_name,
                    "description": description,
                    "parameters": func_info.get("parameters", {}),
                    "tool_data": tool,
                }
            )

        return server_groups

    def _on_tool_selected(self, item, _column):
        """도구 선택 시 호출"""
        tool_data = item.data(0, Qt.UserRole)
        if tool_data:
            self._show_tool_details(tool_data)

    def _show_tool_details(self, tool_data):
        """도구 세부정보 표시"""
        details = f"""
=== 도구 정보: {tool_data['name']} ===

📋 기본 정보:
  • 전체 이름: {tool_data['full_name']}
  • 설명: {tool_data['description']}

🔧 매개변수:
"""

        parameters = tool_data.get("parameters", {})
        if parameters and parameters.get("properties"):
            required_params = parameters.get("required", [])
            for param_name, param_info in parameters["properties"].items():
                param_type = param_info.get("type", "unknown")
                param_desc = param_info.get("description", "설명 없음")
                required_mark = "*" if param_name in required_params else ""
                details += f"  • {param_name} ({param_type}){required_mark}: {param_desc}\n"
        else:
            details += "  • 매개변수 정보 없음\n"

        details += (
            f"\n📊 전체 스키마:\n{json.dumps(tool_data['tool_data'], indent=2, ensure_ascii=False)}"
        )

        self.tool_details_text.setPlainText(details)

        # 로그에 선택 기록
        self.log_manager.add_log(f"🔧 도구 '{tool_data['name']}' 세부정보 표시됨")

    def get_tools_summary(self, tools_data):
        """도구 요약 정보 반환"""
        server_groups = self._group_tools_by_server(tools_data)
        return {
            "total_tools": len(tools_data),
            "servers": list(server_groups.keys()),
            "server_tool_counts": {server: len(tools) for server, tools in server_groups.items()},
        }
