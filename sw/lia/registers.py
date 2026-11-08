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



class DevMemRegisters:
    """
    Used for real hardware access through /dev/mem.
    Must be run as root on the board and only while bitstream is loaded (otherwise an access hangs the CPU)

    Every acces is meant to be only one 32 bit read or write.
    memory is accessed through memoryview with format 'I' (unsigned 32 bit) -> CPython moves each element as one 4-byte word
    If one would copy bytes instead (eg mm[0:4] = data and not mem[0] = data) may be split into byte accesses, 
    which would reach the slave as 4 AXI writes with WSTRB 0001, 0010, ... and briefly give the DDS a half-updated FTW.
    """

    def __init__(self, base=BASE_ADDR, size=MAP_SIZE, path="/dev/mem"):
        # path should only be changed by tests which map ordinary file

        # os.open returns a file descriptor (thus fd name, start with underscore since its internal detail that shouldnt be touched)
        # os.O_RDWR | os.O_SYNC are bitmasks combined using OR -> O_RDWR asks for read and write
        # -> O_SYNC makes mapping uncached, so every access goes out on the bus instead of into the CPU cache
        self._fd = os.open(path, os.O_RDWR | os.O_SYNC)

        try:
            self._mm = mmap.mmap(self._fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset = base)
        except Exception:
            os.close(self._fd)  # need to close file descriptor of something fails, otherwise will stay open forever
            raise
        # try mapping the fils
        # self._fd tells which file to map, size is how many bytes (here 4096), MAP_SHARED: writes go to the real target (/dev/mem, so the hardware), not to a private copy
        # PROT_READ | PROT_WRITE: the mapped memory may be read and written.
        # offset=base: where in the file to start. For /dev/mem, the file position is the physical address, so offset=0x4000_0000 means your registers. It must be a multiple of the page size, 4 KB.


        self._words = memoryview(self._mm).cast("I")    # the page as 1024 uint32 words
        # memoryview(self._mm) gives direct access to the mapped bytes without copying them.
        if self._words.itemsize != 4:
            self.close()
            raise RuntimeError("unsigned int is not 32 bits on this platform")

    def write32(self, offset, value):
        _check_access(offset, value)
        self.words[offset//4] = value   # // is integer division such that 0x04 becomes 1 and 0x00 0
        # Assigning to self._words[1] stores one 32-bit word at byte 4 of the page
        # i.e. at physical address 0x4000_0004, which the CPU turns into one AXI write to AMP

        # slave only stores bottom 16 bit for AMP register so no need to do that here

    def read32(self, offset):
        _check_access(offset)
        return self._words[offset // 4]

    def close(self):
        


































