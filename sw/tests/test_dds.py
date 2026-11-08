"""
test for lia.dds, test it against the fake register backend
"""

import pytest

from lia.conversions import F_RESOLUTION
from lia.dds import Dds
from lia.registers import REG_AMP, REG_FTW, FakeRegisters

@pytest.fixture()
def dds():
    """
    fresh dds on fresh fake reg file for every test
    """
    return Dds(FakeRegisters)

def test_set_frequency_writes_ftw(dds):
    actual = dds.set_frequency(1e6)
    assert dds.regs.read32(REG_FTW) == 0x020C49BA
    assert abs(actual - 1e6) <= F_RESOLUTION / 2

def test_set_amplitude_writes_gain(dds):
    assert dds.set_amplitude(0.5) == pytest.approx(0x8000 / 0xFFFF)
    assert dds.regs.read32(REG_AMP) == 0x8000

def test_exactly_one_write_per_setting(dds):
    """
    Each setting must be one 32-bit write, should never split into pieces
    """
    dds.set_frequency(2e6)
    dds.set_amplitude(1.0)
    assert dds.regs.writes == [(REG_FTW, 0x04189375), (REG_AMP, 0xFFFF)]

def test_get_reads_back(dds):
    dds.set_frequency(10e6)
    dds.set_amplitude(0.25)
    assert dds.get_frequency() == pytest.approx(10e6, abs=F_RESOLUTION)
    assert dds.get_amplitude() == pytest.approx(0.25, abs=1 / 0xFFFF)


def test_invalid_frequency_writes_nothing(dds):
    """
    bad value should be rejected before anything reaches hardware
    """
    with pytest.raises(ValueError):
        dds.set_frequency(100e6)
    assert dds.regs.writes == []


def test_status(dds):
    dds.set_frequency(1e6)
    dds.set_amplitude(1.0)
    s = dds.status()
    assert s["ftw"] == 0x020C49BA and s["gain"] == 0xFFFF
    assert s["amplitude"] == 1.0








