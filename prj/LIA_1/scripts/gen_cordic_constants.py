import numpy as np

N_STAGES    = 16
PHASE_WIDTH = 32
ANGLE_WIDTH = PHASE_WIDTH - 2   # bits representing angle 0 .. pi/2 in radians (first two bits are for quadrant)
OUT_WIDTH   = 14
GUARD_BITS  = 4                 # extra internal precision due to rounding errors after N_stages of CORDIC
WORK_WIDTH  = OUT_WIDTH + GUARD_BITS

# Calc of atan LUT: arctan(2^-i) table, in "quadrant units" with 2**ANGLE_WIDTH == pi/2
# These units are needed for hardware to stay entirely in integer phase units
atan_vals = np.arctan(2.0 ** -np.arange(N_STAGES))
atan_scaled = np.round(atan_vals / (np.pi / 2) * (2 ** ANGLE_WIDTH)).astype(int)

with open("atan_table.mem", "w") as f:
    for v in atan_scaled:
        f.write(f"{v & (2**(ANGLE_WIDTH+1) - 1):0{(ANGLE_WIDTH+1+3)//4}x}\n")
        # v & (2**(ANGLE_WIDTH+1) - 1) -> bitwise AND with 0000111...1 with Angle_width+1 many 1s to make the python integer v fixed widt (angle +1)
        # want angle_width+1 because z angle also needs to go negative, i.e. cover plus minus pi/2 range! Only subangle is width angle_wdth (0,pi/2 range)
        # :0{(ANGLE_WIDTH+1+3)//4}x specifies Python's f-string format specification. x at the end makes it hexadecimal rather than default decimal.
        # 0<N> -> zero pad output on the left to exactly N characters wide, st in file every number has same amount of hex digits, , so Verilog's file reader can consistently map each line onto one ANGLE_WIDTH+1-bit array entry
        # {(ANGLE_WIDTH+1+3)//4} -> number of hex digits needed to represent ANGLE_WIDTH+1 bits. 

# Calcualte CORDIC gain and the gain-precorrected initial x
K = np.prod(np.cos(atan_vals[:N_STAGES]))
print(f"CORDIC gain K = {K:.6f}")

# scale 1 to full work width
work_full_scale = 2 ** (WORK_WIDTH - 1) - 1
x0 = round(K * work_full_scale)

print(f"X0 (WORK_WIDTH={WORK_WIDTH}) = {x0}")
print(f"localparam signed [{WORK_WIDTH-1}:0] X0 = {WORK_WIDTH}'sd{x0};")
# sd stands for signed decimal