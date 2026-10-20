# tbn/test_lia_axil_regs.py
#
# cocotb testbench for the AXI4-Lite register slave (adapted from the Vivado template).
#   0x00  FTW  32-bit, read/write        -> ftw_o
#   0x04  AMP  16-bit, read/write        -> amp_o
#   0x08, 0x0C: read as 0, writes ignored
#
# The "master" below is written by hand on purpose: every handshake is visible in the code.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


