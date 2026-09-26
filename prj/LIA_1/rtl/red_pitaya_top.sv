
////////////////////////////////////////////////////////////////////////////////
// Red Pitaya TOP module. It connects external pins and PS part with
// other application modules.
// Authors: Matej Oblak, Iztok Jeras
// (c) Red Pitaya  http://www.redpitaya.com
////////////////////////////////////////////////////////////////////////////////

/////////
// Adapted barebones file for dds module
/////////

/*
Top module for a barebones project.
*/
module red_pitaya_top #(
  parameter int unsigned PHASE_WIDTH = 32,
  parameter int unsigned N_STAGES = 16,
  parameter int unsigned OUT_WIDTH = 14,
  parameter int unsigned GUARD_BITS = 4
)
(
  // PS connections
  inout  logic [54-1:0] FIXED_IO_mio     ,
  inout  logic          FIXED_IO_ps_clk  ,
  inout  logic          FIXED_IO_ps_porb ,
  inout  logic          FIXED_IO_ps_srstb,
  inout  logic          FIXED_IO_ddr_vrn ,
  inout  logic          FIXED_IO_ddr_vrp ,
  // DDR
  inout  logic [15-1:0] DDR_addr   ,
  inout  logic [ 3-1:0] DDR_ba     ,
  inout  logic          DDR_cas_n  ,
  inout  logic          DDR_ck_n   ,
  inout  logic          DDR_ck_p   ,
  inout  logic          DDR_cke    ,
  inout  logic          DDR_cs_n   ,
  inout  logic [ 4-1:0] DDR_dm     ,
  inout  logic [32-1:0] DDR_dq     ,
  inout  logic [ 4-1:0] DDR_dqs_n  ,
  inout  logic [ 4-1:0] DDR_dqs_p  ,
  inout  logic          DDR_odt    ,
  inout  logic          DDR_ras_n  ,
  inout  logic          DDR_reset_n,
  inout  logic          DDR_we_n,

  // ADC clock -> used as the master timing reference for the whole DAC path (such that ADC and DAC in defined phase relation)
  // (NOT the PS7's FCLK_CLK0 as compared to LED prj)
  // Pin names/constraints should already be in red_pitaya.xdc.
  input  logic [2-1:0]  adc_clk_i,  // pick out diff. pair adc_clk_i[0] and adc_clk_i[1] ({n,p})

  // DAC ports matching shared root sdc/red_pitaya.xdc
  output logic [14-1:0] dac_dat_o,
  output logic          dac_wrt_o,
  output logic          dac_sel_o,
  output logic          dac_clk_o,
  output logic          dac_rst_o 


);

/////////////////////////////
// PS connection
/////////////////////////////

system system_i
(
  // MIO
  .FIXED_IO_mio      (FIXED_IO_mio     ),
  .FIXED_IO_ps_clk   (FIXED_IO_ps_clk  ),
  .FIXED_IO_ps_porb  (FIXED_IO_ps_porb ),
  .FIXED_IO_ps_srstb (FIXED_IO_ps_srstb),
  .FIXED_IO_ddr_vrn  (FIXED_IO_ddr_vrn ),
  .FIXED_IO_ddr_vrp  (FIXED_IO_ddr_vrp ),
  // DDR
  .DDR_addr          (DDR_addr         ),
  .DDR_ba            (DDR_ba           ),
  .DDR_cas_n         (DDR_cas_n        ),
  .DDR_ck_n          (DDR_ck_n         ),
  .DDR_ck_p          (DDR_ck_p         ),
  .DDR_cke           (DDR_cke          ),
  .DDR_cs_n          (DDR_cs_n         ),
  .DDR_dm            (DDR_dm           ),
  .DDR_dq            (DDR_dq           ),
  .DDR_dqs_n         (DDR_dqs_n        ),
  .DDR_dqs_p         (DDR_dqs_p        ),
  .DDR_odt           (DDR_odt          ),
  .DDR_ras_n         (DDR_ras_n        ),
  .DDR_reset_n       (DDR_reset_n      ),
  .DDR_we_n          (DDR_we_n         )
);



/////////////////////////////
// Clock gen
/////////////////////////////

logic adc_clk_in; // output when combine differential adc clk into single ended clk (ending in because goes into fpga!)

// Input buffer differential signaling (need buffer for drive strength since standard ffs very limited current)
// combine differential input into single ended output
IBUFDS i_clk_in (.I (adc_clk_i[1]), .IB (adc_clk_i[0]), .O (adc_clk_in));

logic pll_adc_clk, pll_dac_clk_1x, pll_dac_clk_2x, pll_dac_clk_2p, pll_locked;

red_pitaya_pll pll (
    .clk         (adc_clk_in),
    .rstn        (1'b1      ),   // TODO: include PS reset signal, until then will be held high until AXI communication with PS unit is integrated
    .clk_adc     (pll_adc_clk   ),
    .clk_dac_1x  (pll_dac_clk_1x),
    .clk_dac_2x  (pll_dac_clk_2x),
    .clk_dac_2p  (pll_dac_clk_2p),
    .clk_ser     (), // clk for daisy chain (SATA connector) serial link btw two red pitayas
    .clk_pdm     (), // slow digital PWM ("pulse width modulation")/PDM("pulse density mod") DAC outputs -> pass through external low pass RC filter!
    .pll_locked  (pll_locked)
  );

logic dac_clk_1x, dac_clk_2x, dac_clk_2p;

// Use global clk buffer, for input buffering but also routes through dedicated low-skew global clk routing network!
// BUFG bufg_adc_clk    (.O (adc_clk   ), .I (pll_adc_clk   ));
BUFG bufg_dac_clk_1x (.O (dac_clk_1x), .I (pll_dac_clk_1x));
BUFG bufg_dac_clk_2x (.O (dac_clk_2x), .I (pll_dac_clk_2x));
BUFG bufg_dac_clk_2p (.O (dac_clk_2p), .I (pll_dac_clk_2p));

// Resets given by PLL lock, so if PLL loses lock on we reset
// TODO: later include here PS reset too through OR gate (~frstn[0] | ~pll_locked)
always_ff @(posedge dac_clk_1x)
  dac_rst <= ~pll_locked;

/////////////////////////////
// DDS instant
/////////////////////////////

// temporary hardcoded frequency-tuning word for 1 MHz @ 125 MHz clk (round(1e6 / 125e6 * 2^32) = 42949673)
// TODO: Later connect phase word to register connected to PS
logic [PHASE_WIDTH-1:0] ftw;
assign ftw = 32'd42949673;

logic signed [OUT_WIDTH-1:0] dds_sin, dds_cos;

// instantiate dds module
dds_cordic #(
    .PHASE_WIDTH (PHASE_WIDTH),
    .N_STAGES    (N_STAGES   ),
    .OUT_WIDTH   (OUT_WIDTH  ),
    .GUARD_BITS  (GUARD_BITS )
) i_dds (
    .clk    (dac_clk_1x    ),
    .reset  (dac_rst  ),
    .ftw    (ftw        ),
    .sin_o  (dds_sin    ),
    .cos_o  (dds_cos    )
);

// Convert from 2s complement (DDS output) to straight binary of DAC (signed-to-unsigned) + negative-slope conversion (due to inversion at opamp)
always_ff @(posedge dac_clk_1x) begin
    dac_dat_a <= {dds_cos[14-1], ~dds_cos[14-2:0]};
    dac_dat_b <= {dds_sin[14-1], ~dds_sin[14-2:0]};
end

// ODDR (output double data rate) -> XILINX primitive 
ODDR oddr_dac_clk          (.Q(dac_clk_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2p), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_wrt          (.Q(dac_wrt_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_sel          (.Q(dac_sel_o), .D1(1'b1     ), .D2(1'b0     ), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));
ODDR oddr_dac_rst          (.Q(dac_rst_o), .D1(dac_rst  ), .D2(dac_rst  ), .C(dac_clk_1x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_dat [14-1:0] (.Q(dac_dat_o), .D1(dac_dat_b), .D2(dac_dat_a), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));



endmodule: red_pitaya_top
















