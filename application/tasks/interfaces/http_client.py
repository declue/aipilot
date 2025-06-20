"""HTTP 클라이언트 인터페이스"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IHttpClient(ABC):
    """HTTP 클라이언트 인터페이스"""

    @abstractmethod
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GET 요청을 수행합니다.
        
        Args:
            url: 요청 URL
            headers: 요청 헤더
            
        Returns:
            응답 데이터
        """
        pass

    @abstractmethod
    async def post(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """POST 요청을 수행합니다.
        
        Args:
            url: 요청 URL
            data: 요청 데이터
            headers: 요청 헤더
            
        Returns:
            응답 데이터
        """
        pass

    @abstractmethod
    async def put(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT 요청을 수행합니다.
        
        Args:
            url: 요청 URL
            data: 요청 데이터
            headers: 요청 헤더
            
        Returns:
            응답 데이터
        """
        pass

    @abstractmethod
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """DELETE 요청을 수행합니다.
        
        Args:
            url: 요청 URL
            headers: 요청 헤더
            
        Returns:
            응답 데이터
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """HTTP 클라이언트를 종료합니다."""
        pass 