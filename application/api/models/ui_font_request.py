from pydantic import BaseModel, Field


class UIFontRequest(BaseModel):
    """UI 폰트 크기 변경 요청 모델"""

    font_size: int = Field(..., ge=8, le=72, description="폰트 크기 (8-72)") 