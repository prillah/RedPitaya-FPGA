// rtl/cordic_sincos.sv
//
// Unrolled, Pipelined CORDIC (rotation mode). latency is N_STAGES
// and throughput is 1 sample/clock once filled.
//
// Phase input convention: top 2 bits select the quadrant, 
// the remaining bits represent the sub angle within quadrant
 
module cordic_sincos #(
    parameter int PHASE_WIDTH = 32,   // width of phase accumul., sets freq. resolution
    parameter int N_STAGES    = 16,   // pipeline depth sets angle precision
    parameter int OUT_WIDTH   = 14,   // to match DAC/ADC precision
    parameter int GUARD_BITS  = 4     // extra internal precision due to accumulating rounding errors (approx. log_2(N_stages))
)(
    input  logic clk,
    input  logic [PHASE_WIDTH-1:0] phase,
    output logic signed [OUT_WIDTH-1:0] sin_o,
    output logic signed [OUT_WIDTH-1:0] cos_o
);

    localparam int ANGLE_WIDTH = PHASE_WIDTH - 2;       // because two bits for quadrant
    localparam int WORK_WIDTH  = OUT_WIDTH + GUARD_BITS;    // how wide x,y,z adders and so on need to be (internal precision)

    // X0 = (K * (2**(WORK_WIDTH-1)-1)), K = prod(cos(atan(2^-i))) for i=0,...,15.
    // computed by scripts/gen_cordic_constants.py for chosen N_STAGES.
    // Done to gain-precorrect so no output multiplier is needed after the pipeline.
    localparam signed [WORK_WIDTH-1:0] X0 = 18'sd79593;  // N_STAGES=16, OUT_WIDTH=14, GUARD_BITS=4

    logic signed [ANGLE_WIDTH:0] atan_lut [0:N_STAGES-1];   // declaring memory array: logic signed [packed dimension, i.e. width of one element]   atan_lut   [unpacked dimension, i.e. how many elements, atan_lut[i]]
    initial $readmemh("atan_table.mem", atan_lut);
    // initial -> block that runs exactly once, at the very start of time, not every clock edge
    // $readmemh -> built-in verilog "system task" ($ marks built in utility). reads text file with each line being a hexadecimal number
    //           -> loads them sequentially into the array specified as atan_lut, starting at index 0

    logic [1:0] quadrant;   // two bits to encode the quadrant of the angle
    logic [ANGLE_WIDTH-1:0] subangle;   // angle between 0 and pi/2, i.e. top right quadrant
    assign quadrant = phase[PHASE_WIDTH-1 -: 2];    // syntax: signal[start_bit -: width] -> go down wdth number of bits startng from start_bit ( +: would signal upwards)
    assign subangle = phase[ANGLE_WIDTH-1:0];       // 30 bits for subangle implies z has 31 bits because need to add a sign bit

    // initialize pipeline register arrays for each of the N CORDIC stages (index 0 = initial condition) 
    // gives structure of the bit-parallel unrolled CORDIC algorithm
    logic signed [WORK_WIDTH-1:0] x [0:N_STAGES];
    logic signed [WORK_WIDTH-1:0] y [0:N_STAGES];
    logic signed [ANGLE_WIDTH:0]  z [0:N_STAGES];
    logic [1:0] quad_pipe [0:N_STAGES];     // book-keeping which quadrant we started in for final step after N CORDIC stages

    























