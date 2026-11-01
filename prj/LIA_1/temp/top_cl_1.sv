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
// Clock gen
/////////////////////////////

logic adc_clk_in; // output when combine differential adc clk into single ended clk (ending in because goes into fpga!)

// Input buffer differential signaling (need buffer for drive strength since standard ffs very limited current)
// combine differential input into single ended output
IBUFDS i_clk_in (.I (adc_clk_i[1]), .IB (adc_clk_i[0]), .O (adc_clk_in));

logic pll_adc_clk, pll_dac_clk_1x, pll_dac_clk_2x, pll_dac_clk_2p, pll_locked;

red_pitaya_pll pll (
    .clk         (adc_clk_in),
    .rstn        (1'b1      ),   // LIA: deliberately never reset by the PS: this PLL also makes the AXI clock
                                 // (M_AXI_GP0_ACLK). Stopping it would freeze any CPU access to the registers.
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
// LIA: the PS reset is handled by proc_sys_reset_lia in the block design and resets the registers
// (FTW = 0, AMP = 0 -> silent output). The DDS/DAC reset stays tied to the PLL lock only.
logic dac_rst;   // active-high

always_ff @(posedge dac_clk_1x)
  dac_rst <= ~pll_locked;

/////////////////////////////
// PS connection + AXI register file
/////////////////////////////
// LIA: moved below the clock generation, since it now uses dac_clk_1x and pll_locked
// (SystemVerilog needs a signal declared before it is used; otherwise an implicit 1-bit net is created)

// AXI4-Lite bus from the block design (smartconnect behind PS GP0) to lia_axil_regs.
// Address is 32 bits wide, but the smartconnect already decoded the 4 KB window, so only bits [3:0] matter.
logic [32-1:0] lia_awaddr, lia_araddr, lia_wdata, lia_rdata;
logic [ 4-1:0] lia_wstrb;
logic [ 2-1:0] lia_bresp, lia_rresp;
logic          lia_awvalid, lia_awready, lia_wvalid, lia_wready, lia_bvalid, lia_bready;
logic          lia_arvalid, lia_arready, lia_rvalid, lia_rready;
logic          lia_aresetn;   // synchronized, active low, from proc_sys_reset_lia

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
  .DDR_we_n          (DDR_we_n         ),
  // LIA: clock and reset of the whole PS -> PL register path (one clock domain with the DDS)
  .M_AXI_GP0_ACLK    (dac_clk_1x       ),
  .pll_locked_i      (pll_locked       ),
  .lia_aresetn_o     (lia_aresetn      ),
  // LIA: AXI4-Lite master port (AWPROT/ARPROT left open, the slave ignores them)
  .M_AXI_LIA_awaddr  (lia_awaddr       ),
  .M_AXI_LIA_awvalid (lia_awvalid      ),
  .M_AXI_LIA_awready (lia_awready      ),
  .M_AXI_LIA_wdata   (lia_wdata        ),
  .M_AXI_LIA_wstrb   (lia_wstrb        ),
  .M_AXI_LIA_wvalid  (lia_wvalid       ),
  .M_AXI_LIA_wready  (lia_wready       ),
  .M_AXI_LIA_bresp   (lia_bresp        ),
  .M_AXI_LIA_bvalid  (lia_bvalid       ),
  .M_AXI_LIA_bready  (lia_bready       ),
  .M_AXI_LIA_araddr  (lia_araddr       ),
  .M_AXI_LIA_arvalid (lia_arvalid      ),
  .M_AXI_LIA_arready (lia_arready      ),
  .M_AXI_LIA_rdata   (lia_rdata        ),
  .M_AXI_LIA_rresp   (lia_rresp        ),
  .M_AXI_LIA_rvalid  (lia_rvalid       ),
  .M_AXI_LIA_rready  (lia_rready       )
);

logic [PHASE_WIDTH-1:0] ftw;   // from register 0x00
logic [16-1:0]          amp;   // from register 0x04

lia_axil_regs #(
    .C_S_AXI_DATA_WIDTH (32),
    .C_S_AXI_ADDR_WIDTH (4 )
) i_regs (
    .ftw_o         (ftw              ),
    .amp_o         (amp              ),
    .S_AXI_ACLK    (dac_clk_1x       ),
    .S_AXI_ARESETN (lia_aresetn      ),
    .S_AXI_AWADDR  (lia_awaddr[3:0]  ),
    .S_AXI_AWPROT  (3'b000           ),
    .S_AXI_AWVALID (lia_awvalid      ),
    .S_AXI_AWREADY (lia_awready      ),
    .S_AXI_WDATA   (lia_wdata        ),
    .S_AXI_WSTRB   (lia_wstrb        ),
    .S_AXI_WVALID  (lia_wvalid       ),
    .S_AXI_WREADY  (lia_wready       ),
    .S_AXI_BRESP   (lia_bresp        ),
    .S_AXI_BVALID  (lia_bvalid       ),
    .S_AXI_BREADY  (lia_bready       ),
    .S_AXI_ARADDR  (lia_araddr[3:0]  ),
    .S_AXI_ARPROT  (3'b000           ),
    .S_AXI_ARVALID (lia_arvalid      ),
    .S_AXI_ARREADY (lia_arready      ),
    .S_AXI_RDATA   (lia_rdata        ),
    .S_AXI_RRESP   (lia_rresp        ),
    .S_AXI_RVALID  (lia_rvalid       ),
    .S_AXI_RREADY  (lia_rready       )
);

/////////////////////////////
// DDS instant
/////////////////////////////

// LIA: ftw now comes from register 0x00 (was hardcoded 32'd34359738)
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
logic [14-1:0] dac_dat_a, dac_dat_b;

// LIA: amplitude scaling with gain from register 0x04 (0 = silent, 0xFFFF = full scale).
// Both channels get their own scaler, so both paths have the same latency (2 cycles) and
// sin/cos stay exactly 90 degrees apart.
logic signed [OUT_WIDTH-1:0] cos_scaled, sin_scaled;

amp_scale #(.DATA_WIDTH(OUT_WIDTH), .GAIN_WIDTH(16)) i_amp_cos (
    .clk (dac_clk_1x), .din (dds_cos), .gain (amp), .dout (cos_scaled));
amp_scale #(.DATA_WIDTH(OUT_WIDTH), .GAIN_WIDTH(16)) i_amp_sin (
    .clk (dac_clk_1x), .din (dds_sin), .gain (amp), .dout (sin_scaled));

always_ff @(posedge dac_clk_1x) begin
    dac_dat_a <= {cos_scaled[14-1], ~cos_scaled[14-2:0]};   // LIA: was dds_cos
    dac_dat_b <= {sin_scaled[14-1], ~sin_scaled[14-2:0]};   // LIA: was dds_sin
end

// ODDR (output double data rate) -> XILINX primitive 
ODDR oddr_dac_clk          (.Q(dac_clk_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2p), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_wrt          (.Q(dac_wrt_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_sel          (.Q(dac_sel_o), .D1(1'b1     ), .D2(1'b0     ), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));
ODDR oddr_dac_rst          (.Q(dac_rst_o), .D1(dac_rst  ), .D2(dac_rst  ), .C(dac_clk_1x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_dat [14-1:0] (.Q(dac_dat_o), .D1(dac_dat_b), .D2(dac_dat_a), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));



endmodule: red_pitaya_top