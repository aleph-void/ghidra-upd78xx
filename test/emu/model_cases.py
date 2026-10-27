#!/usr/bin/env python3
"""Write test/emu/model_cases.src: randomised operand values for every ALU / compare / skip form,
with the expected results computed by an independent model of the instruction descriptions and
the flag table (manual 3.4, 14.6) written below. test/emu/cases.py turns it into model_cases.txt.
After each instruction an `inx sp` (1 byte, no flags) shows whether it was skipped:
SP = 8001h when it ran, 8000h when it was skipped.  Z=40h HC=10h CY=01h; the skip flag is consumed."""
import random, sys
rnd = random.Random(20261026)
Z, HC, CY = 0x40, 0x10, 0x01

def alu(op, a, b, cy, bits):
    """returns (result or None, new flags dict (only the ones the instruction changes), skip)"""
    m = (1 << bits) - 1
    f = {}
    def zf(r): return Z if (r & m) == 0 else 0
    if op in ('add', 'adc', 'addnc'):
        c = cy if op == 'adc' else 0
        r = a + b + c
        f = {'Z': zf(r), 'HC': HC if (a & 15) + (b & 15) + c > 15 else 0, 'CY': CY if r > m else 0}
        return r & m, f, (op == 'addnc' and r <= m)
    if op in ('sub', 'sbb', 'subnb'):
        c = cy if op == 'sbb' else 0
        r = a - b - c
        f = {'Z': zf(r), 'HC': HC if (a & 15) < (b & 15) + c else 0, 'CY': CY if a < b + c else 0}
        return r & m, f, (op == 'subnb' and a >= b)
    if op in ('ana', 'ora', 'xra'):
        r = {'ana': a & b, 'ora': a | b, 'xra': a ^ b}[op]
        return r & m, {'Z': zf(r)}, False
    if op == 'gta':
        r = a - b - 1
        return None, {'Z': zf(r), 'HC': HC if (a & 15) < (b & 15) + 1 else 0, 'CY': CY if a < b + 1 else 0}, a > b
    if op in ('lta', 'nea', 'eqa'):
        r = a - b
        f = {'Z': zf(r), 'HC': HC if (a & 15) < (b & 15) else 0, 'CY': CY if a < b else 0}
        return None, f, {'lta': a < b, 'nea': a != b, 'eqa': a == b}[op]
    if op in ('ona', 'offa'):
        r = a & b
        return None, {'Z': zf(r)}, (r != 0) == (op == 'ona')
    raise ValueError(op)

REGS = 'V A B C D E H L'.split()
def edge(bits):
    m = (1 << bits) - 1
    return rnd.choice([0, 1, m, m - 1, 0x0f, 0x10, 0x7f, 0x80, rnd.randrange(m + 1), rnd.randrange(m + 1), rnd.randrange(m + 1)])

def psw_after(psw_in, f):
    p = psw_in & (Z | HC | CY)
    for k, v in f.items():
        bit = {'Z': Z, 'HC': HC, 'CY': CY}[k]
        p = (p & ~bit) | v
    return p

out = []
n = 0
def emit(name, asm, sets, expects):
    global n
    n += 1
    out.append('case %s_%d' % (name, n))
    for l in asm:
        out.append('\t' + l)
    out.append('\tinx sp')
    for k, v in sets.items():
        out.append('set %s 0x%x' % (k, v))
    for k, v in expects.items():
        out.append('expect %s 0x%x' % (k, v))
    out.append('done')

OPS8 = ['add', 'adc', 'sub', 'sbb', 'ana', 'ora', 'xra', 'addnc', 'subnb', 'gta', 'lta', 'nea', 'eqa', 'ona', 'offa']
IMM = {'add': 'adi', 'adc': 'aci', 'sub': 'sui', 'sbb': 'sbi', 'ana': 'ani', 'ora': 'ori', 'xra': 'xri',
       'addnc': 'adinc', 'subnb': 'suinb', 'gta': 'gti', 'lta': 'lti', 'nea': 'nei', 'eqa': 'eqi',
       'ona': 'oni', 'offa': 'offi'}
STORES = ('add', 'adc', 'sub', 'sbb', 'ana', 'ora', 'xra', 'addnc', 'subnb')
RPA = {'(BC)': ('b', 'BC', 0), '(DE)': ('d', 'DE', 0), '(HL)': ('h', 'HL', 0), '(DE+)': ('d+', 'DE', 1),
       '(HL+)': ('h+', 'HL', 1), '(DE-)': ('d-', 'DE', -1), '(HL-)': ('h-', 'HL', -1)}
PORTS = {'pa': 'PORTA', 'pb': 'PORTB', 'pc': 'PORTC', 'pd': 'PORTD', 'pf': 'PORTF', 'mkh': 'MKH', 'mkl': 'MKL',
         'anm': 'ANM', 'smh': 'SMH', 'eom': 'EOM', 'tmm': 'TMM'}

def run8(op, a, b, cy, psw_in, dest_is_op1=True):
    r, f, skip = alu(op, a, b, cy, 8)
    return r, psw_after(psw_in, f), skip

for op in OPS8:
    for rep in range(4):
        for r in REGS:
            for form in ('A,r', 'r,A'):
                if r == 'A' and rep:
                    continue
                psw = rnd.choice([0, CY, HC, Z, CY | HC | Z])
                cy = psw & CY
                a, rv = edge(8), edge(8)
                if r == 'A':
                    rv = a
                sets = {'A': a, 'PSW': psw}
                if r != 'A':
                    sets[r] = rv
                if form == 'A,r':
                    res, p, skip = run8(op, a, rv, cy, psw)
                    asm = ['%s a,%s' % (op, r.lower())]
                    exp = {}
                    if res is not None:
                        exp['A'] = res
                else:
                    res, p, skip = run8(op, rv, a, cy, psw)
                    asm = ['%s %s,a' % (op, r.lower())]
                    exp = {}
                    if res is not None:
                        exp[r] = res
                    if r == 'A' and res is not None:
                        exp['A'] = res
                exp['PSW'] = p
                exp['SP'] = 0x8000 + (0 if skip else 1)
                emit(op + '_' + form.replace(',', '_'), asm, sets, exp)
    # (rpa) forms and working register forms
    for rpa, (txt, regname, post) in RPA.items():
        a, mv = edge(8), edge(8)
        psw = rnd.choice([0, CY, CY | HC])
        base = 0x2400 + rnd.randrange(0x40)
        res, p, skip = run8(op, a, mv, psw & CY, psw)
        exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1), regname: base + post}
        if res is not None:
            exp['A'] = res
        emit(op + 'x', ['%sx %s' % (op, txt)], {'A': a, 'PSW': psw, regname: base, 'ram:%x' % base: mv}, exp)
    a, mv = edge(8), edge(8)
    psw = rnd.choice([0, CY, CY | HC])
    res, p, skip = run8(op, a, mv, psw & CY, psw)
    exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1)}
    if res is not None:
        exp['A'] = res
    emit(op + 'w', ['%sw 5ah' % op], {'A': a, 'PSW': psw, 'V': 0x26, 'ram:265a': mv}, exp)
    # immediates
    for rep in range(3):
        for r in REGS + ['A']:
            a, imm = edge(8), edge(8)
            psw = rnd.choice([0, CY, HC, CY | HC | Z])
            res, p, skip = run8(op, a, imm, psw & CY, psw)
            exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1)}
            if res is not None:
                exp[r] = res
            emit(IMM[op] + '_' + r, ['%s %s,%d' % (IMM[op], r.lower(), imm)], {r: a, 'PSW': psw}, exp)
    for port, reg in PORTS.items():
        a, imm = edge(8), edge(8)
        psw = rnd.choice([0, CY, CY | HC])
        res, p, skip = run8(op, a, imm, psw & CY, psw)
        exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1)}
        if res is not None:
            exp[reg] = res
        emit(IMM[op] + '_' + port, ['%s %s,%d' % (IMM[op], port, imm)], {reg: a, 'PSW': psw}, exp)

# working register immediates: ANIW ORIW GTIW LTIW NEIW EQIW ONIW OFFIW
for op, mn in (('ana', 'aniw'), ('ora', 'oriw'), ('gta', 'gtiw'), ('lta', 'ltiw'), ('nea', 'neiw'),
               ('eqa', 'eqiw'), ('ona', 'oniw'), ('offa', 'offiw')):
    for rep in range(4):
        mv, imm = edge(8), edge(8)
        psw = rnd.choice([0, CY, CY | HC])
        res, p, skip = run8(op, mv, imm, 0, psw)
        exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1)}
        if res is not None:
            exp['ram:2744'] = res
        emit(mn, ['%s 44h,%d' % (mn, imm)], {'V': 0x27, 'ram:2744': mv, 'PSW': psw}, exp)

# 16-bit: EA with rp3
def run16(op, a, b, cy, psw_in):
    base = {'dadd': 'add', 'dadc': 'adc', 'daddnc': 'addnc', 'dsub': 'sub', 'dsbb': 'sbb', 'dsubnb': 'subnb',
            'dan': 'ana', 'dor': 'ora', 'dxr': 'xra', 'dgt': 'gta', 'dlt': 'lta', 'dne': 'nea', 'deq': 'eqa',
            'don': 'ona', 'doff': 'offa'}[op]
    r, f, skip = alu(base, a, b, cy, 16)
    return r, psw_after(psw_in, f), skip

for op in ('dadd', 'dadc', 'daddnc', 'dsub', 'dsbb', 'dsubnb', 'dan', 'dor', 'dxr', 'dgt', 'dlt', 'dne', 'deq', 'don', 'doff'):
    for rp, name in (('b', 'BC'), ('d', 'DE'), ('h', 'HL')):
        for rep in range(5):
            a, b = edge(16), edge(16)
            if rep == 4:
                b = a
            psw = rnd.choice([0, CY, CY | HC, Z])
            res, p, skip = run16(op, a, b, psw & CY, psw)
            exp = {'PSW': p, 'SP': 0x8000 + (0 if skip else 1)}
            if res is not None:
                exp['EA'] = res
            emit(op, ['%s ea,%s' % (op, rp)], {'EA': a, name: b, 'PSW': psw}, exp)
for op, base in (('eadd', 'add'), ('esub', 'sub')):
    for r in 'abc':
        for rep in range(4):
            a, b = edge(16), edge(8)
            psw = rnd.choice([0, CY, Z])
            res, f, skip = alu(base, a, b, 0, 16)
            exp = {'EA': res, 'PSW': psw_after(psw, f), 'SP': 0x8001}
            emit(op, ['%s ea,%s' % (op, r)], {'EA': a, r.upper(): b, 'PSW': psw}, exp)

# inr / dcr / mul / div / shifts / daa
for rep in range(5):
    for r in 'abc':
        v = edge(8)
        psw = rnd.choice([0, CY, CY | HC | Z])
        res = (v + 1) & 255
        f = {'Z': Z if res == 0 else 0, 'HC': HC if (v & 15) == 15 else 0}
        emit('inr', ['inr %s' % r], {r.upper(): v, 'PSW': psw},
             {r.upper(): res, 'PSW': psw_after(psw, f), 'SP': 0x8000 + (0 if v == 255 else 1)})
        res = (v - 1) & 255
        f = {'Z': Z if res == 0 else 0, 'HC': HC if (v & 15) == 0 else 0}
        emit('dcr', ['dcr %s' % r], {r.upper(): v, 'PSW': psw},
             {r.upper(): res, 'PSW': psw_after(psw, f), 'SP': 0x8000 + (0 if v == 0 else 1)})
        a = edge(8)
        emit('mul', ['mul %s' % r], {'A': a, r.upper(): v} if r != 'a' else {'A': a},
             {'EA': (a * (a if r == 'a' else v)) & 0xffff})
        d = rnd.randrange(1, 256)
        ea = edge(16)
        if r == 'a':
            sets = {'EA': ea, 'A': d}
        else:
            sets = {'EA': ea, r.upper(): d}
        emit('div', ['div %s' % r], sets, {'EA': ea // d, r.upper(): ea % d})
        # rotates and shifts (CY only; Z, HC unchanged)
        psw = rnd.choice([0, CY, Z | HC, CY | Z | HC])
        cy = psw & CY
        for mn, fn in (('sll', lambda x, c: ((x << 1) & 255, x >> 7)), ('slr', lambda x, c: (x >> 1, x & 1)),
                       ('rll', lambda x, c: (((x << 1) | c) & 255, x >> 7)), ('rlr', lambda x, c: ((x >> 1) | (c << 7), x & 1)),
                       ('sllc', lambda x, c: ((x << 1) & 255, x >> 7)), ('slrc', lambda x, c: (x >> 1, x & 1))):
            res, ncy = fn(v, cy)
            exp = {r.upper(): res, 'PSW': (psw & ~CY) | ncy}
            if mn in ('sllc', 'slrc'):
                exp['SP'] = 0x8000 + (0 if ncy else 1)
                emit(mn, ['%s %s' % (mn, r)], {r.upper(): v, 'PSW': psw}, exp)
            else:
                exp['SP'] = 0x8001
                emit(mn, ['%s %s' % (mn, r)], {r.upper(): v, 'PSW': psw}, exp)
for rep in range(12):
    ea = edge(16)
    psw = rnd.choice([0, CY, Z | HC, CY | Z | HC])
    cy = psw & CY
    for mn, fn in (('dsll', lambda x, c: ((x << 1) & 0xffff, x >> 15)), ('dslr', lambda x, c: (x >> 1, x & 1)),
                   ('drll', lambda x, c: (((x << 1) | c) & 0xffff, x >> 15)), ('drlr', lambda x, c: ((x >> 1) | (c << 15), x & 1))):
        res, ncy = fn(ea, cy)
        emit(mn, ['%s ea' % mn], {'EA': ea, 'PSW': psw}, {'EA': res, 'PSW': (psw & ~CY) | ncy, 'SP': 0x8001})
# decimal adjust: all 256 values of A with every flag combination
for a in range(256):
    for hc, cy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        if rnd.random() > 0.35:
            continue
        lo, hi = a & 15, a >> 4
        # manual 14.6.10 table
        if lo <= 9 and hc == 0:
            adj = 0 if (hi <= 9 and cy == 0) else 0x60
        elif lo >= 10 and hc == 0:
            adj = 0x06 if (hi < 9 and cy == 0) else 0x66
        else:
            adj = 0x06 if (hi <= 9 and cy == 0) else 0x66
        r = (a + adj) & 255
        ncy = 1 if adj >= 0x60 else 0
        nhc = 1 if lo + (adj & 15) > 15 else 0
        psw = (HC if hc else 0) | (CY if cy else 0)
        emit('daa', ['daa'], {'A': a, 'PSW': psw},
             {'A': r, 'PSW': (Z if r == 0 else 0) | (HC if nhc else 0) | (CY if ncy else 0), 'SP': 0x8001})
sys.stdout.write('\n'.join(out) + '\n')
