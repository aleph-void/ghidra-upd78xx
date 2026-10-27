; CALT / vector test program for the uPD78C10 module (Ghidra-Rare, Apache-2.0).
; Assemble: asl -cpu 78c10 calt_test.asm && p2bin calt_test.p calt_test.bin
	cpu	78c10
	org	0000h
reset:	jmp	start
	org	0004h
nmi:	reti
	org	0060h
softi_v: reti
	org	0080h
calltab: dw	inc_b, dec_c, add_ab, 0	; CALT 80h..86h
	org	0100h
start:	lxi	sp,0f000h
	mvi	b,5
	calt	80h		; inc_b
	calt	82h		; dec_c
	calt	84h		; add_ab (skips the next instruction on carry)
	mvi	d,1
	mvi	e,2
	jmp	done
inc_b:	inr	b
	ret
dec_c:	dcr	c
	ret
add_ab:	addnc	a,b
	rets
	ret
done:	jr	done
