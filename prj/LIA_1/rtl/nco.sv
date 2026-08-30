// rtl/cordic_sincos.sv
//
// Pipelined CORDIC (rotation mode), one stage per clock. Latency =
// N_STAGES cycles; throughput = 1 sample/clock once filled.
//
// Phase input uses the SAME convention as nco.sv's phase accumulator:
// the top 2 bits select the quadrant, the remaining bits represent the
// sub-angle within that quadrant, scaled so full-scale == pi/2. This
// means no radian conversion is ever needed in hardware.
 
module cordic_sincos #(
    parameter int PHASE_WIDTH = 32,
    parameter int N_STAGES    = 16,   // pipeline depth = angle precision
    parameter int OUT_WIDTH   = 14,
    parameter int GUARD_BITS  = 4     // extra internal precision
)(
    input  logic clk,
    input  logic [PHASE_WIDTH-1:0] phase,
    output logic signed [OUT_WIDTH-1:0] sin_o,
    output logic signed [OUT_WIDTH-1:0] cos_o
);
















