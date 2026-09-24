"""Regression tests for current setuptools project metadata.

Setuptools 77+ accepts PEP 639-style SPDX license metadata. The older
``project.license = {text = "MIT"}`` table and duplicate MIT Trove classifier
still build for now, but emit deprecation warnings and would eventually break
routine releases. Keep this small test in CI so packaging metadata does not
quietly drift back to the deprecated form.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"


def _pyproject_text() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


def test_project_license_uses_spdx_string_metadata():
    text = _pyproject_text()
    assert 'license = "MIT"' in text
    assert "license = {" not in text
    assert 'license-files = ["LICENSE"]' in text


def test_deprecated_license_classifier_is_not_reintroduced():
    text = _pyproject_text()
    assert "License :: OSI Approved :: MIT License" not in text


def test_build_backend_requires_setuptools_with_spdx_license_support():
    text = _pyproject_text()
    assert 'requires = ["setuptools>=77", "wheel"]' in text
