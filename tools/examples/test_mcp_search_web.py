import asyncio
import json
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


async def run_search(query: str = "오늘 주요 뉴스", max_results: int = 5) -> None:
    """DuckDuckGo MCP 서버(search_web)를 호출하여 결과를 출력합니다."""

    project_root = Path(__file__).resolve().parents[2]
    duck_path = project_root / "tools" / "web_search" / "duckduckgo.py"

    # 가상환경의 Python 실행 파일 경로를 직접 지정 (Windows 기준)
    venv_python_executable = project_root / "venv" / "Scripts" / "python.exe"

    if not venv_python_executable.exists():
        print(f"❌ 가상환경 Python을 찾을 수 없습니다: {venv_python_executable}")
        # 폴백으로 현재 sys.executable 사용
        python_executable = sys.executable
    else:
        python_executable = str(venv_python_executable)

    server_configs = {
        "web_search": {
            "command": python_executable,
            "args": [str(duck_path)],
            "transport": "stdio",
        }
    }

    print(f"🚀 MCP 서버 실행 (인터프리터: {python_executable})")
    client = MultiServerMCPClient(server_configs)

    # MCP 서버가 기동될 때까지 잠시 대기
    await asyncio.sleep(3)

    print("🔍 도구 로드 중…")
    tools = await client.get_tools()
    target_tool = None
    for tool in tools:
        if tool.name == "search_web":
            target_tool = tool
            break

    if not target_tool:
        print("❌ search_web 도구를 찾을 수 없습니다.")
        return

    print("🔧 search_web 실행…")
    result = await target_tool.ainvoke(
        {
            "query": query,
            "region": "kr-kr",  # 글로벌
            "safe_search": "moderate",
            "max_results": max_results,
        }
    )

    print("✅ 결과 수신\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 프로세스 종료를 위해 client.cleanup() 호출 필요 없음 (현재 버전은 자동 정리)


if __name__ == "__main__":
    asyncio.run(run_search()) 