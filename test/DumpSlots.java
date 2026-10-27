// Decode the first instruction of every fixed-size slot of a corpus file with the language's
// default context (optionally overriding context fields), without mapping the file into memory
// (the address space is 64 KB; the corpus is larger). Slot i is decoded at address
// (offset & 0xffff). Prints "<offset-hex> <len> <text>" per slot, "<offset> 0 BAD" when the
// language rejects it.
// Script args: <corpus> <slot> <outfile> [ctxfield=value ...]
//@category Testing

import java.io.PrintStream;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Paths;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.*;
import ghidra.program.model.mem.ByteMemBufferImpl;
import ghidra.program.model.mem.MemBuffer;

public class DumpSlots extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		byte[] data = Files.readAllBytes(Paths.get(args[0]));
		int slot = Integer.decode(args[1]);
		PrintStream out = new PrintStream(args[2]);
		Language lang = currentProgram.getLanguage();
		ProcessorContextImpl ctx = new ProcessorContextImpl(lang);
		Register cr = lang.getContextBaseRegister();
		if (cr != null && cr != Register.NO_CONTEXT) {
			ctx.setRegisterValue(currentProgram.getProgramContext().getDefaultDisassemblyContext());
		}
		for (int i = 3; i < args.length; i++) {
			String[] kv = args[i].split("=");
			ctx.setValue(lang.getRegister(kv[0]), new BigInteger(kv[1]));
		}
		for (int off = 0; off + slot <= data.length; off += slot) {
			Address a = currentProgram.getAddressFactory().getDefaultAddressSpace()
					.getAddress(off & 0xffff);
			byte[] cell = new byte[slot];
			System.arraycopy(data, off, cell, 0, slot);
			String text;
			int n;
			try {
				MemBuffer buf = new ByteMemBufferImpl(a, cell, lang.isBigEndian());
				InstructionPrototype proto = lang.parse(buf, ctx, false);
				PseudoInstruction pi = new PseudoInstruction(currentProgram, a, proto, buf, ctx);
				text = pi.toString();
				n = pi.getLength();
			}
			catch (Exception e) {
				text = "BAD";
				n = 0;
			}
			out.printf("%08x %d %s%n", off, n, text);
		}
		out.close();
	}
}
