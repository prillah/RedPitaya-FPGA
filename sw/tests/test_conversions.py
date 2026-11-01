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

pytest.mark.parameterize("freq", "ftw", [
    (0.0,       0),
    (1e6,       0x020C49BA),     # value used for monitor test
    (2e6,       0x04189375),
    (1.25e6,    42949673),       # original hardcoded oscilloscope test frequency
    (F_CLK / 4, 2**30),          # should be exactly representable, since is quarter of clock
])
def test_known_ftw_values(freq, ftw):
    assert freq_to_ftw(freq) == ftw

























