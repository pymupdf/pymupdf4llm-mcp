import importlib.metadata as m

from packaging.requirements import Requirement


def test_mcp_dependency_excludes_v2():
    # mcp 2.0 removed mcp.server.fastmcp, which app.py imports, so a fresh
    # `uvx pymupdf4llm-mcp@latest` must not resolve to mcp 2.x.
    requirements = [Requirement(r) for r in m.requires("pymupdf4llm-mcp") or []]
    (mcp_requirement,) = [r for r in requirements if r.name == "mcp"]
    assert not mcp_requirement.specifier.contains("2.0.0")
