import json

import pytest

from nft_splitbrain.cli import main
from nft_splitbrain.core import SplitBrainReport, STATUS_ALTERNATIVES_MISMATCH, STATUS_OK


def _fake_report(status=STATUS_ALTERNATIVES_MISMATCH):
    return SplitBrainReport(
        status=status, explanation="example explanation",
        reported_mode="legacy", alternatives_mode="nft",
        details=["example detail"],
    )


def test_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "nft-splitbrain" in capsys.readouterr().out


def test_text_output_mismatch(monkeypatch, capsys):
    monkeypatch.setattr("nft_splitbrain.cli.diagnose_host", lambda: _fake_report())
    rc = main([])
    out = capsys.readouterr().out
    assert "alternatives_version_mismatch" in out
    assert "example detail" in out
    assert rc == 2


def test_json_output(monkeypatch, capsys):
    monkeypatch.setattr("nft_splitbrain.cli.diagnose_host", lambda: _fake_report())
    rc = main(["--json"])
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == STATUS_ALTERNATIVES_MISMATCH
    assert rc == 2


def test_ok_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr(
        "nft_splitbrain.cli.diagnose_host",
        lambda: SplitBrainReport(status=STATUS_OK, explanation="fine"),
    )
    rc = main([])
    assert rc == 0
