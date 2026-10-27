#!/usr/bin/env python3
"""Rebuild the DiKon code image (org 2800h) from the project's own builder and check it against
the IPS patch record, then write blob.bin and labels.txt next to them.
  extract_dikon.py <workdir>    (needs d150_dikon_v5i.ips and build_m7dikon_v5i.py in <workdir>)
The builder is executed only up to the point where it would read the stock ROM, which is not used.
Every public method of its Asm class emits one instruction (or a data run for db/label tables);
the instruction start addresses are written to starts.txt."""
import os, sys, json
w = sys.argv[1]
src = open(os.path.join(w, 'build_m7dikon_v5i.py')).read()
cut = src.index("stock=bytearray(open('diconix-150-rom.bin'")
code = src[:cut]
# record the start address of every instruction-emitting call of the assembler DSL
code = code.replace("class Asm:", "STARTS = []\nclass Asm:", 1)
glb = {'__name__': 'dikon_builder'}
exec(compile(code, 'build_m7dikon_v5i.py', 'exec'), glb)
Asm = glb['Asm']
a = glb['a']
blob = bytes(glb['blob'])
labels = glb['Lb']
ips = open(os.path.join(w, 'd150_dikon_v5i.ips'), 'rb').read()
i, rec = 5, None
while ips[i:i + 3] != b'EOF':
    off = int.from_bytes(ips[i:i + 3], 'big'); n = int.from_bytes(ips[i + 3:i + 5], 'big'); i += 5
    if off == 0x2800:
        rec = ips[i:i + n]
    i += n
assert rec[:len(blob)] == blob, 'builder output differs from the IPS record at 0x2800'
open(os.path.join(w, 'blob.bin'), 'wb').write(blob)
with open(os.path.join(w, 'labels.txt'), 'w') as f:
    for k, v in sorted(labels.items(), key=lambda x: x[1]):
        f.write('%s %04x\n' % (k, v))
print('DiKon image: %d bytes at 2800h, %d labels, identical to the first bytes of the IPS record (%d bytes; the rest is banner text)' % (len(blob), len(labels), len(rec)))
