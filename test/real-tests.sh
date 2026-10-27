#!/usr/bin/env bash
# Real-code checks: test/real-tests.sh <workdir> <outdir>
# DiKon (uPD78C10 assembly, MIT): disassembly seeded at the builder's labels, auto-analysis, every
# function decompiled, listing compared with MAME unidasm at the same addresses.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -f "$1"); OUTD=$(mkdir -p "$2" && readlink -f "$2")
PROJ=$(mktemp -d "${TMPDIR:-/tmp}/upd78-real.XXXXXX"); trap 'rm -rf "$PROJ"' EXIT
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$PROJ" p -import "$W/blob.bin" -loader BinaryLoader \
	-loader-baseAddr 0x2800 -processor upd78:LE:16:default -scriptPath "$HERE" \
	-postScript RealCheck.java "$W/labels.txt" "$OUTD/dikon_listing.txt" "$OUTD/dikon_summary.txt" BIT16 \
	-deleteProject >"$PROJ/log.txt" 2>&1 || { tail -30 "$PROJ/log.txt" >&2; exit 1; }
grep -E "^(error bookmark|label |decompile failed)" "$PROJ/log.txt" | head -20 || true
echo "DiKon: $(cat "$OUTD/dikon_summary.txt")"
python3 "$HERE/real_compare.py" "$W/blob.bin" 0x2800 "$OUTD/dikon_listing.txt" "$OUTD"
