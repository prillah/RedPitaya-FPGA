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
    """
    Basic operation, write FTW and AMP, check outputs to DDS and then read them back and check again
    """
    start_clock(dut)
    await reset_dut(dut)

    assert await axi_write(dut, FTW, 0x12345678) == OKAY
    assert await axi_write(dut, AMP, 0xABCD) == OKAY

    s = await peek(dut)

    assert s["ftw"] == 0x12345678, f"ftw out is {s['ftw']:#x}"  # check success of write operation to both registers
    assert s["amp"] == 0xABCD, f"amp out is {s['amp']:#x}"

    assert await axi_read(dut, FTW) == (0x12345678, OKAY)
    assert await axi_read(dut, AMP) == (0xABCD, OKAY)

@cocotb.test()
async def test_amp_upper_half(dut):
    """
    since AMP only stores bits 15:0, the upper ones are lost. check that this actually happens (upper ones stay 0)
    """
    start_clock(dut)
    await reset_dut(dut)
    await axi_write(dut, AMP, 0xDEADBEEF)
    assert (await peek(dut))["amp"] == 0xBEEF
    assert await axi_read(dut, AMP) == (0x0000BEEF, OKAY)

@cocotb.test()
async def test_unused_addresses(dut):
    """
    writes to upper addresses 0x08 and 0x0C must complete with no hang and OKAY, and must not touch FTW and AMP
    """
    start_clock(dut)
    await reset_dut(dut)
    await axi_write(dut, FTW, 0x11111111)
    await axi_write(dut, AMP, 0x2222)
    for addr in UNUSED:
        assert await axi_write(dut, addr, 0xFFFFFFFF) == OKAY
        assert await axi_read(dut, addr) == (0, OKAY)
    s = await peek(dut)
    assert (s["ftw"], s["amp"]) == (0x11111111, 0x2222), f"unused address write leaked into FTW/AMP: {s}"

@cocotb.test()
async def test_write_strobes(dut):
    """
    Test all different strobe patterns. range(16) covers 0000 to 1111 which are all possible patterns, since each strobe has one bit per byte of the write data bus
    """
    start_clock(dut)
    await reset_dut(dut)
    model = RegModel()  # instantiate a reference model
    for strb in range(16):  # goes through all strobe possibilities (2**4 possibilities since 4 bytes)
        for addr in (FTW, AMP):
            data = random.getrandbits(32)   # generate random data for all different strobe patterns
            await axi_write(dut, addr, data, strb=strb)
            model.write(addr, data, strb)
        s = await peek(dut)
        assert (s["ftw"], s["amp"]) == (model.ftw, model.amp), (
            f"strb={strb:04b}: dut ftw={s['ftw']:#x} amp={s['amp']:#x}, "
            f"model ftw={model.ftw:#x} amp={model.amp:#x}")

@cocotb.test()
async def test_channel_orderings(dut):
    """
    AXI4Lite protocol lets AW and W arrive in any order and lets BREADY be late. Check that all these combinations work
    """
    start_clock(dut)
    await reset_dut(dut)
    cases = [   # (aw_delay, w_delay, b_delay, description)
        (0, 0, 0, "addresses and data together"),
        (0, 3, 0, "address first, data 3 cycles later"),
        (3, 0, 0, "data first, address 3 cycles later"),
        (0, 0, 5, "master holds BREADY low for 5 cycles"),
        (2, 5, 9, "everything is late"),
    ]

    for i, (aw_d, w_d, b_d, what) in enumerate(cases):
        value = 0x1000 + i  # write different values for each case (space them by 1 and non zero)
        resp = await axi_write(dut, FTW, value, aw_delay=aw_d, w_delay=w_d, b_delay=b_d)
        assert resp == OKAY, f"{what}: BRESP={resp}"
        got = await axi_read(dut, FTW)
        assert got == (value, OKAY), f"{what}: read back {got}, expected {value:#x}"
        dut._log.info(f"ok: {what}")

@cocotb.test()
async def test_read_backpressure(dut):
    """
    Check that when master delays RREADY, that slave holds RVALID and RDATA (check inside axi_read)
    """
    start_clock(dut)
    await reset_dut(dut)
    await axi_write(dut, FTW, 0xCAFE0001)
    assert await axi_read(dut, FTW, r_delay=6) == (0xCAFE0001, OKAY), f"read backpressure test failed with r_delay=6"
    assert await axi_read(dut, FTW, ar_delay=3, r_delay=6) == (0xCAFE0001, OKAY), f"read backpressure test failed with ar_delay=3, r_delay=6"

@cocotb.test()
async def test_early_next_address(dut):
    """
    
    """

















