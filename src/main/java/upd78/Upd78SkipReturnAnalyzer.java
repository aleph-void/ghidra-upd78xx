/* ###
 * IP: Ghidra-Rare contributors (Apache-2.0, as the rest of this module)
 */
package upd78;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.services.AbstractAnalyzer;
import ghidra.app.services.AnalysisPriority;
import ghidra.app.services.AnalyzerType;
import ghidra.app.util.importer.MessageLog;
import ghidra.framework.options.Options;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.Program;
import ghidra.program.model.symbol.FlowType;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.exception.CancelledException;
import ghidra.util.exception.DuplicateNameException;
import ghidra.util.task.TaskMonitor;

/**
 * The uPD78 skip instructions skip the next instruction, and RETS returns to the caller and skips
 * the instruction after the call. The language therefore marks the instruction after every call as
 * "possibly skipped" (context bit possibleSkip), which makes every call site in the decompiler
 * output test the skip flag. Most functions never execute RETS. For each new function that cannot
 * return through RETS (no RETS, no indirect jump and no jump out of its body) this analyzer clears
 * the context bit after every call to it and disassembles that instruction again, so the call
 * sites read like ordinary calls. Functions that contain RETS keep the conservative model.
 */
public class Upd78SkipReturnAnalyzer extends AbstractAnalyzer {
	private static final String NAME = "uPD78 skip-return calls";

	public Upd78SkipReturnAnalyzer() {
		super(NAME, "Removes the skip test after calls to functions that cannot return with RETS",
			AnalyzerType.FUNCTION_ANALYZER);
		setPriority(AnalysisPriority.FUNCTION_ANALYSIS.after());
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

	/** True when a call to the function may come back through RETS (or we cannot tell). */
	static boolean mayReturnSkipping(Program program, Function f) {
		Listing listing = program.getListing();
		AddressSetView body = f.getBody();
		for (Instruction ins : listing.getInstructions(body, true)) {
			String m = ins.getMnemonicString();
			if (m.equals("RETS") || m.equals("JB") || m.equals("JEA")) {
				return true;
			}
			FlowType ft = ins.getFlowType();
			if (ft.isJump()) {
				for (Reference r : ins.getReferencesFrom()) {
					if (r.getReferenceType().isFlow() && !body.contains(r.getToAddress())) {
						return true;
					}
				}
			}
			if (ft.isTerminal() && !m.equals("RET") && !m.equals("RETI") && !ft.isJump()) {
				return true;
			}
		}
		return false;
	}

	@Override
	public boolean added(Program program, AddressSetView set, TaskMonitor monitor, MessageLog log)
			throws CancelledException {
		Register skipReg = program.getRegister("possibleSkip");
		if (skipReg == null) {
			return false;
		}
		Listing listing = program.getListing();
		List<Address> redo = new ArrayList<>();
		for (Function f : program.getFunctionManager().getFunctions(set, true)) {
			monitor.checkCancelled();
			if (f.isExternal() || f.isThunk() || mayReturnSkipping(program, f)) {
				continue;
			}
			ReferenceIterator refs = program.getReferenceManager().getReferencesTo(f.getEntryPoint());
			while (refs.hasNext()) {
				Reference r = refs.next();
				if (!r.getReferenceType().isCall()) {
					continue;
				}
				Instruction call = listing.getInstructionAt(r.getFromAddress());
				if (call == null) {
					continue;
				}
				Address ret = call.getFallThrough();
				if (ret == null) {
					continue;
				}
				BigInteger cur = program.getProgramContext().getValue(skipReg, ret, false);
				if (cur != null && cur.signum() != 0 && listing.getInstructionAt(ret) != null) {
					redo.add(ret);
				}
			}
		}
		for (Address ret : redo) {
			monitor.checkCancelled();
			Instruction ins = listing.getInstructionAt(ret);
			if (ins == null) {
				continue;
			}
			AddressSet one = new AddressSet(ret, ret.add(ins.getLength() - 1));
			try {
				listing.clearCodeUnits(ret, ret.add(ins.getLength() - 1), false);
				program.getProgramContext().setValue(skipReg, ret, ret, BigInteger.ZERO);
				new DisassembleCommand(ret, one, false).applyTo(program, monitor);
			}
			catch (Exception e) {
				log.appendMsg(NAME, "could not redisassemble " + ret + ": " + e.getMessage());
			}
		}
		return !redo.isEmpty();
	}
}
