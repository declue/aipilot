"""HTTP 클라이언트 테스트"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponse, ClientSession

from application.tasks.exceptions import HttpClientError
from application.tasks.services.http_client import HttpClient


class TestHttpClient:
    """HTTP 클라이언트 테스트 클래스"""

    @pytest.fixture
    def http_client(self) -> HttpClient:
        """HTTP 클라이언트 인스턴스 생성"""
        return HttpClient(timeout=10)

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Mock 응답 객체 생성"""
        mock_resp = MagicMock(spec=ClientResponse)
        mock_resp.status = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json = AsyncMock(return_value={"result": "success"})
        mock_resp.text = AsyncMock(return_value="success text")
        return mock_resp

    @pytest.mark.asyncio
    async def test_get_success(self, http_client: HttpClient, mock_response: MagicMock) -> None:
        """GET 요청 성공 테스트"""
        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session

            result = await http_client.get("https://example.com")

            assert result == {"result": "success"}
            mock_session.get.assert_called_once_with("https://example.com", headers=None)

    @pytest.mark.asyncio
    async def test_post_success(self, http_client: HttpClient, mock_response: MagicMock) -> None:
        """POST 요청 성공 테스트"""
        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session

            data = {"key": "value"}
            result = await http_client.post("https://example.com", data)

            assert result == {"result": "success"}
            mock_session.post.assert_called_once_with(
                "https://example.com", json=data, headers=None
            )

    @pytest.mark.asyncio
    async def test_put_success(self, http_client: HttpClient, mock_response: MagicMock) -> None:
        """PUT 요청 성공 테스트"""
        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.put.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session

            data = {"key": "value"}
            result = await http_client.put("https://example.com", data)

            assert result == {"result": "success"}
            mock_session.put.assert_called_once_with(
                "https://example.com", json=data, headers=None
            )

    @pytest.mark.asyncio
    async def test_delete_success(self, http_client: HttpClient, mock_response: MagicMock) -> None:
        """DELETE 요청 성공 테스트"""
        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.delete.return_value.__aenter__.return_value = mock_response
            mock_get_session.return_value = mock_session

            result = await http_client.delete("https://example.com")

            assert result == {"result": "success"}
            mock_session.delete.assert_called_once_with("https://example.com", headers=None)

    @pytest.mark.asyncio
    async def test_error_response(self, http_client: HttpClient) -> None:
        """HTTP 오류 응답 테스트"""
        mock_resp = MagicMock(spec=ClientResponse)
        mock_resp.status = 404
        mock_resp.text = AsyncMock(return_value="Not Found")

        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.get.return_value.__aenter__.return_value = mock_resp
            mock_get_session.return_value = mock_session

            with pytest.raises(HttpClientError) as exc_info:
                await http_client.get("https://example.com")

            assert "404" in str(exc_info.value)
            assert "Not Found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_text_response(self, http_client: HttpClient) -> None:
        """텍스트 응답 처리 테스트"""
        mock_resp = MagicMock(spec=ClientResponse)
        mock_resp.status = 200
        mock_resp.headers = {"content-type": "text/plain"}
        mock_resp.text = AsyncMock(return_value="plain text response")

        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.get.return_value.__aenter__.return_value = mock_resp
            mock_get_session.return_value = mock_session

            result = await http_client.get("https://example.com")

            assert result == {"text": "plain text response", "status": 200}

    @pytest.mark.asyncio
    async def test_network_error(self, http_client: HttpClient) -> None:
        """네트워크 오류 테스트"""
        with patch.object(http_client, '_get_session') as mock_get_session:
            mock_session = MagicMock(spec=ClientSession)
            mock_session.get.side_effect = Exception("Connection failed")
            mock_get_session.return_value = mock_session

            with pytest.raises(HttpClientError) as exc_info:
                await http_client.get("https://example.com")

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close(self, http_client: HttpClient) -> None:
        """클라이언트 종료 테스트"""
        mock_session = MagicMock(spec=ClientSession)
        mock_session.closed = False
        http_client._session = mock_session

        await http_client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_creation(self, http_client: HttpClient) -> None:
        """세션 생성 테스트"""
        # 초기에는 세션이 없음
        assert http_client._session is None

        # 세션 가져오기
        session = http_client._get_session()

        # 세션이 생성됨
        assert session is not None
        assert http_client._session is not None

    @pytest.mark.asyncio
    async def test_session_reuse(self, http_client: HttpClient) -> None:
        """세션 재사용 테스트"""
        # 첫 번째 세션 생성
        session1 = http_client._get_session()

        # 두 번째 호출 시 같은 세션 반환
        session2 = http_client._get_session()

        assert session1 is session2
