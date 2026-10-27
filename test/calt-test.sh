#!/usr/bin/env bash
# CALT and skip-return analyzer test: test/calt-test.sh <outdir>   (needs lib/UPD78XX.jar: test/build-jar.sh)
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
OUTD=$(mkdir -p "$1" && readlink -f "$1")
PROJ=$(mktemp -d "${TMPDIR:-/tmp}/upd78-calt.XXXXXX"); trap 'rm -rf "$PROJ"' EXIT
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$PROJ" p -import "$HERE/real/calt_test.bin" -loader BinaryLoader \
	-processor upd78:LE:16:default -scriptPath "$HERE" -postScript CaltCheck.java "$OUTD/calt.txt" \
	-deleteProject >"$PROJ/log.txt" 2>&1 || { tail -30 "$PROJ/log.txt" >&2; exit 1; }
cat "$OUTD/calt.txt"
grep -q "calts 3  resolved 3  with function 3" "$OUTD/calt.txt"
# the callee of the third CALT executes RETS: its call site keeps the skip test, the others lose it
grep -q "CALT at 0105.*skip test after the call 0" "$OUTD/calt.txt"
grep -q "CALT at 0106.*skip test after the call 0" "$OUTD/calt.txt"
grep -q "CALT at 0107.*skip test after the call 1" "$OUTD/calt.txt"
