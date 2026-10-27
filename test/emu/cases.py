#!/usr/bin/env python3
"""Build test/emu/cases.txt from test/emu/cases.src.
Each case in cases.src is
    case <name>
    <assembler lines>          assembled by AS (asl, cpu 78C10) at org 1000h as a black box
    set <reg> <value> | set ram:<addr>[/<n>] <value|@label>
    expect <reg> <value> | expect ram:<addr>[/<n>] <value|@label>
    end [label]                the emulation stops when the PC reaches the label (default: after the code)
    done
`org` lines inside the assembler text place further segments (vectors, tables, CALF area).
The expected values are written by hand from the manual (flags: Z=40h SK=20h HC=10h L1=08h L0=04h CY=01h);
nothing is taken from the module's own output.
  cases.py [--broken]   --broken changes the expectation of the first case to a wrong value."""
import os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ASL = os.environ.get('ASL', os.path.expanduser('~/.cache/ghidra-rare-scratch/tools/asl/bin/asl'))
broken = '--broken' in sys.argv
srcname = 'cases.src'
if '--src' in sys.argv:
    srcname = sys.argv[sys.argv.index('--src') + 1]
cases, cur = [], None
for line in open(os.path.join(HERE, srcname)):
    s = line.rstrip('\n')
    if not s.strip() or s.strip().startswith('#'):
        continue
    w = s.split()
    if w[0] == 'case':
        cur = {'name': w[1], 'asm': [], 'set': [], 'expect': [], 'end': None}
    elif w[0] == 'set':
        cur['set'].append(w[1:])
    elif w[0] == 'expect':
        cur['expect'].append(w[1:])
    elif w[0] == 'end':
        cur['end'] = w[1] if len(w) > 1 else None
    elif w[0] == 'done':
        cases.append(cur)
    else:
        cur['asm'].append(s)
out = []
for n, c in enumerate(cases):
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'c.asm')
        open(src, 'w').write('\tcpu 78c10\n\torg 1000h\n' + '\n'.join(c['asm']) + '\nendofcode:\n')
        r = subprocess.run([ASL, '-L', '-q', 'c.asm'], capture_output=True, text=True, cwd=d)
        if r.returncode:
            sys.exit('asl failed for %s:\n%s%s' % (c['name'], r.stdout, r.stderr))
        lst = open(os.path.join(d, 'c.lst'), errors='replace').read()
    segs, labels = {}, {}
    for l in lst.splitlines():
        m = re.match(r'^\s*\d+/\s*([0-9A-F]+) :((?: [0-9A-F]{2})+)', l)
        if m:
            a = int(m.group(1), 16)
            segs[a] = bytes.fromhex(m.group(2).replace(' ', ''))
    for m in re.finditer(r'\*?(\w+) :\s+([0-9A-F]+) C', lst):
        labels[m.group(1).lower()] = int(m.group(2), 16)
    # merge consecutive bytes into segments
    merged, last = [], None
    for a in sorted(segs):
        if last is not None and a == last[0] + len(last[1]):
            last[1] += segs[a]
        else:
            last = [a, bytearray(segs[a])]
            merged.append(last)
    out.append('case %s' % c['name'])
    for a, b in merged:
        out.append('code %x %s' % (a, bytes(b).hex()))
    end = labels[c['end'].lower()] if c['end'] else labels['endofcode']
    out.append('end %x' % end)
    for kind in ('set', 'expect'):
        for k, v in c[kind]:
            if v.startswith('@'):
                v = str(labels[v[1:].lower()])
            if broken and n == 0 and kind == 'expect':
                v = str(int(v, 0) ^ 0x80)
                broken = False
            out.append('%s %s %s' % (kind, k, v))
    out.append('done')
    out.append('')
sys.stdout.write('\n'.join(out))
