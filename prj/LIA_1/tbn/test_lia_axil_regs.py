# tbn/test_lia_axil_regs.py
#
# cocotb testbench for the AXI4-Lite register slave (adapted from the Vivado template).
#   0x00  FTW  32-bit, read/write        -> ftw_o
#   0x04  AMP  16-bit, read/write        -> amp_o
#   0x08, 0x0C: read as 0, writes ignored
#
# Timing convention used everywhere in this file:
#   - The DUT's ffs update on the rising edge.
#   - The tbn changes inputs on the falling edge, half a period away from any
#     ff update, so never a race between "TB writes" and "DUT samples".
#   - After driving, wait for ReadOnly -> the simulator has then settled every combinational
#     path (e.g. WREADY depends combinationally on AWVALID...). nothing changes between this point
#     and the next rising edge -> what read here is exactly what ffs will see.
#   -> i.e. when VALID and READY both 1 in snapshot == handshake happens next rising edge

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly

###########################################
### Parameters                          ###
###########################################


CLK_PERIOD_NS = 10
FTW, AMP = 0x0, 0x4                      # register offsets (in bytes)
UNUSED = (0x8, 0xC)
OKAY = 0b00                              # BRESP/RRESP code for "all good"
TIMEOUT = 50                             # cycles before declare the peripheral hung

IDLE_INPUTS = dict(S_AXI_AWVALID=0, S_AXI_AWADDR=0, S_AXI_AWPROT=0,
                   S_AXI_WVALID=0, S_AXI_WDATA=0, S_AXI_WSTRB=0,
                   S_AXI_BREADY=0,
                   S_AXI_ARVALID=0, S_AXI_ARADDR=0, S_AXI_ARPROT=0,
                   S_AXI_RREADY=0)

# Outputs of the slave we look at every cycle (short name -> port name)
OUTPUTS = dict(AWREADY="S_AXI_AWREADY", WREADY="S_AXI_WREADY",
               BVALID="S_AXI_BVALID", BRESP="S_AXI_BRESP",
               ARREADY="S_AXI_ARREADY", RVALID="S_AXI_RVALID",
               RDATA="S_AXI_RDATA", RRESP="S_AXI_RRESP",
               ftw="ftw_o", amp="amp_o")

###########################################
### Helper Functions                    ###
###########################################

def start_clock(dut):
    cocotb.start_soon(Clock(dut.S_AXI_ACLK, CLK_PERIOD_NS, unit="ns").start())

def to_int(value):
    """Signal value -> int or None"""
    try:
        return int(value)
    except ValueError:
        return None

async def cycle(dut, drive, reset=False):
    """Advances one clock period.

    drive: dict {port name: value} for this cycle. each input not mentioned goes back to its
           idle value -> each call is a complete description of masters pins
    Returns dict snapshot of slave outputs as next rising edge will see """

    await FallingEdge(dut.S_AXI_ACLK)
    dut.S_AXI_ARESETN.value = 0 if reset else 1          # active low reset
    for name, val in {**IDLE_INPUTS, **drive}.items():   # later dict wins -> drive overrides idle
        getattr(dut, name).value = val
    await ReadOnly()    # await ReadOnly() pauses coroutine until the simulator has finished all activity in current time step
    return {short: to_int(getattr(dut, port).value) for short, port in OUTPUTS.items()}

async def reset_dut(dut, n_cycles=5):
    for _ in range(n_cycles):
        await cycle(dut, {}, reset=True)
    await cycle(dut, {})          # slave spends one cycle in state Idle before raising AW/W/ARREADY

###########################################
### Master Side                         ###
###########################################

async def axi_write(dut, addr, data, strb=0xF, aw_delay=0, w_delay=0, b_delay=0):
    """One AXI4-Lite write. The three channels run independently:
       AW (address) starts after aw_delay cycles, W (data+strobes) after w_delay,
       and BREADY is raised after b_delay cycles (b_delay > 0 = master applies backpressure).
       Returns BRESP. Also checks the slave's side of the protocol rules."""
    aw_done = w_done = False
    bvalid_seen = False
    for n in range(TIMEOUT):
        drive = {}
        if not aw_done and n >= aw_delay:
            drive.update(S_AXI_AWVALID=1, S_AXI_AWADDR=addr)
        if not w_done and n >= w_delay:
            drive.update(S_AXI_WVALID=1, S_AXI_WDATA=data, S_AXI_WSTRB=strb)
        if n >= b_delay:
            drive["S_AXI_BREADY"] = 1

        s = await cycle(dut, drive)

        # Response channel first, using the flags from PREVIOUS cycles:
        # a response may only appear after both address and data have been accepted.
        if s["BVALID"]:
            assert aw_done and w_done, f"cycle {n}: BVALID before address and data were both accepted"
            bvalid_seen = True
            if drive.get("S_AXI_BREADY"):
                return s["BRESP"]
        else:
            assert not bvalid_seen, f"cycle {n}: slave dropped BVALID before BREADY handshake"

        if drive.get("S_AXI_AWVALID") and s["AWREADY"]:
            aw_done = True
        if drive.get("S_AXI_WVALID") and s["WREADY"]:
            w_done = True
    raise AssertionError(f"write to 0x{addr:X} timed out (aw_done={aw_done}, w_done={w_done})")







