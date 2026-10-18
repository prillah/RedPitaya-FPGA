



module amp_scale #(
    parameter int DATA_WIDTH = 14,  // DAC and ADC width of red pitaya
    parameter int GAIN_WIDTH = 16  // resolution of gain factor multiplied with DDS output
) (
    input logic clk,
    input logic signed [DATA_WIDTH-1:0] din,
    input logic [GAIN_WIDTH-1:0] gain,
    output logic signed [DATA_WIDTH-1:0] dout
);

    // multiply 14 and 16 bit number, so need 30 bits max for product of the two
    localparam int PROD_WIDTH = DATA_WIDTH + GAIN_WIDTH;
    