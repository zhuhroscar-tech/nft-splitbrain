"""nft-splitbrain CLI."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import diagnose_host, STATUS_OK, STATUS_NO_BACKEND_FOUND


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nft-splitbrain",
        description=(
            "Detect iptables-legacy/iptables-nft/nftables 'split-brain' "
            "firewall backend conflicts: alternatives-vs-self-reported-mode "
            "mismatches, and rules hidden in the unselected backend. "
            "Strictly read-only: never modifies alternatives or any ruleset."
        ),
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return p


def _print_text(report) -> None:
    print(f"Status: {report.status}")
    print(report.explanation)
    if report.reported_mode:
        print(f"  iptables --version reports: {report.reported_mode}")
    if report.alternatives_mode:
        print(f"  update-alternatives selects: {report.alternatives_mode}")
    if report.legacy_rule_lines is not None:
        print(f"  iptables-legacy-save rule lines: {report.legacy_rule_lines}")
    if report.nft_rule_lines is not None:
        print(f"  nft list ruleset rule lines: {report.nft_rule_lines}")
    for d in report.details:
        print(f"  - {d}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    report = diagnose_host()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_text(report)

    if report.status in (STATUS_OK, STATUS_NO_BACKEND_FOUND):
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
