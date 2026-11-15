#!/usr/bin/env python3

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
    original = text # keep unmodified input string for error message if something goes wrong
    text = text.strip() # remove leading and trailing white spaces
    factor = 1.0    # default for inputs without suffixes
    if text and text[-1] in SUFFIXES:        # check text is false for an empty string and if last character is key in SUFFIX dict.
        factor = SUFFIXES[text[-1]]
        text = text[:-1]    # remove last character
    try:
        return float(text) * factor
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a frequency: {original!r}")


def build_parser():
    """
    When type "python3 lia_ctl.py --freq 2.5M --amp 0.5" into shell, shell splits this into list of strings available as sys.argv (['lia_ctl.py', '--freq', '2.5M', '--amp', '0.5']).
    Argparse turns list into named and typed values (Namespace(freq=2500000.0, amp=0.5, fake=False)) and handles all errors and so on.
    """
    parser = argparse.ArgumentParser(
        description="Set and read the DDS frequency and amplitude of the LIA bitstream."
    )
    parser.add_argument("--freq", type=parse_frequency, metavar="Hz", help="output frequency, e.g. 1e6, 2.5M or 100k")
    parser.add_argument("--amp", type=float, metavar="0...1", help="relative output amplitude, 0 = off, 1 = full scale")
    parser.add_argument("--fake", action="store_true", help="use a simulated register file (for testing on a PC)")
    return parser


def open_registers(fake):
    """
    Chooses the backend.
    """
    return FakeRegisters() if fake else DevMemRegisters()


def format_status(status):
    """Some formating of the status variable"""
    return (f"frequency: {status['freq_hz']:14.3f} Hz   (FTW 0x{status['ftw']:08x})\n"
            f"amplitude: {status['amplitude']:14.6f}      (AMP 0x{status['gain']:04x})")


def main(argv=None):
    """
    Runs the tool.argv=None means the it uses the real command line (sys.argv)
    returns exit code: 0 is a success and 1 an error
    """
    args = build_parser().parse_args(argv)
    # parse_args() reads arguments and returns a object (argparse.Namespace) with attributes args.freq, args.amp, args.fake.
    # if argv=None, then it reads real command line sys.argv[1:]. A test would pass its own list instead

    try:    # try opening the hardware
        regs = open_registers(args.fake)
    except PermissionError: # PermissionError is a subclass of OSError, so need to check for it first
        print("error: no access to /dev/mem, run as root", file=sys.stderr) # file=sys.stderr sends the message to the error stream.
        return 1
    except OSError as e:
        print(f"error: cannot map the registers:  {e}", file=sys.stderr)
        return 1

    # apply the settings
    with regs:   # calls regs.__enter__()
        dds = Dds(regs)
        try:
            if args.freq is not None:
                dds.set_frequency(args.freq)
            if args.amp is not None:
                dds.set_amplitude(args.amp)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(format_status(dds.status()))
    return 0
    
















