#!/usr/bin/env bash
# uPD78C1x module test suite.   test/run-tests.sh [--real <workdir>]
# Needs GHIDRA_INSTALL_DIR (a Ghidra with this module under Ghidra/Processors/), python3, and
# optionally: MAME unidasm (decode differential), AS (asl; assembler round trip and regeneration of
# the emulator cases), a JDK with javac (JAVAC_HOME) to build lib/UPD78XX.jar for the CALT analyzer test.
# --real <workdir> also fetches the real-code sample (pinned URL + SHA-256) and checks it.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
MOD=$(cd "$HERE/.." && pwd)
OUT=${TMPDIR:-/tmp}/upd78-tests
mkdir -p "$OUT"
REAL=
[[ ${1:-} == --real ]] && REAL=$2

echo "## 1. spec compiles"
for s in "$MOD"/data/languages/*.slaspec; do
	"$GHIDRA_INSTALL_DIR/support/sleigh" "$s" "$OUT/$(basename "$s" .slaspec).sla" >"$OUT/sleigh.log" 2>&1 \
		|| { tail -20 "$OUT/sleigh.log"; exit 1; }
	echo "  $(basename "$s"): $(stat -c %s "$OUT/$(basename "$s" .slaspec).sla") bytes"
done

echo "## 2. emulator cases: hand-computed, model-checked (random operands) and whole programs; a deliberately broken expectation"
ASL=${ASL:-$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/asl}
if [[ -x $ASL ]]; then
	ASL=$ASL python3 "$HERE/emu/cases.py" | diff -q - "$HERE/emu/cases.txt"
	for c in model prog; do
		python3 "$HERE/emu/${c}_cases.py" > "$OUT/${c}_cases.src"
		diff -q "$OUT/${c}_cases.src" "$HERE/emu/${c}_cases.src"
		ASL=$ASL python3 "$HERE/emu/cases.py" --src "$HERE/emu/${c}_cases.src" | diff -q - "$HERE/emu/${c}_cases.txt"
	done
	echo "  cases.txt, model_cases and prog_cases reproduce from their sources"
fi
"$HERE/emu-test.sh" "$OUT"
"$HERE/emu-test.sh" --broken "$OUT"
CASES=$HERE/emu/model_cases.txt "$HERE/emu-test.sh" "$OUT/model"
CASES=$HERE/emu/prog_cases.txt "$HERE/emu-test.sh" "$OUT/prog"

echo "## 3. every constructor reached"
"$HERE/every-entry.sh" "$OUT/every"

echo "## 4. decode differential (MAME unidasm, AS)"
"$HERE/decode-diff.sh" "$OUT/decode"

echo "## 5. CALT analyzer"
if [[ -f $MOD/lib/UPD78XX.jar ]] || { [[ -n ${JAVAC_HOME:-} ]] && "$HERE/build-jar.sh"; }; then
	"$HERE/calt-test.sh" "$OUT/calt"
else
	echo "  SKIPPED: no lib/UPD78XX.jar (set JAVAC_HOME to a JDK and run test/build-jar.sh)"
fi

if [[ -n $REAL ]]; then
	echo "## 6. real code"
	"$HERE/real/fetch-samples.sh" "$REAL"
	"$HERE/real-tests.sh" "$REAL" "$OUT/real"
fi
echo "all tests passed"
