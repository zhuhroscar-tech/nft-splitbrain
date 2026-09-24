"""Repository-level completeness contracts for release maintenance."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_required_project_files_are_present():
    for relative_path in (
        "README.md",
        "README.zh-CN.md",
        "CHANGELOG.md",
        "LICENSE",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        ".github/workflows/codeql.yml",
    ):
        assert (ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_readmes_link_release_history_license_and_downloads():
    checks = {
        "README.md": ("[Changelog](CHANGELOG.md)", "[Releases]", "[MIT license](LICENSE)", "SHA256SUMS.txt"),
        "README.zh-CN.md": ("[更新日志](CHANGELOG.md)", "[发布文件]", "[MIT 许可证](LICENSE)", "SHA256SUMS.txt"),
    }
    for relative_path, needles in checks.items():
        text = _read(relative_path)
        for needle in needles:
            assert needle in text, f"{relative_path} missing {needle!r}"


def test_changelog_documents_current_project_version():
    pyproject = _read("pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, "pyproject.toml must contain a project version"
    version = match.group(1)

    changelog = _read("CHANGELOG.md")
    assert f"## v{version}" in changelog
    assert "v0.1.0" in changelog


def test_ci_runs_tests_builds_artifacts_and_smokes_zipapp():
    workflow = _read(".github/workflows/ci.yml")
    assert "python -m pytest -v" in workflow
    assert "python -m build" in workflow
    assert "dist/nft-splitbrain.pyz" in workflow
    assert "python3 dist/nft-splitbrain.pyz --version" in workflow
    assert "SHA256SUMS.txt" in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_codeql_workflow_covers_python():
    workflow = _read(".github/workflows/codeql.yml")
    assert "github/codeql-action/init" in workflow
    assert "python" in workflow.lower()
    assert "github/codeql-action/analyze" in workflow
