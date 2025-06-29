import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from dspilot_core.llm.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AskAgent(BaseAgent):
    """단순 정보 조회(검색/날씨/시간 등) 전용 에이전트.

    • 복잡한 워크플로우나 React-Agent 를 사용하지 않고, 기본 LLM 응답을 우선 시도한다.
    • MCP 도구가 연결돼 있으면 `auto_tool_flow()` 로 검색·날씨·시간 같은 읽기 전용
      도구를 자동 선택하도록 LLM 에 위임한다. 실패 시에는 순수 LLM 답변으로 폴백한다.
    """

    # AskAgent 는 항상 basic 응답에 집중하므로 BaseAgent 의 모드 결정 로직을 무시한다.
    def _get_llm_mode(self) -> str:  # pylint: disable=arguments-differ
        return "basic"

    # 읽기 전용 툴 화이트리스트 (필요시 확장)
    _READ_ONLY_TOOLS = {
        "get_current_time",
        "get_current_date",
        "get_current_weather",
        "search_web",
        "search_news",
        "rss_search",
    }

    async def _auto_tool_flow_read_only(self, user_message: str, cb=None):
        """auto_tool_flow 래퍼 – 허용된 읽기 전용 MCP 도구만 노출"""
        if self.mcp_tool_manager is None:
            return None

        # 기존 MCP ToolManager 의 메서드 복사
        if not hasattr(self.mcp_tool_manager, "get_langchain_tools"):
            return None

        all_tools = await self.mcp_tool_manager.get_langchain_tools()
        # 화이트리스트 필터링
        filtered = [t for t in all_tools if getattr(t, "name", "") in self._READ_ONLY_TOOLS]

        if not filtered:
            return None

        # 임시로 MCP ToolManager 를 래핑하여 get_langchain_tools() 결과를 제한
        class _Proxy:
            def __init__(self, mgr, tools):
                self._mgr = mgr
                self._tools = tools

            async def get_langchain_tools(self):
                return self._tools

            async def call_mcp_tool(self, name, args):
                return await self._mgr.call_mcp_tool(name, args)

        proxy_mgr = _Proxy(self.mcp_tool_manager, filtered)

        # BaseAgent.auto_tool_flow 를 호출하되, manager 를 프록시로 치환
        original_mgr = self.mcp_tool_manager
        try:
            self.mcp_tool_manager = proxy_mgr  # type: ignore
            return await super().auto_tool_flow(user_message, cb)
        finally:
            self.mcp_tool_manager = original_mgr

    async def generate_response(self, user_message: str, streaming_callback=None):  # noqa: D401
        """정보 조회 응답 생성.

        1. 사용자 메시지를 기록하고
        2. MCP 도구가 있을 경우 auto_tool_flow 로 한 번 시도
        3. 도구를 사용하지 못하거나 필요 없으면 기본 LLM 응답으로 폴백
        """
        # 1) 히스토리 저장
        self.add_user_message(user_message)

        # 2) MCP 도구 활용 (선택)
        if self.mcp_tool_manager is not None:
            try:
                result = await self._auto_tool_flow_read_only(user_message, streaming_callback)
                if result is not None:
                    return result
            except Exception as exc:  # pylint: disable=broad-except
                # 도구 실행이 실패해도 치명적 오류로 취급하지 않고 LLM 폴백
                import logging
                logging.getLogger(__name__).warning("auto_tool_flow 실패, LLM 폴백: %s", exc)

        # 3) 순수 LLM 응답
        response_text = await self._generate_basic_response(user_message, streaming_callback)
        return self._create_response_data(response_text)

    # =================================================================
    # UI에서 사용하는 정적 유틸리티 메서드들 (BasicAgent에서 이동)
    # =================================================================
    
    @staticmethod
    async def test_connection(api_key: str, base_url: str, model: str) -> Dict[str, Any]:
        """
        LLM API 연결 테스트
        
        Args:
            api_key: API 키
            base_url: 서버 URL
            model: 모델명
            
        Returns:
            Dict: {"success": bool, "message": str, "model": str, "response": str}
        """
        try:
            # LLM 클라이언트 생성
            llm_kwargs = {
                "model": model,
                "api_key": api_key,
                "temperature": 0.1,
                "max_tokens": 50,
            }
            
            if base_url:
                llm_kwargs["base_url"] = base_url
            
            llm = ChatOpenAI(**llm_kwargs)
            
            # 간단한 테스트 메시지 전송
            test_message = HumanMessage(content="안녕하세요. 연결 테스트입니다.")
            response = await llm.ainvoke([test_message])
            
            logger.info(f"LLM 연결 테스트 성공: {model}")
            
            return {
                "success": True,
                "message": "연결 성공",
                "model": model,
                "response": response.content if hasattr(response, 'content') else str(response)
            }
            
        except Exception as e:
            logger.error(f"LLM 연결 테스트 실패: {e}")
            return {
                "success": False,
                "message": str(e),
                "model": model,
                "response": ""
            }
    
    @staticmethod
    async def get_available_models(api_key: str, base_url: str) -> Dict[str, Any]:
        """
        사용 가능한 모델 목록 조회
        
        Args:
            api_key: API 키
            base_url: 서버 URL
            
        Returns:
            Dict: {"success": bool, "message": str, "models": List[str]}
        """
        try:
            import httpx

            # 모델 목록 API 호출
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # base_url에서 /v1 제거 후 /v1/models 추가
            if base_url.endswith('/v1'):
                models_url = base_url + '/models'
            elif base_url.endswith('/v1/'):
                models_url = base_url + 'models'
            else:
                models_url = base_url.rstrip('/') + '/v1/models'
            
            async with httpx.AsyncClient() as client:
                response = await client.get(models_url, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                data = response.json()
                
                # OpenAI API 형식 처리
                if "data" in data and isinstance(data["data"], list):
                    models = [model.get("id", "") for model in data["data"] if model.get("id")]
                # Ollama API 형식 처리
                elif "models" in data and isinstance(data["models"], list):
                    models = [model.get("name", "") for model in data["models"] if model.get("name")]
                else:
                    models = []
                
                if models:
                    logger.info(f"모델 목록 조회 성공: {len(models)}개")
                    return {
                        "success": True,
                        "message": f"총 {len(models)}개의 모델을 찾았습니다.",
                        "models": sorted(models)
                    }
                else:
                    return {
                        "success": False,
                        "message": "사용 가능한 모델을 찾을 수 없습니다.",
                        "models": []
                    }
                    
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP 오류 {e.response.status_code}: {e.response.text}"
            logger.error(f"모델 목록 조회 HTTP 오류: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "models": []
            }
        except httpx.RequestError as e:
            error_msg = f"네트워크 오류: {str(e)}"
            logger.error(f"모델 목록 조회 네트워크 오류: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "models": []
            }
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.error(f"모델 목록 조회 실패: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "models": []
            } 