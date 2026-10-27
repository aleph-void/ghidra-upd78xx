#!/usr/bin/env python3
"""Corpus of 8-byte slots: 4 instruction bytes followed by 4 zero bytes (NOPs, so that a
sequential disassembler resynchronises at every slot).
  gen_corpus.py <out.bin> exhaustive <tails>   every (b0,b1) pair with <tails> random b2,b3 tails
  gen_corpus.py <out.bin> random <seed> <n>    n random 4-byte words"""
import random, struct, sys
out, mode = sys.argv[1], sys.argv[2]
buf = bytearray()
if mode == 'exhaustive':
    n = int(sys.argv[3]); rnd = random.Random(7)
    for b0 in range(256):
        for b1 in range(256):
            for t in range(n):
                if t == 0:
                    tail = bytes([0, 0])
                elif t == 1:
                    tail = bytes([0xff, 0xff])
                else:
                    tail = bytes([rnd.randrange(256), rnd.randrange(256)])
                buf += bytes([b0, b1]) + tail + bytes(4)
else:
    rnd = random.Random(int(sys.argv[3]))
    for i in range(int(sys.argv[4])):
        buf += bytes(rnd.randrange(256) for _ in range(4)) + bytes(4)
open(out, 'wb').write(buf)
print(len(buf) // 8, 'slots')
