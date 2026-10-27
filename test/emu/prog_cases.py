#!/usr/bin/env python3
"""Write test/emu/prog_cases.src: small whole programs in the idioms of the family (skip-style
loops, auto-increment addressing, BLOCK, decimal adjust, 16-bit shifts) run in the emulator on
random inputs.  The expected memory is computed by a Python reference of each algorithm, never
by the module.  test/emu/cases.py assembles the programs with AS and builds prog_cases.txt."""
import random, sys
rnd = random.Random(7810)
out = []
n = 0
def emit(name, asm, sets, exps):
    global n
    n += 1
    out.append('case %s_%d' % (name, n))
    out.extend(asm.strip('\n').split('\n'))
    out.append('fin:')
    for k, v in sets.items():
        out.append('set %s 0x%x' % (k, v))
    for k, v in exps.items():
        out.append('expect %s 0x%x' % (k, v))
    out.append('end fin')
    out.append('done')

def mem(base, data):
    return {'ram:%x' % (base + i): b for i, b in enumerate(data)}

# 1. sum of 16 bytes (addx h+, dcr/jr skip loop)
SUM = '''
	lxi	h,2000h
	mvi	c,15
	xra	a,a
loop:	addx	h+
	dcr	c
	jr	loop
	mov	2100h,a
'''
for _ in range(8):
    d = [rnd.randrange(256) for _ in range(16)]
    s = dict(mem(0x2000, d))
    emit('sum16', SUM, s, {'ram:2100': sum(d) & 255})

# 2. bubble sort of 8 bytes
BUBBLE = '''
	mvi	b,7
outer:	lxi	h,2000h
	mvi	c,6
inner:	ldax	h+
	mov	e,a
	ldax	h
	lta	a,e
	jr	noswap
	mov	d,a
	mov	a,e
	stax	h-
	mov	a,d
	stax	h+
noswap:	dcr	c
	jr	inner
	dcr	b
	jre	outer
'''
for _ in range(10):
    d = [rnd.choice([0, 255, rnd.randrange(256), rnd.randrange(16)]) for _ in range(8)]
    emit('bubble8', BUBBLE, mem(0x2000, d), mem(0x2000, sorted(d)))

# 3. 8x8 -> 16 multiply by repeated addition (dadd ea,rp3), result stored with steax
MULT = '''
	mov	b,2000h
	lxi	d,0
	mov	e,2001h
	lxi	h,0
	dmov	ea,h
	mov	a,b
	nei	a,0
	jr	store
	sui	a,1
	mov	b,a
loop:	dadd	ea,d
	dcr	b
	jr	loop
store:	lxi	h,2002h
	steax	h
'''
for _ in range(10):
    x, y = rnd.choice([0, 1, 255, rnd.randrange(256)]), rnd.choice([0, 1, 255, rnd.randrange(256)])
    emit('mult', MULT, {'ram:2000': x, 'ram:2001': y}, {'ram:2002/2': x * y})

# 4. packed BCD addition of two 4-byte numbers (adcx, daa), carry out in 2024h
BCD = '''
	lxi	h,2000h
	lxi	d,2010h
	lxi	b,2020h
	mvi	v,30h
	mviw	0,3
	clc
loop:	ldax	h+
	adcx	d+
	daa
	stax	b
	inx	b
	dcrw	0
	jr	loop
	xra	a,a
	adc	a,a
	mov	2024h,a
'''
def bcd(v):  # 8 packed digits little endian bytes
    return [((v // 10 ** (2 * i + 1)) % 10) << 4 | (v // 10 ** (2 * i)) % 10 for i in range(4)]
for _ in range(12):
    a, b = rnd.randrange(10 ** 8), rnd.randrange(10 ** 8)
    if _ == 0: a, b = 99999999, 1
    if _ == 1: a, b = 0, 0
    s = a + b
    sets = dict(mem(0x2000, bcd(a)))
    sets.update(mem(0x2010, bcd(b)))
    exp = mem(0x2020, bcd(s % 10 ** 8))
    exp['ram:2024'] = s // 10 ** 8
    emit('bcd8', BCD, sets, exp)

# 5. string compare: index of the first difference (or of the common terminator) in C
STRCMP = '''
	lxi	h,2000h
	lxi	d,2040h
	mvi	c,0
cmp:	ldax	h+
	neax	d+
	jr	same
	jre	fin
same:	eqi	a,0
	jr	cont
	jre	fin
cont:	inr	c
	jr	cmp
'''
for _ in range(12):
    L = rnd.randrange(1, 30)
    s1 = [rnd.randrange(1, 256) for _ in range(L)] + [0]
    s2 = list(s1)
    if rnd.random() < 0.8:
        k = rnd.randrange(L)
        s2[k] = rnd.choice([x for x in range(1, 256) if x != s1[k]])
    idx = next((i for i in range(L + 1) if s1[i] != s2[i]), L)
    sets = dict(mem(0x2000, s1))
    sets.update(mem(0x2040, s2))
    emit('strcmp', STRCMP, sets, {'C': idx})

# 6. CRC-8 (polynomial 07h) over 16 bytes, shift / carry / skip idiom
CRC = '''
	lxi	h,2000h
	mvi	d,0
	mvi	b,15
bytel:	ldax	h+
	xra	a,d
	mvi	c,7
bitl:	sll	a
	skn	cy
	xri	a,7
	dcr	c
	jr	bitl
	mov	d,a
	dcr	b
	jr	bytel
	mov	2100h,d
'''
def crc8(data):
    c = 0
    for byte in data:
        c ^= byte
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 255 if c & 0x80 else (c << 1) & 255
    return c
for _ in range(10):
    d = [rnd.randrange(256) for _ in range(16)]
    emit('crc8', CRC, mem(0x2000, d), {'ram:2100': crc8(d)})

# 7. population count of a 16-bit word with dslr ea and the carry flag
POP = '''
	lded	2000h
	dmov	ea,d
	mvi	c,0
	mvi	b,15
loop:	dslr	ea
	skn	cy
	inr	c
	dcr	b
	jr	loop
	mov	2100h,c
'''
for _ in range(10):
    w = rnd.choice([0, 0xffff, 1, 0x8000, rnd.randrange(65536), rnd.randrange(65536)])
    emit('popcount16', POP, {'ram:2000/2': w}, {'ram:2100': bin(w).count('1')})

# 8. word table lookup with EA, (HL+A) addressing; and block copy
TBL = '''
	lxi	h,2000h
	mov	a,2100h
	ldeax	h+a
	lxi	h,2102h
	steax	h
	lxi	h,2000h
	lxi	d,2200h
	mvi	c,31
	block
'''
for _ in range(8):
    tbl = [rnd.randrange(65536) for _ in range(16)]
    i = rnd.randrange(16)
    sets = {'ram:%x/2' % (0x2000 + 2 * k): v for k, v in enumerate(tbl)}
    sets['ram:2100'] = 2 * i
    exp = {'ram:2102/2': tbl[i]}
    for k in range(32):
        exp['ram:%x' % (0x2200 + k)] = (tbl[k // 2] >> (8 * (k % 2))) & 255
    emit('table_block', TBL, sets, exp)
sys.stdout.write('\n'.join(out) + '\n')
