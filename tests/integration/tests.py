# -*- coding: utf-8 -*-

import os
from copy import copy
import hashlib
import random
import json

from pokemontools.interval_map import IntervalMap
from pokemontools.chars import chars, jap_chars

from pokemontools.romstr import (
    RomStr,
    AsmList,
)

from pokemontools.item_constants import (
    item_constants,
    find_item_label_by_id,
    generate_item_constants,
)

from pokemontools.pointers import (
    calculate_bank,
    calculate_pointer,
)

from pokemontools.pksv import (
    pksv_gs,
    pksv_crystal,
)

from pokemontools.labels import (
    remove_quoted_text,
    line_has_comment_address,
    line_has_label,
    get_label_from_line,
)

from pokemontools.crystal import (
    rom,
    load_rom,
    rom_until,
    direct_load_rom,
    parse_script_engine_script_at,
    parse_text_engine_script_at,
    parse_text_at2,
    find_all_text_pointers_in_script_engine_script,
    SingleByteParam,
    HexByte,
    MultiByteParam,
    PointerLabelParam,
    ItemLabelByte,
    DollarSignByte,
    DecimalParam,
    rom_interval,
    map_names,
    Label,
    scan_for_predefined_labels,
    all_labels,
    write_all_labels,
    parse_map_header_at,
    old_parse_map_header_at,
    process_00_subcommands,
    parse_all_map_headers,
    translate_command_byte,
    map_name_cleaner,
    load_map_group_offsets,
    load_asm,
    asm,
    is_valid_address,
    index,
    how_many_until,
    grouper,
    get_pokemon_constant_by_id,
    generate_map_constant_labels,
    get_map_constant_label_by_id,
    get_id_for_map_constant_label,
    calculate_pointer_from_bytes_at,
    isolate_incbins,
    process_incbins,
    get_labels_between,
    generate_diff_insert,
    find_labels_without_addresses,
    rom_text_at,
    get_label_for,
    split_incbin_line_into_three,
    reset_incbins,
)

import unittest

class BasicTestCase(unittest.TestCase):
    "this is where i cram all of my unit tests together"

    @classmethod
    def setUpClass(cls):
        global rom
        cls.rom = direct_load_rom()
        rom = cls.rom

    @classmethod
    def tearDownClass(cls):
        del cls.rom

    def test_direct_load_rom(self):
        rom = self.rom
        self.assertEqual(len(rom), 2097152)
        self.failUnless(isinstance(rom, RomStr))

    def test_load_rom(self):
        global rom
        rom = None
        load_rom()
        self.failIf(rom == None)
        rom = RomStr(None)
        load_rom()
        self.failIf(rom == RomStr(None))

    def test_load_asm(self):
        asm = load_asm()
        joined_lines = "\n".join(asm)
        self.failUnless("SECTION" in joined_lines)
        self.failUnless("bank" in joined_lines)
        self.failUnless(isinstance(asm, AsmList))

    def test_rom_file_existence(self):
        "ROM file must exist"
        self.failUnless("baserom.gbc" in os.listdir("../"))

    def test_rom_md5(self):
        "ROM file must have the correct md5 sum"
        rom = self.rom
        correct = "9f2922b235a5eeb78d65594e82ef5dde"
        md5 = hashlib.md5()
        md5.update(rom)
        md5sum = md5.hexdigest()
        self.assertEqual(md5sum, correct)

    def test_bizarre_http_presence(self):
        rom_segment = self.rom[0x112116:0x112116+8]
        self.assertEqual(rom_segment, "HTTP/1.0")

    def test_rom_interval(self):
        address = 0x100
        interval = 10
        correct_strings = ['0x0', '0xc3', '0x6e', '0x1', '0xce',
                           '0xed', '0x66', '0x66', '0xcc', '0xd']
        byte_strings = rom_interval(address, interval, strings=True)
        self.assertEqual(byte_strings, correct_strings)
        correct_ints = [0, 195, 110, 1, 206, 237, 102, 102, 204, 13]
        ints = rom_interval(address, interval, strings=False)
        self.assertEqual(ints, correct_ints)

    def test_rom_until(self):
        address = 0x1337
        byte = 0x13
        bytes = rom_until(address, byte, strings=True)
        self.failUnless(len(bytes) == 3)
        self.failUnless(bytes[0] == '0xd5')
        bytes = rom_until(address, byte, strings=False)
        self.failUnless(len(bytes) == 3)
        self.failUnless(bytes[0] == 0xd5)

    def test_how_many_until(self):
        how_many = how_many_until(chr(0x13), 0x1337)
        self.assertEqual(how_many, 3)

    def test_calculate_pointer_from_bytes_at(self):
        addr1 = calculate_pointer_from_bytes_at(0x100, bank=False)
        self.assertEqual(addr1, 0xc300)
        addr2 = calculate_pointer_from_bytes_at(0x100, bank=True)
        self.assertEqual(addr2, 0x2ec3)

    def test_rom_text_at(self):
        self.assertEquals(rom_text_at(0x112116, 8), "HTTP/1.0")

class TestRomStr(unittest.TestCase):
    sample_text = "hello world!"
    sample = None

    def test_rom_interval(self):
        global rom
        load_rom()
        address = 0x100
        interval = 10
        correct_strings = ['0x0', '0xc3', '0x6e', '0x1', '0xce',
                           '0xed', '0x66', '0x66', '0xcc', '0xd']
        byte_strings = rom.interval(address, interval, strings=True)
        self.assertEqual(byte_strings, correct_strings)
        correct_ints = [0, 195, 110, 1, 206, 237, 102, 102, 204, 13]
        ints = rom.interval(address, interval, strings=False)
        self.assertEqual(ints, correct_ints)

    def test_rom_until(self):
        global rom
        load_rom()
        address = 0x1337
        byte = 0x13
        bytes = rom.until(address, byte, strings=True)
        self.failUnless(len(bytes) == 3)
        self.failUnless(bytes[0] == '0xd5')
        bytes = rom.until(address, byte, strings=False)
        self.failUnless(len(bytes) == 3)
        self.failUnless(bytes[0] == 0xd5)

class TestAsmList(unittest.TestCase):
    # this test takes a lot of time :(
    def xtest_scan_for_predefined_labels(self):
        # label keys: line_number, bank, label, offset, address
        load_asm()
        all_labels = scan_for_predefined_labels()
        label_names = [x["label"] for x in all_labels]
        self.assertIn("GetFarByte", label_names)
        self.assertIn("AddNTimes", label_names)
        self.assertIn("CheckShininess", label_names)

if __name__ == "__main__":
    unittest.main()
