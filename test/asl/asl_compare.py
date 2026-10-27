#!/usr/bin/env python3
"""Round trip against the assembler AS (asl, `cpu 78C10`, used as a black box).
  asl_compare.py prep    <forms.lst> <corpus.bin> <expected.txt>   listing -> 8-byte slot corpus + expected text
  asl_compare.py compare <ghidra.txt> <expected.txt>               Ghidra slot dump vs the assembler source
The source is spelled in the NEC notation of the user's manual (B/D/H for register pairs, D+ for
(DE)+ ...); it is rewritten into this module's notation before comparing."""
import re, sys

SFR = {'PA': 'PORTA', 'PB': 'PORTB', 'PC': 'PORTC', 'PD': 'PORTD', 'PF': 'PORTF'}
RP = {'B': 'BC', 'D': 'DE', 'H': 'HL', 'V': 'VA'}
RPA_MN = {'ADCX', 'ADDNCX', 'ADDX', 'ANAX', 'EQAX', 'GTAX', 'LDAX', 'LTAX', 'NEAX', 'OFFAX', 'ONAX',
          'ORAX', 'SBBX', 'SUBNBX', 'SUBX', 'XRAX', 'STAX', 'LDEAX', 'STEAX', 'MVIX'}
RP_MN = {'INX', 'DCX', 'LXI', 'PUSH', 'POP', 'DMOV', 'DADD', 'DADC', 'DADDNC', 'DAN', 'DEQ', 'DGT',
         'DLT', 'DNE', 'DOFF', 'DON', 'DOR', 'DSBB', 'DSUB', 'DSUBNB', 'DXR'}
WA_MN = {'ADCW', 'ADDNCW', 'ADDW', 'ANAW', 'EQAW', 'GTAW', 'LTAW', 'NEAW', 'OFFAW', 'ONAW', 'ORAW',
         'SBBW', 'SUBNBW', 'SUBW', 'XRAW', 'ANIW', 'EQIW', 'GTIW', 'LTIW', 'NEIW', 'OFFIW', 'ONIW',
         'ORIW', 'MVIW', 'INRW', 'DCRW', 'STAW', 'LDAW', 'BIT'}
MEM_MN = {'LBCD', 'LDED', 'LHLD', 'LSPD', 'SBCD', 'SDED', 'SHLD', 'SSPD'}

def num(t):
    t = t.strip()
    m = re.fullmatch(r'([0-9][0-9a-f]*)h', t, re.I)
    if m:
        return '0x%x' % int(m.group(1), 16)
    return t

def rpa(o):
    o = o.upper()
    m = re.fullmatch(r'([DH])([+-]{1,2})', o)
    if m:
        return '(%s%s)' % (RP[m.group(1)], m.group(2))
    m = re.fullmatch(r'([DH])\+(A|B|EA)', o)
    if m:
        return '(%s+%s)' % (RP[m.group(1)], m.group(2))
    m = re.fullmatch(r'([DH])\+(.+)', o)
    if m:
        return '(%s+%s)' % (RP[m.group(1)], num(m.group(2).lower()))
    if o in RP:
        return '(%s)' % RP[o]
    return o

def canon_src(src, addr, bs):
    src = src.strip()
    m = re.match(r'^(\w+)\s*(.*)$', src)
    mn = m.group(1).upper()
    ops = [o.strip() for o in m.group(2).split(',')] if m.group(2) else []
    out = []
    for i, o in enumerate(ops):
        u = o.upper()
        if mn in ('JR', 'JRE', 'CALT', 'CALF'):
            out.append('@T')
        elif mn in RPA_MN and i == 0 and mn != 'MVIX' or (mn == 'MVIX' and i == 0):
            out.append(rpa(o))
        elif mn in ('LDEAX', 'STEAX'):
            out.append(rpa(o))
        elif mn in RP_MN and u in RP:
            out.append(RP[u])
        elif mn in WA_MN and re.fullmatch(r'[0-9a-f]+h?', o, re.I) and ((mn == 'BIT' and i == 1) or (mn != 'BIT' and i == 0)):
            out.append('(V+%s)' % num(o.lower() if o.lower().endswith('h') else o))
        elif mn in MEM_MN:
            out.append('(%s)' % num(o))
        elif mn == 'MOV' and re.fullmatch(r'[0-9][0-9a-f]*h?', o, re.I):
            out.append('(%s)' % num(o))
        elif u in SFR and mn not in ('INX',):
            out.append(SFR[u])
        else:
            out.append(num(o) if re.fullmatch(r'[0-9][0-9a-f]*h?', o, re.I) else u)
    return mn + (' ' + ','.join(out) if out else '')

def prep(lst, corpus, expected):
    ins = []
    for line in open(lst, errors='replace'):
        m = re.match(r'^\s*\d+/\s*([0-9A-F]+) :((?: [0-9A-F]{2})+)\s+(.*)$', line)
        if m:
            ins.append([int(m.group(1), 16), m.group(2).split(), m.group(3)])
            continue
        m = re.match(r'^\s*\d+/\s*([0-9A-F]+) :((?: [0-9A-F]{2})+)\s*$', line)
        if m and ins:
            ins[-1][1] += m.group(2).split()
    buf = bytearray()
    with open(expected, 'w') as f:
        for addr, bs, src in ins:
            b = bytes(int(x, 16) for x in bs)
            buf += (b + bytes(8))[:8] if len(b) <= 4 else (b[:8])
            if len(b) > 4:
                sys.exit('instruction longer than 4 bytes: ' + src)
            f.write('%d %s\t%s\n' % (len(b), addr, src.strip()))
    # slots are decoded at (offset & 0xffff) by DumpSlots; branch targets are rebuilt from that
    open(corpus, 'wb').write(buf)
    print(len(ins), 'forms')

def target(mn, off, b):
    a = off & 0xffff
    if mn == 'JR':
        d = b[0] & 0x3f
        d = d - 64 if d & 0x20 else d
        return '0x%04x' % ((a + 1 + d) & 0xffff)
    if mn == 'JRE':
        d = b[1] | ((b[0] & 1) << 8)
        d = d - 512 if d & 0x100 else d
        return '0x%04x' % ((a + 2 + d) & 0xffff)
    if mn == 'CALT':
        return '0x%x' % (0x80 + ((b[0] & 0x1f) << 1))
    if mn == 'CALF':
        return '0x%04x' % (0x800 + ((b[0] & 7) << 8) + b[1])

NUMRE = re.compile(r'\b(0x[0-9a-f]+|[0-9][0-9a-f]*h|[0-9]+)\b', re.I)

def numnorm(t):
    t = re.sub(r'\s+', ' ', t.strip().upper())
    def f(m):
        g = m.group(1).lower()
        v = int(g[2:], 16) if g.startswith('0x') else int(g[:-1], 16) if g.endswith('h') else int(g)
        return '0x%x' % v
    return NUMRE.sub(f, t).replace('0X', '0x').upper().replace('0X', '0x')

def compare(ghidra, expected, corpus):
    data = open(corpus, 'rb').read()
    gh = {}
    for line in open(ghidra):
        off, n, t = line.rstrip('\n').split(' ', 2)
        gh[int(off, 16)] = (int(n), t)
    exact = 0
    bad = []
    for i, line in enumerate(open(expected)):
        n, rest = line.rstrip('\n').split(' ', 1)
        addr, src = rest.split('\t', 1)
        n = int(n)
        mn = src.split()[0].upper()
        want = canon_src(src, int(addr), None)
        if mn in ('JR', 'JRE', 'CALT', 'CALF'):
            want = mn + ' ' + target(mn, i * 8, data[i * 8:i * 8 + 4])
        gn, gt = gh.get(i * 8, (0, 'BAD'))
        gtn = numnorm(gt)
        w = numnorm(want)
        if gn == n and gtn.lower() == w.lower():
            exact += 1
        else:
            bad.append((i, src.strip(), data[i * 8:i * 8 + n].hex(), gn, gt, want))
    print('forms %d  identical to the assembler source %d  different %d' % (exact + len(bad), exact, len(bad)))
    for b in bad[:60]:
        print('  DIFF slot %d: source "%s" bytes %s -> ghidra[%d] "%s" (expected "%s")' % b)
    return 1 if bad else 0

if __name__ == '__main__':
    if sys.argv[1] == 'prep':
        prep(*sys.argv[2:5])
    else:
        sys.exit(compare(*sys.argv[2:5]))
