from pathlib import Path

from pymupdf4llm_mcp.app import check_font_reliability

_HERE = Path(__file__).parent
dummy_pdf_path = _HERE / "dummy.pdf"


def test_check_font_reliability_clean_pdf():
    """The dummy PDF has standard fonts and should report as reliable."""
    result = check_font_reliability(dummy_pdf_path.as_posix())
    assert result["success"] is True
    assert result["is_reliable"] is True
    assert result["unreliable_pages"] == []
    assert result["total_pages_checked"] == 1
    assert result["warnings"] == []


def test_check_font_reliability_file_not_found():
    result = check_font_reliability("/nonexistent/path/to/file.pdf")
    assert result["success"] is False
    assert "error" in result


def test_check_font_reliability_page_selection():
    result = check_font_reliability(dummy_pdf_path.as_posix(), pages="0")
    assert result["success"] is True
    assert result["total_pages_checked"] == 1


def test_check_font_reliability_invalid_pages():
    result = check_font_reliability(dummy_pdf_path.as_posix(), pages="abc")
    assert result["success"] is False
    assert "Invalid pages" in result["error"]
