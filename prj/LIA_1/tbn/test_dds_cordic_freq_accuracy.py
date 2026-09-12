# /tbn/test_dds_cordic_freq_accuracy.py
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
async def test_frequency_accuracy(dut):
    ##################
    # Set specific ftw and then let dds run. Check the final FFT versus the expected frequency.
    # Since CORDIC own precision was already checked, just need to test if the frequency is right.
    ##################

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    n_samples = 1024
    n_cycles = 37  # coherent choice as in cordic test
    ftw = n_cycles * 2**PHASE_WIDTH // n_samples
    dut.ftw.value = ftw

    # Let values propagate through the N stages of the CORDIC algo
    for _ in range(LATENCY):
        await RisingEdge(dut.clk)

    samples = np.empty(n_samples, dtype=np.int64)
    for k in range(n_samples):
        await RisingEdge(dut.clk)
        samples[k] = dut.sin_o.value.signed_integer


    spectrum = np.abs(np.fft.fft(samples))
    peak_bin = np.argmax(spectrum[1:n_samples // 2]) + 1    # need +1 because take spectrum starting from index 1 (new index 0)

    assert peak_bin == n_cycles, (f"FFT peak at bin {peak_bin}, expected {n_cycles}")

    dut._log.info(f"ftw={ftw} correctly produced a tone at bin {peak_bin}/{n_samples}.")

"""@cocotb.test()
async def test_frequency_resolution(dut):
"""
































