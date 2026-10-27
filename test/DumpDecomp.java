// Print the decompilation of the function at an address (or of every function when none is given).
// Script args: [hexaddr]   (run after RealCheck-style import/analysis; analysis is run here)
//@category Testing
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

public class DumpDecomp extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		DecompInterface di = new DecompInterface();
		di.openProgram(currentProgram);
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			if (args.length > 0 && f.getEntryPoint().getOffset() != Long.parseLong(args[0], 16)) {
				continue;
			}
			DecompileResults r = di.decompileFunction(f, 60, monitor);
			println("==== " + f.getName() + " @ " + f.getEntryPoint());
			println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "FAILED " + r.getErrorMessage());
		}
	}
}
