# Ghidra-Rare notes: NEC uPD78C1x (UPD78XX)

Verification of the community module from Ghidra pull request #7930 (ajxs, continuing depili's #1509)
to the Ghidra-Rare bar. Credits and the list of changes: [CREDITS.md](CREDITS.md). Language
`upd78:LE:16:default` (the upstream ID, unchanged). Built for Ghidra 12.1.3, 12.1.4 and 12.2.

## Results

| Area | Result |
|---|---|
| Decode vs MAME | `unidasm -arch upd7810`: every (byte 0, byte 1) pair with three tails (196,608 slots) and 200,000 random words. 0 unexplained. Slots: 153,951 + 160,022 spelled identically (after the register-name / hex-format mapping in `test/explain_mame.py`), 36,777 + 33,832 identical once numbers are compared as values, 5,868 + 6,139 invalid on both sides, 12 + 7 explained (below). |
| Decode vs AS | All 2,607 operand combinations of the 213 instruction forms in the manual's notation (chapter 14) assembled by `asl -cpu 78C10` decode to the same text; no decoded form lies outside those forms. |
| Constructors | 317/317 reached (`test/every-entry.sh`; this catches shadowed patterns that "both invalid" results hide). |
| Semantics | 2,616 emulator cases, all passing: 132 hand-computed (manual examples included: DAA 88h+79h, RLD/RRD, SOFTI/RETI frame, RETS skip, stacked MVI/LXI), 2,404 randomised operand cases whose results come from an independent model of the manual's instruction descriptions and flag table, 80 whole programs (sum, bubble sort, multiply, packed-BCD add, strcmp, CRC-8, popcount, table lookup + BLOCK) checked against Python references. A deliberately wrong expectation is detected. The original upstream spec fails 23 of the 132 hand cases and about 500 of the 2,404 model cases. |
| Real code | DiKon (MIT, hand-written uPD78C10 assembly, 1,833 bytes): 682 instructions, all identical to MAME at the same addresses, 14 functions, 0 decompile failures, 0 bad-instruction bookmarks, all 94 code labels of the author's builder fall on instruction starts. 3 error bookmarks are jumps into the Kodak ROM that the image does not contain. |
| Analyzers | CALT: 3/3 call targets resolved and made functions; skip-return: the call site of a function containing RETS keeps its skip test, the others lose it. |

### How the numbers are produced

`test/run-tests.sh [--real <workdir>]` (needs `GHIDRA_INSTALL_DIR`; MAME `unidasm` and AS `asl`
are optional, each step says when it is skipped).

| Step | Script |
|---|---|
| spec compiles | `sleigh` |
| emulator cases, broken-expectation check | `emu-test.sh`, `emu/cases.src` (hand), `emu/model_cases.py`, `emu/prog_cases.py`; code bytes come from AS, expectations from the manual or a model, never from the module |
| every constructor reached | `every-entry.sh` / `CoverageCheck.java` |
| decode differential | `decode-diff.sh` (`gen_corpus.py`, `ref_slots.py`, `compare.py`, `explain_mame.py`, `asl/`) |
| analyzers | `calt-test.sh` (needs `lib/UPD78XX.jar`: `test/build-jar.sh`, JDK with javac) |
| real code | `real/fetch-samples.sh` (pinned commit + SHA-256), `real-tests.sh`, `RealCheck.java`, `real_compare.py` |

## What was wrong in the pull request

Found by the tests above, all fixed (details in the commit messages):

* decode: `ANAX` at the wrong opcode; `LDEAX`/`STEAX (HL+EA)` using the `(HL+byte)` code;
  `MOV A,sr1`/`MOV sr,A` accepting registers that cannot be read/written (SML, ETMM, TXB, RXB, MM ...)
  and a CR pattern that matched half of the S5..S0 space (so `MOV ZCM,A` decoded as `MOV CR0,A`);
  SML/ETMM accepted in the `sr2` immediates, `OFFI sr2h` missing; no `SB` flag for `SKIT`; `EADD`/`ESUB`
  with V; `SBBW`/`DSBB` misspelled.
* semantics: `ORI r,byte` operated on A; `MUL` multiplied EA instead of A; `DIV` put the remainder in
  A instead of r2; `INR`/`DCR` changed CY; `GTA` family wrong Z/HC at the wrap (A=0, r=FFh) and HC;
  `DADC`/`DSBB` lost carries; `DAA` was a pcodeop; `TABLE` read the wrong address; `BIT`, `SKIT`,
  `SKNIT` (no flag reset); `SOFTI` could be skipped; the call stack pointer adjustment in the cspec
  was `-2` for a stack that grows down with an explicit push (decompiler showed `BADSPACEBASE`).

## Upstream's known limitations (pull request reviews, README: none existed)

| Item | State |
|---|---|
| `L0`/`L1` not modelled, "PSW won't be modelled correctly" (GhidorahRex) | **Fixed**: flags are registers, `L0`/`L1` set/cleared like the hardware and the stacked-instruction rule implemented. |
| Stacked `MVI A` / `MVI L` / `LXI H` (ajxs, manual 14.7) | **Fixed** (dynamic, correct for jumps into the middle of a pair). |
| `RETS` skip: "sets possibleSkip at the address after the RETS" | Already handled in the head by flagging the instruction after each call; now **refined**: the skip-return analyzer removes the test where the callee cannot execute RETS. |
| Manual stack manipulation leading to RETS | **Remains**: cannot be seen statically (ajxs' own conclusion). |
| `SOFTI` "should be a pcodeop / software breakpoint" | Settled as a real call to 0060h pushing PSW and the next address, as the manual says; never skipped. |
| 16-bit macros and half-carry | **Fixed**: dedicated 16-bit macros. The manual defines HC only as "carry out of bit 3"; for 16-bit operations bit 3 of the low byte is used (no way to check without hardware). |
| Unused `doPseudo`, `sleighArgs.txt`, the NEC PDF | Already removed in #7930's head. |
| `CALT` is an indirect call | **Fixed** by the CALT analyzer. |
| Interrupt flag reset by `SKIT`/`SKNIT` | **Fixed** (NMI exempt, as the manual says). |

No open or closed issues exist for the processor in NationalSecurityAgency/ghidra; the two pull
requests are the only record. `gh search repos` for uPD78/uPD7810/78C10 finds only two stand-alone
disassemblers (keerden/78C10-disassembler GPL-3, covert-skunkworks/uPD7810_Disassembler) and no
other SLEIGH module.

## Doesn't work

* Interrupts: vectoring, the interrupt-enable state and the stacking of PSW on an interrupt (`EI`,
  `DI` are user ops; `HLT`, `STOP` are user ops): hardware state with no memory-mapped model.
  `RETI` restores SK, but an interrupt between a skip instruction and the skipped one is not
  modelled, so that SK never becomes 1 at a place the static model does not expect.
* Peripherals, timers, serial, A/D; ports are plain registers: the manual says arithmetic on a port
  reads the pins of input bits but the latch of output bits, which a single register cannot show.
* `DIV` by zero: the manual does not define it; the emulator reports the p-code division error.
* `NEGA` leaves the flags alone, as the manual lists no flag effect (hardware may differ).
* Manual stack manipulation that returns with RETS (see above); calling-convention guesses in the
  cspec (A and B as inputs, A or EA as output): there is no compiler for the family to compare.
* Other cores: uPD7800/7801/7802, 78C05/06 and the uPD7807/7808/7809 (extended bit instructions,
  different opcode map, e.g. `BLOCK D+`, `SETB`) are not implemented, nor is the NMOS uPD7810
  (no `STOP`/`ZCM`; everything else is a subset). MAME's disassembler for the 7807 prints
  `illegal` for the bit-operand register names, so it cannot serve as an oracle for them; AS could.
* No ELF/DWARF/loader support: the family has no ELF toolchain; firmware is raw ROM or Intel HEX.

## Unverified

* Behaviour on real silicon (no hardware): flag details the manual leaves open (16-bit HC, NEGA, DAA's
  HC result); every semantic claim is checked against the manual only.
* Only one freely licensed real program was found (DiKon, 1.8 KB). The factory firmware of the
  products that use these chips is not freely licensed and was not used.

## Reference-tool differences (none are confirmed bugs)

* MAME decodes `SK`/`SKN` with F2F1F0 = 001 as `NV` (the overflow flag of the uPD7807 series) and `EADD`/`ESUB`
  with R1R0 = 00 as `EADD EA,V`. The 78C1x manual lists only CY, HC, Z and r2 = A, B, C and AS rejects both;
  these 12 + 7 slots are the only "explained" classes.
* MAME spells `HLT` as `HALT`, writes working-register operands as `VV:xx`, ports as `PA`..`PF`
  and `MVIX BC,x` without parentheses; mapped in `test/explain_mame.py`.
* AS and the manual agree on every one of the 2,607 forms; no AS bug was seen.
