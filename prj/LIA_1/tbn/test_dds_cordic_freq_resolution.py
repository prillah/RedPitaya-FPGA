# /tbn/test_dds_cordic_freq_resolution.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import numpy as np
import matplotlib.pyplot as plt


# setup parameters for cordic module as well as some for python simulation
N_STAGES    = 16
OUT_WIDTH   = 14
LATENCY     = N_STAGES + 1  # cycles needed from phase input to valid output

async def reset_dut(dut):   # coroutine to reset the DUT in every test
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.reset.value = 0

@cocotb.test()
async def test_frequency_resolution(dut):
    """
    Test if really get Delta_f = f_clk/phase_width frequency resolution.
    We specifically consider ftw = 1 which is the lowest frequency possible that is not DC
    This means it takes the most clk cycles to reach one period, i.e. most accumulations of errors.
    We will check if we get the exact starting value after 2**Phase_width cycles.
    This does not check if neighbouring frequencies are destinguishable.
    """

    small_phase_width = int(dut.PHASE_WIDTH.value)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    dut.ftw.value = 1
    expected_period_cycles = 2 ** small_phase_width # how many clk cycles needed to theoretically complete one period

    for _ in range(LATENCY):
        await RisingEdge(dut.clk)

    start_val = dut.sin_o.value.signed_integer
    measured_period = 0

    for cycle in range(1, expected_period_cycles+5):
        await RisingEdge(dut.clk)
        if dut.sin_o.value.signed_integer == start_val and cycle>1:
            measured_period = cycle
            break

    assert measured_period!=0, "did not observe the accumulator wrapping back around"

    assert measured_period == expected_period_cycles, (
        f"measured period {measured_period} cycles, "
        f"expected {expected_period_cycles} (= 2**PHASE_WIDTH / ftw)")
    
    dut._log.info(f"Confirmed: period = {measured_period} cycles = 2**{small_phase_width}, "
                  f"matching Delta_f = f_clk/2**{small_phase_width}.")

