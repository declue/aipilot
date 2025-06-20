"""MCP 로그 관리 모듈"""

import datetime

from PySide6.QtGui import QTextCursor


class MCPLogManager:
    """MCP 로그 관리를 담당하는 클래스"""

    def __init__(self, logs_text):
        self.logs_text = logs_text
        self.max_log_lines = 1000  # 최대 로그 라인 수

    def add_log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        self.logs_text.append(log_message)

        # 스크롤을 맨 아래로
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.logs_text.setTextCursor(cursor)

        # 로그 라인 수 제한
        self._limit_log_lines()

    def clear_logs(self):
        """로그 지우기"""
        self.logs_text.clear()
        self.add_log("🗑️ 로그가 지워졌습니다")

    def _limit_log_lines(self):
        """로그 라인 수 제한"""
        document = self.logs_text.document()
        if document.blockCount() > self.max_log_lines:
            # 오래된 로그 삭제
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)

            blocks_to_remove = document.blockCount() - self.max_log_lines
            for _ in range(blocks_to_remove):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # 줄바꿈 문자 제거

    def log_data_refresh_start(self):
        """데이터 새로고침 시작 로그"""
        self.add_log("🔄 MCP 데이터 새로고침 시작...")

    def log_data_refresh_success(self, server_count, tools_count):
        """데이터 새로고침 성공 로그"""
        self.add_log(
            f"✅ 데이터 새로고침 완료 - 서버 {server_count}개, 도구 {tools_count}개"
        )

    def log_data_refresh_error(self, error_message):
        """데이터 새로고침 오류 로그"""
        self.add_log(f"❌ 데이터 로드 실패: {error_message}")

    def log_initial_config_creation(self):
        """초기 설정 생성 로그"""
        self.add_log("📋 MCP 설정 파일이 없어서 기본 설정을 생성합니다...")
        self.add_log("✅ 기본 MCP 설정이 생성되었습니다")

    def log_config_found(self, config_file):
        """설정 파일 발견 로그"""
        self.add_log(f"✅ MCP 설정 파일 발견: {config_file}")

    def log_guidance_messages(self, server_count, tools_count, enabled_server_count):
        """안내 메시지 로그"""
        if server_count == 0:
            self.add_log(
                "💡 MCP 서버가 설정되지 않았습니다. mcp.json 파일을 확인하세요"
            )
        elif tools_count == 0:
            if enabled_server_count == 0:
                self.add_log(
                    "💡 MCP 서버가 비활성화되어 있습니다. mcp.json에서 enabled를 true로 설정하세요"
                )
            else:
                self.add_log(
                    "💡 활성화된 서버에서 도구를 로드할 수 없습니다. 서버 설정을 확인하세요"
                )

    def log_config_file_location(self, file_path):
        """설정 파일 위치 로그"""
        self.add_log(f"📁 설정 파일 위치: {file_path}")
        self.add_log("💡 GitHub 토큰을 설정하려면 mcp.json 파일을 편집하세요")
