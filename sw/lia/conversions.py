"""
This file converts between physical units and the actual register values (so from Hz and Volts to integers)

It mirrors the hardware:
-> DDS: f_out = FTW*F_CLK/2**PHASE_WIDTH (this comes from dds_cordic.sv)
-> Scaling: dout = (din*Gain + 2**15)>>16 (this is from amp_scale.sv)

These are just the conversion functions, no hardware is accessed in here.
"""















