from dspilot_cli.summary_utils import compress_text


def test_compress_text_reduces_lines():
    long_text = "\n".join([f"Line {i}." for i in range(200)])
    compressed = compress_text(long_text, max_lines=50)
    assert compressed.count("\n") <= 50


def test_compress_preserves_code_block():
    code_block = "```python\nprint('hi')\n```"
    long_text = f"intro\n{code_block}\n" + "\n".join(["text"] * 100)
    compressed = compress_text(long_text, max_lines=50)
    assert "print('hi')" in compressed 