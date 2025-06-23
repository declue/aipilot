from pydantic import BaseModel, ConfigDict, Field


class ConversationFileRequest(BaseModel):
    """대화 파일 저장/불러오기 요청 모델"""

    model_config = ConfigDict(
        json_schema_extra={"example": {"file_path": "/path/to/conversation.json", "action": "save"}}
    )

    file_path: str = Field(..., description="파일 경로")
    action: str = Field(..., description="작업 유형 (save/load)")
