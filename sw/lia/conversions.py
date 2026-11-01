"""
This file converts between physical units and the actual register values (so from Hz and Volts to integers)

It mirrors the hardware:
-> DDS: f_out = FTW*F_CLK/2**PHASE_WIDTH (this comes from dds_cordic.sv)
-> Scaling: dout = (din*Gain + 2**15)>>16 (this is from amp_scale.sv)

These are just the conversion functions, no hardware is accessed in here.
"""


from __future__ import annotations
# Annotations are type information in signatures like in def freq_to_ftw(freq_hz: float) -> int:
# freq_hz: float and -> int are hints for readers, editors and type checkers. Python does not enforce them
# Normally python evaluates each annotation when function is defined, i.e. it looks up float and int as objects
# with "from __future__ import annotations" annotations are stored as plain strings and never evaluated at that point -> “postponed evaluation”.
# can help with newer syntax on older python versions or with forward references

import math

# Define params
F_CLK = 125_000_000         # DDS clk in Hz (is dac_clk_1x from rtl files)
PHASE_WIDTH = 32            # width/bits of phase accumulator and thus FTW register
GAIN_WIDTH = 16             # width/bits of AMP register (amplitude resolution)

FTW_MAX = 2**PHASE_WIDTH - 1
GAIN_MAX = 2**GAIN_WIDTH - 1                 # 0xFFFF is full scale
F_RESOLUTION = F_CLK / 2**PHASE_WIDTH        # ~0.0291 Hz: frequency step of one FTW count
F_NYQUIST = F_CLK / 2                        # 62.5 MHz: above this the output aliases

def _round_half_up(x: float) -> int:
    """
    rounds x.5 up as in the rtl file amp_scale. since round() does round x.5 to x and not x+1, include function that does this.
    """

    return int(math.floor(x + 0.5))

def freq_to_ftw(freq_hz: float) -> int:
    """
    Input is frequency in Hz and out should go integer freq tuning word (nearest achievable)
    """
    if not 0 <= freq_hz < F_NYQUIST:
        raise ValueError(f"frequency must be in [0, {F_NYQUIST:.0f}) Hz, got {freq_hz}")
    return _round_half_up(freq_hz * 2**PHASE_WIDTH / F_CLK)

def ftw_to_freq(ftw: int) -> float:
    """
    Convert frequency tuning word to exact frequency the DDS produces
    """
    if not 0 <= ftw <= FTW_MAX:
        raise ValueError(f"FTW must be in [0, {FTW_MAX}], got {ftw}")
    return ftw * F_CLK / 2**PHASE_WIDTH

def amp_to_gain(amplitude: float) -> int:
    """
    Convert the relative amplitude 0-1V into and AMP register value 0x0000-0xFFFF
    """
    if not 0 <= amplitude <= 1.0:
        raise ValueError(f"amplitude must be in [0, 1], got {amplitude}")
    return _round_half_up(amplitude * GAIN_MAX)

def gain_to_amp(gain: int) -> float:
    """
    Convert a AMP register value (0x0000-0xFFFF) back into a relative amplitude (0-1V) for the excitation
    """
    if not 0 <= gain <= GAIN_MAX:
        raise ValueError(f"gain must be in [0, {GAIN_MAX}], got {gain}")
    return gain/GAIN_MAX












