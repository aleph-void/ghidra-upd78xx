// Checks that the CALT analyzer resolved every CALT and that the skip-return analyzer removed the skip test after calls
// to functions without RETS: a computed-call reference to the vector's
// target, and a function at the target. Run after auto-analysis (headless import without -noanalysis).
// Script args: <outfile>
//@category Testing
import java.io.PrintStream;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

public class CaltCheck extends GhidraScript {
	@Override
	protected void run() throws Exception {
		PrintStream out = new PrintStream(getScriptArgs()[0]);
		int calts = 0, resolved = 0, funcs = 0;
		for (Instruction i : currentProgram.getListing().getInstructions(true)) {
			if (!i.getMnemonicString().equals("CALT")) {
				continue;
			}
			calts++;
			int ta = i.getByte(0) & 0x1f;
			Address entry = toAddr(0x80 + 2 * ta);
			Address dest = toAddr((currentProgram.getMemory().getByte(entry) & 0xff) |
				((currentProgram.getMemory().getByte(entry.add(1)) & 0xff) << 8));
			boolean ref = false;
			for (Reference r : i.getReferencesFrom()) {
				ref |= r.getToAddress().equals(dest) && r.getReferenceType().isCall();
			}
			boolean fn = currentProgram.getFunctionManager().getFunctionAt(dest) != null;
			if (ref) {
				resolved++;
			}
			if (fn) {
				funcs++;
			}
			java.math.BigInteger sk = currentProgram.getProgramContext().getValue(
				currentProgram.getRegister("possibleSkip"), i.getFallThrough(), false);
			out.printf(
				"CALT at %s: table %s -> %s  call reference %b  function %b  skip test after the call %s%n",
				i.getAddress(), entry, dest, ref, fn, sk);
		}
		out.printf("calts %d  resolved %d  with function %d%n", calts, resolved, funcs);
		out.close();
	}
}
