"""
Search result processor for DuckDuckGo and other search tools
"""

import json
import logging
from typing import Dict, List

from application.llm.processors.base_processor import ToolResultProcessor

logger = logging.getLogger(__name__)


class SearchToolResultProcessor(ToolResultProcessor):
    """Specialized processor for search tools like DuckDuckGo"""

    def can_process(self, tool_name: str) -> bool:
        """Check if this is a search-related tool"""
        search_tools = {
            "search_web", 
            "search_with_time_filter",
            "duckduckgo_search",
            "web_search"
        }
        return tool_name in search_tools

    def process(self, tool_name: str, tool_result: str) -> str:
        """Process search results with rich formatting"""
        try:
            data = json.loads(tool_result)
            if "result" not in data:
                return f"- {tool_result.strip()}"

            result_obj = data["result"]
            results_list = result_obj.get("results", [])
            
            if not results_list:
                return "- 검색 결과가 없습니다."

            return self._format_search_results(result_obj, results_list)

        except Exception as e:
            logger.error(f"검색 결과 처리 중 오류: {e}")
            return f"- 검색 결과 처리 실패: {tool_result[:100]}..."

    def _format_search_results(self, result_obj: Dict, results_list: List[Dict]) -> str:
        """Format search results with rich content"""
        output_lines: List[str] = []
        
        # 검색 결과 헤더
        total_chars = result_obj.get("total_content_chars", 0)
        query = result_obj.get("query", "검색")
        output_lines.append(f"\n🔍 웹 검색 결과 ({len(results_list)}개, 총 {total_chars:,}자 본문):")
        output_lines.append(f"📝 검색어: {query}")
        
        # 본문이 있는 결과 우선 처리
        content_results = [r for r in results_list if r.get("full_content")]
        
        if content_results:
            output_lines.append("\n📰 주요 검색 결과 (본문 포함):")
            for i, item in enumerate(content_results[:5], 1):  # 상위 5개만
                formatted_item = self._format_single_result(item, i)
                output_lines.append(formatted_item)
        
        # 본문이 없는 결과들은 간단히 제목만
        other_results = [r for r in results_list if not r.get("full_content")]
        if other_results:
            output_lines.append(f"\n📋 추가 검색 결과 ({len(other_results)}개):")
            for item in other_results[:3]:  # 상위 3개만
                title = item.get("title", "(제목 없음)")
                url = item.get("url", "")
                source = item.get("source", "")
                output_lines.append(f"- {title} | {source} | {url}")
        
        return "\n".join(output_lines)

    def _format_single_result(self, item: Dict, index: int) -> str:
        """Format a single search result item"""
        lines = []
        
        title = item.get("title", "(제목 없음)")
        url = item.get("url", "")
        full_content = item.get("full_content", "")
        published_date = item.get("published_date", "")
        source = item.get("source", "")
        content_type = item.get("content_type", "")
        
        lines.append(f"\n[{index}] {title}")
        
        if published_date:
            lines.append(f"📅 발행일: {published_date}")
        
        if source:
            lines.append(f"🔗 출처: {source}")
            
        if content_type:
            lines.append(f"🏷️ 타입: {content_type}")
        
        lines.append(f"🌐 URL: {url}")
        
        if full_content and len(full_content.strip()) > 50:
            # 본문이 충분히 길면 포함 (LLM이 분석할 수 있도록)
            lines.append(f"📝 본문: {full_content.strip()}")
        else:
            # 본문이 짧으면 description 사용
            description = item.get("description", "")
            if description:
                lines.append(f"📝 요약: {description}")
        
        return "\n".join(lines)

    def get_priority(self) -> int:
        """High priority for search tools"""
        return 100 