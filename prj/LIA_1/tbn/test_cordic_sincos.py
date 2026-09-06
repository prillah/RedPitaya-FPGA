import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import numpy as np


# setup parameters for cordic module as well as some for python simulation
PHASE_WIDTH = 32
N_STAGES    = 16
OUT_WIDTH   = 14
LATENCY     = N_STAGES + 1  # cycles needed from phase input to valid output

FULL_SCALE = 2 ** (OUT_WIDTH - 1) - 1   # needed to scale output back to [-1,1] range -> divide by largest twos complement number



def deg_to_phase(theta_deg: float) -> int:  # function arg is a float that represents an angle in degrees. Output is a whole integer value
    return round(theta_deg / 360.0 * 2**PHASE_WIDTH) % 2**PHASE_WIDTH   # theta_deg / 360.0 gives us fraction of whole circle.
            # scaling by  2**PHASE_WIDTH since this is total number of states in 32 bits. Also ensures that largest number (2**N - 1) + 1 gets wrapped to start again
            # -> think dividing range into even pieces and since have 2**32 states need to divide by 2**32!!!
            # % 2**PHASE_WIDTH ensures that like in digital system the phase overflows to 0 after largest number!


async def drive_and_read(dut, theta_deg: float):
    """Drives one phase value, waits out the pipeline latency and then reads the result.
    Need async def here, becuase this function should be coroutine, i.e. being able to wait for HDL simulator feedback before continuing sequentially."""

    dut.phase.value = deg_to_phase(theta_deg)   # syntax for adressing the phase input value!
    for _ in range(LATENCY):
        await RisingEdge(dut.clk)
    cos_raw = dut.cos_o.value.signed_integer
    sin_raw = dut.sin_o.value.signed_integer
    return cos_raw / FULL_SCALE, sin_raw / FULL_SCALE









