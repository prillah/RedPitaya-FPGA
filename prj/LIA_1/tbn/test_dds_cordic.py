# /tbn/test_dds_cordic.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import numpy as np
import matplotlib.pyplot as plt


# setup parameters for cordic module as well as some for python simulation
PHASE_WIDTH = 32
N_STAGES    = 16
OUT_WIDTH   = 14
LATENCY     = N_STAGES + 1  # cycles needed from phase input to valid output

async def reset_dut(dut):   # coroutine to reset the DUT in every test
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.reset.value = 0

@cocotb.test()
async def test_reset(dut):
    """
    Test if set phase_acc to 0 with reset signal
    """

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # instantiate the module with some finite value
    dut.ftw.value = 12345
    dut.reset.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    assert dut.phase_acc.value.integer != 0, "setup issue: phase_acc never advanced/changed"

    await reset_dut(dut)

    assert dut.phase_acc.value.integer == 0, "phase_acc not cleared on reset"
    dut._log.info("phase_acc correctly cleared on reset")

@cocotb.test()
async def test_dds(dut):
    """
    
    """

































