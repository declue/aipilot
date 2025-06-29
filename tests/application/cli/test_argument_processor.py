
from dspilot_cli.execution.argument_processor import ArgumentProcessor


def test_generate_generic_fallback():
    """_generate_fallback_content 가 도메인 특화 텍스트 없이 범용 메시지를 반환하는지 확인."""
    processor = ArgumentProcessor()
    data = {"query": "테스트 검색", "count": 0}

    result = processor._extract_content_by_context(data, "content")  # pylint: disable=protected-access

    assert "유효한 결과를 찾을 수 없습니다" in result
    # 도메인 특화 키워드가 들어가지 않아야 함 (예: IT 뉴스 매거진)
    assert "IT 뉴스" not in result 