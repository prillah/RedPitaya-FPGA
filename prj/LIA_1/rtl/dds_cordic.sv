// rtl/dds_cordic.sv
//
// Direct Digital Synthesis (DDS) module based on cordic_sincos.sv

module dds_cordic #(
    parameter int PHASE_WIDTH = 32,   // width of phase accumul., sets freq. resolution
    parameter int N_STAGES    = 16,   // pipeline depth sets angle precision
    parameter int OUT_WIDTH   = 14,   // to match DAC/ADC precision
    parameter int GUARD_BITS  = 4     // extra internal precision due to accumulating rounding errors (approx. log_2(N_stages))
)(
    input  logic clk,
    input  logic reset,               // synchronous and active-high
    input  logic [PHASE_WIDTH-1:0] ftw,
    output logic signed [OUT_WIDTH-1:0] sin_o,
    output logic signed [OUT_WIDTH-1:0] cos_o
);

    logic [PHASE_WIDTH-1:0] phase_acc;

    always_ff @(posedge clk) begin

        if (reset) begin
            phase_acc <= '0;
        end
        else begin
            phase_acc <= phase_acc + ftw;
        end
    end

    cordic_sincos #(.PHASE_WIDTH(PHASE_WIDTH), .N_STAGES(N_STAGES),
                     .OUT_WIDTH(OUT_WIDTH), .GUARD_BITS(GUARD_BITS))
    cordic_i (.clk(clk), .reset(reset), .phase(phase_acc), .sin_o(sin_o), .cos_o(cos_o));

endmodule




