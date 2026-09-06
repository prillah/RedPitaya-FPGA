import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import numpy as np


# setup parameters for cordic module as well as some for python simulation
PHASE_WIDTH = 32
N_STAGES    = 16
OUT_WIDTH   = 14
LATENCY     = N_STAGES + 1  # cycles needed from phase input to valid output

FULL_SCALE = 2 ** (OUT_WIDTH - 1) - 1   # needed to scale output back to [-1,1] range -> divide by largest twos complement number



def deg_to_phase(theta_deg: float) -> int:  # function arg is a float that represents an angle in degrees. Output is a whole integer value
    return round(theta_deg / 360.0 * 2**PHASE_WIDTH) % 2**PHASE_WIDTH   # theta_deg / 360.0 gives us fraction of whole circle.
            # scaling by  2**PHASE_WIDTH since this is total number of states in 32 bits. Also ensures that largest number (2**N - 1) + 1 gets wrapped to start again
            # -> think dividing range into even pieces and since have 2**32 states need to divide by 2**32!!!
            # % 2**PHASE_WIDTH ensures that like in digital system the phase overflows to 0 after largest number!

async def reset_dut(dut):   # coroutine to reset the DUT in every test
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0

async def drive_and_read(dut, theta_deg: float):
    """Drives one phase value, waits out the pipeline latency and then reads the result.
    Need async def here, becuase this function should be coroutine, i.e. being able to wait for HDL simulator feedback before continuing sequentially."""

    dut.phase.value = deg_to_phase(theta_deg)   # syntax for adressing the phase input value!
    for _ in range(LATENCY):                    # let system run
        await RisingEdge(dut.clk)
    cos_raw = dut.cos_o.value.signed_integer    # interpret value as signed integer in python. In cocotb return type of dut.q.value is LogicArray or BinaryArray and not binary number/integer.
    sin_raw = dut.sin_o.value.signed_integer
    return cos_raw / FULL_SCALE, sin_raw / FULL_SCALE   # rescale into [-1,+1] range



@cocotb.test()
async def test_reset(dut):
    """Test if reset clears stage 0 (i.e. x[0], y[0], z[0]) synchronously,
    also if real, non-zero data already loaded into the pipeline registers."""

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())    # coroutine, schedules it to run in the background alongside main test function -> otherwise testbench gets forever stuck here
    dut.reset.value = 0

    # fill stage 0 with non zero data
    dut.phase.value = deg_to_phase(137.0)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert dut.x[0].value.signed_integer != 0 or dut.z[0].value.signed_integer != 0, (
        "Error: stage 0 didn't actually load data properly!"
    )

    await reset_dut(dut)

    assert dut.x[0].value.signed_integer == 0, "x[0] did not clear on reset"
    assert dut.y[0].value.signed_integer == 0, "y[0] did not clear on reset"
    assert dut.z[0].value.signed_integer == 0, "z[0] did not clear on reset"

    dut._log.info("Reset correctly clears stage 0.")



@cocotb.text()
async def test_static_angles(dut):
    """
    Feed the CORDIC module specific angles and check for its precision.
    Specifically check +90/-90 degree collision points and some others as well as 0.
    """

    # Initialize and start clk
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    test_angles = [0.0, 45.0, 89.9, 90.0, 90.1, 135.0, 179.9, 200.0,
                   269.9, 270.0, 315.0, -30.0, -89.9, -90.0, -90.1, -135.0]

    tolerance = 2.0 / FULL_SCALE  # ~1 LSB (from final truncation rounding error) plus CORDIC approximation error due to finite number of stages, i.e. accecpt error of +-2 of full integer value

    for theta in test_angles:
        cos_meas, sin_meas = await drive_and_read(dut, theta)   # need to use await with coroutines! Wait until task finished without blocking underlying simulator!
        cos_exp = np.cos(np.radians(theta))
        sin_exp = np.sin(np.radians(theta))

        assert abs(cos_meas - cos_exp) < tolerance, (
            f"cos({theta}) mismatch: got {cos_meas:.5f}, expected {cos_exp:.5f}")
        assert abs(sin_meas - sin_exp) < tolerance, (
            f"sin({theta}) mismatch: got {sin_meas:.5f}, expected {sin_exp:.5f}")

    dut._log.info("All static angle checks passed.")



async def measure_sfdr_and_noise_floor(dut, n_cycles: int, n_samples: int = 1024):
    """
    Drive a sample tone coherently, i.e. the cycles completed per sample window is a whole integer!
    Needed since FFT assumes signal perfectly repeats itself, so would get sharp features otherwise leading to broad features in
    FFT space (spectral leaking).
    n_samples: How many output samples do we capture (chosen as 1024 a power of 2 helping the FFT efficiency)
               -> n_samples must evenly divide 2^PHASE_WIDTH, such that ftw = n_cycles * 2^PHASE_WIDTH // n_samples
                  comes out exact, with zero rounding remainder guaranteeing coherent sampling.
    n_cycles: how many periods of the test tone fit inside n_sample-window.Test frequency will be: f_test = (n_cycles / n_samples) × f_clk!!!
              -> n_samples/2 tests close to Nyquist. But n_samples should not be simple multiple of n_cycles to not include some artificial periodicities from somewhere else.
              -> Choose ideally as something like a prime number
    """ 

    assert 2**PHASE_WIDTH % n_samples == 0, "n_samples must divide 2**PHASE_WIDTH exactly"
    ftw = n_cycles * 2**PHASE_WIDTH // n_samples  # fix tuning word like this such that get an exact integer, no rounding error

    await reset_dut(dut)

    phase_acc = 0   # initialize phase accum. for generating the signal later

    samples = np.empty(n_samples, dtype=np.int64)

    # Prime pipeline with LATENCY cycles of the same ramp before sampling anything. (not recorded) Needed to get smooth oscillation.
    for _ in range(LATENCY):
        phase_acc = (phase_acc + ftw) % 2**PHASE_WIDTH
        dut.phase.value = phase_acc
        await RisingEdge(dut.clk)

    # now start recording
    for k in range(n_samples):
        phase_acc = (phase_acc + ftw) % 2**PHASE_WIDTH
        dut.phase.value = phase_acc
        await RisingEdge(dut.clk)
        samples[k] = dut.sin_o.value.signed_integer

    spectrum = np.abs(np.fft.fft(samples))
    spectrum_db = 20 * np.log10(spectrum / spectrum[n_cycles] + 1e-12)
    # In an N-point FFT, the k-th bin corresponds to a freq component completing exactly k full cycles over the N-sample window.
    # ftw chosen as integer ftw = n_cycles * 2^PHASE_WIDTH // n_samples such that it completes n_cycles of full periods within the n_samples window!
    #
    # 20*log10 and not 10*log10 since want dB definition for amplitudes and not powers 10*log10(A**2)=20*log(A)
    #
    # +1e-12 is purely to avoid log(0) which is -inf! if bin is truly zero then get -240dB, not to worry about.

    















