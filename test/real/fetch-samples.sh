#!/usr/bin/env bash
# Fetch the real-code samples into <workdir> (pinned URL + SHA-256; nothing here is committed).
#   fetch-samples.sh <workdir>
# DiKon (https://github.com/TheRND2/dikon, MIT, commit 5d93a7be82c3): a PCL3 raster interpreter
# written in uPD78C10 assembly (about 1.8 KB of hand-written code and tables). The repository ships it
# as an IPS patch of RND2 Labs' own bytes (the stock Kodak ROM is not part of it and is never
# used here) plus the Python builder whose assembler DSL gives the label addresses and the byte
# image. extract_dikon.py rebuilds the 1,833-byte code image from the builder and checks it against the patch
# record.
set -euo pipefail
W=$(mkdir -p "$1" && cd "$1" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
COMMIT=5d93a7be82c361aa4ab91c05f5a6452e112bbfe4
fetch() { # name sha256
	[[ -f $W/$1 ]] || curl -sSfL -o "$W/$1" "https://raw.githubusercontent.com/TheRND2/dikon/$COMMIT/$3"
	echo "$2  $W/$1" | sha256sum -c --quiet - || { echo "bad checksum for $1" >&2; exit 1; }
}
fetch d150_dikon_v5i.ips ef57a9bd2994e57eae3a56f0a910e603b507d01929fc0bbc05b182e6d6e024d5 patch/d150_dikon_v5i.ips
fetch build_m7dikon_v5i.py 12d4fe300f23364cf9c29b77d3212826fe431025174842ff0c4a507ac02635c3 tools/build_m7dikon_v5i.py
python3 -I "$HERE/extract_dikon.py" "$W"
