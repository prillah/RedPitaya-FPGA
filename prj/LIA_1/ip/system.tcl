
################################################################
# This is a generated script based on design: system
#
# Though there are limitations about the generated script,
# the main purpose of this utility is to make learning
# IP Integrator Tcl commands easier.
################################################################

namespace eval _tcl {
proc get_script_folder {} {
   set script_path [file normalize [info script]]
   set script_folder [file dirname $script_path]
   return $script_folder
}
}
variable script_folder
set script_folder [_tcl::get_script_folder]

if {![info exists ::cpu_part]} {
    error "Variable cpu_part not defined"
}

if {![info exists ::bus_w_bit]} {
    error "Variable bus_w_bit not defined"
}

if {![info exists ::dram_w_bit]} {
    error "Variable dram_w_bit not defined"
}

if {![info exists ::gpio_width]} {
    error "Variable gpio_width not defined"
}


################################################################
# Check if script is running in correct Vivado version.
################################################################
set scripts_vivado_version 2025.1
set current_vivado_version [version -short]

if { [string first $scripts_vivado_version $current_vivado_version] == -1 } {
   puts ""
   catch {common::send_gid_msg -ssname BD::TCL -id 2041 -severity "ERROR" "This script was generated using Vivado <$scripts_vivado_version> and is being run in <$current_vivado_version> of Vivado. Please run the script in Vivado <$scripts_vivado_version> then open the design in Vivado <$current_vivado_version>. Upgrade the design by running \"Tools => Report => Report IP Status...\", then run write_bd_tcl to create an updated script."}

   return 1
}

################################################################
# START
################################################################

# To test this script, run the following commands from Vivado Tcl console:
# source system_script.tcl

# If there is no project opened, this script will create a
# project, but make sure you do not have an existing project
# <./myproj/project_1.xpr> in the current working folder.

set list_projs [get_projects -quiet]
if { $list_projs eq "" } {
   create_project project_1 myproj -part $::cpu_part
}


# CHANGE DESIGN NAME HERE
variable design_name
set design_name system

# If you do not already have an existing IP Integrator design open,
# you can create a design using the following command:
#    create_bd_design $design_name

# Creating design if needed
set errMsg ""
set nRet 0

set cur_design [current_bd_design -quiet]
set list_cells [get_bd_cells -quiet]

if { ${design_name} eq "" } {
   # USE CASES:
   #    1) Design_name not set

   set errMsg "Please set the variable <design_name> to a non-empty value."
   set nRet 1

} elseif { ${cur_design} ne "" && ${list_cells} eq "" } {
   # USE CASES:
   #    2): Current design opened AND is empty AND names same.
   #    3): Current design opened AND is empty AND names diff; design_name NOT in project.
   #    4): Current design opened AND is empty AND names diff; design_name exists in project.

   if { $cur_design ne $design_name } {
      common::send_gid_msg -ssname BD::TCL -id 2001 -severity "INFO" "Changing value of <design_name> from <$design_name> to <$cur_design> since current design is empty."
      set design_name [get_property NAME $cur_design]
   }
   common::send_gid_msg -ssname BD::TCL -id 2002 -severity "INFO" "Constructing design in IPI design <$cur_design>..."

} elseif { ${cur_design} ne "" && $list_cells ne "" && $cur_design eq $design_name } {
   # USE CASES:
   #    5) Current design opened AND has components AND same names.

   set errMsg "Design <$design_name> already exists in your project, please set the variable <design_name> to another value."
   set nRet 1
} elseif { [get_files -quiet ${design_name}.bd] ne "" } {
   # USE CASES:
   #    6) Current opened design, has components, but diff names, design_name exists in project.
   #    7) No opened design, design_name exists in project.

   set errMsg "Design <$design_name> already exists in your project, please set the variable <design_name> to another value."
   set nRet 2

} else {
   # USE CASES:
   #    8) No opened design, design_name not in project.
   #    9) Current opened design, has components, but diff names, design_name not in project.

   common::send_gid_msg -ssname BD::TCL -id 2003 -severity "INFO" "Currently there is no design <$design_name> in project, so creating one..."

   create_bd_design $design_name

   common::send_gid_msg -ssname BD::TCL -id 2004 -severity "INFO" "Making design <$design_name> as current_bd_design."
   current_bd_design $design_name

}

common::send_gid_msg -ssname BD::TCL -id 2005 -severity "INFO" "Currently the variable <design_name> is equal to \"$design_name\"."

if { $nRet != 0 } {
   catch {common::send_gid_msg -ssname BD::TCL -id 2006 -severity "ERROR" $errMsg}
   return $nRet
}

set bCheckIPsPassed 1
##################################################################
# CHECK IPs
##################################################################
set bCheckIPs 1
if { $bCheckIPs == 1 } {
   set list_check_ips "\
xilinx.com:ip:processing_system7:5.5\
xilinx.com:ip:proc_sys_reset:5.0\
"

   set list_ips_missing ""
   common::send_gid_msg -ssname BD::TCL -id 2011 -severity "INFO" "Checking if the following IPs exist in the project's IP catalog: $list_check_ips ."

   foreach ip_vlnv $list_check_ips {
      set ip_obj [get_ipdefs -all $ip_vlnv]
      if { $ip_obj eq "" } {
         lappend list_ips_missing $ip_vlnv
      }
   }

   if { $list_ips_missing ne "" } {
      catch {common::send_gid_msg -ssname BD::TCL -id 2012 -severity "ERROR" "The following IPs are not found in the IP Catalog:\n  $list_ips_missing\n\nResolution: Please add the repository containing the IP(s) to the project." }
      set bCheckIPsPassed 0
   }

}

if { $bCheckIPsPassed != 1 } {
  common::send_gid_msg -ssname BD::TCL -id 2023 -severity "WARNING" "Will not continue with creation of design due to the error(s) above."
  return 3
}

##################################################################
# DESIGN PROCs
##################################################################



# Procedure to create entire design; Provide argument to make
# procedure reusable. If parentCell is "", will use root.
proc create_root_design { parentCell } {

  variable script_folder
  variable design_name

  if { $parentCell eq "" } {
     set parentCell [get_bd_cells /]
  }

  # Get object for parentCell
  set parentObj [get_bd_cells $parentCell]
  if { $parentObj == "" } {
     catch {common::send_gid_msg -ssname BD::TCL -id 2090 -severity "ERROR" "Unable to find parent cell <$parentCell>!"}
     return
  }

  # Make sure parentObj is hier blk
  set parentType [get_property TYPE $parentObj]
  if { $parentType ne "hier" } {
     catch {common::send_gid_msg -ssname BD::TCL -id 2091 -severity "ERROR" "Parent <$parentObj> has TYPE = <$parentType>. Expected to be <hier>."}
     return
  }

  # Save current instance; Restore later
  set oldCurInst [current_bd_instance .]

  # Set parent object as current
  current_bd_instance $parentObj


  # Create interface ports
  set DDR [ create_bd_intf_port -mode Master -vlnv xilinx.com:interface:ddrx_rtl:1.0 DDR ]

  set FIXED_IO [ create_bd_intf_port -mode Master -vlnv xilinx.com:display_processing_system7:fixedio_rtl:1.0 FIXED_IO ]


  # Create ports
  set M_AXI_GP0_ACLK [ create_bd_port -dir I -type clk -freq_hz 125000000 M_AXI_GP0_ACLK ]

  set_property -dict [ list \
   CONFIG.ASSOCIATED_BUSIF {M_AXI_GP0} \
 ] $M_AXI_GP0_ACLK



  ####################################

  # set FCLK_CLK0 [ create_bd_port -dir O -type clk -freq_hz 125000000 FCLK_CLK0 ]
  set FCLK_CLK0 [ create_bd_port -dir O -type clk FCLK_CLK0 ]

  # set FCLK_CLK0 [ ... ] -> [] are the return value, so set FCLK.. to whatever gets returned
  # create_bd_port -> creates new ordinary (not bundled) external  port on the currently active block design.
  # -dir O -> direction, from the block design's own perspective (O = output, this port sends a signal out of the block design, I for input, IO for bidirectional).
  # -type clk -> this ports role is a clock not just generic data.
  # -freq_hz 125000000 -> frequency as metadata on the port (other IP blocks' "block automation" can read this to auto-configure themselves correctly) (what .xdc timing constraints (create_clock) are checked against)
  # FCLK_CLK0 -> Name given to that new port.

  ####################################


  set S_AXI_HP0_aclk [ create_bd_port -dir I -type clk -freq_hz 125000000 S_AXI_HP0_aclk ]
  set S_AXI_HP1_aclk [ create_bd_port -dir I -type clk -freq_hz 125000000 S_AXI_HP1_aclk ]
  set S_AXI_HP2_aclk [ create_bd_port -dir I -type clk -freq_hz 125000000 S_AXI_HP2_aclk ]
  set S_AXI_HP3_aclk [ create_bd_port -dir I -type clk -freq_hz 125000000 S_AXI_HP3_aclk ]

  source ip/ps7_config.tcl

  # Create instance: processing_system7, and set properties
  set processing_system7 [ create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7 ]

  configure_ps7 $processing_system7

  # Create instance: proc_sys_reset_0, and set properties
  set proc_sys_reset_0 [ create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0 ]

  # Create instance: proc_sys_reset_1, and set properties
  set proc_sys_reset_1 [ create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_1 ]

  # Create instance: proc_sys_reset_2, and set properties
  set proc_sys_reset_2 [ create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_2 ]

  # Create instance: proc_sys_reset_3, and set properties
  set proc_sys_reset_3 [ create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_3 ]



  ####################################

  connect_bd_net -net processing_system7_FCLK_CLK0  [get_bd_pins processing_system7/FCLK_CLK0] \
  [get_bd_pins proc_sys_reset_0/slowest_sync_clk] \
  [get_bd_ports FCLK_CLK0]

  # connect_bd_net -> creates a net (a wire, electrically. joins together any pin/port reference passed to it.
  # Pass it three references, and all three become the same signal, not three separate point-to-point wires.
  # -net processing_system7_FCLK_CLK0 -> optional flag giving this net an explicit name, rather than letting Vivado auto-generate one.
  # shows up labeling the wire in the GUI's schematic view, and if a net with that name already exists passing the same -net name extends that existing net to include the new endpoint (imagine in the GUI).
  # [get_bd_pins processing_system7/FCLK_CLK0] -> a query, find the pin named FCLK_CLK0 on the cell named processing_system7.
  # This is the actual source of the clock signal — a pin on an instantiated IP block inside the design.
  # Rmk: -> A cell is just Vivado's term for one instantiated IP block inside a block design — the schematic-diagram equivalent of a module instance in your RTL
  #      -> When you drag the Zynq PS7 IP onto the canvas, that instance becomes a cell named processing_system7
  #      -> When you drag in a "Processor System Reset" IP, that instance becomes a cell named proc_sys_reset_0.
  #      -> get_bd_pins <cell>/<pin> is how you address "this specific pin, on this specific instance" — exactly like dut.led_blink_i.counter would address a signal inside a specific instance in a simulation waveform
  #      -> "Slowest sync clk" reads as "the (slowest) clock to synchronize to" — a clock you'd feed into a synchronizer, not one it would produce. Thus is an input port
  # [get_bd_pins proc_sys_reset_0/slowest_sync_clk] -> reset generator's clock input.
  # [get_bd_ports FCLK_CLK0] -> a reference to the new external port just created. 
  # "pins" live on cells/IP instances inside the block design , while "ports" are on the block design's own outer boundary (what becomes visible to whatever instantiates system from outside, i.e. red_pitaya_top.sv)
  # 
  # "connect the PS7's actual FCLK_CLK0 output pin, the reset generator's existing clock input pin, and the new external port you just created, all together as one single wire."

  ####################################



  # Create interface connections
  connect_bd_intf_net -intf_net processing_system7_0_ddr [get_bd_intf_ports DDR] [get_bd_intf_pins processing_system7/DDR]
  connect_bd_intf_net -intf_net processing_system7_0_fixed_io [get_bd_intf_ports FIXED_IO] [get_bd_intf_pins processing_system7/FIXED_IO]

  # Create port connections
  connect_bd_net -net m_axi_gp0_aclk_1  [get_bd_ports M_AXI_GP0_ACLK] \
  [get_bd_pins processing_system7/M_AXI_GP0_ACLK]

  connect_bd_net -net processing_system7_0_fclk_clk3  [get_bd_pins processing_system7/FCLK_CLK3] \
  [get_bd_pins processing_system7/M_AXI_GP1_ACLK] \
  [get_bd_pins proc_sys_reset_3/slowest_sync_clk]

  # connect_bd_net -net processing_system7_FCLK_CLK0  [get_bd_pins processing_system7/FCLK_CLK0] \
  # [get_bd_pins proc_sys_reset_0/slowest_sync_clk]

  connect_bd_net -net processing_system7_FCLK_CLK1  [get_bd_pins processing_system7/FCLK_CLK1] \
  [get_bd_pins proc_sys_reset_2/slowest_sync_clk]

  connect_bd_net -net processing_system7_FCLK_CLK2  [get_bd_pins processing_system7/FCLK_CLK2] \
  [get_bd_pins proc_sys_reset_1/slowest_sync_clk]

  connect_bd_net -net processing_system7_FCLK_RESET0_N  [get_bd_pins processing_system7/FCLK_RESET0_N] \
  [get_bd_pins proc_sys_reset_0/ext_reset_in]

  connect_bd_net -net processing_system7_FCLK_RESET1_N  [get_bd_pins processing_system7/FCLK_RESET1_N] \
  [get_bd_pins proc_sys_reset_2/ext_reset_in]

  connect_bd_net -net processing_system7_FCLK_RESET2_N  [get_bd_pins processing_system7/FCLK_RESET2_N] \
  [get_bd_pins proc_sys_reset_1/ext_reset_in]

  connect_bd_net -net processing_system7_FCLK_RESET3_N  [get_bd_pins processing_system7/FCLK_RESET3_N] \
  [get_bd_pins proc_sys_reset_3/ext_reset_in]

  connect_bd_net -net s_axi_hp0_aclk  [get_bd_ports S_AXI_HP0_aclk] \
  [get_bd_pins processing_system7/S_AXI_GP0_ACLK] \
  [get_bd_pins processing_system7/S_AXI_HP0_ACLK]

  connect_bd_net -net s_axi_hp1_aclk  [get_bd_ports S_AXI_HP1_aclk] \
  [get_bd_pins processing_system7/S_AXI_HP1_ACLK]

  connect_bd_net -net s_axi_hp2_aclk  [get_bd_ports S_AXI_HP2_aclk] \
  [get_bd_pins processing_system7/S_AXI_HP2_ACLK]

  connect_bd_net -net s_axi_hp3_aclk  [get_bd_ports S_AXI_HP3_aclk] \
  [get_bd_pins processing_system7/S_AXI_HP3_ACLK]

  # Create address segments


  # Restore current instance
  current_bd_instance $oldCurInst

  validate_bd_design

  set_property pfm_name "redpitaya_platform" [get_files -all {system.bd}]

  set_property PFM.CLOCK { \
     FCLK_CLK0 {id "0" is_default "true" proc_sys_reset "proc_sys_reset_0"} \
  } [get_bd_cells /processing_system7]


  set_property PFM.AXI_PORT { \
    M_AXI_GP0 {memport "M_AXI_GP"} \
    S_AXI_HP0 {memport "S_AXI_HP"} \
  } [get_bd_cells /processing_system7]

  save_bd_design
}
# End of create_root_design()


##################################################################
# MAIN FLOW
##################################################################

create_root_design ""


