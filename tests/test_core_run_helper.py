"""Real subprocess.run() coverage for core.run() / core.run_capture().

Every other test in this suite exercises these two helpers only through a
fake runner substituted via the `runner=`/`capture_runner=` parameters --
the real subprocess.run() call inside each helper (the success path, the
FileNotFoundError-on-missing-binary path, and the genuine TimeoutExpired
path) has never actually executed a real process. That is the exact gap
this file closes, following the pattern already established in
unmount-doctor's tests/test_cli_run_helper.py.
"""
import subprocess

from nft_splitbrain.core import run, run_capture


def test_run_missing_binary_returns_empty_string():
    """A nonexistent binary raises FileNotFoundError inside run(), which
    must be caught and turned into "" rather than propagating."""
    result = run(["definitely-not-a-real-binary-xyz123"])
    assert result == ""


def test_run_real_success_path():
    """A real, trivial command should flow through subprocess.run() and
    return its actual stdout, exercising the non-exceptional branch."""
    result = run(["echo", "hello-nft-splitbrain"])
    assert "hello-nft-splitbrain" in result


def test_run_real_timeout_raises_and_is_caught():
    """Force a genuine subprocess.TimeoutExpired (not a mocked one) by
    giving a real sleep a timeout shorter than its runtime, and confirm
    run() swallows it and returns ""."""
    result = run(["sleep", "2"], timeout=0)
    assert result == ""


def test_run_capture_missing_binary_returns_empty_triple():
    stdout, stderr, returncode = run_capture(["definitely-not-a-real-binary-xyz123"])
    assert stdout == ""
    assert stderr == ""
    assert returncode is None


def test_run_capture_real_success_path():
    stdout, stderr, returncode = run_capture(["echo", "hi"])
    assert "hi" in stdout
    assert returncode == 0


def test_run_capture_real_nonzero_exit_preserves_stderr_and_code():
    """A real failing command (not mocked) must surface its actual stderr
    and returncode unchanged -- this is what count_ruleset_lines' permission
    denied detection depends on."""
    stdout, stderr, returncode = run_capture(["ls", "/definitely/not/a/real/path/xyz123"])
    assert returncode != 0
    assert stderr != ""


def test_run_capture_real_timeout_raises_and_is_caught():
    stdout, stderr, returncode = run_capture(["sleep", "2"], timeout=0)
    assert stdout == ""
    assert stderr == ""
    assert returncode is None
