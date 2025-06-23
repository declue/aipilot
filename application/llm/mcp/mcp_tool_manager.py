"""
MCP 도구 관리자 - langchain-mcp-adapters를 사용한 진정한 MCP 통합
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from application.llm.mcp.mcp_manager import MCPManager
from application.util.logger import setup_logger

logger = setup_logger("mcp_tool_manager") or logging.getLogger("mcp_tool_manager")


class MCPToolManager:
    """
    진정한 MCP 통합을 위한 도구 관리자
    langchain-mcp-adapters를 사용하여 MCP 서버와 연동
    """
    
    def __init__(self, mcp_manager: MCPManager, config_manager):
        self.mcp_manager = mcp_manager
        self.config_manager = config_manager
        self.mcp_client: Optional[MultiServerMCPClient] = None
        self.langchain_tools: List[Any] = []
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """MCP 클라이언트 초기화"""
        async with self._lock:
            if self._initialized:
                return True
                
            try:
                # MCP 설정 로드
                mcp_config = self.mcp_manager.get_mcp_config()
                if not mcp_config or not mcp_config.enabled:
                    logger.info("MCP가 비활성화되어 있습니다")
                    return False
                
                # 서버 설정 구성
                server_configs = {}
                enabled_servers = mcp_config.get_enabled_servers()
                
                for server_name, server_data in enabled_servers.items():
                    config = {
                        "command": server_data.get("command"),
                        "args": server_data.get("args", []),
                        "transport": "stdio"  # 기본값
                    }
                    
                    if "env" in server_data:
                        config["env"] = server_data["env"]
                        
                    server_configs[server_name] = config
                
                if not server_configs:
                    logger.warning("활성화된 MCP 서버가 없습니다")
                    return False
                
                logger.info(f"MCP 서버 설정: {list(server_configs.keys())}")
                
                # MultiServerMCPClient 생성 (컨텍스트 매니저 사용 안 함)
                self.mcp_client = MultiServerMCPClient(server_configs)
                
                # 도구 로드
                await self._load_tools()
                
                self._initialized = True
                logger.info(f"MCP 도구 관리자 초기화 완료: {len(self.langchain_tools)}개 도구")
                return True
                
            except Exception as e:
                logger.error(f"MCP 도구 관리자 초기화 실패: {e}")
                return False
    
    async def _load_tools(self):
        """Langchain 도구 로드"""
        try:
            if not self.mcp_client:
                return
                
            # MCP 클라이언트에서 도구 가져오기
            self.langchain_tools = await self.mcp_client.get_tools()
            
            logger.info(f"Langchain 도구 {len(self.langchain_tools)}개 로드 완료")
            for tool in self.langchain_tools:
                logger.info(f"  - {tool.name}: {tool.description}")
                
        except Exception as e:
            logger.error(f"도구 로드 실패: {e}")
            self.langchain_tools = []
    
    async def get_langchain_tools(self) -> List[Any]:
        """Langchain 도구 목록 반환"""
        if not self._initialized:
            await self.initialize()
        return self.langchain_tools
    
    async def refresh_tools(self) -> None:
        """도구 목록 새로고침"""
        async with self._lock:
            try:
                if self.mcp_client:
                    await self._load_tools()
                    logger.info("MCP 도구 목록 새로고침 완료")
            except Exception as e:
                logger.error(f"도구 새로고침 실패: {e}")
    
    def get_tool_descriptions(self) -> str:
        """도구 설명 텍스트 반환"""
        if not self.langchain_tools:
            return "사용 가능한 MCP 도구가 없습니다."
        
        descriptions = []
        for tool in self.langchain_tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    async def get_openai_tools(self) -> List[Dict[str, Any]]:
        """OpenAI 형식의 도구 스키마 반환 (하위 호환성)"""
        tools = []
        for langchain_tool in self.langchain_tools:
            try:
                # Langchain 도구를 OpenAI 형식으로 변환
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": langchain_tool.name,
                        "description": langchain_tool.description,
                        "parameters": getattr(langchain_tool, "args_schema", {}).model_json_schema() if hasattr(langchain_tool, "args_schema") and langchain_tool.args_schema else {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                tools.append(tool_schema)
            except Exception as e:
                logger.warning(f"도구 {langchain_tool.name} 스키마 변환 실패: {e}")
        
        return tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """MCP 도구 호출 (하위 호환성 - 직접 호출하지 말고 Langchain을 통해 사용)"""
        try:
            # Langchain 도구 찾기
            target_tool = None
            for tool in self.langchain_tools:
                if tool.name == tool_name:
                    target_tool = tool
                    break
            
            if not target_tool:
                return f"도구 '{tool_name}'을 찾을 수 없습니다."
            
            # 도구 실행
            result = await target_tool.ainvoke(arguments)
            return str(result)
            
        except Exception as e:
            logger.error(f"MCP 도구 {tool_name} 호출 실패: {e}")
            return f"도구 호출 실패: {e}"
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            if self.mcp_client:
                # MultiServerMCPClient는 컨텍스트 매니저로 사용되므로 
                # 명시적 정리가 필요하지 않을 수 있음
                self.mcp_client = None
                
            self.langchain_tools = []
            self._initialized = False
            logger.info("MCP 도구 관리자 정리 완료")
            
        except Exception as e:
            logger.error(f"MCP 도구 관리자 정리 실패: {e}")

    # 하위 호환성을 위한 메서드들
    async def start_servers(self) -> None:
        """서버 시작 (하위 호환성)"""
        await self.initialize()
    
    async def run_agent_with_tools(self, user_message: str) -> Dict[str, Any]:
        """에이전트 실행 (하위 호환성 - 사용하지 않음)"""
        return {
            "response": "이 메서드는 더 이상 사용되지 않습니다. LLMAgent를 직접 사용하세요.",
            "tools_used": []
        }
    
    def stop_all_servers(self):
        """서버 중지 (하위 호환성)"""
        asyncio.create_task(self.cleanup()) 