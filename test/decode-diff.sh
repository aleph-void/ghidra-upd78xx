#!/usr/bin/env bash
# Decode differential: test/decode-diff.sh <outdir>
#  1. every (byte0, byte1) pair with three tails (196,608 slots) and 200,000 random words are
#     decoded by Ghidra and by MAME unidasm -arch upd7810; every difference must be explained
#     (test/explain_mame.py);
#  2. every operand combination of every instruction form of the manual's notation (2,607 lines,
#     test/asl/gen_asm.py) is assembled by AS (asl -cpu 78C10, black box) and must decode to the
#     source text, and no decoded form may lie outside those forms.
# Needs unidasm (MAME) and ASL (the asl binary); each step is skipped with a message when its tool
# is not installed.
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
HERE=$(cd "$(dirname "$0")" && pwd)
OUTD=$(readlink -m "${1:-${TMPDIR:-/tmp}/upd78-decode}")
mkdir -p "$OUTD"
LANG_ID=${LANG_ID:-upd78:LE:16:default}
ARCH=${ARCH:-upd7810}
rc=0
if command -v unidasm >/dev/null; then
	python3 "$HERE/gen_corpus.py" "$OUTD/ex.bin" exhaustive 3 >/dev/null
	python3 "$HERE/gen_corpus.py" "$OUTD/rnd.bin" random 1 200000 >/dev/null
	for c in ex rnd; do
		"$HERE/ghidra-slots.sh" "$LANG_ID" "$OUTD/$c.bin" 8 "$OUTD/gh_$c.txt"
		python3 "$HERE/ref_slots.py" "$ARCH" "$OUTD/$c.bin" "$OUTD/ud_$c.txt" "$OUTD"
		python3 "$HERE/compare.py" "$OUTD/gh_$c.txt" "$OUTD/ud_$c.txt" "$OUTD/$c.bin" --explain "$HERE/explain_mame.py" \
			> "$OUTD/cmp_$c.txt" || rc=1
		echo "MAME unidasm -arch $ARCH, corpus $c: $(head -1 "$OUTD/cmp_$c.txt")"
		sed -n '3,$p' "$OUTD/cmp_$c.txt" | grep -E '^  (explained|DIFF)' | head -20 || true
	done
else
	echo "MAME unidasm not installed: skipped"
fi
ASL=${ASL:-$(command -v asl || true)}
[[ -n $ASL ]] || ASL=$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/asl
if [[ -x $ASL ]]; then
	python3 "$HERE/asl/gen_asm.py" > "$OUTD/forms.asm"
	(cd "$OUTD" && "$ASL" -L -q -cpu 78c10 forms.asm >/dev/null 2>&1 || true)
	python3 "$HERE/asl/asl_compare.py" prep "$OUTD/forms.lst" "$OUTD/forms.bin" "$OUTD/forms.exp"
	"$HERE/ghidra-slots.sh" "$LANG_ID" "$OUTD/forms.bin" 8 "$OUTD/forms.gh"
	python3 "$HERE/asl/asl_compare.py" compare "$OUTD/forms.gh" "$OUTD/forms.exp" "$OUTD/forms.bin" || rc=1
	if [[ -f $OUTD/gh_ex.txt ]]; then
		python3 "$HERE/asl/asl_unlisted.py" "$OUTD/forms.gh" "$OUTD/gh_ex.txt" "$OUTD/ex.bin" || rc=1
	fi
else
	echo "asl not found (set ASL): the assembler round trip is skipped"
fi
exit $rc
