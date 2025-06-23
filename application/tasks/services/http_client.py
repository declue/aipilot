"""HTTP 클라이언트 구현"""

import logging
from typing import Any, Dict, Optional, cast

import aiohttp

from application.tasks.exceptions import HttpClientError
from application.tasks.interfaces.http_client import IHttpClient
from application.util.logger import setup_logger

logger: logging.Logger = setup_logger("task") or logging.getLogger("task")


class HttpClient(IHttpClient):
    """HTTP 클라이언트 구현"""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        """세션을 가져오거나 생성합니다."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GET 요청을 수행합니다."""
        try:
            session = self._get_session()
            async with session.get(url, headers=headers) as response:
                return await self._process_response(response, url)
        except Exception as e:
            logger.error(f"GET 요청 실패: {url} - {e}")
            raise HttpClientError(url, message=str(e))

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """POST 요청을 수행합니다."""
        try:
            session = self._get_session()
            async with session.post(url, json=data, headers=headers) as response:
                return await self._process_response(response, url)
        except Exception as e:
            logger.error(f"POST 요청 실패: {url} - {e}")
            raise HttpClientError(url, message=str(e))

    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """PUT 요청을 수행합니다."""
        try:
            session = self._get_session()
            async with session.put(url, json=data, headers=headers) as response:
                return await self._process_response(response, url)
        except Exception as e:
            logger.error(f"PUT 요청 실패: {url} - {e}")
            raise HttpClientError(url, message=str(e))

    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """DELETE 요청을 수행합니다."""
        try:
            session = self._get_session()
            async with session.delete(url, headers=headers) as response:
                return await self._process_response(response, url)
        except Exception as e:
            logger.error(f"DELETE 요청 실패: {url} - {e}")
            raise HttpClientError(url, message=str(e))

    async def _process_response(self, response: aiohttp.ClientResponse, url: str) -> Dict[str, Any]:
        """응답을 처리합니다."""
        try:
            if response.status >= 400:
                error_text = await response.text()
                raise HttpClientError(url, response.status, error_text)

            # JSON 응답인지 확인
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return cast(Dict[str, Any], await response.json())
            else:
                text = await response.text()
                return {"text": text, "status": response.status}

        except aiohttp.ContentTypeError:
            # JSON 파싱 실패 시 텍스트로 반환
            text = await response.text()
            return {"text": text, "status": response.status}

    async def close(self) -> None:
        """HTTP 클라이언트를 종료합니다."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("HTTP 클라이언트 세션 종료")
