import importlib.metadata as m
import tempfile
from pathlib import Path

from inline_snapshot import snapshot

from pymupdf4llm_mcp.app import convert_pdf_to_markdown

_HERE = Path(__file__).parent
dummy_pdf_path = _HERE / "dummy.pdf"


def test_pymupdf4llm_version_is_pinned():
    assert m.version("pymupdf4llm") == "1.27.2.3"


def test_convert_pdf_to_markdown():
    result = convert_pdf_to_markdown(dummy_pdf_path.as_posix())
    assert result["success"] is True
    assert "markdown_content" in result
    assert result["markdown_content"] == snapshot("""\
# **Dummy PDF file** \n\

""")

    # temporary file to write the markdown content
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)
        result = convert_pdf_to_markdown(dummy_pdf_path.as_posix(), save_path=temp_file_path.as_posix())
        assert result["success"] is True
        assert "markdown_path" in result
        assert result["markdown_path"] == temp_file_path.expanduser().resolve().absolute().as_posix()
        with open(temp_file_path, encoding="utf-8") as f:
            content = f.read()
            assert content == snapshot("""\
# **Dummy PDF file** \n\

""")
