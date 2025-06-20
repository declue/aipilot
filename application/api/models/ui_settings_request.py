from typing import Optional

from pydantic import BaseModel


class UISettingsRequest(BaseModel):
    """UI 설정 변경 요청 모델"""

    font_family: Optional[str] = None
    font_size: Optional[int] = None
    theme: Optional[str] = None
