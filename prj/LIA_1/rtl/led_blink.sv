// hdl/led_blink.sv
module led_blink #(
    parameter int COUNTER_WIDTH = 26,   //roughly 1.8 Hz blinking since 125 MHz clock and 2^26-1 highest counter number
    parameter int LED_BIT       = 25    // bit of counter that drives led
)(
    input  logic clk,
    output logic led_o
);

    logic [COUNTER_WIDTH-1:0] counter;

    always_ff @(posedge clk) begin
        counter <= counter + 1'b1;
    end

    assign led_o = counter[LED_BIT];

endmodule