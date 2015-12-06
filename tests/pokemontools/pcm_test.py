from pokemontools import pcm

from nose.tools import raises
import unittest

#####################################################
# Tests for pcm.unpack_sample                       #
#####################################################
def test_unpack_sample_width1_shouldpass():
    sample_width = 1
    value = '\x48'
    expected = 0x48
    actual = pcm.unpack_sample(value, sample_width)
    assert expected == actual

def test_unpack_sample_width1_shouldfail():
    sample_width = 1
    value = '\x48'
    incorrect_result = 0x84
    actual = pcm.unpack_sample(value, sample_width)
    assert incorrect_result != actual

def test_unpack_sample_width2_shouldpass():
    sample_width = 2
    value = '\x40\x30'
    expected = 0x3040
    actual = pcm.unpack_sample(value, sample_width)
    assert expected == actual

def test_unpack_sample_width2_shouldfail():
    sample_width = 2
    value = '\x30\x40'
    incorrect_result = 0x3040
    actual = pcm.unpack_sample(value, sample_width)
    assert incorrect_result != actual

@raises(Exception)
def test_unpack_sample_sample_width3_shouldFail():
    sample_width = 3
    value = '\x30\x40\x50'
    # Should throw exception because sample width of 3 isn't supported.
    pcm.unpack_sample(value, sample_width)

@raises(Exception)
def test_unpack_sample_mismatched_sizes_throws_exception():
    sample_width = 1
    value = '\x00\xff'
    # Should throw exception because sample width and size of value are mismatched.
    actual = pcm.unpack_sample(value, sample_width)


#####################################################
# Tests for pcm.resample                            #
#####################################################
def test_resample_sampleratio1_shouldpass():
    base_sample_rate = 22050
    sample_rate = base_sample_rate
    samples  = [1, 2, 3, 4, 5, 6, 7, 8]
    expected = [1, 2, 3, 4, 5, 6, 7, 8]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert expected == actual

def test_resample_sampleratio1_shouldfail():
    base_sample_rate = 22050
    sample_rate = base_sample_rate
    samples  = [8, 7, 6, 5, 4, 3, 2, 1]
    incorrect_result = [1, 2, 3, 4, 5, 6, 7, 8]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert incorrect_result != actual

def test_resample_sampleratio2_shouldpass():
    base_sample_rate = 22050
    sample_rate = base_sample_rate * 2
    samples  = [1, 2, 3, 4, 5, 6, 7, 8]
    expected = [1, 3, 5, 7]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert expected == actual

def test_resample_sampleratio2_shouldfail():
    base_sample_rate = 22050
    sample_rate = base_sample_rate * 2
    samples  = [1, 2, 3, 4, 5, 6, 7, 8]
    incorrect_result = [2, 4, 6, 8]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert incorrect_result != actual

def test_resample_sampleratio_half_shouldpass():
    base_sample_rate = 22050
    sample_rate = base_sample_rate / 2
    samples  = [1, 2, 3, 4]
    expected = [1, 1, 2, 2, 3, 3, 4, 4]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert expected == actual

def test_resample_sampleratio_half_shouldfail():
    base_sample_rate = 22050
    sample_rate = base_sample_rate / 2
    samples  = [1, 2, 3, 4]
    incorrect_result = [1, 2, 2, 2, 3, 3, 4, 4]
    actual = pcm.resample(samples, sample_rate, base_sample_rate)
    assert incorrect_result != actual


#####################################################
# Tests for pcm.clamp_samples                       #
#####################################################
def test_clamp_samples_shouldpass():
    samples = [10, 3, 4, 6, 2, 9, 8, 4, 3, 0, 2]
    average_sample = 4.636363637
    expected = [1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0]
    actual = pcm.clamp_samples(samples, average_sample)
    assert expected == actual

def test_clamp_samples_shouldfail():
    samples = [10, 3, 4, 6, 2, 9, 8, 4, 3, 0, 2]
    average_sample = 4.636363637
    incorrect_result = [1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0]
    actual = pcm.clamp_samples(samples, average_sample)
    assert incorrect_result != actual


#####################################################
# Tests for pcm.clamp_samples                       #
#####################################################
def test_add_pcm_padding_needspadding_shouldpass():
    pcm_samples = [1, 0, 1]
    expected = [1, 0, 1, 0, 0, 0, 0, 0]
    actual = pcm.add_pcm_padding(pcm_samples)
    assert expected == actual

def test_add_pcm_padding_nopadding_shouldpass():
    pcm_samples = [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1]
    expected = [1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1]
    actual = pcm.add_pcm_padding(pcm_samples)
    assert expected == actual

def test_add_pcm_padding_needspadding_shouldfail():
    pcm_samples = [1, 0]
    incorrect_result = [1, 0]
    actual = pcm.add_pcm_padding(pcm_samples)
    assert incorrect_result != actual


#####################################################
# Tests for pcm.pack_pcm_samples                    #
#####################################################
def test_pack_pcm_samples_shouldpass():
    pcm_samples = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0]
    expected = bytearray('\xf0\xac')
    actual = pcm.pack_pcm_samples(pcm_samples)
    assert expected == actual

def test_pack_pcm_samples_shouldfail():
    pcm_samples = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0]
    incorrect_result = bytearray('\x0f\xca')
    actual = pcm.pack_pcm_samples(pcm_samples)
    assert incorrect_result != actual

def test_pack_pcm_samples_not_multiple_of_8_shouldpass():
    # The last 4 missing bits should be padded with 0.
    pcm_samples = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0]
    expected = bytearray('\xf0\xa0')
    actual = pcm.pack_pcm_samples(pcm_samples)
    assert expected == actual
