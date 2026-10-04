// rtl/cordic_sincos.sv
//
// Unrolled, Pipelined CORDIC (rotation mode). latency is N_STAGES
// and throughput is 1 sample/clock once filled.
//
// Range reduction using a single-bit +-180deg pre-rotation (splitting 360 domain into two 180 domains)
// Based on Andraka's CORDIC survey, Sec. 3 example 2. This lies perfectly in (~+-99.7 deg), which is CORDICs natural convergence range.
// No need for rotating back at the end, can just rotate initial vector too ([x0,y0] -> [-x0,-y0])!
//
// Interpreting phase as signed integer maps the original [0,2pi] range onto [-pi,pi], just as wanted for CORDIC.ANGLE_WIDTH
// z is then the top working_width bits startin after the signed bit of phase
// The top two bits of phase give the indication of one is in the left or right half circle, i.e. if pre rotation is needed.ANGLE_WIDTH
// Like this we need no radian conversion in the hardware.ANGLE_WIDTH
//
// Synchr. reset celaring stage 0 only -> self flushes rest since each stage only dependent on previous one
 
module cordic_sincos #(
    parameter int PHASE_WIDTH = 32,   // width of phase accumul., sets freq. resolution
    parameter int N_STAGES    = 16,   // pipeline depth sets angle precision
    parameter int OUT_WIDTH   = 14,   // to match DAC/ADC precision
    parameter int GUARD_BITS  = 4     // extra internal precision due to accumulating rounding errors (approx. log_2(N_stages))
)(
    input  logic clk,
    input  logic reset,               // synchronous and active-high
    input  logic [PHASE_WIDTH-1:0] phase,
    output logic signed [OUT_WIDTH-1:0] sin_o,
    output logic signed [OUT_WIDTH-1:0] cos_o
);

    `include "cordic_constants.svh" // reads sv header file to get x0 and also assert that the calculation of it was with the right params.
    // Elaboration-time consistency check: fires when the design is elaborated (simulation and synthesis alike)
    if (N_STAGES   != `CORDIC_GEN_N_STAGES  ||
        OUT_WIDTH  != `CORDIC_GEN_OUT_WIDTH ||
        GUARD_BITS != `CORDIC_GEN_GUARD_BITS) begin : gen_const_check
        $fatal(1, "cordic_constants.svh was generated for N_STAGES=%0d OUT_WIDTH=%0d GUARD_BITS=%0d, but this instance uses N_STAGES=%0d OUT_WIDTH=%0d GUARD_BITS=%0d; rerun scripts/gen_cordic_constants.py",
            `CORDIC_GEN_N_STAGES, `CORDIC_GEN_OUT_WIDTH, `CORDIC_GEN_GUARD_BITS,
            N_STAGES, OUT_WIDTH, GUARD_BITS);
    end

    localparam int WORK_WIDTH  = OUT_WIDTH + GUARD_BITS;    // how wide x,y,z adders and so on need to be (internal precision)

    ///////////// old code /////////////
    // -> keep it because comments are useful
    // old way to read X0
    // X0 = (K * (2**(WORK_WIDTH-1)-1)), K = prod(cos(atan(2^-i))) for i=0,...,15.
    // computed by scripts/gen_cordic_constants.py for chosen N_STAGES.
    // Done to gain-precorrect so no output multiplier is needed after the pipeline.
    // localparam signed [WORK_WIDTH-1:0] X0 = 18'sd79593;  // N_STAGES=16, OUT_WIDTH=14, GUARD_BITS=4

    // old way to read atan lut
    //logic signed [WORK_WIDTH-1:0] atan_lut [0:N_STAGES-1];   // declaring memory array: logic signed [packed dimension, i.e. width of one element]   atan_lut   [unpacked dimension, i.e. how many elements, atan_lut[i]]
    //initial $readmemh("atan_table.mem", atan_lut);
    // initial -> block that runs exactly once, at the very start of time, not every clock edge
    // $readmemh -> built-in verilog "system task" ($ marks built in utility). reads text file with each line being a hexadecimal number
    //           -> loads them sequentially into the array specified as atan_lut, starting at index 0
    //////////////////////////////////

    // atan LUT: constants sliced out of ATAN_FLAT, generated into cordic_constants.svh
    // Keep as a signed array st the stage logic below (z[i] -/+ atan_lut[i]) is unchanged
    logic signed [WORK_WIDTH-1:0] atan_lut [0:N_STAGES-1];

    generate
        for (genvar k = 0; k < N_STAGES; k++) begin : atan_const
            assign atan_lut[k] = ATAN_FLAT[k*WORK_WIDTH +: WORK_WIDTH];
        end
    endgenerate

    // If top two bits of the phase are equal (00 or 11) then angle is already in [-pi/2, pi/2] range.
    // If they differ then need to prerotate -> is exactly XOR gate.
    logic need_prerotate;
    assign need_prerotate = phase[PHASE_WIDTH-1] ^ phase[PHASE_WIDTH-2];    // XOR of top two bits

    // initialize pipeline register arrays for each of the N CORDIC stages (index 0 = initial condition) 
    // gives structure of the bit-parallel unrolled CORDIC algorithm
    logic signed [WORK_WIDTH-1:0] x [0:N_STAGES];
    logic signed [WORK_WIDTH-1:0] y [0:N_STAGES];
    logic signed [WORK_WIDTH-1:0] z [0:N_STAGES];
    
    // stage number 0, the initialization step of the CORDIC -> TODO: Find out if could save 1 clock cycle of latency by making this an always_comb block?
    always_ff @(posedge clk) begin
        if (reset) begin
            x[0] <= '0;
            y[0] <= '0;
            z[0] <= '0;
        end else begin
            x[0] <= need_prerotate ? -X0 : X0;  // Initial scaled value accounting for CORDIC gain and size of x (done in gen_cordic_constants.py). If prerotation is needed, flip sign of initial vector -> then no need to rotate back later.
            y[0] <= '0; // Initialize as 0 to get just sine value ('0 is SystemVerilog unsized literal, meaning "the value zero, sized to match whatever context it's used in")
            z[0] <= phase[PHASE_WIDTH-2 -: WORK_WIDTH]; // interpreting phase as signe -> range [-pi,pi] -> dropping sign bit of phase -> range [-pi/2,pi/2], exactly what is needed for CORDIC!
        end
    end

    genvar i;   // variable only existing for compile-time book-keeping. After VIVADO built circuit there is no variable i and no for loop
    generate    // for procedurally creating hardware blocks, done at compile time (for loops run at runtime inside a always_ff or intital block!)
        for (i=0; i<N_STAGES; i++) begin : cordic_stage // creates a named hierarchical scope, a single stage can be addressed by cordic_stage [0] e.g. in GTKWave or VIVADO!
            always_ff @(posedge clk) begin
                if (z[i] >= 0) begin
                    x[i+1] <= x[i] - (y[i] >>> i);  // division by 2^n is right bit shift by n bits
                    y[i+1] <= y[i] + (x[i] >>> i);
                    z[i+1] <= z[i] - atan_lut[i];
                end else begin
                    x[i+1] <= x[i] + (y[i] >>> i);  // flip sign
                    y[i+1] <= y[i] - (x[i] >>> i);
                    z[i+1] <= z[i] + atan_lut[i];
                end
            end
        end
    endgenerate

    // final stage, assign the outputs -> just truncation for DAC/ADC width (no rotation or so needed)
    always_comb begin
        cos_o = x[N_STAGES][WORK_WIDTH-1 -: OUT_WIDTH];
        sin_o = y[N_STAGES][WORK_WIDTH-1 -: OUT_WIDTH];
    end
    // TODO: Be aware of the fact that this truncation is like floor() in python and adds a dc offset (since we work with 2s complement)!!!

    // Would need to add something like the following in order to remove the DC bias
    // localparam signed [WORK_WIDTH-1:0] ROUND_CONST = 1 <<< (GUARD_BITS-1);
    // localparam signed [WORK_WIDTH-1:0] WORK_MAX    = {1'b0, {(WORK_WIDTH-1){1'b1}}}; // max positive value, e.g. 131071

    // logic signed [WORK_WIDTH:0] x_sum, y_sum;   // one extra bit — can't silently wrap here
    // logic signed [WORK_WIDTH-1:0] x_rnd, y_rnd;

    // always_comb begin
    //     x_sum = {x[N_STAGES][WORK_WIDTH-1], x[N_STAGES]} + ROUND_CONST; // sign-extend, then add
    //     y_sum = {y[N_STAGES][WORK_WIDTH-1], y[N_STAGES]} + ROUND_CONST;

        // saturate back down in case rounding pushed us past full scale
    //     x_rnd = (x_sum > WORK_MAX) ? WORK_MAX : x_sum[WORK_WIDTH-1:0];
    //     y_rnd = (y_sum > WORK_MAX) ? WORK_MAX : y_sum[WORK_WIDTH-1:0];

    //     cos_o = x_rnd[WORK_WIDTH-1 -: OUT_WIDTH];
    //     sin_o = y_rnd[WORK_WIDTH-1 -: OUT_WIDTH];
    // end

endmodule



