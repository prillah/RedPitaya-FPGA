import cocotb  
from cocotb.clock import Clock # helper class for clock
from cocotb.triggers import RisingEdge, Timer # functions to tell python to pause execution and wait for some simulator event like rising edge



@cocotb.test() # decorator that tells function below is executable test case
async def test_led_toggles_at_expected_cycle(dut):
    """Check if led_o goes high after 2**LED_BIT clock edges, and
    back low after another 2**LED_BIT edges.
 
    LED_BIT here must match the -GLED_BIT override in the Makefile - the
    simulation uses a small counter width so the toggle happens within a
    handful of cycles instead of the 2**25 needed on real hardware.
    """
 
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
 
    # No reset signal exists and Verilator initializes registers with 0 by default.
    await RisingEdge(dut.clk)

    led_bit = 5  # match LED_BIT in the Makefile's EXTRA_ARGS
    toggle_period = 2 ** led_bit
 
    assert dut.led_o.value == 0, "error: led_o should start low" 

    for _ in range(toggle_period):
        await RisingEdge(dut.clk)

    assert dut.led_o.value == 1, (
        f"error: led_o should be high after {toggle_period} clock edges, "
        f"but got {dut.led_o.value}"
    )
 
    for _ in range(toggle_period):
        await RisingEdge(dut.clk)
 
    assert dut.led_o.value == 0, (
        f"error: led_o should be low after {2*toggle_period} clock edges, "
        f"but got {dut.led_o.value}"
    )
 
    dut._log.info("***LED toggle timing verified successfully!***")








