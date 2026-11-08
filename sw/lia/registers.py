"""
File to access lia_axil_regs registers using a python script

Rgeister map (these are the offsets from base address BASE_ADDR, see lia.axil.regs.v):
    0x00 FTW 32 bit, read and write
    0x04 AMP 16 bit, read and write (the upper 16 bits read as 0)
    0x08, 0x0C are unused, read 0 and writes are ignored

Slave only decodes offset bits [3:2], so map repeats every 16 bytes

includes 2 versions of the same backend with the same two methods: write32() and read32():
    FakeRegisters is a pure python model of the hardware and is used to run tests on a pc beforehand
    DevMemRegisters is to communicate with real hardware through /dev/mem (on the board, as root)
"""

import mmap
import os

BASE_ADDR = 0x4000_0000     # set in tcl command and red pitaya docs: assign_bd_address -offset in system.tcl
MAP_SIZE = 0x1000           # address range :assign_bd_address -range: 4 KB (should be one Linux page)

REG_FTW = 0x00
REG_AMP = 0x04

U32_MAX = 0xFFFF_FFFF



def _check_access(offset, value = None):
    """
    Reject access to hardware already at this stage, if address or value are non sensical
    """
    if not 0 <= offset <= MAP_SIZE:
        raise ValueError(f"offset {offset:#x} outside the 4 KB window")
    if offset % 4:
        raise ValueError(f"offset {offset:#x} is not 32-bit aligned")
    if value is not None and not 0 <= value <= U32_MAX:
        raise ValueError(f"value {value} does not fit in 32 bits")



class FakeRegisters:
    """
    Should behave like lia_axil_regs.v, used to test software without hardware
    """

    def __init__(self):
        self.ftw = 0
        self.amp = 0
        self.writes = []    # log of (offset, value) pairs for tests to check what was written

    def write32(self, offset, value):
        _check_access(offset, value)
        self.writes.append((offset, value))
        index = (offset >> 2) & 0b11    # only bits [3:2] matter
        if index == 0:
            self.ftw = value
        elif index == 1:
            self.amp = value & 0xFFFF   # only 16 bits exist in hardware for amp register
        # index 2 and 3 are ignaored/unused, no write

    def read32(self, offset):
        _check_access(offset)
        index = (offset >> 2) & 0b11
        return {0: self.ftw, 1: self.amp}.get(index, 0)

    def close():    # nothing to really close, so just pass/do nothing
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


        
































