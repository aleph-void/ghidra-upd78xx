/* ###
 * IP: Ghidra-Rare contributors (Apache-2.0, as the rest of this module)
 */
package upd78;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.services.AbstractAnalyzer;
import ghidra.app.services.AnalyzerType;
import ghidra.app.util.importer.MessageLog;
import ghidra.framework.options.Options;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Program;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.symbol.RefType;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.SourceType;
import ghidra.util.exception.CancelledException;
import ghidra.util.task.TaskMonitor;

/**
 * Resolves CALT instructions of the uPD78C1x. CALT ta jumps through the 16-bit vector stored at
 * 0080h + 2*ta (the call table, 0080h-00BFh), so the p-code can only express an indirect call.
 * For every CALT whose table entry is in initialised memory this analyzer adds a computed call
 * reference to the vector's target, a data reference to the table entry, disassembles the target
 * and makes it a function.
 */
public class Upd78CaltAnalyzer extends AbstractAnalyzer {
	private static final String NAME = "uPD78 CALT table calls";
	private static final long TABLE = 0x80;

	public Upd78CaltAnalyzer() {
		super(NAME, "Adds the call target of every CALT instruction from the call table at 0080h",
			AnalyzerType.INSTRUCTION_ANALYZER);
		setPriority(ghidra.app.services.AnalysisPriority.DISASSEMBLY.after());
		setSupportsOneTimeAnalysis();
	}

	@Override
	public boolean getDefaultEnablement(Program program) {
		return true;
	}

	@Override
	public boolean canAnalyze(Program program) {
		return program.getLanguage().getProcessor().toString().equals("upd78");
	}

	@Override
	public void registerOptions(Options options, Program program) {
		// no options
	}

	@Override
	public boolean added(Program program, AddressSetView set, TaskMonitor monitor, MessageLog log)
			throws CancelledException {
		AddressSet newCode = new AddressSet();
		for (Instruction ins : program.getListing().getInstructions(set, true)) {
			monitor.checkCancelled();
			if (!ins.getMnemonicString().equals("CALT")) {
				continue;
			}
			try {
				int ta = ins.getByte(0) & 0x1f;
				Address entry = ins.getAddress().getNewAddress(TABLE + 2L * ta);
				if (!program.getMemory().contains(entry) ||
					!program.getMemory().contains(entry.add(1))) {
					continue;
				}
				int target = (program.getMemory().getByte(entry) & 0xff) |
					((program.getMemory().getByte(entry.add(1)) & 0xff) << 8);
				Address dest = entry.getNewAddress(target);
				if (!program.getMemory().contains(dest)) {
					continue;
				}
				boolean have = false;
				for (Reference r : ins.getReferencesFrom()) {
					if (r.getToAddress().equals(dest) && r.getReferenceType().isCall()) {
						have = true;
					}
				}
				if (!have) {
					program.getReferenceManager().addMemoryReference(ins.getAddress(), dest,
						RefType.COMPUTED_CALL, SourceType.ANALYSIS, 0);
				}
				program.getReferenceManager().addMemoryReference(ins.getAddress(), entry,
					RefType.READ, SourceType.ANALYSIS, 0);
				if (program.getListing().getInstructionAt(dest) == null) {
					new DisassembleCommand(dest, null, true).applyTo(program, monitor);
				}
				if (program.getFunctionManager().getFunctionAt(dest) == null &&
					program.getListing().getInstructionAt(dest) != null) {
					new CreateFunctionCmd(dest).applyTo(program, monitor);
				}
				newCode.add(dest);
			}
			catch (MemoryAccessException e) {
				// table not readable: leave the call unresolved
			}
		}
		return !newCode.isEmpty();
	}
}
