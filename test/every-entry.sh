#!/usr/bin/env bash
# Every-entry test: test/every-entry.sh [outdir] [language-id ...]
# CoverageCheck.java builds instructions from every root-table pattern of the SLEIGH decision tree
# (random free bits and contexts) and lists the constructors (in every subtable) that no decode
# reached, i.e. shadowed or unreachable entries.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
OUTD=$(readlink -m "${1:-${TMPDIR:-/tmp}/upd78-every}")
shift || true
LANGS=("$@")
[[ ${#LANGS[@]} -gt 0 ]] || LANGS=(upd78:LE:16:default)
mkdir -p "$OUTD"
head -c 64 /dev/zero > "$OUTD/z.bin"
rc=0
for l in "${LANGS[@]}"; do
	"$HERE/ghidra-script.sh" raw "$l" "$OUTD/z.bin" CoverageCheck.java "$OUTD/cov_${l//:/_}.txt" 256 1
	echo "$l: $(tail -1 "$OUTD/cov_${l//:/_}.txt")"
	grep -q ' 0 unreached' "$OUTD/cov_${l//:/_}.txt" || { grep unreached "$OUTD/cov_${l//:/_}.txt" | head -20; rc=1; }
done
exit $rc
