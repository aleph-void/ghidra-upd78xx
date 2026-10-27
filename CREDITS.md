# Credits

## Upstream

* **Source:** NationalSecurityAgency/ghidra pull request
  [#7930](https://github.com/NationalSecurityAgency/ghidra/pull/7930) "Add support for NEC uPD78
  series processors", head commit `5b96b28ac60591b8fcbf26c86ac7bbc9f44a96db` (open at the time of
  import). The files under `Ghidra/Processors/upd78/` were committed unchanged as the first commit
  of this repository's history.
* **License:** Apache-2.0 (Ghidra contribution terms); the license text is in [LICENSE](LICENSE).
  Ghidra-Rare's additions and modifications are under the same license.
* **Original authors**
  * **Vesa-Pekka Palmu** ([@depili](https://github.com/depili), `vpalmu@depili.fi`): wrote the
    first uPD78 module, pull request
    [#1509](https://github.com/NationalSecurityAgency/ghidra/pull/1509) (closed in favour of
    #7930). Author of the first commit of #7930 ("Add support for NEC uPD78 microcontrollers").
  * **Anthony** ([@ajxs](https://github.com/ajxs), `ajxs@panoptic.online`): took the module over,
    fixed the opcode encodings (LTI, OFFI sr2, LDEAX, ONI), the carry/half-carry macros, DRLL/DRLR,
    CALT and the skip handling, and opened #7930 (20 further commits).
  * Review comments on both pull requests by **GhidorahRex** shaped the skip/`RETS` handling and the
    macros.
* The 21 commits of #7930 (author, subject) are the history that precedes ours:
  a017fe6 Vesa-Pekka Palmu "Add support for NEC uPD78 microcontrollers"; ba43651, 81865ed, 41d7a65,
  c70b7c5, 6228cf0, 3540f95, f452263, c939e5e, 6e5a244, 216ddec, 2486866, addd045, 3ff6564, 476be51,
  b9d7b20, 71b497e, d5e8c68, dbb5ff0, ce6fba8, 5b96b28 by Anthony (see the pull request).
* #1509 (`fe3783f4ecf9081dbf03b2f03804ec16164c9783`) is the same SLEIGH as the first commit of #7930
  apart from field naming; #7930 was used as the base because it contains the later fixes.

## Ghidra-Rare changes

All changes are commits on branch `ghidra-rare` on top of the unchanged pull request.

1. **Decode fixes** (found against MAME `unidasm -arch upd7810` and the AS assembler):
   `MOV sr,A` / `MOV A,sr1` use the real special-register lists (RXB read-only, TXB write-only,
   ZCM, CR0-CR3 read-only with exact patterns); `sr2` immediates no longer include SML and ETMM
   and `OFFI sr2h` exists; `ANAX` was at 70 80 instead of 70 88; `LDEAX`/`STEAX (HL+EA)` used the
   code of `(HL+byte)`; `SKIT`/`SKNIT` accept the SB flag; `SBBW` and `DSBB` were spelled
   `SSBW`/`DSSB`; `EADD`/`ESUB` no longer accept `r2 = V`.
2. **Semantics**: flag macros rewritten after Table 3-2 of the manual (logical operations change only
   Z, ONA/OFFA change Z and SK, INR/DCR leave CY, `GTA` family computes a-b-1 exactly, real 16-bit
   carry for `DADC`/`DSBB`); `MUL` (A x r2), `DIV` (remainder in r2), `DAA` (manual 14.6.10 table
   instead of a pcodeop), `ORI r,byte`, `TABLE`, `BIT`, `SKIT`/`SKNIT` flag reset, `SOFTI`;
   stacking flags `L0`/`L1` and the stacked `MVI A` / `MVI L` / `LXI H` rule (manual 14.7).
3. **Structure**: instruction constructors moved into a sub-table so that one wrapper clears
   the stacking flags; the status flags became individual registers (`CY Z HC SK L0 L1`), the
   status byte exists only on the stack (`SOFTI` / `RETI`).
4. **Spec files**: `cspec` `extrapop`/`stackshift` corrected to +2 (the call pushes the return
   address in p-code), `strategy="register"`; `pspec` tracks `SK`/`L0`/`L1` = 0 at function entry
   and marks the interrupt vectors as entry points; `ldefs` description.
5. **Analyzers** (`src/main/java/upd78`): CALT table calls; skip-return calls.
6. **Ghidra-Rare notes, credits and tests**: `GHIDRA-RARE.md`, `README.md` (the pull requests had
   none), `CREDITS.md`, `LICENSE`, `build.gradle`, `extension.properties`, `.gitignore` and `test/`.

## Sources used for the verification

* *uPD78C18 / 78C14 / 78C12 / 78C11 / 78C10 User's Manual* (NEC; "87AD series", the copy that was
  attached to pull request #1509): read for the instruction descriptions, the flag table and the
  stacking rule. It is not part of this repository.
* MAME `unidasm -arch upd7810` and the AS macro assembler (`asl`, `cpu 78C10`), used only as
  black-box programs; no source code of either was read.
* DiKon (<https://github.com/TheRND2/dikon>, MIT, RND2 Labs / TheRND2): a PCL3 raster interpreter
  written in uPD78C10 assembly; its 1,833-byte code image is rebuilt from the project's own builder
  by `test/real/fetch-samples.sh` (pinned commit and SHA-256) and is never committed.
