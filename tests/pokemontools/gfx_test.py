from pokemontools import gfx

import mock
from nose.tools import raises
import unittest


#####################################################
# Tests for gfx.read_filename_arguments             #
#####################################################
def test_read_filename_arguments_4_args():
    filename = "test.w16.h16.anonymous.arg.2bpp"
    expected = 4
    parsed_args = gfx.read_filename_arguments(filename)
    assert expected == len(parsed_args)

def test_read_filename_arguments_int_args():
    filename = "test.w16.h8.t4.2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert 16 == parsed_args['width']
    assert 8 == parsed_args['height']
    assert 4 == parsed_args['tile_padding']

def test_read_filename_arguments_arrange():
    filename = "test.arrange.2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert True == parsed_args['norepeat']
    assert True == parsed_args['tilemap']

def test_read_filename_arguments_dimensions():
    filename = "test.16x48.2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert (16, 48) == parsed_args['pic_dimensions']

def test_read_filename_arguments_bad_dimensions():
    filename = "test.16x4x3.2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert 'pic_dimensions' not in parsed_args

def test_read_filename_arguments_anonymous():
    filename = "test.interleave.blah.2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert True == parsed_args["interleave"]
    assert True == parsed_args["blah"]

def test_read_filename_arguments_empty_args():
    filename = "test....2bpp"
    parsed_args = gfx.read_filename_arguments(filename)
    assert 0 == len(parsed_args)


#####################################################
# Tests for gfx.try_decompress                      #
#####################################################
@mock.patch('pokemontools.gfx.decompress')
def test_try_decompress_lz_file_decompress_called(mock_decompress):
    filename = 'test.2bpp.lz'
    gfx.try_decompress(filename)
    mock_decompress.assert_called_with([filename])

@mock.patch('pokemontools.gfx.decompress')
def test_try_decompress_2bpp_file_decompress_not_called(mock_decompress):
    filename = 'test.2bpp'
    gfx.try_decompress(filename)
    mock_decompress.assert_not_called()


#####################################################
# Tests for gfx.get_decompressed_filename           #
#####################################################
def test_get_decompressed_filename_lz_file():
    filename = 'test.2bpp.lz'
    expected = 'test.2bpp'
    actual = gfx.get_decompressed_filename(filename)
    assert expected == actual

def test_get_decompressed_filename_not_lz_file():
    filename = 'test.2bpp'
    expected = 'decompressed_test.2bpp'
    actual = gfx.get_decompressed_filename(filename)
    assert expected == actual
