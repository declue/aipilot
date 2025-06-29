import logging
import sys
import threading

from dspilot_app.api.api_server import APIServer
from dspilot_app.services.execution_manager import ExecutionManager
from dspilot_app.services.planning_service import PlanningService
from dspilot_app.ui.qt_app import QtApp
from dspilot_app.ui.signals.notification_signals import NotificationSignals
from dspilot_core.config.config_manager import ConfigManager
from dspilot_core.llm.agents.agent_factory import AgentFactory
from dspilot_core.llm.agents.base_agent import BaseAgent
from dspilot_core.llm.mcp.mcp_manager import MCPManager
from dspilot_core.llm.mcp.mcp_tool_manager import MCPToolManager
from dspilot_core.util.logger import setup_logger
from dspilot_core.util.webhook_client import WebhookClient

logger = setup_logger("app") or logging.getLogger("app")


# pylint: disable=too-few-public-methods
class App:
    """메인 애플리케이션 클래스 - QT와 FastAPI를 통합 관리"""

    config_manager: ConfigManager
    mcp_manager: MCPManager
    mcp_tool_manager: MCPToolManager
    planning_service: PlanningService
    execution_manager: ExecutionManager
    api_app: APIServer
    notification_signals: NotificationSignals
    qt_app: QtApp
    webhook_client: WebhookClient | None
    llm_agent: BaseAgent

    def _init_config(self) -> ConfigManager:
        """Config 관리자 초기화"""
        config_manager = ConfigManager()
        config_manager.load_config()
        logger.debug("Config 관리자 초기화 완료")
        return config_manager

    def _init_mcp(self) -> tuple[MCPManager, MCPToolManager]:
        """MCP 관리자 초기화"""
        mcp_manager = MCPManager(self.config_manager)
        logger.debug("MCP 관리자 초기화 완료")
        mcp_tool_manager = MCPToolManager(mcp_manager, self.config_manager)
        logger.debug("MCP 도구 관리자 초기화 완료")
        return mcp_manager, mcp_tool_manager

    def _init_planning_service(
        self, llm_agent: BaseAgent, mcp_tool_manager: MCPToolManager
    ) -> PlanningService:
        """계획 서비스 초기화"""
        planning_service = PlanningService(llm_agent, mcp_tool_manager)
        logger.debug("계획 서비스 초기화 완료")
        return planning_service

    def _init_execution_manager(
        self, llm_agent: BaseAgent, mcp_tool_manager: MCPToolManager
    ) -> ExecutionManager:
        """실행 관리자 초기화"""
        execution_manager = ExecutionManager(llm_agent, mcp_tool_manager)
        logger.debug("실행 관리자 초기화 완료")
        return execution_manager

    def _init_api(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        notification_signals: NotificationSignals,
    ) -> APIServer:
        """API 앱 초기화"""
        api_app = APIServer(mcp_manager, mcp_tool_manager, notification_signals)

        # API 포트와 호스트 설정
        port = self.config_manager.get_config_value("API", "port", "8000")
        host = self.config_manager.get_config_value("API", "host", "127.0.0.1")
        logger.info("애플리케이션 시작")
        logger.info("FastAPI 서버는 http://%s:%s 에서 실행됩니다", host, port)
        logger.info("API 문서는 http://%s:%s/docs 에서 확인할 수 있습니다", host, port)

        # API 엔드포인트 등록
        api_app.register_endpoints()
        return api_app

    def _init_qt(
        self,
        mcp_manager: MCPManager,
        mcp_tool_manager: MCPToolManager,
        api_app: APIServer,
        planning_service: PlanningService,
        execution_manager: ExecutionManager,
    ) -> QtApp:
        """QT 앱 초기화 - 메인 App 인스턴스(self)를 전달"""
        return QtApp(
            mcp_manager,
            mcp_tool_manager,
            api_app,
            planning_service=planning_service,
            execution_manager=execution_manager,
        )

    def _init_webhook_client(self) -> WebhookClient | None:
        """Webhook 클라이언트 초기화"""
        # 설정에서 webhook 서버 정보 읽기
        webhook_enabled_str = self.config_manager.get_config_value("WEBHOOK", "enabled", "false")
        webhook_enabled = webhook_enabled_str.lower() == "true" if webhook_enabled_str else False

        if not webhook_enabled:
            logger.info("Webhook 클라이언트가 비활성화되었습니다.")
            return None

        webhook_server_url = (
            self.config_manager.get_config_value("WEBHOOK", "server_url", "http://localhost:8005")
            or "http://localhost:8005"
        )
        client_name = (
            self.config_manager.get_config_value("WEBHOOK", "client_name", "DSPilot Client")
            or "DSPilot Client"
        )
        client_description = (
            self.config_manager.get_config_value(
                "WEBHOOK", "client_description", "DSPilot 애플리케이션 클라이언트"
            )
            or "DSPilot 애플리케이션 클라이언트"
        )

        # polling 간격 설정
        poll_interval_str = (
            self.config_manager.get_config_value("WEBHOOK", "poll_interval", "10") or "10"
        )
        poll_interval = int(poll_interval_str)

        # WebhookClient가 자체적으로 app.config의 repositories 설정을 읽음
        webhook_client = WebhookClient(
            webhook_server_url=webhook_server_url,
            client_name=client_name,
            client_description=client_description,
            poll_interval=poll_interval,
        )

        logger.info("Webhook 클라이언트 초기화 완료")
        return webhook_client

    def _init_llm_agent(self) -> BaseAgent:
        """LLM Agent 초기화"""
        logger.debug("LLM Agent 초기화 시작")
        agent = AgentFactory.create_agent(
            config_manager=self.config_manager,
            mcp_tool_manager=self.mcp_tool_manager,
            agent_type="problem"
        )
        logger.debug("LLM Agent 초기화 완료")
        return agent

    def __init__(self) -> None:
        """애플리케이션 초기화"""
        # 공통 컴포넌트 초기화
        self.notification_signals = NotificationSignals()
        
        # Config 관리자 초기화
        self.config_manager = self._init_config()
        
        # MCP 관리자 초기화
        self.mcp_manager, self.mcp_tool_manager = self._init_mcp()
        
        # LLM 에이전트 초기화
        self.llm_agent = self._init_llm_agent()
        
        # 계획 및 실행 서비스 초기화
        self.planning_service = self._init_planning_service(self.llm_agent, self.mcp_tool_manager)
        self.execution_manager = self._init_execution_manager(
            self.llm_agent, self.mcp_tool_manager
        )
        
        # API 초기화
        self.api_app = self._init_api(
            self.mcp_manager,
            self.mcp_tool_manager,
            self.notification_signals
        )
        
        # QT 앱 초기화
        self.qt_app = self._init_qt(
            self.mcp_manager,
            self.mcp_tool_manager,
            self.api_app,
            self.planning_service,
            self.execution_manager,
        )
        
        # 웹훅 클라이언트 초기화
        self.webhook_client = self._init_webhook_client()
        
        logger.info("애플리케이션 초기화 완료")

    def _start_webhook_client(self) -> None:
        """Webhook 클라이언트 시작 - 별도 스레드에서 실행"""
        if not self.webhook_client:
            logger.info("Webhook 클라이언트가 비활성화되어 있습니다.")
            return

        def start_webhook_async() -> None:
            try:
                # webhook_client가 None이 아님을 확인
                if not self.webhook_client:
                    return

                # 설정 초기화
                if not self.webhook_client.initialize_config():
                    logger.error("Webhook 클라이언트 설정 초기화 실패")
                    return

                # webhook 서버에 클라이언트 등록
                if self.webhook_client.register_client():
                    # polling 시작
                    if self.webhook_client.start_polling():
                        logger.info("Webhook 클라이언트가 성공적으로 시작되었습니다.")
                    else:
                        logger.error("Webhook polling 시작에 실패했습니다.")
                else:
                    logger.error("Webhook 클라이언트 등록에 실패했습니다.")
            except Exception as e:
                logger.error(f"Webhook 클라이언트 시작 중 오류 발생: {e}")

        # 별도 스레드에서 실행하여 메인 스레드 블로킹 방지

        webhook_thread = threading.Thread(target=start_webhook_async, daemon=True)
        webhook_thread.start()
        logger.info("Webhook 클라이언트 백그라운드 시작 중...")

    def _stop_webhook_client(self) -> None:
        """Webhook 클라이언트 정지"""
        if self.webhook_client:
            try:
                self.webhook_client.stop_polling()
                logger.info("Webhook 클라이언트가 정상적으로 종료되었습니다.")
            except Exception as e:
                logger.error(f"Webhook 클라이언트 종료 중 오류 발생: {e}")

    def run(self) -> None:
        """애플리케이션 실행"""
        # QT 환경 설정
        self.qt_app.setup_qt_environment()

        # QT 애플리케이션 생성
        self.qt_app.create_qt_application()

        # 트레이 앱 생성
        self.qt_app.create_tray_app()

        # Webhook 클라이언트 시작
        self._start_webhook_client()

        # QT 애플리케이션 실행
        try:
            sys.exit(self.qt_app.run())
        finally:
            # 애플리케이션 종료 시 webhook 클라이언트 정리
            self._stop_webhook_client()
