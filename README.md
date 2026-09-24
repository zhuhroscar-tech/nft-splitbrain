# nft-splitbrain

[![English](https://img.shields.io/badge/English-555555?style=flat)](README.md) [![简体中文](https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-555555?style=flat)](README.zh-CN.md)

Inspect a Linux host for mismatches between `iptables-legacy`, `iptables-nft` and nftables. It helps identify rules in a backend that your usual inspection command may not show, without changing the firewall.

![nft-splitbrain example output](docs/images/example-output.png)

[Demo video](docs/demo.mp4)

## Checks

- Compare `iptables --version` with `update-alternatives --display iptables`, where available.
- When nft is selected, inspect `iptables-legacy-save` for legacy content.
- When legacy is selected, inspect `nft list ruleset` for nftables content.
- Report recognized permission failures and an undetermined active mode instead of presenting those as a clean check.

## Install and run

Requires Python 3.9+ on Linux and the firewall tools relevant to your host (iptables 1.8+ and/or nftables). No Python runtime dependencies.

```bash
git clone https://github.com/zhuhroscar-tech/nft-splitbrain.git
cd nft-splitbrain
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

```bash
nft-splitbrain
sudo .venv/bin/nft-splitbrain --json
```

Reading rulesets generally requires root or `CAP_NET_ADMIN`; the explicit virtualenv path avoids relying on sudo's `PATH`. The program never elevates itself. Alternatively, download the `.pyz` from [releases](https://github.com/zhuhroscar-tech/nft-splitbrain/releases), verify the matching `SHA256SUMS.txt`, and run `python3 nft-splitbrain.pyz`.

Exit `0` covers `ok`, `no_backend_found` and `nft_only_no_iptables`; exit `2` covers conflicts, unknown mode and recognized permission failures. **A zero exit code is not a firewall security audit.** Inspect the reported status.

## Safety and limits

No rule changes, flushes, restores, backend switching, network requests or telemetry. Findings are a snapshot of the current network namespace, not a traffic simulation or complete host/IPv6 audit. Ruleset line counts are a coarse presence heuristic, not a semantic rule count; some command failures may not match the permission detector.

Before changing anything, identify the owning service (such as Docker or firewalld), inspect both backends and plan any migration. Do not blindly flush rules or switch backends on a remote host: you can lose access.

## Development and removal

```bash
python -m pytest -q
python -m pip uninstall nft-splitbrain
```

[Changelog](CHANGELOG.md) · [Releases](https://github.com/zhuhroscar-tech/nft-splitbrain/releases) · [MIT license](LICENSE)
