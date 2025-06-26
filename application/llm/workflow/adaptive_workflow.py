import json
import logging
from typing import Any, Callable, Dict, List, Optional

from application.llm.workflow.base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class AdaptiveWorkflow(BaseWorkflow):
    """
    사용자 요청을 분석하여 필요한 도구와 단계를 자동으로 계획하고 실행하는 적응형 워크플로우
    키워드나 특정 조건에 의존하지 않는 범용적인 접근법
    """

    def __init__(self):
        self.max_steps = 10  # 최대 실행 단계 수
        self.step_results = {}  # 각 단계별 결과 저장

    async def run(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        적응형 워크플로우 실행
        1. 요청 분석 및 계획 수립
        2. 계획된 단계들 순차 실행
        3. 결과 통합 및 검증
        """
        try:
            logger.info("적응형 워크플로우 시작: %s", message[:100])
            
            # 1단계: 워크플로우 계획 수립
            workflow_plan = await self._analyze_and_plan(agent, message, streaming_callback)
            if not workflow_plan or not workflow_plan.get("steps"):
                logger.warning("워크플로우 계획 수립 실패")
                return await agent._generate_basic_response(message, streaming_callback)
            
            logger.info("워크플로우 계획 완료: %d단계", len(workflow_plan["steps"]))
            
            # 2단계: 계획된 단계들 순차 실행
            execution_results = await self._execute_workflow_steps(
                agent, workflow_plan, message, streaming_callback
            )
            
            # 3단계: 결과 통합 및 최종 응답 생성
            final_response = await self._integrate_and_finalize(
                agent, message, workflow_plan, execution_results, streaming_callback
            )
            
            return final_response
            
        except Exception as e:
            logger.error("적응형 워크플로우 실행 중 오류: %s", e)
            return f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}"

    async def _analyze_and_plan(
        self, 
        agent: Any, 
        message: str, 
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        사용자 요청을 분석하여 필요한 도구와 실행 순서를 계획
        """
        try:
            # 사용 가능한 도구 목록 가져오기
            available_tools = []
            if hasattr(agent, 'mcp_tool_manager') and agent.mcp_tool_manager:
                langchain_tools = await agent.mcp_tool_manager.get_langchain_tools()
                available_tools = [
                    {"name": tool.name, "description": tool.description} 
                    for tool in langchain_tools
                ]
            
            if not available_tools:
                logger.warning("사용 가능한 도구가 없습니다")
                return {}
            
            # 도구 설명 생성
            tools_desc = "\n".join([
                f"- {tool['name']}: {tool['description']}" 
                for tool in available_tools
            ])
            
            # 워크플로우 계획 프롬프트
            planning_prompt = f"""사용자 요청을 분석하여 단계별 실행 계획을 수립해주세요.

사용자 요청: {message}

사용 가능한 도구들:
{tools_desc}

다음 지침에 따라 워크플로우를 계획하세요:

1. 요청을 완전히 처리하기 위해 필요한 모든 단계를 식별
2. 각 단계에서 사용할 도구와 매개변수 결정
3. 단계 간 의존성과 실행 순서 고려
4. 데이터 수집 → 처리/가공 → 저장/출력 순서로 구성

**중요한 지침:**
- 파일 저장 단계에서는 content 매개변수에 "${{step_N_result}}" 형태로 이전 단계 결과를 참조하세요
- 검색 후 저장하는 경우: content에 "${{step_1_result}}"와 같이 검색 결과를 참조
- 실제 데이터나 플레이스홀더 텍스트가 아닌 단계 참조를 사용하세요

**응답 형식 (JSON):**
{{
    "analysis": "요청 분석 결과",
    "goal": "최종 목표",
    "steps": [
        {{
            "step_number": 1,
            "description": "단계 설명",
            "tool_name": "사용할 도구명",
            "arguments": {{"param": "value"}},
            "expected_output": "예상 결과",
            "dependencies": []
        }},
        {{
            "step_number": 2,
            "description": "단계 설명",
            "tool_name": "사용할 도구명", 
            "arguments": {{"param": "value", "content": "${{step_1_result}}"}},
            "expected_output": "예상 결과",
            "dependencies": [1]
        }}
    ]
}}

반드시 JSON 형식으로만 응답하세요."""

            # 계획 수립 요청
            response = await agent._generate_basic_response(planning_prompt, streaming_callback)
            
            # JSON 파싱
            plan = self._extract_json_from_response(response)
            
            if not plan:
                logger.warning("워크플로우 계획 JSON 파싱 실패: %s", response[:200])
                return {}
                
            # 계획 검증
            if not self._validate_workflow_plan(plan):
                logger.warning("워크플로우 계획 검증 실패")
                return {}
                
            logger.debug("워크플로우 계획 수립 성공: %s", plan.get("goal", ""))
            return plan
            
        except Exception as e:
            logger.error("워크플로우 계획 수립 중 오류: %s", e)
            return {}

    async def _execute_workflow_steps(
        self,
        agent: Any,
        workflow_plan: Dict[str, Any],
        original_message: str,
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        계획된 워크플로우 단계들을 순차적으로 실행
        """
        execution_results = {}
        steps = workflow_plan.get("steps", [])
        
        if streaming_callback:
            streaming_callback(f"🔄 워크플로우 실행 시작 ({len(steps)}단계)\n\n")
        
        for step in steps:
            step_number = step.get("step_number", 0)
            
            try:
                # 의존성 확인
                dependencies = step.get("dependencies", [])
                if not self._check_dependencies(dependencies, execution_results):
                    logger.warning("단계 %d: 의존성 미충족", step_number)
                    execution_results[step_number] = {
                        "success": False,
                        "error": "의존성 미충족",
                        "result": None
                    }
                    continue
                
                # 단계 실행
                step_result = await self._execute_single_step(
                    agent, step, execution_results, streaming_callback
                )
                
                execution_results[step_number] = step_result
                
                # 스트리밍 피드백
                if streaming_callback:
                    status = "✅" if step_result.get("success") else "❌"
                    description = step.get("description", f"단계 {step_number}")
                    streaming_callback(f"{status} {description}\n")
                    
            except Exception as e:
                logger.error("단계 %d 실행 중 오류: %s", step_number, e)
                execution_results[step_number] = {
                    "success": False,
                    "error": str(e),
                    "result": None
                }
                
                if streaming_callback:
                    description = step.get("description", f"단계 {step_number}")
                    streaming_callback(f"❌ {description} (오류: {str(e)})\n")
        
        if streaming_callback:
            successful_steps = sum(1 for r in execution_results.values() if r.get("success"))
            streaming_callback(f"\n🎯 워크플로우 완료: {successful_steps}/{len(steps)}단계 성공\n\n")
        
        return execution_results

    async def _execute_single_step(
        self,
        agent: Any,
        step: Dict[str, Any],
        previous_results: Dict[int, Dict[str, Any]],
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        개별 워크플로우 단계 실행
        """
        try:
            tool_name = step.get("tool_name")
            arguments = step.get("arguments", {})
            
            if not tool_name:
                return {"success": False, "error": "도구명이 없습니다", "result": None}
            
            # 이전 단계 결과를 기반으로 매개변수 동적 조정
            processed_arguments = self._process_arguments(arguments, previous_results)
            
            # 매개변수 최종 검증 및 타입 변환 (특히 write_file 도구용)
            if tool_name == "write_file" and "content" in processed_arguments:
                content = processed_arguments["content"]
                logger.info("write_file content 타입 확인: %s, 값: %s", type(content).__name__, str(content)[:100])
                
                if not isinstance(content, str):
                    # 딕셔너리나 다른 타입을 문자열로 변환
                    if isinstance(content, dict):
                        import json
                        processed_arguments["content"] = json.dumps(content, ensure_ascii=False, indent=2)
                        logger.info("딕셔너리를 JSON 문자열로 변환 완료")
                    else:
                        processed_arguments["content"] = str(content)
                        logger.info("기타 타입을 문자열로 변환 완료")
                else:
                    logger.info("이미 문자열 타입임")
                    
            # 모든 매개변수 타입 검증 및 변환
            for key, value in processed_arguments.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    logger.warning("매개변수 %s가 복합 타입임: %s", key, type(value).__name__)
                    if isinstance(value, dict):
                        import json
                        processed_arguments[key] = json.dumps(value, ensure_ascii=False, indent=2)
                        logger.info("매개변수 %s를 JSON 문자열로 변환", key)
                    else:
                        processed_arguments[key] = str(value)
                        logger.info("매개변수 %s를 문자열로 변환", key)
            
            # 도구 실행
            if hasattr(agent, 'mcp_tool_manager') and agent.mcp_tool_manager:
                tool_result = await agent.mcp_tool_manager.call_mcp_tool(
                    tool_name, processed_arguments
                )
                
                # 결과 검증
                success = not self._has_tool_error(tool_result)
                
                return {
                    "success": success,
                    "error": None if success else self._extract_error_message(tool_result),
                    "result": tool_result,
                    "tool_name": tool_name,
                    "arguments": processed_arguments
                }
            else:
                return {"success": False, "error": "MCP 도구 관리자가 없습니다", "result": None}
                
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}

    async def _integrate_and_finalize(
        self,
        agent: Any,
        original_message: str,
        workflow_plan: Dict[str, Any],
        execution_results: Dict[int, Dict[str, Any]],
        streaming_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        워크플로우 실행 결과를 통합하여 최종 응답 생성
        """
        try:
            # 성공한 단계들의 결과 수집
            successful_results = {
                step_num: result for step_num, result in execution_results.items()
                if result.get("success")
            }
            
            if not successful_results:
                return "워크플로우 실행 중 모든 단계가 실패했습니다."
            
            # 결과 요약 생성
            results_summary = self._create_results_summary(workflow_plan, execution_results)
            
            # 최종 응답 생성 프롬프트
            integration_prompt = f"""워크플로우 실행 결과를 종합하여 사용자에게 완전한 응답을 제공해주세요.

원래 사용자 요청: {original_message}

워크플로우 목표: {workflow_plan.get('goal', '목표 불명')}

실행 결과 요약:
{results_summary}

다음 지침에 따라 최종 응답을 작성하세요:
1. 사용자의 원래 요청이 완전히 처리되었는지 확인
2. 각 단계의 결과를 논리적으로 연결하여 통합된 답변 제공
3. 실패한 단계가 있다면 그 영향과 대안 설명
4. 구체적이고 실용적인 정보 포함
5. 사용자가 추가로 필요한 조치가 있다면 안내

완전하고 유용한 응답을 제공해주세요."""

            final_response = await agent._generate_basic_response(integration_prompt, streaming_callback)
            return final_response
            
        except Exception as e:
            logger.error("결과 통합 중 오류: %s", e)
            return f"워크플로우 결과 통합 중 오류가 발생했습니다: {str(e)}"

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """응답에서 JSON 추출"""
        try:
            import re

            # 마크다운 코드 블록 제거 후 JSON 추출
            json_patterns = [
                r'```(?:json)?\s*(\{.*?\})\s*```',  # 마크다운 블록
                r'(\{[^{}]*"steps"[^{}]*\[.*?\]\s*\})',  # steps 포함한 JSON
                r'(\{.*?\})'  # 일반 JSON
            ]
            
            for pattern in json_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    json_text = match.group(1).strip()
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        continue
            
            # 패턴 매칭 실패 시 전체 텍스트로 시도
            return json.loads(response.strip())
            
        except Exception as e:
            logger.error("JSON 추출 실패: %s", e)
            return {}

    def _validate_workflow_plan(self, plan: Dict[str, Any]) -> bool:
        """워크플로우 계획 검증"""
        try:
            if not isinstance(plan, dict):
                return False
            
            steps = plan.get("steps", [])
            if not isinstance(steps, list) or not steps:
                return False
            
            # 각 단계 검증
            for step in steps:
                if not isinstance(step, dict):
                    return False
                
                required_fields = ["step_number", "description", "tool_name"]
                if not all(field in step for field in required_fields):
                    return False
            
            return True
            
        except Exception:
            return False

    def _check_dependencies(self, dependencies: List[int], completed_steps: Dict[int, Dict[str, Any]]) -> bool:
        """단계 의존성 확인"""
        for dep in dependencies:
            if dep not in completed_steps or not completed_steps[dep].get("success"):
                return False
        return True

    def _process_arguments(self, arguments: Dict[str, Any], previous_results: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """이전 단계 결과를 기반으로 매개변수 동적 처리"""
        processed = arguments.copy()
        
        # 플레이스홀더 치환 (예: ${step_1_result})
        for key, value in processed.items():
            if isinstance(value, str):
                # 이전 단계 결과 참조 처리
                for step_num, result in previous_results.items():
                    placeholder = f"${{step_{step_num}_result}}"
                    if placeholder in value and result.get("success"):
                        step_result = result.get("result", "")
                        
                        # 결과가 문자열이면 직접 사용, 딕셔너리면 의미있는 내용 추출
                        if isinstance(step_result, str):
                            # JSON 문자열인지 확인하고 파싱 시도
                            try:
                                import json
                                parsed_result = json.loads(step_result)
                                if isinstance(parsed_result, dict):
                                    step_result = self._extract_meaningful_content(parsed_result)
                            except json.JSONDecodeError:
                                pass
                        elif isinstance(step_result, dict):
                            step_result = self._extract_meaningful_content(step_result)
                        
                        # 문자열로 변환하여 치환
                        processed[key] = value.replace(placeholder, str(step_result))
                        
                # 특별한 키워드 처리 (content가 플레이스홀더인 경우)
                if key == "content" and any(phrase in value.lower() for phrase in [
                    "검색 결과", "뉴스", "요약", "데이터", "정보"
                ]):
                    # 가장 최근 성공한 단계의 결과를 사용
                    latest_result = self._get_latest_successful_result(previous_results)
                    if latest_result:
                        formatted_content = self._format_content_for_saving(latest_result, value)
                        # 확실히 문자열로 변환
                        processed[key] = str(formatted_content)
        
        return processed
    
    def _extract_meaningful_content(self, data: Dict[str, Any]) -> str:
        """딕셔너리에서 의미있는 내용 추출"""
        try:
            # DuckDuckGo 검색 도구 결과 처리 - result 키 내부의 results 확인
            if "result" in data and isinstance(data["result"], dict):
                result_data = data["result"]
                if "results" in result_data and isinstance(result_data["results"], list):
                    results = result_data["results"]
                    return self._format_search_results_as_news(results, result_data.get("query", ""))
            
            # 직접 results가 있는 경우
            elif "results" in data and isinstance(data["results"], list):
                results = data["results"]
                return self._format_search_results_as_news(results, data.get("query", ""))
            
            # 일반적인 성공 메시지나 결과 추출
            elif "message" in data:
                return str(data["message"])
            elif "content" in data:
                return str(data["content"])
            elif "result" in data:
                return str(data["result"])
            else:
                return str(data)
                
        except Exception as e:
            logger.error("의미있는 내용 추출 중 오류: %s", e)
            return str(data)
    
    def _format_search_results_as_news(self, results: list, query: str = "") -> str:
        """검색 결과를 뉴스 형식으로 포맷팅"""
        try:
            from datetime import datetime

            # 뉴스 데이터 구조화
            news_data = {
                "search_query": query,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "generated_at": datetime.now().isoformat(),
                "total_articles": len(results),
                "news": []
            }
            
            for i, item in enumerate(results[:15], 1):  # 최대 15개
                if isinstance(item, dict):
                    # 카테고리 추정 (제목이나 출처를 기반으로)
                    category = self._estimate_news_category(item.get("title", ""), item.get("source", ""))
                    
                    news_item = {
                        "id": i,
                        "category": category,
                        "title": item.get("title", "제목 없음").strip(),
                        "summary": self._create_article_summary(item),
                        "source": item.get("source", "출처 없음"),
                        "url": item.get("url", ""),
                        "published_date": item.get("published_date", item.get("timestamp", "")),
                        "content_type": item.get("content_type", "article")
                    }
                    news_data["news"].append(news_item)
            
            import json
            return json.dumps(news_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error("검색 결과 포맷팅 중 오류: %s", e)
            return json.dumps({"error": f"포맷팅 오류: {str(e)}", "raw_results": results}, ensure_ascii=False, indent=2)
    
    def _estimate_news_category(self, title: str, source: str) -> str:
        """제목과 출처를 기반으로 뉴스 카테고리 추정"""
        title_lower = title.lower()
        source_lower = source.lower()
        
        # 정치 관련 키워드
        if any(word in title_lower for word in ['대통령', '정부', '국회', '정치', '선거', '정당', '국정', '장관', '총리']):
            return "정치"
        
        # 경제 관련 키워드
        elif any(word in title_lower for word in ['경제', '주식', '부동산', '금융', '은행', '투자', '시장', '기업', '매출', '아파트']):
            return "경제"
        
        # 사회 관련 키워드
        elif any(word in title_lower for word in ['사회', '사건', '사고', '범죄', '교육', '출생', '혼인', '인구', '복지']):
            return "사회"
        
        # 국제 관련 키워드
        elif any(word in title_lower for word in ['미국', '중국', '일본', '북한', '트럼프', '국제', '외교', '협상', '나토']):
            return "국제"
        
        # 기술/IT 관련 키워드
        elif any(word in title_lower for word in ['기술', 'ai', '인공지능', '스마트폰', '삼성', 'lg', '애플', '구글']):
            return "기술/IT"
        
        # 스포츠 관련 키워드
        elif any(word in title_lower for word in ['스포츠', '축구', '야구', '올림픽', '월드컵', '선수']):
            return "스포츠"
        
        # 날씨 관련 키워드
        elif any(word in title_lower for word in ['날씨', '기온', '장마', '폭염', '한파', '태풍', '비', '눈']):
            return "날씨"
        
        else:
            return "일반"
    
    def _create_article_summary(self, item: dict) -> str:
        """기사 요약 생성"""
        # 본문 내용이 있으면 활용
        full_content = item.get("full_content", "")
        description = item.get("description", "")
        
        if full_content and len(full_content) > 100:
            # 본문의 첫 200자를 요약으로 사용
            summary = full_content[:200].strip()
            if len(full_content) > 200:
                summary += "..."
            return summary
        elif description:
            return description.strip()
        else:
            return "요약 정보 없음"
    
    def _get_latest_successful_result(self, previous_results: Dict[int, Dict[str, Any]]) -> Any:
        """가장 최근 성공한 단계의 결과 반환"""
        latest_step = max(previous_results.keys()) if previous_results else 0
        for step_num in range(latest_step, 0, -1):
            if step_num in previous_results and previous_results[step_num].get("success"):
                return previous_results[step_num].get("result")
        return None
    
    def _format_content_for_saving(self, result_data: Any, original_value: str) -> str:
        """저장할 내용 포맷팅"""
        try:
            # 결과가 문자열이면 JSON 파싱 시도
            if isinstance(result_data, str):
                try:
                    import json
                    parsed_data = json.loads(result_data)
                    if isinstance(parsed_data, dict):
                        result_data = parsed_data
                except json.JSONDecodeError:
                    pass
            
            # 딕셔너리 형태 결과 처리
            if isinstance(result_data, dict):
                # 검색 결과인 경우
                if "results" in result_data and isinstance(result_data["results"], list):
                    return self._extract_meaningful_content(result_data)
                # 기타 딕셔너리는 JSON으로 변환
                else:
                    import json
                    return json.dumps(result_data, ensure_ascii=False, indent=2)
            
            # 문자열이면 그대로 반환
            return str(result_data)
            
        except Exception as e:
            logger.error("내용 포맷팅 중 오류: %s", e)
            return f"데이터 처리 중 오류 발생: {str(e)}"

    def _create_results_summary(self, workflow_plan: Dict[str, Any], execution_results: Dict[int, Dict[str, Any]]) -> str:
        """실행 결과 요약 생성"""
        summary_parts = []
        steps = workflow_plan.get("steps", [])
        
        for step in steps:
            step_number = step.get("step_number", 0)
            description = step.get("description", f"단계 {step_number}")
            
            if step_number in execution_results:
                result = execution_results[step_number]
                if result.get("success"):
                    summary_parts.append(f"✅ {description}: 성공")
                    if result.get("result"):
                        # 결과가 너무 길면 요약
                        result_text = str(result["result"])[:200]
                        summary_parts.append(f"   결과: {result_text}...")
                else:
                    error = result.get("error", "알 수 없는 오류")
                    summary_parts.append(f"❌ {description}: 실패 ({error})")
            else:
                summary_parts.append(f"⏭️ {description}: 실행되지 않음")
        
        return "\n".join(summary_parts)

    def _has_tool_error(self, tool_result: Any) -> bool:
        """도구 결과에 오류가 있는지 확인"""
        try:
            if isinstance(tool_result, str):
                try:
                    result_dict = json.loads(tool_result)
                    return "error" in result_dict and result_dict["error"]
                except json.JSONDecodeError:
                    return False
            elif isinstance(tool_result, dict):
                return "error" in tool_result and tool_result["error"]
            return False
        except Exception:
            return False

    def _extract_error_message(self, tool_result: Any) -> str:
        """도구 결과에서 오류 메시지 추출"""
        try:
            if isinstance(tool_result, str):
                try:
                    result_dict = json.loads(tool_result)
                except json.JSONDecodeError:
                    return f"도구 실행 오류: {tool_result}"
            elif isinstance(tool_result, dict):
                result_dict = tool_result
            else:
                return f"알 수 없는 오류: {str(tool_result)}"
            
            if "error" in result_dict:
                return str(result_dict["error"])
            else:
                return "오류 메시지 없음"
        except Exception:
            return "오류 메시지 추출 실패" 