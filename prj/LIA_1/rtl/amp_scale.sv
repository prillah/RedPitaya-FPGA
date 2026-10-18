// rtl/amp_scale.sv

// Amplitude scaler: dout = round(din * gain / 2**GAIN_WIDTH)
//   gain = 0       -> output 0
//   gain = 0x8000  -> output = din / 2
//   gain = 0xFFFF  -> output = din (65535/65536 plus rounding returns every 14-bit input unchanged)
// Rounding: round half up (add half an output LSB, then drop GAIN_WIDTH bits).

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
    localparam logic signed [PROD_WIDTH-1:0] ROUND = 1 <<< (GAIN_WIDTH - 1);
    // half an output LSB to account for rounding (otherwise dropping GAIN_WIDTH bits leads to always rounding down -> DC bias for signed ints)

    (* use_dsp = "yes" *) logic signed [PROD_WIDTH-1:0] product;   
    // use a synthesis attribute (*...*) to tell VIVADO to build the arithmetic that feeds this signal in a DSP48 block
    // This is a dedicated adder/multiplier on the chip (makes it more efficient and faster than using hundreds of LUTs)
    // Might not be strictly needed, since VIVADO could do this automatically -> TODO: Find out if (* *) is strictly needed

    always_ff @(posedge clk) begin  // use seq. logic to minimize delays
        product <= din * $signed({1'b0, gain});
        // zero-extend the gain by one bit so the multiplier sees a positive signed number
        // $signed is a sv function that casts argument to signed number
        dout    <= DATA_WIDTH'((product + ROUND) >>> GAIN_WIDTH);
        // round and then drop the fractional bits (arithmetic shift keeps the signbit at the top)
        // size cast syntax <size>'(<expression>) used to convert a value to a specific bit-width -> keep LSB and disregard MSB
        // GAIN_WIDTH shift to the right is the 2**GAIN_WIDTH division!
    end

endmodule 