"""Core logic for nft-splitbrain.

The problem: since iptables 1.8, the `iptables` command can be backed by
either the legacy kernel API ("iptables-legacy") or a compatibility
layer that actually writes nftables rules ("iptables-nft"). Multiple
2026 write-ups (cr0x.net's "Debian 13: iptables vs nftables conflict",
simplified.guide's backend-check guide, several Zenn/Qiita posts on
ufw/iptables/nftables relationships) document the same "silent firewall
war" failure mode: some tool (Docker, Kubernetes, a legacy script, a
stale runbook) writes rules through one backend while the operator
inspects or a different tool manages rules through the other, and both
"work" while producing genuinely different, disagreeing rulesets. The
existing prior art (`iptables-wrappers`) only solves this for building
portable container images -- it doesn't diagnose an already-running
bare-metal host. Firewall *linters* like `firewallscope` analyze a single
pasted ruleset for security smells, but don't check for backend
divergence across the live host.

This tool performs exactly that live, read-only host diagnosis:

  1. Which alternative does `iptables`/`ip6tables` currently point to
     (nft or legacy), via `update-alternatives --display` (or absence of
     an alternatives system entirely).
  2. Does `iptables --version` / `ip6tables --version` self-report
     "(nf_tables)" or "(legacy)" -- and does that match #1.
  3. Are there any rules present in the *other*, currently-unselected
     backend (`iptables-legacy-save` / `iptables-nft-save`) that would
     silently keep taking effect or silently be invisible depending on
     which command an operator or tool runs.

Strictly read-only: it never runs `update-alternatives --set`, never
flushes or modifies any ruleset, and never calls `-restore`.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional


STATUS_OK = "ok"
STATUS_ALTERNATIVES_MISMATCH = "alternatives_version_mismatch"
STATUS_HIDDEN_LEGACY_RULES = "hidden_legacy_rules"
STATUS_HIDDEN_NFT_RULES = "hidden_nft_rules"
STATUS_NO_BACKEND_FOUND = "no_backend_found"

STATUS_EXPLANATIONS = {
    STATUS_OK: (
        "The active iptables backend (as reported by 'iptables --version') "
        "matches the alternatives selection, and no rules were found lurking "
        "in the other, unselected backend."
    ),
    STATUS_ALTERNATIVES_MISMATCH: (
        "'update-alternatives' says iptables points to one backend, but "
        "'iptables --version' self-reports the other. Some tool or manual "
        "override has bypassed the alternatives system -- treat this as a "
        "'split-brain' warning sign: inspection commands and actual behavior "
        "may disagree."
    ),
    STATUS_HIDDEN_LEGACY_RULES: (
        "The active backend is nft, but 'iptables-legacy-save' shows rules "
        "still present in the legacy kernel API. These rules are invisible to "
        "'nft list ruleset' and to plain 'iptables -S' but may still be "
        "loaded and affecting traffic -- likely leftovers from before a "
        "migration to nftables, or a tool that still calls iptables-legacy "
        "directly."
    ),
    STATUS_HIDDEN_NFT_RULES: (
        "The active backend is legacy, but 'nft list ruleset' shows rules "
        "already present in nftables. These are invisible to plain "
        "'iptables -S' -- likely a partially-completed migration to "
        "nftables, or a tool (firewalld, Docker in some configurations) that "
        "manages its own nftables tables independently of the iptables "
        "command."
    ),
    STATUS_NO_BACKEND_FOUND: (
        "Neither 'iptables' nor 'nft' appears to be installed or usable on "
        "this host -- nothing to diagnose."
    ),
}


def run(cmd: list, timeout: int = 15) -> str:
    """Run a read-only subprocess command, returning stdout (empty on error)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def which(cmd: str, runner=run) -> bool:
    out = runner(["which", cmd])
    return bool(out.strip())


_VERSION_MODE_RE = re.compile(r"\((nf_tables|legacy)\)")


def get_reported_mode(binary: str, runner=run) -> Optional[str]:
    """Return 'nft' or 'legacy' as self-reported by `<binary> --version`."""
    out = runner([binary, "--version"])
    m = _VERSION_MODE_RE.search(out)
    if not m:
        return None
    return "nft" if m.group(1) == "nf_tables" else "legacy"


_ALTERNATIVES_POINTS_TO_RE = re.compile(r"link currently points to (\S+)")


def get_alternatives_mode(binary: str, runner=run) -> Optional[str]:
    """Return 'nft' or 'legacy' per `update-alternatives --display <binary>`,
    or None if the alternatives system doesn't manage this binary."""
    out = runner(["update-alternatives", "--display", binary])
    m = _ALTERNATIVES_POINTS_TO_RE.search(out)
    if not m:
        return None
    target = m.group(1)
    if "nft" in target:
        return "nft"
    if "legacy" in target:
        return "legacy"
    return None


def count_ruleset_lines(cmd: list, runner=run) -> int:
    """Count non-empty, non-comment lines in a `*-save`/`nft list ruleset`
    style dump -- a simple proxy for "are there rules here"."""
    out = runner(cmd)
    count = 0
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


@dataclass
class SplitBrainReport:
    status: str
    explanation: str
    reported_mode: Optional[str] = None
    alternatives_mode: Optional[str] = None
    legacy_rule_lines: Optional[int] = None
    nft_rule_lines: Optional[int] = None
    details: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "explanation": self.explanation,
            "reported_mode": self.reported_mode,
            "alternatives_mode": self.alternatives_mode,
            "legacy_rule_lines": self.legacy_rule_lines,
            "nft_rule_lines": self.nft_rule_lines,
            "details": list(self.details),
        }


def diagnose(
    iptables_available: bool,
    nft_available: bool,
    reported_mode: Optional[str],
    alternatives_mode: Optional[str],
    legacy_rule_lines: Optional[int],
    nft_rule_lines: Optional[int],
) -> SplitBrainReport:
    """Classify the host's iptables/nftables backend state.

    Priority: no backend found; then alternatives/self-report mismatch
    (most surprising -- inspection tools disagree about ground truth);
    then hidden rules in the unselected backend; else ok.
    """
    details = []

    if not iptables_available and not nft_available:
        return SplitBrainReport(
            status=STATUS_NO_BACKEND_FOUND,
            explanation=STATUS_EXPLANATIONS[STATUS_NO_BACKEND_FOUND],
        )

    if (
        reported_mode is not None
        and alternatives_mode is not None
        and reported_mode != alternatives_mode
    ):
        details.append(
            f"update-alternatives selects '{alternatives_mode}' but "
            f"'iptables --version' self-reports '{reported_mode}'."
        )
        return SplitBrainReport(
            status=STATUS_ALTERNATIVES_MISMATCH,
            explanation=STATUS_EXPLANATIONS[STATUS_ALTERNATIVES_MISMATCH],
            reported_mode=reported_mode,
            alternatives_mode=alternatives_mode,
            legacy_rule_lines=legacy_rule_lines,
            nft_rule_lines=nft_rule_lines,
            details=details,
        )

    active_mode = reported_mode or alternatives_mode

    if active_mode == "nft" and legacy_rule_lines:
        details.append(f"{legacy_rule_lines} rule line(s) found via iptables-legacy-save.")
        return SplitBrainReport(
            status=STATUS_HIDDEN_LEGACY_RULES,
            explanation=STATUS_EXPLANATIONS[STATUS_HIDDEN_LEGACY_RULES],
            reported_mode=reported_mode,
            alternatives_mode=alternatives_mode,
            legacy_rule_lines=legacy_rule_lines,
            nft_rule_lines=nft_rule_lines,
            details=details,
        )

    if active_mode == "legacy" and nft_rule_lines:
        details.append(f"{nft_rule_lines} rule line(s) found via nft list ruleset.")
        return SplitBrainReport(
            status=STATUS_HIDDEN_NFT_RULES,
            explanation=STATUS_EXPLANATIONS[STATUS_HIDDEN_NFT_RULES],
            reported_mode=reported_mode,
            alternatives_mode=alternatives_mode,
            legacy_rule_lines=legacy_rule_lines,
            nft_rule_lines=nft_rule_lines,
            details=details,
        )

    return SplitBrainReport(
        status=STATUS_OK,
        explanation=STATUS_EXPLANATIONS[STATUS_OK],
        reported_mode=reported_mode,
        alternatives_mode=alternatives_mode,
        legacy_rule_lines=legacy_rule_lines,
        nft_rule_lines=nft_rule_lines,
    )


def diagnose_host(runner=run) -> SplitBrainReport:
    iptables_available = which("iptables", runner=runner)
    nft_available = which("nft", runner=runner)

    reported_mode = get_reported_mode("iptables", runner=runner) if iptables_available else None
    alternatives_mode = get_alternatives_mode("iptables", runner=runner) if iptables_available else None

    active_mode = reported_mode or alternatives_mode
    legacy_rule_lines = None
    nft_rule_lines = None

    if active_mode == "nft" and which("iptables-legacy", runner=runner):
        legacy_rule_lines = count_ruleset_lines(["iptables-legacy-save"], runner=runner)
    if active_mode == "legacy" and nft_available:
        nft_rule_lines = count_ruleset_lines(["nft", "list", "ruleset"], runner=runner)

    return diagnose(
        iptables_available=iptables_available,
        nft_available=nft_available,
        reported_mode=reported_mode,
        alternatives_mode=alternatives_mode,
        legacy_rule_lines=legacy_rule_lines,
        nft_rule_lines=nft_rule_lines,
    )
