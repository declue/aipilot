"""
Agent Workflow 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.llm.workflow.agent_workflow import (
    AgentWorkflow,
    WorkflowStage,
    WorkflowState
)


class TestAgentWorkflow:
    """Agent Workflow 테스트 클래스"""

    @pytest.fixture
    def mock_agent(self):
        """Mock Agent 생성"""
        agent = MagicMock()
        agent._generate_basic_response = AsyncMock(return_value="Mock response")
        agent.mcp_tool_manager = MagicMock()
        agent.generate_response = AsyncMock(return_value={
            "response": "Mock response with tools",
            "used_tools": ["mock_tool1", "mock_tool2"]
        })
        return agent

    @pytest.fixture
    def workflow(self):
        """Agent Workflow 인스턴스 생성"""
        return AgentWorkflow()

    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow, mock_agent):
        """워크플로우 초기화 테스트"""
        message = "테스트 요청입니다"
        
        # 첫 실행 (초기화)
        result = await workflow.run(mock_agent, message, None)
        
        # 상태 확인
        assert workflow.state is not None
        assert workflow.state.stage == WorkflowStage.CONTEXT_GATHERING
        assert workflow.state.original_request == message
        assert workflow.iteration_count == 0
        assert "요청 분석 완료" in result
        
    @pytest.mark.asyncio
    async def test_workflow_continuation(self, workflow, mock_agent):
        """워크플로우 계속 실행 테스트"""
        # 초기화
        await workflow.run(mock_agent, "초기 요청", None)
        
        # 계속 실행
        result = await workflow.run(mock_agent, "사용자 피드백", None)
        
        # 상태 확인
        assert workflow.iteration_count == 1
        assert len(workflow.state.user_feedback) == 1
        assert workflow.state.user_feedback[0] == "사용자 피드백"
        
    @pytest.mark.asyncio
    async def test_context_gathering_stage(self, workflow, mock_agent):
        """컨텍스트 수집 단계 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.CONTEXT_GATHERING,
            original_request="테스트 요청",
            context={"analysis": "테스트 분석"}
        )
        
        result = await workflow._handle_context_gathering(mock_agent, None)
        
        # 결과 확인
        assert "컨텍스트 수집 완료" in result
        assert workflow.state.stage == WorkflowStage.PLANNING
        assert "gathered_info" in workflow.state.context
        
    @pytest.mark.asyncio
    async def test_planning_stage(self, workflow, mock_agent):
        """계획 수립 단계 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.PLANNING,
            original_request="테스트 요청",
            context={
                "analysis": "테스트 분석",
                "gathered_info": "수집된 정보"
            }
        )
        
        result = await workflow._handle_planning(mock_agent, None)
        
        # 결과 확인
        assert "실행 계획 수립 완료" in result
        assert "계획 승인" in result
        assert workflow.state.current_plan is not None
        
    @pytest.mark.asyncio
    async def test_execution_stage_with_approval(self, workflow, mock_agent):
        """실행 단계 테스트 (계획 승인된 경우)"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.EXECUTION,
            original_request="테스트 요청",
            context={},
            user_feedback=["1", "승인"]  # 계획 승인
        )
        workflow.state.current_plan = {"description": "테스트 계획"}
        
        result = await workflow._handle_execution(mock_agent, None)
        
        # 결과 확인
        assert "계획 실행 완료" in result
        assert workflow.state.stage == WorkflowStage.REVIEW
        assert len(workflow.state.execution_results) == 1
        
    @pytest.mark.asyncio
    async def test_execution_stage_without_approval(self, workflow, mock_agent):
        """실행 단계 테스트 (계획 미승인된 경우)"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.EXECUTION,
            original_request="테스트 요청",
            context={},
            user_feedback=["계획을 수정해주세요"]
        )
        workflow.state.current_plan = {"description": "테스트 계획"}
        
        result = await workflow._handle_execution(mock_agent, None)
        
        # 결과 확인
        assert "계획 수정 요청 접수" in result
        
    @pytest.mark.asyncio
    async def test_review_stage(self, workflow, mock_agent):
        """검토 단계 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.REVIEW,
            original_request="테스트 요청",
            context={},
            execution_results=[{"result": "테스트 결과", "success": True}]
        )
        
        result = await workflow._handle_review(mock_agent, None)
        
        # 결과 확인
        assert "결과 검토 완료" in result
        assert "다음 단계 선택" in result
        assert "review" in workflow.state.context
        
    @pytest.mark.asyncio
    async def test_completion_stage(self, workflow, mock_agent):
        """완료 단계 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.COMPLETED,
            original_request="테스트 요청",
            context={"review": "검토 완료"},
            execution_results=[{"result": "테스트 결과", "success": True}]
        )
        workflow.iteration_count = 3
        
        result = await workflow._handle_completed(mock_agent, None)
        
        # 결과 확인
        assert "Agent Workflow 완료" in result
        assert workflow.state is None  # 상태 초기화됨
        assert workflow.iteration_count == 0  # 카운터 초기화됨
        
    def test_plan_approval_detection(self, workflow):
        """계획 승인 감지 테스트"""
        # 승인 키워드들 테스트
        assert workflow._is_plan_approved("승인합니다") is True
        assert workflow._is_plan_approved("1") is True
        assert workflow._is_plan_approved("실행해주세요") is True
        assert workflow._is_plan_approved("좋습니다") is True
        assert workflow._is_plan_approved("ok") is True
        
        # 비승인 케이스
        assert workflow._is_plan_approved("수정해주세요") is False
        assert workflow._is_plan_approved("다른 방법으로") is False
        assert workflow._is_plan_approved("") is False
        
    def test_workflow_completion_detection(self, workflow):
        """워크플로우 완료 감지 테스트"""
        # 완료 키워드들 테스트
        assert workflow._should_complete_workflow("완료") is True
        assert workflow._should_complete_workflow("1") is True
        assert workflow._should_complete_workflow("결과 수락") is True
        assert workflow._should_complete_workflow("만족합니다") is True
        
        # 비완료 케이스
        assert workflow._should_complete_workflow("추가 작업") is False
        assert workflow._should_complete_workflow("개선 필요") is False
        
    def test_additional_work_detection(self, workflow):
        """추가 작업 감지 테스트"""
        # 추가 작업 키워드들 테스트
        assert workflow._should_do_additional_work("추가 개선") is True
        assert workflow._should_do_additional_work("2") is True
        assert workflow._should_do_additional_work("수정해주세요") is True
        assert workflow._should_do_additional_work("보완 필요") is True
        
        # 비추가작업 케이스
        assert workflow._should_do_additional_work("완료") is False
        assert workflow._should_do_additional_work("새로운 요청") is False
        
    def test_new_request_detection(self, workflow):
        """새로운 요청 감지 테스트"""
        # 새요청 키워드들 테스트
        assert workflow._should_start_new_request("새로운 작업") is True
        assert workflow._should_start_new_request("3") is True
        assert workflow._should_start_new_request("다른 요청") is True
        
        # 비새요청 케이스
        assert workflow._should_start_new_request("완료") is False
        assert workflow._should_start_new_request("추가 작업") is False
        
    def test_context_building(self, workflow):
        """컨텍스트 구성 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.PLANNING,
            original_request="테스트 요청",
            context={
                "analysis": "분석 결과",
                "gathered_info": "수집된 정보"
            },
            user_feedback=["피드백1", "피드백2"]
        )
        
        context = workflow._build_full_context()
        
        # 결과 확인
        assert "분석 결과" in context
        assert "수집된 정보" in context
        assert "피드백1" in context
        assert "피드백2" in context
        
    def test_execution_results_summary(self, workflow):
        """실행 결과 요약 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.REVIEW,
            original_request="테스트 요청",
            context={},
            execution_results=[
                {"result": "첫 번째 결과입니다", "success": True},
                {"result": "두 번째 결과입니다", "success": True}
            ]
        )
        
        summary = workflow._summarize_execution_results()
        
        # 결과 확인
        assert "실행 1" in summary
        assert "실행 2" in summary
        assert "첫 번째 결과" in summary
        assert "두 번째 결과" in summary
        
    def test_final_summary_creation(self, workflow):
        """최종 요약 생성 테스트"""
        # 상태 설정
        workflow.state = WorkflowState(
            stage=WorkflowStage.COMPLETED,
            original_request="테스트 요청",
            context={
                "analysis": "분석 완료",
                "gathered_info": "정보 수집",
                "review": "검토 완료"
            },
            execution_results=[{"result": "결과", "success": True}]
        )
        workflow.state.current_plan = {"description": "계획"}
        
        summary = workflow._create_final_summary()
        
        # 결과 확인
        assert "요청 정확히 분석" in summary
        assert "컨텍스트 및 정보 수집" in summary
        assert "실행 계획 수립" in summary
        assert "계획 실행 및 결과 생성" in summary
        assert "결과 검토 및 품질 확인" in summary
        
    @pytest.mark.asyncio
    async def test_error_handling(self, workflow, mock_agent):
        """오류 처리 테스트"""
        # Mock에서 예외 발생시키기
        mock_agent._generate_basic_response.side_effect = Exception("테스트 오류")
        
        result = await workflow.run(mock_agent, "테스트 요청", None)
        
        # 오류 메시지 확인
        assert "워크플로우 실행 중 오류가 발생했습니다" in result
        
    @pytest.mark.asyncio
    async def test_stage_progression(self, workflow, mock_agent):
        """단계 진행 테스트"""
        # 초기 실행
        result1 = await workflow.run(mock_agent, "테스트 요청", None)
        assert workflow.state.stage == WorkflowStage.CONTEXT_GATHERING
        
        # 컨텍스트 수집 완료
        result2 = await workflow.run(mock_agent, "", None)
        assert workflow.state.stage == WorkflowStage.PLANNING
        
        # 계획 수립 완료 및 승인
        result3 = await workflow.run(mock_agent, "승인", None)
        assert workflow.state.stage == WorkflowStage.REVIEW
        
        # 검토 완료
        result4 = await workflow.run(mock_agent, "완료", None)
        assert workflow.state is None  # 워크플로우 완료로 상태 초기화
``` 