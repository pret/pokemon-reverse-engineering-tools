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

from pokemontools.helpers import (
    grouper,
    index,
)

from pokemontools.crystalparts.old_parsers import (
    old_parse_map_header_at,
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
    process_00_subcommands,
    parse_all_map_headers,
    translate_command_byte,
    map_name_cleaner,
    load_map_group_offsets,
    load_asm,
    asm,
    is_valid_address,
    how_many_until,
    get_pokemon_constant_by_id,
    generate_map_constant_labels,
    get_map_constant_label_by_id,
    get_id_for_map_constant_label,
    calculate_pointer_from_bytes_at,
    isolate_incbins,
    process_incbins,
    get_labels_between,
    generate_diff_insert,
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

class TestEncodedText(unittest.TestCase):
    """for testing chars-table encoded text chunks"""

    def test_process_00_subcommands(self):
        g = process_00_subcommands(0x197186, 0x197186+601, debug=False)
        self.assertEqual(len(g), 42)
        self.assertEqual(len(g[0]), 13)
        self.assertEqual(g[1], [184, 174, 180, 211, 164, 127, 20, 231, 81])

    def test_parse_text_at2(self):
        oakspeech = parse_text_at2(0x197186, 601, debug=False)
        self.assertIn("encyclopedia", oakspeech)
        self.assertIn("researcher", oakspeech)
        self.assertIn("dependable", oakspeech)

    def test_parse_text_engine_script_at(self):
        p = parse_text_engine_script_at(0x197185, debug=False)
        self.assertEqual(len(p.commands), 2)
        self.assertEqual(len(p.commands[0]["lines"]), 41)

class TestScript(unittest.TestCase):
    """for testing parse_script_engine_script_at and script parsing in
    general. Script should be a class."""
    #def test_parse_script_engine_script_at(self):
    #    pass # or raise NotImplementedError, bryan_message

    def test_find_all_text_pointers_in_script_engine_script(self):
        address = 0x197637 # 0x197634
        script = parse_script_engine_script_at(address, debug=False)
        bank = calculate_bank(address)
        r = find_all_text_pointers_in_script_engine_script(script, bank=bank, debug=False)
        results = list(r)
        self.assertIn(0x197661, results)

class TestByteParams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_rom()
        cls.address = 10
        cls.sbp = SingleByteParam(address=cls.address)

    @classmethod
    def tearDownClass(cls):
        del cls.sbp

    def test__init__(self):
        self.assertEqual(self.sbp.size, 1)
        self.assertEqual(self.sbp.address, self.address)

    def test_parse(self):
        self.sbp.parse()
        self.assertEqual(str(self.sbp.byte), str(45))

    def test_to_asm(self):
        self.assertEqual(self.sbp.to_asm(), "$2d")
        self.sbp.should_be_decimal = True
        self.assertEqual(self.sbp.to_asm(), str(45))

    # HexByte and DollarSignByte are the same now
    def test_HexByte_to_asm(self):
        h = HexByte(address=10)
        a = h.to_asm()
        self.assertEqual(a, "$2d")

    def test_DollarSignByte_to_asm(self):
        d = DollarSignByte(address=10)
        a = d.to_asm()
        self.assertEqual(a, "$2d")

    def test_ItemLabelByte_to_asm(self):
        i = ItemLabelByte(address=433)
        self.assertEqual(i.byte, 54)
        self.assertEqual(i.to_asm(), "COIN_CASE")
        self.assertEqual(ItemLabelByte(address=10).to_asm(), "$2d")

    def test_DecimalParam_to_asm(self):
        d = DecimalParam(address=10)
        x = d.to_asm()
        self.assertEqual(x, str(0x2d))

class TestMultiByteParam(unittest.TestCase):
    def setup_for(self, somecls, byte_size=2, address=443, **kwargs):
        self.cls = somecls(address=address, size=byte_size, **kwargs)
        self.assertEqual(self.cls.address, address)
        self.assertEqual(self.cls.bytes, rom_interval(address, byte_size, strings=False))
        self.assertEqual(self.cls.size, byte_size)

    def test_two_byte_param(self):
        self.setup_for(MultiByteParam, byte_size=2)
        self.assertEqual(self.cls.to_asm(), "$f0c0")

    def test_three_byte_param(self):
        self.setup_for(MultiByteParam, byte_size=3)

    def test_PointerLabelParam_no_bank(self):
        self.setup_for(PointerLabelParam, bank=None)
        # assuming no label at this location..
        self.assertEqual(self.cls.to_asm(), "$f0c0")
        global all_labels
        # hm.. maybe all_labels should be using a class?
        all_labels = [{"label": "poop", "address": 0xf0c0,
                       "offset": 0xf0c0, "bank": 0,
                       "line_number": 2
                     }]
        self.assertEqual(self.cls.to_asm(), "poop")

class TestPostParsing(unittest.TestCase):
    """tests that must be run after parsing all maps"""
    def test_signpost_counts(self):
        self.assertEqual(len(map_names[1][1]["signposts"]), 0)
        self.assertEqual(len(map_names[1][2]["signposts"]), 2)
        self.assertEqual(len(map_names[10][5]["signposts"]), 7)

    def test_warp_counts(self):
        self.assertEqual(map_names[10][5]["warp_count"], 9)
        self.assertEqual(map_names[18][5]["warp_count"], 3)
        self.assertEqual(map_names[15][1]["warp_count"], 2)

    def test_map_sizes(self):
        self.assertEqual(map_names[15][1]["height"], 18)
        self.assertEqual(map_names[15][1]["width"], 10)
        self.assertEqual(map_names[7][1]["height"], 4)
        self.assertEqual(map_names[7][1]["width"], 4)

    def test_map_connection_counts(self):
        self.assertEqual(map_names[7][1]["connections"], 0)
        self.assertEqual(map_names[10][1]["connections"], 12)
        self.assertEqual(map_names[10][2]["connections"], 12)
        self.assertEqual(map_names[11][1]["connections"], 9) # or 13?

    def test_second_map_header_address(self):
        self.assertEqual(map_names[11][1]["second_map_header_address"], 0x9509c)
        self.assertEqual(map_names[1][5]["second_map_header_address"], 0x95bd0)

    def test_event_address(self):
        self.assertEqual(map_names[17][5]["event_address"], 0x194d67)
        self.assertEqual(map_names[23][3]["event_address"], 0x1a9ec9)

    def test_people_event_counts(self):
        self.assertEqual(len(map_names[23][3]["people_events"]), 4)
        self.assertEqual(len(map_names[10][3]["people_events"]), 9)

class TestMapParsing(unittest.TestCase):
    def test_parse_all_map_headers(self):
        global parse_map_header_at, old_parse_map_header_at, counter
        counter = 0
        for k in map_names.keys():
            if "offset" not in map_names[k].keys():
                map_names[k]["offset"] = 0
        temp = parse_map_header_at
        temp2 = old_parse_map_header_at
        def parse_map_header_at(address, map_group=None, map_id=None, debug=False):
            global counter
            counter += 1
            return {}
        old_parse_map_header_at = parse_map_header_at
        parse_all_map_headers(debug=False)
        # parse_all_map_headers is currently doing it 2x
        # because of the new/old map header parsing routines
        self.assertEqual(counter, 388 * 2)
        parse_map_header_at = temp
        old_parse_map_header_at = temp2

if __name__ == "__main__":
    unittest.main()
