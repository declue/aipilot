# LLM 모듈 사용 예시

## 1. 기본 에이전트 사용

```python
from application.llm import AgentFactory

# 에이전트 생성
agent = AgentFactory.create_agent(config_manager)

# 기본 채팅
response = await agent.generate_response("안녕하세요!")
print(response["response"])

# 스트리밍 채팅
def streaming_callback(chunk):
    print(chunk, end="", flush=True)

response = await agent.generate_response("스트리밍 테스트", streaming_callback)
```

## 2. 설정 검증

```python
from application.llm.validators import LLMConfigValidator, MCPConfigValidator
from application.llm.models import LLMConfig, MCPConfig

# LLM 설정 검증
try:
    config = LLMConfig(api_key="test", model="gpt-4o-mini", temperature=0.7)
    LLMConfigValidator.validate_config(config)
    print("✅ LLM 설정 유효")
except Exception as e:
    print(f"❌ LLM 설정 오류: {e}")

# MCP 설정 검증
try:
    mcp_config = MCPConfig.from_dict({
        "enabled": True,
        "mcp_servers": {
            "search": {"command": "uvx", "args": ["mcp-server-duckduckgo"]}
        }
    })
    MCPConfigValidator.validate_config(mcp_config)
    print("✅ MCP 설정 유효")
except Exception as e:
    print(f"❌ MCP 설정 오류: {e}")
```

## 3. 성능 모니터링

```python
from application.llm.monitoring import get_metrics, PerformanceTracker

# 성능 추적
async def example_with_tracking():
    tracker = PerformanceTracker(
        operation_name="example_operation",
        agent_type="BasicAgent", 
        model="gpt-4o-mini",
        track_metrics=True
    )
    
    async with tracker.atrack():
        # 실제 작업 수행
        result = await agent.generate_response("테스트 메시지")
        return result

# 메트릭스 조회
metrics = get_metrics()
summary = metrics.get_summary_report()
print(f"총 요청: {summary['total_requests']}")
print(f"성공률: {summary['success_rate']:.2%}")
print(f"평균 응답 시간: {summary['average_response_time']:.2f}초")
```

## 4. 워크플로우 사용

```python
from application.llm.workflow import get_workflow

# 연구 워크플로우
research_workflow = get_workflow("research")()
result = await research_workflow.run(agent, "AI 기술 동향 분석")

# 문제 해결 워크플로우  
problem_workflow = get_workflow("problem_solving")()
result = await problem_workflow.run(agent, "서버 성능 이슈 해결")

# 다단계 워크플로우
multi_step_workflow = get_workflow("multi_step")()
result = await multi_step_workflow.run(agent, "복잡한 프로젝트 계획 수립")
```

## 5. 커스텀 워크플로우

```python
from application.llm.workflow import BaseWorkflow, register_workflow

class CodeReviewWorkflow(BaseWorkflow):
    async def run(self, agent, message, streaming_callback=None):
        # 1단계: 코드 분석
        analysis_prompt = f"다음 코드를 분석해주세요:\n{message}"
        analysis = await agent._generate_basic_response(analysis_prompt)
        
        # 2단계: 개선점 도출
        improvement_prompt = f"분석 결과:\n{analysis}\n\n개선점을 제안해주세요."
        improvements = await agent._generate_basic_response(improvement_prompt)
        
        return f"## 코드 분석\n{analysis}\n\n## 개선 제안\n{improvements}"

# 워크플로우 등록 및 사용
register_workflow("code_review", CodeReviewWorkflow)
workflow = get_workflow("code_review")()
result = await workflow.run(agent, "def hello(): print('world')")
```

## 6. MCP 도구 활용

```python
from application.llm.mcp import MCPManager, MCPToolManager

# MCP 초기화
mcp_manager = MCPManager(config_manager)
mcp_tool_manager = MCPToolManager(mcp_manager, config_manager)

await mcp_tool_manager.initialize()

# 사용 가능한 도구 확인
tools = await mcp_tool_manager.get_langchain_tools()
print(f"사용 가능한 도구: {[tool.name for tool in tools]}")

# 도구 직접 호출
result = await mcp_tool_manager.call_mcp_tool("search_web", {"query": "Python"})
print(result)
```

## 7. 커스텀 프로세서

```python
from application.llm.processors import ToolResultProcessor

class WeatherProcessor(ToolResultProcessor):
    def can_process(self, tool_name: str) -> bool:
        return "weather" in tool_name.lower()
    
    def process(self, tool_name: str, tool_result: str) -> str:
        import json
        try:
            data = json.loads(tool_result)
            result = data.get("result", {})
            
            return f"""
🌤️ 날씨 정보:
📍 위치: {result.get('location', 'N/A')}
🌡️ 온도: {result.get('temperature', 'N/A')}°C
💧 습도: {result.get('humidity', 'N/A')}%
🌬️ 바람: {result.get('wind_speed', 'N/A')} m/s
☁️ 상태: {result.get('condition', 'N/A')}
"""
        except:
            return f"날씨 정보 처리 실패: {tool_result}"
    
    def get_priority(self) -> int:
        return 80

# 프로세서 등록 (BaseAgent 인스턴스에서)
agent._get_processor_registry().register(WeatherProcessor())
```

## 8. 구조화된 로깅

```python
from application.llm.utils.logging_utils import get_llm_logger, LogLevel

logger = get_llm_logger(__name__)

# 일반 로그
logger.info("에이전트 시작", context={"user_id": "123", "session_id": "abc"})

# Agent 활동 로그
logger.log_agent_activity(
    agent_type="ReactAgent",
    operation="generate_response", 
    message="응답 생성 완료",
    duration=2.5,
    success=True
)

# MCP 이벤트 로그
logger.log_mcp_event(
    server_name="search",
    operation="tool_call",
    message="검색 도구 호출",
    tool_name="search_web"
)

# 워크플로우 로그
logger.log_workflow_event(
    workflow_name="research",
    step="data_collection",
    message="정보 수집 단계 완료"
)
```

이 예시들을 참고하여 LLM 모듈을 효과적으로 활용하세요! 🚀
