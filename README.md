# NEC uPD78C1x (uCOM-87AD) processor module for Ghidra

SLEIGH processor module for the NEC **uPD78C10** family of 8-bit microcontrollers (uCOM-87AD
series: uPD78C10, 78C11, 78C12, 78C14, 78C17, 78C18 and the PROM/ROM-less variants, which share
one instruction set). It started as Ghidra pull request
[#7930](https://github.com/NationalSecurityAgency/ghidra/pull/7930) by **Anthony (ajxs)**, which
continues pull request [#1509](https://github.com/NationalSecurityAgency/ghidra/pull/1509) by
**Vesa-Pekka Palmu (depili)**; both are credited in [CREDITS.md](CREDITS.md). The instruction
decoder and p-code were then checked against the NEC user's manual, MAME and the AS assembler;
what was found and fixed is in [GHIDRA-RARE.md](GHIDRA-RARE.md).

Ghidra target: **12.1.4** (the release zips also build for 12.1.3 and 12.2). Prebuilt zips are on
this repository's *Releases* page; to build one yourself:

```sh
GHIDRA_INSTALL_DIR=/path/to/ghidra_12.1.4_PUBLIC gradle buildExtension
```

then install the zip from `dist/` with *File > Install Extensions*.

## Language

| Language ID | Description |
|---|---|
| `upd78:LE:16:default` | NEC uPD78C1x, 16-bit address space `ram`, little endian |

The register file is V A B C D E H L (with the pairs VA BC DE HL and the extended accumulator
EA = EAH:EAL), the alternate set VA' BC' DE' HL' EA', SP, PC and the special registers (ports PA-PF
as `PORTA`..`PORTF`, MKH, MKL, ANM, SMH, SML, EOM, ETMM, TMM, MM, MCC, MA, MB, MC, MF, TXB, RXB,
TM0, TM1, ZCM, CR0-CR3, ETM0, ETM1, ECNT, ECPT). `PORTC`/`PORTA` etc. are named that way because
`PC` is the program counter.

Every status flag is a register of its own: `CY`, `Z`, `HC`, `SK` (skip), `L0`, `L1` (stacking
flags). The status byte `0 Z SK HC L1 L0 0 CY` only exists on the stack, where `SOFTI` pushes it
and `RETI` pops it.

### Skip instructions

The family has no conditional branches: many instructions (`GTA`, `EQI`, `ADDNC`, `DCR`, `BIT`,
`SK`, `SKIT`, `SLLC`, ...) set the SK flag and the next instruction is then not executed. The
language models this exactly. The instruction after a skip-capable instruction carries a context
bit (`possibleSkip`) that makes its p-code start with "if SK, skip me", so the decompiler shows a
normal `if`. `RETS` returns and skips the instruction after the call, so the instruction after
every `CALL`/`CALF`/`CALB`/`CALT` carries the same bit. `SOFTI` is never skipped.

### Stacked `MVI A` / `MVI L` / `LXI H`

If two instructions of the same group are placed one after the other (group A: `MVI A,byte`,
group B: `MVI L,byte` and `LXI H,word`), only the first one takes effect (manual section 14.7).
The language implements the `L1`/`L0` flags the way the hardware does: those three instructions
set them, every other instruction clears them, and a stacked instruction does nothing. A jump
straight to the second instruction of a pair therefore executes it.

### Analyzers (`lib/UPD78XX.jar`)

* **uPD78 CALT table calls**: `CALT ta` calls through the vector at 0080h + 2*ta. The analyzer adds
  the computed call reference and the table-entry reference and creates a function at the target.
* **uPD78 skip-return calls**: removes the skip test after calls to functions that cannot return
  through `RETS`, so most call sites read like ordinary calls. Functions that contain `RETS`, an
  indirect jump or a jump out of their body keep the conservative model.

The vectors at 0000h, 0004h ... 0060h (RESET, NMI, INTT0/INTT1, INT1/INT2, INTE0/INTE1,
INTEIN/INTAD, INTSR/INTST, SOFTI) are entry points; 0080h is the CALT table.

## Not supported

* The older/other cores that share the "uPD78" name but not the opcode map: uPD7800/7801/7802,
  uPD78C05/78C06 and the uPD7807/7808/7809 (extended bit instructions) are not implemented, and
  neither is the NMOS uPD7810 (no `STOP`, no `ZCM`; its code is a subset of what is decoded here).
  The 78K/0, 78K/II ... families are different CPUs.
* Interrupt vectoring and the interrupt-enable state (`EI`/`DI` are user ops), `HLT`/`STOP`,
  the peripherals and the difference between port pin and port latch.

The upstream pull requests had no README. Their open review remarks (unmodelled L0/L1 flags,
`RETS`, `SOFTI`, 16-bit half-carry) and how each was settled are listed in
[GHIDRA-RARE.md](GHIDRA-RARE.md).

## Tests

`test/run-tests.sh [--real <workdir>]` runs everything that needs no non-redistributable input
(see [GHIDRA-RARE.md](GHIDRA-RARE.md) for what it checks and the results).
