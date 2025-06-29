
from dspilot_cli.constants import Defaults
from dspilot_cli.conversation_manager import ConversationManager


def test_prompt_token_budget():
    """ConversationManager가 토큰 예산을 초과하지 않도록 프롬프트를 생성하는지 확인"""

    cm = ConversationManager()

    # 매우 긴 메시지로 토큰 예산 초과 상황 구성
    long_text = "word " * 5000  # 약 5000 단어 → 5000+ 토큰

    # user/assistant 메시지를 여러 번 추가하여 컨텍스트 비대화
    for _ in range(4):
        cm.add_to_history("user", long_text)
        cm.add_to_history("assistant", long_text)

    prompt = cm.build_enhanced_prompt("마무리 응답")

    # tiktoken 사용 가능 여부에 따라 토큰 계산
    try:
        import tiktoken  # pylint: disable=import-error

        encoder = tiktoken.get_encoding("cl100k_base")
        token_len = len(encoder.encode(prompt))
    except ModuleNotFoundError:
        # fallback – 공백 단위 길이로 근사하지만 예산을 넉넉히 잡는다
        token_len = len(prompt.split())

    assert token_len <= Defaults.MAX_PROMPT_TOKENS, (
        f"생성된 프롬프트 토큰 수 {token_len}가 예산({Defaults.MAX_PROMPT_TOKENS})을 초과했습니다."
    ) 