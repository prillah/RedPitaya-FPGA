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

    

















