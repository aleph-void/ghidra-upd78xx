#!/usr/bin/env python3
"""Generate an exhaustive assembler source (one line per instruction form and operand combination,
spelled in the NEC notation of the uPD78C1x user's manual, chapter 14) for AS (asl) `cpu 78C10`.
Usage: gen_asm.py > forms.asm      Each line is "<label>: <instruction>" at its own org-less slot;
the listing/bytes are produced with `asl -L` and compared with Ghidra by test/asl/asl_compare.py."""
import itertools, sys

R = 'V A B C D E H L'.split()
R1 = 'EAH EAL B C D E H L'.split()
R2 = 'A B C'.split()
SR = 'PA PB PC PD PF MKH MKL ANM SMH SML EOM ETMM TMM MM MCC MA MB MC MF TXB TM0 TM1 ZCM'.split()
SR1 = 'PA PB PC PD PF MKH MKL ANM SMH EOM TMM RXB CR0 CR1 CR2 CR3'.split()
SR2 = 'PA PB PC PD PF MKH MKL ANM SMH EOM TMM'.split()
SR3 = 'ETM0 ETM1'.split()
SR4 = 'ECNT ECPT'.split()
RP = 'SP B D H'.split()
RP1 = 'V B D H EA'.split()
RP2 = 'SP B D H EA'.split()
RP3 = 'B D H'.split()
RPA = 'B D H D+ H+ D- H-'.split()
RPA1 = 'B D H'.split()
RPA2 = RPA + ['D+{b}', 'H+A', 'H+B', 'H+EA', 'H+{b}']
RPA3 = 'D H D++ H++ D+{b} H+A H+B H+EA H+{b}'.split()
F = 'CY HC Z'.split()
IRF = 'NMI FT0 FT1 F1 F2 FE0 FE1 FEIN FAD FSR FST ER OV AN4 AN5 AN6 AN7 SB'.split()
BYTES = ['0', '1', '55h', '0ffh', '80h']
WA = ['0', '1', '5ah', '0ffh']
WORDS = ['0', '1234h', '0ffffh']
BITS = list(range(8))

BR = {'JR': ['$+10h', '$-10h', '$+2'], 'JRE': ['$+100h', '$-80h', '$+3'], 'CALT': ['80h', '0beh'], 'CALF': ['800h', '0fffh']}
DOM = {'r': R, 'r1': R1, 'r2': R2, 'sr': SR, 'sr1': SR1, 'sr2': SR2, 'sr3': SR3, 'sr4': SR4,
       'rp': RP, 'rp1': RP1, 'rp2': RP2, 'rp3': RP3, 'rpa': RPA, 'rpa1': RPA1, 'rpa2': RPA2,
       'rpa3': RPA3, 'f': F, 'irf': IRF, 'byte': BYTES, 'wa': WA, 'word': WORDS,
       'bit': [str(b) for b in BITS], 'A': ['A'], 'EA': ['EA']}

FORMS = open(__file__.replace('gen_asm.py', 'forms.txt')).read().split('\n')
out = ['\tcpu\t78c10', '\torg\t1000h', 'top:']
n = 0
for line in FORMS:
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    parts = line.split(None, 1)
    mn = parts[0]
    ops = [o.strip() for o in parts[1].split(',')] if len(parts) > 1 else []
    doms = [DOM.get(o, [o]) for o in ops]
    if mn in BR:
        doms = [BR[mn]]
    for combo in itertools.product(*doms):
        combo = [c.replace('{b}', '11h') for c in combo]
        # relative jumps and calls need an in-range target
        out.append('\t%s\t%s' % (mn, ','.join(combo)) if combo else '\t%s' % mn)
        n += 1
print('\n'.join(out))
sys.stderr.write('%d lines\n' % n)
