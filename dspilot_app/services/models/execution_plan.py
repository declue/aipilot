"""실행 계획 관련 모델 정의"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ExecutionStep(BaseModel):
    """실행 단계 모델"""
    step: int
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    confirm_message: Optional[str] = None


class ExecutionPlan(BaseModel):
    """실행 계획 모델"""
    description: str
    steps: List[ExecutionStep]
