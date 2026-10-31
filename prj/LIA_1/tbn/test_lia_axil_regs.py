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
    for name, val in {**IDLE_INPUTS, **drive}.items():   # later dict wins -> drive overrides idle ( ** unpacks a dict into the new one, when both contain the same key, the later one wins)
        getattr(dut, name).value = val
    await ReadOnly()    # await ReadOnly() pauses coroutine until the simulator has finished all activity in current time step (let all logic paths settle before reading any values)
    return {short: to_int(getattr(dut, port).value) for short, port in OUTPUTS.items()}

async def reset_dut(dut, n_cycles=5):
    for _ in range(n_cycles):
        await cycle(dut, {}, reset=True)
    await cycle(dut, {})          # slave spends one cycle in state Idle before raising AW/W/ARREADY

###########################################
### Master Side                         ###
###########################################

async def axi_write(dut, addr, data, strb=0xF, aw_delay=0, w_delay=0, b_delay=0):
    """
    one AXI4-Lite write. the three channels run independently:
    -> AW (address) starts after aw_delay cycles
    -> W (data+strobes) after w_delay,
    -> BREADY is raised after b_delay cycles (b_delay > 0 = master applies backpressure)
    Returns BRESP and checks the slaves side of the protocol rules
    """
    aw_done = w_done = False
    bvalid_seen = False
    for n in range(TIMEOUT):    # TIMEOUT is max cycles before declare that the peripheral hangs
        drive = {}  # drive collects the pins that are not idle in this cycle
        if not aw_done and n >= aw_delay:
            drive.update(S_AXI_AWVALID=1, S_AXI_AWADDR=addr)    # d.update(...) takes key/value pairs given and writes into dictionary d. if key not exist yet, it is added. already existing key is overwritten.
        if not w_done and n >= w_delay:
            drive.update(S_AXI_WVALID=1, S_AXI_WDATA=data, S_AXI_WSTRB=strb)
        if n >= b_delay:
            drive["S_AXI_BREADY"] = 1

        s = await cycle(dut, drive) # s is snapshot taken after cycle(), so holds slave’s outputs as next rising edge will see them

        # response may only appear after both address and data have been accepted
        # BVALID is output of ff, so can only go high after rising edge where address and data were accepted
        if s["BVALID"]:
            assert aw_done and w_done, f"cycle {n}: BVALID before address and data were both accepted"
            bvalid_seen = True
            if drive.get("S_AXI_BREADY"):   # handshake check: BVALID=1 in snapshot. if also drive BREADY = 1 in same cycle then both high at next rising edge, so B transfer happens there
                return s["BRESP"]   # handshake at the next edge, return BRESP
        else:
            assert not bvalid_seen, f"cycle {n}: slave dropped BVALID before BREADY handshake"

        if drive.get("S_AXI_AWVALID") and s["AWREADY"]:
            aw_done = True
        if drive.get("S_AXI_WVALID") and s["WREADY"]:
            w_done = True
    raise AssertionError(f"write to 0x{addr:X} timed out (aw_done={aw_done}, w_done={w_done})")

async def axi_read(dut, addr, ar_delay=0, r_delay=0):
    """
    one AXI4-Lite read. Returns (RDATA, RRESP).
    -> r_delay > 0 makes the master hold RREADY low for a while (backpressure), during which
       the slave must keep RVALID high and RDATA/RRESP unchanged
    """
    ar_done = False
    held = None                      # memory that saves (RDATA, RRESP) when RVALID first went high (so saves original, first offered data)
    # After data is offered is no longer None and thus no longer updated. Lets us compare data on bus now with first offered data.
    # If they differ, the slave changed RDATA or RRESP while RVALID was high and no handshake had happened yet -> stability rule violation
    # the write function doesn’t need it, because the payload is only BRESP (2 bits), and in this slave it is constant
    for n in range(TIMEOUT):
        drive = {}
        if not ar_done and n >= ar_delay:
            drive.update(S_AXI_ARVALID=1, S_AXI_ARADDR=addr)
        if n >= r_delay:
            drive["S_AXI_RREADY"] = 1

        s = await cycle(dut, drive)

        if s["RVALID"]:
            assert ar_done, f"cycle {n}: RVALID before the read address was accepted"
            now = (s["RDATA"], s["RRESP"])
            if held is None:    # save original data (first offer) after that no longer update held
                held = now
            assert now == held, f"cycle {n}: RDATA/RRESP changed while RVALID high: {held} -> {now}"
            if drive.get("S_AXI_RREADY"):
                return held
        else:
            assert held is None, f"cycle {n}: slave dropped RVALID before RREADY handshake"

        if drive.get("S_AXI_ARVALID") and s["ARREADY"]:
            ar_done = True
    raise AssertionError(f"read from 0x{addr:X} timed out (ar_done={ar_done})")

async def peek(dut):
    """
    Returns snapshot of outputs without doing anything on bus
    """
    return await cycle(dut, {})

###########################################
### Reference model                     ###
###########################################

class RegModel:
    """
    What the register file SHOULD contain. Reference to compare with Verilog DUT output. Important to keep track of
    many random write/read and strobe combinations and their history.
    """
    def __init__(self): # like hardwares reset values, start at 0
        self.ftw = 0
        self.amp = 0

    def write(self, addr, data, strb=0xF):
        mask = sum(0xFF << (8 * i) for i in range(4) if (strb >> i) & 1)   # build byte mask from the strobe bits
        # (strb >> i) & 1 extracts bit i of strb, i.e. “is byte lane i enabled?”
        # 0xFF << (8 * i) is a byte of ones placed at lane i
        # this generator expression produces one such byte for each enabled lane and sum combines them 
        # since the lanes never overlap, adding is the same as OR operation
        idx = (addr >> 2) & 0b11                                           # bits [3:2] select register (mirrors axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] in Verilog)
        if idx == 0:
            self.ftw = (self.ftw & ~mask & 0xFFFFFFFF) | (data & mask)    # merge old and new data using mask
            # self.ftw & ~mask keeps old data in the lanes that were not enabled
            # data & mask takes new bytes in the enabled lanes -> merge old and new using |
        elif idx == 1:
            self.amp = ((self.amp & ~mask) | (data & mask)) & 0xFFFF      # only 16 bits exist

    def read(self, addr):
        return {0: self.ftw, 1: self.amp}.get((addr >> 2) & 0b11, 0)    # .get(key, 0) returns value of key or default 0 when key is missing

    # When traffic is tested, then apply every write/read to both dut and ref model as follows
    # await axi_write(dut, addr, data, strb, ...)   # real hardware (simulated using cocotb+verilator)
    # model.write(addr, data, strb)                 # reference

###########################################
### Tests                               ###
###########################################

@cocotb.test()
async def resettest_reset_values(dut):
    """
    after every reset both registers should be 0, the outputs 0, and all addresses read 0 with OKAY
    """
    start_clock(dut)
    await reset_dut(dut)
    s = await peek(dut)
    assert s["ftw"] == 0 and s["amp"] == 0, f"outputs not zero after reset but: {s}"
    for addr in (FTW, AMP, *UNUSED):        # the * operator performs iterable unpacking (** is to unpack dictionaries not iterable lists)
        data, resp = await axi_read(dut, addr)
        assert (data, resp) == (0, OKAY), f"0x{addr:X} read {data:#x}, resp {resp}"   
        # :X gives the formatting instructions for the string -> X is hexadecimal
        # :x formats the number as a lowercase hexadecimal string (ff)
        # :#x automatically includes the base prefix (0x for hex) so 0xff for example

@cocotb.test()
async def test_write_then_read(dut):
    

