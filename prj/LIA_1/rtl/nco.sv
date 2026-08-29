// rtl/nco.sv
module nco #(
    parameter int PHASE_WIDTH    = 32,   // phase accumulator width
    parameter int LUT_ADDR_WIDTH = 10,   // 2^10 = 1024-entry sine table
    parameter int OUT_WIDTH      = 14    // matches ADC/DAC resolution
)(
    input  logic clk,
    input  logic [PHASE_WIDTH-1:0] ftw,        // frequency tuning word
    output logic signed [OUT_WIDTH-1:0] sin_o,
    output logic signed [OUT_WIDTH-1:0] cos_o
);
