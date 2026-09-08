import numpy as np
from pathlib import Path

script_dir = Path(__file__).resolve().parent
output_path = script_dir.parent / "rtl" / "atan_table.mem"

output_path.parent.mkdir(parents=True, exist_ok=True)

N_STAGES    = 16
PHASE_WIDTH = 32
OUT_WIDTH   = 14
GUARD_BITS  = 4                 # extra internal precision due to rounding errors after N_stages of CORDIC
WORK_WIDTH  = OUT_WIDTH + GUARD_BITS

# Calc of atan LUT: arctan(2^-i) table, accounting for size of z.
# scale atan values such that largest signed WORKING_WIDTH bits integer is equal to pi/2!
atan_vals = np.arctan(2.0 ** -np.arange(N_STAGES))
atan_scaled = np.round(atan_vals / (np.pi / 2) * (2 ** (WORK_WIDTH - 1))).astype(int)
# take 2**(width-1) as weight and not 2**(width-1) -1 as weight although is largest 2compl number
# -> Can see it as inheritance from phase. bit k of phase always carries a weight of (360°/2^32) × 2^k. phase[31] is 180 degrees. 
#    Look at sign bit of z, i.e. phase[30] then this has weight of 90 degrees. So need to scale to that bit, i.e. 2^(WORK_WIDTH-1)
# -> Can also see this since pi/2 and -pi/2 are given by 10...0 and thus are the smallest negative number in twos complement (i.e. -2^(WORK_WIDTH-1))
#    So scale to that, then our range is [-pi/2,pi/2)!

with open("atan_table.mem", "w") as f:
    for v in atan_scaled:
            f.write(f"{v & (2**WORK_WIDTH - 1):0{(WORK_WIDTH+3)//4}x}\n")
            # v & (2**WORK_WIDTH - 1) -> bitwise AND with 0000111...1 with WORK_WIDTH many 1s to make the python integer v fixed width (WORK_WIDTH)
            #                            this is exactly the size of z in the CORDIC stages!
            # :0{(WORK_WIDTH+3)//4}x  -> specifies Python's f-string format specification. x at the end makes it hexadecimal rather than default decimal.
            # {(WORK_WIDTH+3)//4}x}   -> number of hex digits needed to represent WORK_WIDTH bits.    

# with open(output_path, "w") as f:
#     for v in atan_scaled:
#         f.write(f"{v & (2**WORK_WIDTH - 1):0{(WORK_WIDTH+3)//4}x}\n")
        # v & (2**WORK_WIDTH - 1) -> bitwise AND with 0000111...1 with WORK_WIDTH many 1s to make the python integer v fixed width (WORK_WIDTH)
        #                            this is exactly the size of z in the CORDIC stages!
        # :0{(WORK_WIDTH+3)//4}x  -> specifies Python's f-string format specification. x at the end makes it hexadecimal rather than default decimal.
        # {(WORK_WIDTH+3)//4}x}   -> number of hex digits needed to represent WORK_WIDTH bits.    

# Calcualte CORDIC gain and the gain-precorrected initial x
K = np.prod(np.cos(atan_vals[:N_STAGES]))
print(f"CORDIC gain K = {K:.6f}")

# scale 1 to full work width
work_full_scale = 2 ** (WORK_WIDTH - 1) - 1
x0 = round(K * work_full_scale)

print(f"X0 (WORK_WIDTH={WORK_WIDTH}) = {x0}")
print(f"localparam signed [{WORK_WIDTH-1}:0] X0 = {WORK_WIDTH}'sd{x0};")
# sd stands for signed decimal