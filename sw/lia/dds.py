"""
For high level DDS control. Inputs are in physical values (Hz and fraction of max amplitude), outputs are register values

Should work with both register backends (FakeRegisters or DevMemRegisters)
"""

from .conversions import amp_to_gain, freq_to_ftw, ftw_to_freq, gain_to_amp
from .registers import REG_AMP, REG_FTW

class Dds:
    def __init__(self, regs):
        self.regs = regs
        # regs = FakeRegisters() or DevMemRegisters()
        # then instantiate dds = Dds(regs)
    
    def set_frequency(self, freq_hz):
        """
        Sets the output frq and returns the freq the DDS produces
        """
        ftw = freq_to_ftw(freq_hz)
        self.regs.write32(REG_FTW, ftw)
        return ftw_to_freq(ftw)

    def set_amplitude(self, amplitude):
        """
        sets relative amplitude (0-1) and returns value applied to DDS
        """
        gain = amp_to_gain(amplitude)
        self.regs.write32(REG_AMP, gain)
        return gain_to_amp(gain)

    def get_frequency(self):
        return ftw_to_freq(self.regs.read32(REG_FTW))

    def get_amplitude(self):
        return gain_to_amp(self.regs.read32(REG_AMP))

    def status(self):
        """
        raw and converted register contents, used for printing
        """
        ftw = self.regs.read32(REG_FTW)
        gain = self.regs.read32(REG_AMP)
        return {"ftw": ftw, "freq_hz": ftw_to_freq(ftw), "gain": gain, "amplitude": gain_to_amp(gain)}   

    
