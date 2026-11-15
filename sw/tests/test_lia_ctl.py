"""
test the lia ctl command line tool written in python (use fake backend)
"""

import argparse

import pytest

import lia_ctl
from lia_ctl import main, parse_frequency

### Test parsing frequencies first

@pytest.mark.parametrize("text, hz", [("1e6", 1e6), ("1000000", 1e6), ("2.5M", 2.5e6), ("100k", 1e5), (" 7 ", 7.0)])
def test_parse_frequency(text, hz):
    assert parse_frequency(text) == hz

@pytest.mark.parametrize("text", ["abc", "1x", "", "M"])
def test_parse_freq_rejects_bad_words(text):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_frequency(text)


### check running main part of command line tool

def test_set_and_show(capsys):
    """
    capsys captures everything printed by main() for the test to inspect it
    """
    assert main(["--fake", "--freq", "1M", "--amp", "0.5"]) == 0
    out = capsys.readouterr().out
    assert "FTW 0x020c49ba" in out
    assert "AMP 0x8000" in out
    assert "999999.989 Hz" in out

def test_no_options_only_init_reads(capsys):
    assert main(["--fake"]) == 0
    assert "FTW 0x00000000" in capsys.readouterr().out

def test_invalid_freq_returns_clean_err(capsys):
    assert main(["--fake", "--freq", "100M"]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert captured.out == ""

def test_invalid_amp_returns_clean_err(capsys):
    assert main(["--fake", "--amp", "1.5"]) == 1
    assert "error:" in capsys.readouterr().err

def test_unparseable_option_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--fake", "--freq", "abc"])
    assert exc.value.code == 2

def test_no_root_acc_gives_clean_err(monkeypatch, capsys):
    """monkeypatch temporarily replaces open_registers by a version that fails
        like /dev/mem does for a normal user; it is restored after the test."""
    def deny(fake):
        raise PermissionError("[Errno 13] Permission denied: '/dev/mem'")
    monkeypatch.setattr(lia_ctl, "open_registers", deny)
    assert main(["--freq", "1M"]) == 1
    assert "run as root" in capsys.readouterr().err
    
