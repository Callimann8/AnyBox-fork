// Lists every call a program makes to the imports of one DLL, with the
// instructions that set the first four argument registers before each call.
// Run headless: analyzeHeadless <project dir> <name> -import <file>
//   -scriptPath tools/ghidra -postScript ImportCallArgs.java <dll> [output]
// @category AnyBox

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.ExternalLocation;
import ghidra.program.model.symbol.ExternalLocationIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.lang.Register;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ImportCallArgs extends GhidraScript {
    private static final String[] ARGUMENTS = {"RCX", "RDX", "R8", "R9"};
    private static final int LOOKBACK = 24;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            printerr("usage: ImportCallArgs.java <dll name> [output file]");
            return;
        }
        String dll = args[0];
        List<String> lines = new ArrayList<>();
        lines.add("# " + currentProgram.getName() + ": calls into " + dll);
        ExternalLocationIterator externals = currentProgram.getExternalManager().getExternalLocations(findLibrary(dll));
        if (findLibrary(dll) == null) {
            lines.add("no imports from " + dll);
            write(args, lines);
            return;
        }
        while (externals.hasNext()) {
            ExternalLocation external = externals.next();
            String name = external.getLabel();
            Set<Address> sites = callSites(external);
            lines.add("");
            lines.add("## " + name + " (" + sites.size() + " call sites)");
            for (Address site : sites) {
                Instruction call = getInstructionAt(site);
                Function function = getFunctionContaining(site);
                lines.add(site + " in " + (function == null ? "?" : function.getName()) + ": " + call);
                for (Map.Entry<String, String> argument : arguments(call).entrySet()) {
                    lines.add("    " + argument.getKey() + " <- " + argument.getValue());
                }
            }
        }
        write(args, lines);
    }

    private String findLibrary(String dll) {
        for (String library : currentProgram.getExternalManager().getExternalLibraryNames()) {
            if (library.equalsIgnoreCase(dll)) {
                return library;
            }
        }
        return null;
    }

    private Set<Address> callSites(ExternalLocation external) {
        Set<Address> sites = new LinkedHashSet<>();
        Set<Address> pointers = new LinkedHashSet<>();
        Address entry = external.getExternalSpaceAddress();
        for (Reference reference : getReferencesTo(entry)) {
            pointers.add(reference.getFromAddress());
        }
        Function thunked = external.getFunction();
        if (thunked != null) {
            for (Address thunk : thunked.getFunctionThunkAddresses(true) == null ? new Address[0] : thunked.getFunctionThunkAddresses(true)) {
                pointers.add(thunk);
            }
        }
        for (Address pointer : pointers) {
            for (Reference reference : getReferencesTo(pointer)) {
                Instruction instruction = getInstructionAt(reference.getFromAddress());
                if (instruction != null && instruction.getFlowType().isCall()) {
                    sites.add(instruction.getAddress());
                }
                if (instruction != null && instruction.getFlowType().isJump()) {
                    Function thunk = getFunctionContaining(instruction.getAddress());
                    if (thunk != null) {
                        for (Reference caller : getReferencesTo(thunk.getEntryPoint())) {
                            Instruction call = getInstructionAt(caller.getFromAddress());
                            if (call != null && call.getFlowType().isCall()) {
                                sites.add(call.getAddress());
                            }
                        }
                    }
                }
            }
        }
        return sites;
    }

    private Map<String, String> arguments(Instruction call) {
        Map<String, String> found = new LinkedHashMap<>();
        Instruction instruction = call.getPrevious();
        for (int step = 0; step < LOOKBACK && instruction != null && found.size() < ARGUMENTS.length; step++) {
            if (instruction.getFlowType().isCall() || instruction.getFlowType().isTerminal()) {
                break;
            }
            for (Object result : instruction.getResultObjects()) {
                if (!(result instanceof Register register)) {
                    continue;
                }
                String base = register.getBaseRegister().getName();
                for (String argument : ARGUMENTS) {
                    if (base.equals(argument) && !found.containsKey(argument)) {
                        found.put(argument, instruction.getAddress() + "  " + instruction);
                    }
                }
            }
            instruction = instruction.getPrevious();
        }
        Map<String, String> ordered = new LinkedHashMap<>();
        for (String argument : ARGUMENTS) {
            ordered.put(argument, found.getOrDefault(argument, "(not set within " + LOOKBACK + " instructions)"));
        }
        return ordered;
    }

    private void write(String[] args, List<String> lines) throws Exception {
        if (args.length > 1) {
            Files.write(Path.of(args[1]), lines, StandardCharsets.UTF_8);
        }
        for (String line : lines) {
            println(line);
        }
    }
}
