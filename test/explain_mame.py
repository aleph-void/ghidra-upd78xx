"""Maps MAME unidasm (upd7810) text and Ghidra text to one spelling, and explains the
remaining difference classes (confirmed MAME bugs, encodings the manual forbids)."""
import re

SFR = {'PA': 'PORTA', 'PB': 'PORTB', 'PC': 'PORTC', 'PD': 'PORTD', 'PF': 'PORTF'}

def canon(t, side):
    t = t.strip()
    if side == 'ref':
        t = re.sub(r'\$([0-9A-Fa-f]+)', r'0x\1', t)
        t = re.sub(r'VV:([0-9A-Fa-f]{2})', r'(V+0x\1)', t)
        m = re.match(r'^(\w+)\s+(.*)$', t)
        if m:
            mn, ops = m.groups()
            parts = ops.split(',')
            if mn.upper() in ('MOV', 'MVI', 'ADI', 'ACI', 'SUI', 'SBI', 'ANI', 'ORI', 'XRI', 'GTI', 'LTI',
                              'NEI', 'EQI', 'ONI', 'OFFI', 'ADINC', 'SUINB'):
                parts = [SFR.get(p, p) for p in parts]
            if mn.upper() in ('SSPD', 'LSPD', 'SBCD', 'LBCD', 'SDED', 'LDED', 'SHLD', 'LHLD'):
                parts[0] = '(' + parts[0] + ')'
            if mn.upper() == 'HALT':
                mn = 'HLT'
            if mn.upper() == 'MVIX':
                parts[0] = '(' + parts[0] + ')'
            if mn.upper() == 'CALT':
                parts[0] = parts[0].strip('()')
            t = mn + ' ' + ','.join(parts)
    if side == 'ref' and t.upper() == 'HALT':
        t = 'HLT'
    return t

def classify(off, rn, rt, gn, gt, data):
    # F2F1F0 = 001 is the overflow flag NV of the uPD7807 series; the uPD78C1x manual lists
    # only CY (010), HC (011) and Z (100) for SK/SKN.
    if gn == 0 and re.match(r'^SKN? NV$', rt):
        return 'SK/SKN NV: uPD7807 overflow flag, not in the 78C1x manual'
    # EADD/ESUB: the manual lists r2 = A, B, C only (R1R0 = 1..3); MAME also decodes R1R0 = 0 as V,
    # and AS rejects it.
    if gn == 0 and re.match(r'^(EADD|ESUB) EA,V$', rt):
        return 'EADD/ESUB EA,V: R1R0 = 00 is not in the manual (AS rejects it)'
    return None
