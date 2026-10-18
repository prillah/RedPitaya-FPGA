# tbn/test_amp_scale.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import numpy as np

# Set up parameters for the test of the amp_scale.sv module
DATA_WIDTH = 14
GAIN_WIDTH = 16
LATENCY    = 2                                  # clock cycles from inputs to output
DIN_MIN    = -2 ** (DATA_WIDTH - 1)             # -8192
DIN_MAX    =  2 ** (DATA_WIDTH - 1) - 1         #  8191
GAIN_MAX   =  2 ** GAIN_WIDTH - 1               # 65535
DIN_MASK   =  2 ** DATA_WIDTH - 1


def model(din, gain):
    """exact reference to bit precision. round half up, arithmetic shift (Python's >> floorsjust like >>> does in SV)."""
    return (din * gain + (1 << (GAIN_WIDTH - 1))) >> GAIN_WIDTH


async def start(dut):
    """Start up sequence of ampl scaler -> reset to 0 and wait for product and dout registers to reset too"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.din.value = 0
    dut.gain.value = 0
    for _ in range(LATENCY + 1):                # wait for product and dout registers to reset too
        await RisingEdge(dut.clk)

async def run_stream(dut, dins, gains):
    """Feed a din & gain pair into DUT every clk cycle. return the outputs accounting for the latency delay"""
    n = len(dins)
    outs = []
    for k in range(n + LATENCY - 1):
        if k<n:
            dut.din.value = int(dins[k]) & DIN_MASK     # need the mask since din can be negative
            dut.gain.value = int(gains[k])              # here mask is not needed since gain is never negative
        await RisingEdge(dut.clk)   # wait
        await Timer(1, unit="ns")
        if k >= LATENCY - 1:
            outs.append(dut.dout.value.to_signed()) # append output after latetncy wait to have the corresponding input output pairs
    return outs

@cocotb.test()
async def test_latency(dut):
    """Check that output follows the inputs after exactly LATENCY clk cycles"""
    await start(dut)    # flush system with 0
    dut.din.value = 1000
    dut.gain.value = GAIN_MAX
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.dout.value.to_signed() == 0, "output changed after 1 cycle"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.dout.value.to_signed() == 1000, "output not valid after 2 cycles"

@cocotb.test()
async def test_gain_zero(dut):
    """If gain is 0 the output should stay silent"""
    await start(dut)
    dins = list(range(DIN_MIN, DIN_MAX + 1))
    outs = await run_stream(dut, dins, [0] * len(dins))
    assert all(o == 0 for o in outs), "gain 0 must give 0"  # all() returns True if every element in an iterable is truthy, and False if any element is falsy.

@cocotb.test()
async def test_gain_half(dut):
    """Check if gain 0x8000 halves the inputs"""
    await start(dut)
    dins = list(range(DIN_MIN, DIN_MAX + 1))
    outs = await run_stream(dut, dins, [0x8000] * len(dins)) 
    for d, o in zip(dins, outs):
        assert o == model(d, 0x8000), f"din={d}: got {o}, model {model(d, 0x8000)}"
        assert abs(o - d / 2) <= 0.5, f"din={d}: {o} is not within 0.5 of {d / 2}"

@cocotb.test()
async def test_gain_full(dut):
    """Check if gain 0xFFFF returns input non changed"""
    await start(dut)
    dins = list(range(DIN_MIN, DIN_MAX + 1))
    outs = await run_stream(dut, dins, [GAIN_MAX] * len(dins))
    bad = [(d, o) for d, o in zip(dins, outs) if d != o]
    assert not bad, f"gain 0xFFFF changed {len(bad)} values, first: {bad[0]}"

@cocotb.test()
async def test_extremes_no_wrap(dut):
    """Check if extreme inputs and gains match the model (do not get wrap-around in the 30-bit product)"""
    await start(dut)
    pairs = [(d, g) for d in (DIN_MIN, DIN_MAX) for g in (0, 1, 0x8000, GAIN_MAX)]
    dins, gains = zip(*pairs)
    outs = await run_stream(dut, dins, gains)
    for (d, g), o in zip(pairs, outs):
        assert o == model(d, g), f"din={d}, gain={g}: got {o}, model {model(d, g)}"

@cocotb.test()
async def test_gain_sweep(dut):
    """Check every gain value at full-scale input"""
    await start(dut)
    gains = list(range(GAIN_MAX + 1))
    outs = await run_stream(dut, [DIN_MAX] * len(gains), gains)
    for g, o in zip(gains, outs):
        assert o == model(DIN_MAX, g), f"gain={g}: got {o}, expected {model(DIN_MAX, g)}"




























