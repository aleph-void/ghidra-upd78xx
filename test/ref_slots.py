#!/usr/bin/env python3
"""Run MAME unidasm (-arch <arch>) over a corpus of 8-byte slots (4 instruction bytes + 4 zero
bytes) and write "<slot-offset> <len> <text>" lines, the format compare.py reads.
  ref_slots.py <arch> <corpus.bin> <out.txt> [workdir]
Branch targets are printed by unidasm relative to the cell address; they are moved to the
slot address so that they match Ghidra's output at the same offset."""
import os, re, subprocess, sys, tempfile
arch, src, outp = sys.argv[1:4]
work = sys.argv[4] if len(sys.argv) > 4 else tempfile.gettempdir()
data = open(src, 'rb').read()
n = len(data) // 8
tmp = os.path.join(work, 'ud_%d.bin' % os.getpid())
open(tmp, 'wb').write(data)
res = subprocess.run(['unidasm', '-arch', arch, tmp], capture_output=True, text=True).stdout
os.unlink(tmp)
got = {}
for line in res.splitlines():
    m = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)$', line)
    if not m:
        continue
    off = int(m.group(1), 16)
    if off % 8:
        continue
    txt = re.sub(r'\s+', ' ', m.group(3).strip())
    got[off // 8] = (len(m.group(2).split()), txt)
with open(outp, 'w') as f:
    for i in range(n):
        ln, txt = got.get(i, (0, 'illegal'))
        f.write(f'{i * 8:08x} {ln} {txt}\n')
