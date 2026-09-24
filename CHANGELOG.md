# Changelog

## v0.1.9 - Repository completeness contracts

- Add release-history documentation and link it from the English and Chinese READMEs.
- Add repository-contract tests for required project files, README release/license/download links, current changelog coverage, CI wiring, CodeQL, and release artifact generation.
- Bump the package/runtime version to `0.1.9` for a source-quality maintenance release.

## v0.1.8 - Packaging license metadata

- Modernized package license metadata to current SPDX string format.
- Added `license-files` metadata and removed the deprecated MIT Trove classifier.
- Added regression tests to keep packaging metadata from drifting back.

## v0.1.7 - Execution failure is not a clean ruleset

- Fixed a silent false-clean result when `iptables-legacy-save` or `nft list ruleset` failed to execute or timed out during hidden-rules checks.
- Treats execution failure as `cannot_verify_hidden_rules_permission_denied` instead of silently counting zero rules.

## v0.1.6 - nft-only hosts are clean

- Fixed a false positive on hosts that have `nft` installed but no `iptables` binary.
- Added the `nft_only_no_iptables` status, treated as clean because there is no iptables backend to conflict with nftables.

## v0.1.5 - Zipapp exit-code propagation

- Fixed the standalone `.pyz` build so it propagates the CLI exit code instead of always returning success.

## v0.1.4 - Zipapp packaging maintenance

- Published the zipapp exit-code propagation packaging fix as a release artifact.

## v0.1.3 - Undetermined backend is not OK

- Fixed a silent false-OK when neither `iptables --version` nor `update-alternatives --display` could determine the active backend.
- Reports `undetermined_active_mode` for manual investigation instead of claiming the host is clean.

## v0.1.2 - Permission-denied hidden-rules checks

- Fixed a false-OK when the hidden backend check failed due to insufficient privileges.
- Reports `cannot_verify_hidden_rules_permission_denied` with a sudo/root hint and a non-zero exit code.

## v0.1.1 - Shared CLI style system

- Adopted the shared semantic-only ANSI style system, including `NO_COLOR` and `--no-color` support.
- JSON output and diagnosis logic were unchanged.

## v0.1.0 - Initial release

- Added read-only detection for iptables-legacy, iptables-nft, and nftables backend split-brain conflicts on Linux hosts.
