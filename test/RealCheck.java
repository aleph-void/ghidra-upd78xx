// Real-code check: seed disassembly at the given label addresses, run the auto-analysis, report
// instruction/function/bookmark counts, decompile every function, and dump the listing.
// Script args: <labels.txt> <out-listing> <out-summary> [data-label ...]
// labels.txt: "<name> <hexaddr>" per line; labels named on the command line are data.
//@category Testing

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.PrintStream;
import java.util.*;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class RealCheck extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		Set<String> data = new HashSet<>(Arrays.asList(args).subList(3, args.length));
		Map<Long, String> labels = new TreeMap<>();
		try (BufferedReader r = new BufferedReader(new FileReader(args[0]))) {
			String l;
			while ((l = r.readLine()) != null) {
				String[] f = l.trim().split("\\s+");
				if (f.length == 2) {
					labels.put(Long.parseLong(f[1], 16), f[0]);
				}
			}
		}
		for (Map.Entry<Long, String> e : labels.entrySet()) {
			Address a = toAddr(e.getKey());
			createLabel(a, e.getValue(), true);
			if (!data.contains(e.getValue())) {
				disassemble(a);
			}
		}
		analyzeAll(currentProgram);
		PrintStream out = new PrintStream(args[1]);
		int n = 0;
		for (Instruction i : currentProgram.getListing().getInstructions(true)) {
			out.printf("%08x %d %s%n", i.getAddress().getOffset(), i.getLength(), i);
			n++;
		}
		out.close();
		int bad = 0, err = 0;
		for (Bookmark b : (Iterable<Bookmark>) () -> currentProgram.getBookmarkManager().getBookmarksIterator()) {
			String t = b.getTypeString();
			if (t.equals("Error")) {
				err++;
				println("error bookmark " + b.getAddress() + ": " + b.getComment());
			}
			if (t.equals("Bad Instruction") || b.getComment().contains("Bad Instruction")) {
				bad++;
			}
		}
		int labelsNotStarts = 0;
		for (Map.Entry<Long, String> e : labels.entrySet()) {
			if (data.contains(e.getValue())) {
				continue;
			}
			Instruction i = currentProgram.getListing().getInstructionAt(toAddr(e.getKey()));
			if (i == null) {
				labelsNotStarts++;
				println("label " + e.getValue() + " is not an instruction start");
			}
		}
		int funcs = 0, fail = 0;
		DecompInterface di = new DecompInterface();
		di.openProgram(currentProgram);
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			funcs++;
			DecompileResults r = di.decompileFunction(f, 60, monitor);
			if (!r.decompileCompleted() || r.getDecompiledFunction() == null) {
				fail++;
				println("decompile failed: " + f.getName() + " " + r.getErrorMessage());
			}
		}
		long gaps = 0;
		long start = currentProgram.getMinAddress().getOffset(), end = currentProgram.getMaxAddress().getOffset();
		for (long a = start; a <= end; a++) {
			if (currentProgram.getListing().getCodeUnitContaining(toAddr(a)) instanceof Data) {
				gaps++;
			}
		}
		PrintStream s = new PrintStream(args[2]);
		s.printf("instructions %d  functions %d  decompile failures %d  bad-instruction bookmarks %d  error bookmarks %d  labels not at an instruction start %d  undefined bytes %d of %d%n",
			n, funcs, fail, bad, err, labelsNotStarts, gaps, end - start + 1);
		s.close();
	}
}
