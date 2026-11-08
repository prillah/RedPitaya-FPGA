"""
command line control of the LIA DDS on the red pitaya

Examples (on the board, as root, with bitstream already loaded):
    python3 lia_ctl.py --freq 1e6 --amp 0.5     set frequency and amplitude
    python3 lia_ctl.py --freq 2.5M              change only the frequency (k/M suffixes allowed)
    python3 lia_ctl.py                          just show the current settings
On a PC, add --fake to use a simulated register file instead of the hardware for tests
"""

import argparse
import sys

from lia.dds import Dds
from lia.registers import DevMemRegisters, FakeRegisters

SUFFIXES = {"k": 1e3, "M": 1e6}



def parse_frequency(text):
    """
    convert strings like "1M", "10, .. into freq in Hz (float)

    Use argparse as parser for command line interface. this makes also error handling nicer
    """
    original = text
    text = text.strip() # remove leading and trailing white spaces
    factor = 1.0
    if text and text
















