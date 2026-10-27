#!/usr/bin/env python3
"""Compare a Ghidra listing ("<addr> <len> <text>") of a raw image with MAME unidasm (upd7810)
at the same addresses.  real_compare.py <image> <base> <listing> <outdir>"""
import importlib.util, os, re, subprocess, sys, tempfile
img, base, listing, outd = sys.argv[1], int(sys.argv[2], 0), sys.argv[3], sys.argv[4]
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('explain', os.path.join(here, 'explain_mame.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
res = subprocess.run(['unidasm', img, '-arch', 'upd7810', '-basepc', '%x' % base], capture_output=True, text=True).stdout
ref = {}
for l in res.splitlines():
    m = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)$', l)
    if m:
        ref[int(m.group(1), 16)] = (len(m.group(2).split()), re.sub(r'\s+', ' ', m.group(3).strip()))
sys.path.insert(0, here)
import compare as cmp
same = diff = nomatch = 0
bad = []
for l in open(listing):
    a, n, t = l.rstrip('\n').split(' ', 2)
    a = int(a, 16); n = int(n)
    if a not in ref:
        nomatch += 1
        continue
    rn, rt = ref[a]
    if rn == n and cmp.norm(ex.canon(rt, 'ref'), True) == cmp.norm(ex.canon(t, 'ghidra'), True):
        same += 1
    else:
        diff += 1
        bad.append((a, n, t, rn, rt))
print('compared with MAME unidasm: %d identical, %d different, %d not on a MAME instruction boundary' % (same, diff, nomatch))
for b in bad[:20]:
    print('  %04x ghidra[%d] %s | mame[%d] %s' % b)
sys.exit(0)
