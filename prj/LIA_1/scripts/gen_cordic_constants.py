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

# --- CORDIC gain and gain-precorrected initial x ---
K = np.prod(np.cos(atan_vals[:N_STAGES]))
print(f"CORDIC gain K = {K:.6f}")

# Compute directly at WORK_WIDTH scale - do NOT compute at OUT_WIDTH scale
# and then left-shift; (2**(OUT_WIDTH-1)-1) << GUARD_BITS is NOT the same
# value as 2**(WORK_WIDTH-1)-1, since "full scale minus one" does not shift
# the way you'd expect (the "-1" is a much bigger step at the wider scale).
work_full_scale = 2 ** (WORK_WIDTH - 1) - 1
x0 = round(K * work_full_scale)

print(f"X0 (WORK_WIDTH={WORK_WIDTH}) = {x0}")
print(f"localparam signed [{WORK_WIDTH-1}:0] X0 = {WORK_WIDTH}'sd{x0};")