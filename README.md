# nft-splitbrain

Detect `iptables-legacy` / `iptables-nft` / `nftables` "split-brain"
firewall backend conflicts on a Linux host.

## The problem

Since iptables 1.8, the `iptables` command can be backed by either the
legacy kernel API (`iptables-legacy`) or a compatibility layer that
actually writes nftables rules (`iptables-nft`). Multiple 2026 write-ups
document the same "silent firewall war" failure mode (cr0x.net's *Debian
13: iptables vs nftables conflict*, simplified.guide's backend-check
guide, several Zenn/Qiita posts on the ufw/iptables/nftables
relationship): some tool (Docker, a legacy script, a stale runbook, a
manual override) writes rules through one backend while a different tool
or operator inspects/manages rules through the other — and both "work"
while silently producing disagreeing rulesets.

The existing prior art doesn't cover this case: `iptables-wrappers`
(Kubernetes) only solves backend selection for *building portable
container images*, not diagnosing an already-running bare-metal host.
Firewall linters like `firewallscope` analyze a pasted ruleset for
security smells, not for backend divergence on the live host.

## What this does

```
$ nft-splitbrain

Status: hidden_legacy_rules
The active backend is nft, but 'iptables-legacy-save' shows rules still
present in the legacy kernel API. These rules are invisible to 'nft list
ruleset' and to plain 'iptables -S' but may still be loaded and affecting
traffic -- likely leftovers from before a migration to nftables, or a
tool that still calls iptables-legacy directly.
  iptables --version reports: nft
  update-alternatives selects: nft
  iptables-legacy-save rule lines: 14
  - 14 rule line(s) found via iptables-legacy-save.
```

Checks performed, in priority order:

1. **Alternatives vs. self-report mismatch** — does `update-alternatives
   --display iptables` agree with what `iptables --version` itself
   claims? A mismatch means something bypassed the alternatives system.
2. **Hidden legacy rules** — if the active backend is nft, are there
   still rules loaded via `iptables-legacy-save` that `nft list ruleset`
   and plain `iptables -S` can't see?
3. **Hidden nft rules** — if the active backend is legacy, does `nft
   list ruleset` already show rules that plain `iptables -S` can't see
   (a partial migration, or firewalld/Docker managing its own nftables
   tables)?

**Strictly read-only.** It never runs `update-alternatives --set`, never
flushes or modifies any ruleset, and never calls `-restore`. It only
reads command output.

## Install

Requires Python 3.9+ on Linux with `iptables`/`nft` present (meaningless
on macOS/Windows, or a host with neither backend).

```bash
pip install nft-splitbrain
```

Or run the standalone zipapp with no install:

```bash
curl -LO https://github.com/zhuhroscar-tech/nft-splitbrain/releases/download/v0.1.0/nft-splitbrain.pyz
python3 nft-splitbrain.pyz --version
```

Verify the download against `SHA256SUMS.txt` in the same release before
running it.

## Usage

```bash
sudo nft-splitbrain          # human-readable diagnosis (root needed to read rulesets)
sudo nft-splitbrain --json   # machine-readable output
```

Exit code `0` = consistent/clean (or genuinely no firewall backend
present), `2` = a split-brain condition was detected.

## If it finds a problem

This tool only diagnoses; it never modifies anything.

- `alternatives_version_mismatch` → run `update-alternatives --config
  iptables` (and `ip6tables`) to see and fix the actual selection, or
  find what bypassed it (a package postinst script, a manual symlink).
- `hidden_legacy_rules` → decide on one backend. If migrating to
  nftables, run `iptables-legacy-save` to inspect what's still there,
  then intentionally migrate or remove those rules — don't just ignore
  them, they are still live.
- `hidden_nft_rules` → check which tool owns those nftables tables
  (`nft list ruleset` shows table names — `firewalld`'s tables are named
  distinctly, Docker's networking tables likewise) before touching
  anything.

## Uninstall

```bash
pip uninstall nft-splitbrain
```
No config files, no persistent state — a stateless read-only diagnostic.

## Privacy / permissions

- No network access, no telemetry.
- Reads `iptables --version`, `update-alternatives --display`,
  `iptables-legacy-save`, and `nft list ruleset` output. Reading the full
  ruleset typically requires root, same as any other use of these
  commands.
- Writes nothing to disk.

## Distro / architecture support

Any Linux distro shipping iptables 1.8+ and/or nftables (the vast
majority of current distros). Pure Python, no compiled dependencies.

## Reproducible build / test

```bash
git clone https://github.com/zhuhroscar-tech/nft-splitbrain
cd nft-splitbrain
python3 -m pip install -e .[dev]
python3 -m pytest -v
```

CI (`.github/workflows/ci.yml`) runs the suite on real Ubuntu runners
across Python 3.9 and 3.12, installs real `iptables`/`nftables` packages,
then smoke-tests the tool against actual backend state on the runner
before building and verifying the wheel/sdist and a standalone `.pyz`.

## License

MIT — see [LICENSE](LICENSE).
