"""
test for .ia.registers. just a test for the software equivalent (FakeRegisters), hardware test later
"""

import pytest

from lia.registers import MAP_SIZE, REG_AMP, REG_FTW, FakeRegisters

def test_reset_values():
    regs = FakeRegisters()
    assert regs.read32(REG_FTW) == 0
    assert regs.read32(REG_AMP) == 0

def test_ftw_stores_32_bits():
    regs = FakeRegisters()
    regs.write32(REG_FTW, 0xDEADBEEF)
    assert regs.read32(REG_FTW) == 0xDEADBEEF

def test_amp_keeps_only_16_bits():
    regs = FakeRegisters()
    regs.write32(REG_AMP, 0xDEADBEEF)
    assert regs.read32(REG_AMP) == 0xBEEF

@pytest.mark.parametrize("offset", [0x8, 0xC])
def test_unused_offsets(offset):
    regs = FakeRegisters()
    regs.write32(offset, 0xFFFFFFFF)
    assert regs.read32(offset) == 0
    assert (regs.ftw, regs.amp) == (0, 0)

def test_aliasing_every_16_bytes():
    regs = FakeRegisters()
    regs.write32(0x10, 0x1234)
    assert regs.read32(REG_FTW) == 0x1234

@pytest.mark.parametrize("offset", [-4, MAP_SIZE, 0x2])
def test_reject_bad_offsets(offset):
    regs = FakeRegisters()
    with pytest.raises(ValueError):
        regs.write32(offset, 0)
    with pytest.raises(ValueError):
        regs.read32(offset)

@pytest.mark.parametrize("value", [-1, 2**32])
def test_reject_bad_values(value):
    with pytest.raises(ValueError):
        FakeRegisters().write32(REG_FTW, value)



# Check DevMemRegisters mechanics, using ordinary file instead of /dev/mem

from lia.registers import DevMemRegisters

@pytest.fixture
def mapped_file(tmp_path):
    """A 4 KB file of zeros, as stand in for the register page."""
    f = tmp_path / "fake_mem"
    f.write_bytes(bytes(MAP_SIZE))
    return f

def test_devmem_word_access(mapped_file):
    with DevMemRegisters(base=0, path=str(mapped_file)) as regs:
        regs.write32(REG_AMP, 0x12345678)
        assert regs.read32(REG_AMP) == 0x12345678
        assert regs.read32(REG_FTW) == 0            # neighbouring word untouched
    # the word landed at byte offset 4, little-endian (like PS arm cpu)
    assert mapped_file.read_bytes()[4:8] == bytes([0x78, 0x56, 0x34, 0x12])

def test_devmem_close_twice_is_safe(mapped_file):
    regs = DevMemRegisters(base=0, path=str(mapped_file))
    regs.close()
    regs.close()


