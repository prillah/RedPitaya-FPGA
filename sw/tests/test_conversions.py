"""
Test for lia.conversions
Run from sw/ folder using: python3 -m pytest -v
"""

import pytest
# runs small test functions automatically and reports which ones pass or fail
# pytest works by naming convention -> it looks for files named test_*.py (or *_test.py), inside them, it runs every function whose name starts with test_
#
# @pytest.mark.parametrize runs one test function with several inputs
#
# pytest.raises checks that something should fail: with pytest.raises(ValueError): freq_to_ftw(-1.0)
#
# pytest.approx compares floating-point numbers with a tolerance: assert F_RESOLUTION == pytest.approx(0.0291038304567, rel=1e-9)
#
# GENERAL: def test(): assert structure!

from lia.conversions import (F_CLK, F_NYQUIST, F_RESOLUTION, FTW_MAX, GAIN_MAX, amp_to_gain, freq_to_ftw, ftw_to_freq, gain_to_amp)

###############################
### Frequency               ###
###############################

@pytest.mark.parametrize("freq, ftw", [
    (0.0,       0),
    (1e6,       0x020C49BA),     # value used for monitor test
    (2e6,       0x04189375),
    (1.25e6,    42949673),       # original hardcoded oscilloscope test frequency
    (F_CLK / 4, 2**30)          # should be exactly representable, since is quarter of clock
])
def test_known_ftw_values(freq, ftw):
    assert freq_to_ftw(freq) == ftw

# no need for pytest macro here because looks for test_... in general
def test_ftw_is_int():
    assert isinstance(freq_to_ftw(1234.5), int)


@pytest.mark.parametrize("freq", [1.0, 137.0, 1e3, 12345.678, 1e6, 10e6, 50e6, F_NYQUIST - 1])
def test_round_trip_error_below_half_step(freq):
    """
    converting back and forth gives error below half a step
    """
    round_trip = ftw_to_freq(freq_to_ftw(freq))
    assert abs(round_trip - freq) <= F_RESOLUTION / 2

def test_resolution():
    """
    assert get the desired resolution for 32 bit ftw
    """
    assert F_RESOLUTION == pytest.approx(0.0291038304567, rel=1e-9)   # 125e6 / 2**32

@pytest.mark.parametrize("bad_freq", [-1.0, F_NYQUIST, 100e6])
def test_out_of_range_freq(bad_freq):
    """
    check some out of range freqs
    """
    with pytest.raises(ValueError): # used to test that specific piece of code raises expected exception
        freq_to_ftw(bad_freq)

@pytest.mark.parametrize("bad_ftw", [-1, FTW_MAX + 1])
def test_out_of_range_ftw(bad_ftw):
    """
    check some out of range ftws
    """
    with pytest.raises(ValueError):
        ftw_to_freq(bad_ftw)


###############################
### Amplitude               ###
###############################

@pytest.mark.parametrize("amp, gain", [(0.0, 0), (1.0, GAIN_MAX), (0.5, 0x8000)])
def test_known_gain_values(amp, gain):
    assert amp_to_gain(amp) == gain

@pytest.mark.parametrize("gain", [0, 1, 0x1234, 0x8000, GAIN_MAX])
def test_gain_round_trip_exact(gain):
    assert amp_to_gain(gain_to_amp(gain)) == gain

@pytest.mark.parametrize("bad_amp", [-0.1, 1.01])
def test_out_of_range_amp(bad_amp):
    with pytest.raises(ValueError):
        amp_to_gain(bad_amp)

@pytest.mark.parametrize("bad_gain", [-1, GAIN_MAX + 1])
def test_out_of_range_gain(bad_gain):
    with pytest.raises(ValueError):
        amp_to_gain(bad_gain)
















