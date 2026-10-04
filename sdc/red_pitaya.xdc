set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports {adc_clk_i[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {dac_dat_o[*]}]
set_property SLEW FAST [get_ports {dac_dat_o[*]}]
set_property DRIVE 8 [get_ports {dac_dat_o[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports dac_*_o]
set_property SLEW FAST [get_ports dac_*_o]
set_property DRIVE 8 [get_ports dac_*_o]
#
# $Id: red_pitaya.xdc 961 2014-01-21 11:40:39Z matej.oblak $
#
# @brief Red Pitaya location constraints.
#
# @Author Matej Oblak
#
# (c) Red Pitaya  http://www.redpitaya.com
#

############################################################################
# IO constraints                                                           #
############################################################################

### ADC

# ADC data
# IOSTANDARD defines the electrical signaling convention for that pin: voltage levels, single-ended vs. differential
# with LVCMOS33 encoding just ordinary single-ended CMOS logic at 3.3 V
# IOB TRUE forces the flip-flop capturing this signal to be physically implemented
# inside the pin's own dedicated I/O logic, rather than in the general FPGA fabric somewhere nearby.

# ADC 0 data
# {adc_dat_i[0][0]} is name chosen for signal -> one bit of one of ADC channels data port (how HDL refers to that wire)
# V17 is fixed physical location (one of the pins going out of the chip and onto the PCB, thus package pin)
# "take the port in my design named adc_dat_i[0][0], and route it out to the physical contact at package location V17."
# PACKAGE_PIN is the property name

# ADC 1 data

# DIFF_HSTL_I_18 for differential, High Speed Transceiver Logic,nominal signaling voltage, 1.8 V
# This is the forward clk sent to FPGA guaranteed to be correctly phase-aligned with sent data
# -> this is very timing critical so use differential signals
# -> diff pair adc_clk_i[0] and adc_clk_i[1]

# Output ADC clock
#set_property IOB        TRUE     [get_ports {adc_clk_o[*]}]
# adc_clk_o generated inside the FPGA and sent out to the ADC chip, master sampling clock
# telling ADC to sample now and do it a given freqiuency -> no need for DIFF IOSTANDARD because ADC also handles inside how to sample cleanly


# SLEW, how quickly the pin transitions between logic levels (SLOW, FAST)
# DRIVE, output driver's current strength, in milliamps


# ADC clock stabilizer

### DAC

# data
#set_property IOB        TRUE     [get_ports {dac_dat_o[*]}]


# control
#set_property IOB        TRUE     [get_ports dac_*_o]


### PWM DAC


### XADC
#AD0
#AD1
#AD8
#AD9
#V_0

### Expansion connector



# The -dict flag is purely a syntactic convenience — it lets you set multiple
# properties on the same port in one single command, by passing a Tcl dictionary

#set_property PULLDOWN TRUE [get_ports {exp_p_io[0]}]
#set_property PULLDOWN TRUE [get_ports {exp_n_io[0]}]
#set_property PULLUP   TRUE [get_ports {exp_p_io[7]}]
#set_property PULLUP   TRUE [get_ports {exp_n_io[7]}]


### LED


############################################################################
# Clock constraints                                                        #
############################################################################

#NET "adc_clk" TNM_NET = "adc_clk";
#TIMESPEC TS_adc_clk = PERIOD "adc_clk" 125 MHz;

create_clock -period 8.000 -name adc_clk [get_ports {adc_clk_i[1]}]



create_clock -period 8.000 -name dac_clk_o [get_ports dac_clk_o]

set_false_path -from [get_clocks adc_clk] -to [get_clocks dac_clk_o]


# timing constraint, not an electrical/pin one tells Vivado's static timing analyzer: don't bother checking
# setup/hold timing for any signal path that starts in the adc_clk domain and ends in the dac_clk_o domain
# because these are two independently-generated clocks

