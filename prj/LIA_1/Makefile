# ============================================================
# cocotb + Verilator Makefile
# ============================================================

# Which simulator to use
SIM ?= verilator

# Verilog/SystemVerilog vs VHDL
TOPLEVEL_LANG ?= verilog

export PYTHONPATH := $(PWD)/tbn:$(PYTHONPATH)

# One or more HDL source files. $(PWD) makes the path absolute.
# For a design spanning multiple files, just add more lines:
#   VERILOG_SOURCES += $(PWD)/hdl/nco.sv
VERILOG_SOURCES += $(PWD)/rtl/cordic_sincos.sv

# The module cocotb attaches its `dut` object to. Must match a module
# name inside your .sv file(s).
COCOTB_TOPLEVEL = cordic_sincos

# The Python file(s) containing your @cocotb.test() functions, without
# the .py extension. Comma-separate for more than one:
# cocotb runs every @cocotb.test() function found across all of them.
COCOTB_TEST_MODULES = test_cordic_sincos

# for a dump.vcd waveform viewable in GTKWave.
EXTRA_ARGS += --trace --trace-structs

# Override parameters for simulation
# EXTRA_ARGS += -GCOUNTER_WIDTH=6 -GLED_BIT=5

sim: atan_table.mem
 
atan_table.mem: scripts/gen_cordic_constants.py
	python3 scripts/gen_cordic_constants.py


# ============================================================
# Fixed machinery - do not edit below this line
# ============================================================
include $(shell cocotb-config --makefiles)/Makefile.sim