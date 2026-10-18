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
    



























