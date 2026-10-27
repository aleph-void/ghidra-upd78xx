#!/usr/bin/env python3
"""Lists the decoded forms (operand values folded to N) of a corpus dump that the assembler round
trip did not produce, i.e. encodings Ghidra decodes that no manual-notation form of forms.txt covers.
  asl_unlisted.py <forms.gh> <corpus.gh> <corpus.bin>      exit status 1 when any remain"""
import re, collections, sys
def skel(t):
    return re.sub(r'0x[0-9a-fA-F]+', 'N', t.strip())
S = set()
for l in open(sys.argv[1]):
    off, n, t = l.rstrip('\n').split(' ', 2)
    if t != 'BAD':
        S.add(skel(t))
G = collections.defaultdict(list)
for l in open(sys.argv[2]):
    off, n, t = l.rstrip('\n').split(' ', 2)
    if t == 'BAD':
        continue
    k = skel(t)
    if k not in S:
        G[k].append(int(off, 16))
data = open(sys.argv[3], 'rb').read()
print('%d assembler-form skeletons; %d decoded forms outside them' % (len(S), len(G)))
for k, v in sorted(G.items()):
    print('  %s x%d (e.g. %s)' % (k, len(v), data[v[0]:v[0] + 4].hex()))
sys.exit(1 if G else 0)
