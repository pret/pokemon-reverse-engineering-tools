# -*- coding: utf-8 -*-
"""
GBC disassembler
"""
from __future__ import print_function
from __future__ import absolute_import

import os
import argparse
from ctypes import c_int8

from . import configuration
from .wram import read_constants

z80_table = [
	('nop', 0),                    # 00
	('ld bc, {}', 2),              # 01
	('ld [bc], a', 0),             # 02
	('inc bc', 0),                 # 03
	('inc b', 0),                  # 04
	('dec b', 0),                  # 05
	('ld b, ${:02x}', 1),          # 06
	('rlca', 0),                   # 07
	('ld [{}], sp', 2),            # 08
	('add hl, bc', 0),             # 09
	('ld a, [bc]', 0),             # 0a
	('dec bc', 0),                 # 0b
	('inc c', 0),                  # 0c
	('dec c', 0),                  # 0d
	('ld c, ${:02x}', 1),          # 0e
	('rrca', 0),                   # 0f
	('db $10', 0),                 # 10
	('ld de, {}', 2),              # 11
	('ld [de], a', 0),             # 12
	('inc de', 0),                 # 13
	('inc d', 0),                  # 14
	('dec d', 0),                  # 15
	('ld d, ${:02x}', 1),          # 16
	('rla', 0),                    # 17
	('jr {}', 1),                  # 18
	('add hl, de', 0),             # 19
	('ld a, [de]', 0),             # 1a
	('dec de', 0),                 # 1b
	('inc e', 0),                  # 1c
	('dec e', 0),                  # 1d
	('ld e, ${:02x}', 1),          # 1e
	('rra', 0),                    # 1f
	('jr nz, {}', 1),              # 20
	('ld hl, {}', 2),              # 21
	('ld [hli], a', 0),            # 22
	('inc hl', 0),                 # 23
	('inc h', 0),                  # 24
	('dec h', 0),                  # 25
	('ld h, ${:02x}', 1),          # 26
	('daa', 0),                    # 27
	('jr z, {}', 1),               # 28
	('add hl, hl', 0),             # 29
	('ld a, [hli]', 0),            # 2a
	('dec hl', 0),                 # 2b
	('inc l', 0),                  # 2c
	('dec l', 0),                  # 2d
	('ld l, ${:02x}', 1),          # 2e
	('cpl', 0),                    # 2f
	('jr nc, {}', 1),              # 30
	('ld sp, {}', 2),              # 31
	('ld [hld], a', 0),            # 32
	('inc sp', 0),                 # 33
	('inc [hl]', 0),               # 34
	('dec [hl]', 0),               # 35
	('ld [hl], ${:02x}', 1),       # 36
	('scf', 0),                    # 37
	('jr c, {}', 1),               # 38
	('add hl, sp', 0),             # 39
	('ld a, [hld]', 0),            # 3a
	('dec sp', 0),                 # 3b
	('inc a', 0),                  # 3c
	('dec a', 0),                  # 3d
	('ld a, ${:02x}', 1),          # 3e
	('ccf', 0),                    # 3f
	('ld b, b', 0),                # 40
	('ld b, c', 0),                # 41
	('ld b, d', 0),                # 42
	('ld b, e', 0),                # 43
	('ld b, h', 0),                # 44
	('ld b, l', 0),                # 45
	('ld b, [hl]', 0),             # 46
	('ld b, a', 0),                # 47
	('ld c, b', 0),                # 48
	('ld c, c', 0),                # 49
	('ld c, d', 0),                # 4a
	('ld c, e', 0),                # 4b
	('ld c, h', 0),                # 4c
	('ld c, l', 0),                # 4d
	('ld c, [hl]', 0),             # 4e
	('ld c, a', 0),                # 4f
	('ld d, b', 0),                # 50
	('ld d, c', 0),                # 51
	('ld d, d', 0),                # 52
	('ld d, e', 0),                # 53
	('ld d, h', 0),                # 54
	('ld d, l', 0),                # 55
	('ld d, [hl]', 0),             # 56
	('ld d, a', 0),                # 57
	('ld e, b', 0),                # 58
	('ld e, c', 0),                # 59
	('ld e, d', 0),                # 5a
	('ld e, e', 0),                # 5b
	('ld e, h', 0),                # 5c
	('ld e, l', 0),                # 5d
	('ld e, [hl]', 0),             # 5e
	('ld e, a', 0),                # 5f
	('ld h, b', 0),                # 60
	('ld h, c', 0),                # 61
	('ld h, d', 0),                # 62
	('ld h, e', 0),                # 63
	('ld h, h', 0),                # 64
	('ld h, l', 0),                # 65
	('ld h, [hl]', 0),             # 66
	('ld h, a', 0),                # 67
	('ld l, b', 0),                # 68
	('ld l, c', 0),                # 69
	('ld l, d', 0),                # 6a
	('ld l, e', 0),                # 6b
	('ld l, h', 0),                # 6c
	('ld l, l', 0),                # 6d
	('ld l, [hl]', 0),             # 6e
	('ld l, a', 0),                # 6f
	('ld [hl], b', 0),             # 70
	('ld [hl], c', 0),             # 71
	('ld [hl], d', 0),             # 72
	('ld [hl], e', 0),             # 73
	('ld [hl], h', 0),             # 74
	('ld [hl], l', 0),             # 75
	('halt', 0),                   # 76
	('ld [hl], a', 0),             # 77
	('ld a, b', 0),                # 78
	('ld a, c', 0),                # 79
	('ld a, d', 0),                # 7a
	('ld a, e', 0),                # 7b
	('ld a, h', 0),                # 7c
	('ld a, l', 0),                # 7d
	('ld a, [hl]', 0),             # 7e
	('ld a, a', 0),                # 7f
	('add b', 0),                  # 80
	('add c', 0),                  # 81
	('add d', 0),                  # 82
	('add e', 0),                  # 83
	('add h', 0),                  # 84
	('add l', 0),                  # 85
	('add [hl]', 0),               # 86
	('add a', 0),                  # 87
	('adc b', 0),                  # 88
	('adc c', 0),                  # 89
	('adc d', 0),                  # 8a
	('adc e', 0),                  # 8b
	('adc h', 0),                  # 8c
	('adc l', 0),                  # 8d
	('adc [hl]', 0),               # 8e
	('adc a', 0),                  # 8f
	('sub b', 0),                  # 90
	('sub c', 0),                  # 91
	('sub d', 0),                  # 92
	('sub e', 0),                  # 93
	('sub h', 0),                  # 94
	('sub l', 0),                  # 95
	('sub [hl]', 0),               # 96
	('sub a', 0),                  # 97
	('sbc b', 0),                  # 98
	('sbc c', 0),                  # 99
	('sbc d', 0),                  # 9a
	('sbc e', 0),                  # 9b
	('sbc h', 0),                  # 9c
	('sbc l', 0),                  # 9d
	('sbc [hl]', 0),               # 9e
	('sbc a', 0),                  # 9f
	('and b', 0),                  # a0
	('and c', 0),                  # a1
	('and d', 0),                  # a2
	('and e', 0),                  # a3
	('and h', 0),                  # a4
	('and l', 0),                  # a5
	('and [hl]', 0),               # a6
	('and a', 0),                  # a7
	('xor b', 0),                  # a8
	('xor c', 0),                  # a9
	('xor d', 0),                  # aa
	('xor e', 0),                  # ab
	('xor h', 0),                  # ac
	('xor l', 0),                  # ad
	('xor [hl]', 0),               # ae
	('xor a', 0),                  # af
	('or b', 0),                   # b0
	('or c', 0),                   # b1
	('or d', 0),                   # b2
	('or e', 0),                   # b3
	('or h', 0),                   # b4
	('or l', 0),                   # b5
	('or [hl]', 0),                # b6
	('or a', 0),                   # b7
	('cp b', 0),                   # b8
	('cp c', 0),                   # b9
	('cp d', 0),                   # ba
	('cp e', 0),                   # bb
	('cp h', 0),                   # bc
	('cp l', 0),                   # bd
	('cp [hl]', 0),                # be
	('cp a', 0),                   # bf
	('ret nz', 0),                 # c0
	('pop bc', 0),                 # c1
	('jp nz, {}', 2),              # c2
	('jp {}', 2),                  # c3
	('call nz, {}', 2),            # c4
	('push bc', 0),                # c5
	('add ${:02x}', 1),            # c6
	('rst $0', 0),                 # c7
	('ret z', 0),                  # c8
	('ret', 0),                    # c9
	('jp z, {}', 2),               # ca
	('bitops', 1),                 # cb
	('call z, {}', 2),             # cc
	('call {}', 2),                # cd
	('adc ${:02x}', 1),            # ce
	('rst $8', 0),                 # cf
	('ret nc', 0),                 # d0
	('pop de', 0),                 # d1
	('jp nc, ${:04x}', 2),         # d2
	('db $d3', 0),                 # d3
	('call nc, {}', 2),            # d4
	('push de', 0),                # d5
	('sub ${:02x}', 1),            # d6
	('rst $10', 0),                # d7
	('ret c', 0),                  # d8
	('reti', 0),                   # d9
	('jp c, ${:04x}', 2),          # da
	('db $db', 0),                 # db
	('call c, {}', 2),             # dc
	('db $dd', 2),                 # dd
	('sbc ${:02x}', 1),            # de
	('rst $18', 0),                # df
	('ld [{}], a', 1),             # e0
	('pop hl', 0),                 # e1
	('ld [$ff00+c], a', 0),        # e2
	('db $e3', 0),                 # e3
	('db $e4', 0),                 # e4
	('push hl', 0),                # e5
	('and ${:02x}', 1),            # e6
	('rst $20', 0),                # e7
	('add sp, ${:02x}', 1),        # e8
	('jp [hl]', 0),                # e9
	('ld [{}], a', 2),             # ea
	('db $eb', 0),                 # eb
	('db $ec', 2),                 # ec
	('db $ed', 2),                 # ed
	('xor ${:02x}', 1),            # ee
	('rst $28', 0),                # ef
	('ld a, [{}]', 1),             # f0
	('pop af', 0),                 # f1
	('db $f2', 0),                 # f2
	('di', 0),                     # f3
	('db $f4', 0),                 # f4
	('push af', 0),                # f5
	('or ${:02x}', 1),             # f6
	('rst $30', 0),                # f7
	('ld hl, sp+${:02x}', 1),      # f8
	('ld sp, [hl]', 0),            # f9
	('ld a, [{}]', 2),             # fa
	('ei', 0),                     # fb
	('db $fc', 2),                 # fc
	('db $fd', 2),                 # fd
	('cp ${:02x}', 1),             # fe
	('rst $38', 0),                # ff
]
 
bit_ops_table = [
	"rlc b",     "rlc c",     "rlc d",     "rlc e",     "rlc h",     "rlc l",     "rlc [hl]",     "rlc a",       # $00 - $07
	"rrc b",     "rrc c",     "rrc d",     "rrc e",     "rrc h",     "rrc l",     "rrc [hl]",     "rrc a",       # $08 - $0f
	"rl b",      "rl c",      "rl d",      "rl e",      "rl h",      "rl l",      "rl [hl]",      "rl a",        # $10 - $17
	"rr b",      "rr c",      "rr d",      "rr e",      "rr h",      "rr l",      "rr [hl]",      "rr a",        # $18 - $1f
	"sla b",     "sla c",     "sla d",     "sla e",     "sla h",     "sla l",     "sla [hl]",     "sla a",       # $20 - $27
	"sra b",     "sra c",     "sra d",     "sra e",     "sra h",     "sra l",     "sra [hl]",     "sra a",       # $28 - $2f
	"swap b",    "swap c",    "swap d",    "swap e",    "swap h",    "swap l",    "swap [hl]",    "swap a",      # $30 - $37
	"srl b",     "srl c",     "srl d",     "srl e",     "srl h",     "srl l",     "srl [hl]",     "srl a",       # $38 - $3f
	"bit 0, b",  "bit 0, c",  "bit 0, d",  "bit 0, e",  "bit 0, h",  "bit 0, l",  "bit 0, [hl]",  "bit 0, a",    # $40 - $47
	"bit 1, b",  "bit 1, c",  "bit 1, d",  "bit 1, e",  "bit 1, h",  "bit 1, l",  "bit 1, [hl]",  "bit 1, a",    # $48 - $4f
	"bit 2, b",  "bit 2, c",  "bit 2, d",  "bit 2, e",  "bit 2, h",  "bit 2, l",  "bit 2, [hl]",  "bit 2, a",    # $50 - $57
	"bit 3, b",  "bit 3, c",  "bit 3, d",  "bit 3, e",  "bit 3, h",  "bit 3, l",  "bit 3, [hl]",  "bit 3, a",    # $58 - $5f
	"bit 4, b",  "bit 4, c",  "bit 4, d",  "bit 4, e",  "bit 4, h",  "bit 4, l",  "bit 4, [hl]",  "bit 4, a",    # $60 - $67
	"bit 5, b",  "bit 5, c",  "bit 5, d",  "bit 5, e",  "bit 5, h",  "bit 5, l",  "bit 5, [hl]",  "bit 5, a",    # $68 - $6f
	"bit 6, b",  "bit 6, c",  "bit 6, d",  "bit 6, e",  "bit 6, h",  "bit 6, l",  "bit 6, [hl]",  "bit 6, a",    # $70 - $77
	"bit 7, b",  "bit 7, c",  "bit 7, d",  "bit 7, e",  "bit 7, h",  "bit 7, l",  "bit 7, [hl]",  "bit 7, a",    # $78 - $7f
	"res 0, b",  "res 0, c",  "res 0, d",  "res 0, e",  "res 0, h",  "res 0, l",  "res 0, [hl]",  "res 0, a",    # $80 - $87
	"res 1, b",  "res 1, c",  "res 1, d",  "res 1, e",  "res 1, h",  "res 1, l",  "res 1, [hl]",  "res 1, a",    # $88 - $8f
	"res 2, b",  "res 2, c",  "res 2, d",  "res 2, e",  "res 2, h",  "res 2, l",  "res 2, [hl]",  "res 2, a",    # $90 - $97
	"res 3, b",  "res 3, c",  "res 3, d",  "res 3, e",  "res 3, h",  "res 3, l",  "res 3, [hl]",  "res 3, a",    # $98 - $9f
	"res 4, b",  "res 4, c",  "res 4, d",  "res 4, e",  "res 4, h",  "res 4, l",  "res 4, [hl]",  "res 4, a",    # $a0 - $a7
	"res 5, b",  "res 5, c",  "res 5, d",  "res 5, e",  "res 5, h",  "res 5, l",  "res 5, [hl]",  "res 5, a",    # $a8 - $af
	"res 6, b",  "res 6, c",  "res 6, d",  "res 6, e",  "res 6, h",  "res 6, l",  "res 6, [hl]",  "res 6, a",    # $b0 - $b7
	"res 7, b",  "res 7, c",  "res 7, d",  "res 7, e",  "res 7, h",  "res 7, l",  "res 7, [hl]",  "res 7, a",    # $b8 - $bf
	"set 0, b",  "set 0, c",  "set 0, d",  "set 0, e",  "set 0, h",  "set 0, l",  "set 0, [hl]",  "set 0, a",    # $c0 - $c7
	"set 1, b",  "set 1, c",  "set 1, d",  "set 1, e",  "set 1, h",  "set 1, l",  "set 1, [hl]",  "set 1, a",    # $c8 - $cf
	"set 2, b",  "set 2, c",  "set 2, d",  "set 2, e",  "set 2, h",  "set 2, l",  "set 2, [hl]",  "set 2, a",    # $d0 - $d7
	"set 3, b",  "set 3, c",  "set 3, d",  "set 3, e",  "set 3, h",  "set 3, l",  "set 3, [hl]",  "set 3, a",    # $d8 - $df
	"set 4, b",  "set 4, c",  "set 4, d",  "set 4, e",  "set 4, h",  "set 4, l",  "set 4, [hl]",  "set 4, a",    # $e0 - $e7
	"set 5, b",  "set 5, c",  "set 5, d",  "set 5, e",  "set 5, h",  "set 5, l",  "set 5, [hl]",  "set 5, a",    # $e8 - $ef
	"set 6, b",  "set 6, c",  "set 6, d",  "set 6, e",  "set 6, h",  "set 6, l",  "set 6, [hl]",  "set 6, a",    # $f0 - $f7
	"set 7, b",  "set 7, c",  "set 7, d",  "set 7, e",  "set 7, h",  "set 7, l",  "set 7, [hl]",  "set 7, a"     # $f8 - $ff
]

unconditional_returns = [0xc9, 0xd9]
absolute_jumps = [0xc3, 0xc2, 0xca, 0xd2, 0xda]
call_commands = [0xcd, 0xc4, 0xcc, 0xd4, 0xdc]
relative_jumps = [0x18, 0x20, 0x28, 0x30, 0x38]
unconditional_jumps = [0xc3, 0x18]


def asm_label(address):
	"""
	Return a local label name for asm at <address>.
	"""
	return '.asm_%x' % address

def data_label(address):
	"""
	Return a local label name for data at <address>.
	"""
	return '.data_%x' % address

def get_local_address(address):
	"""
	Return the local address of a rom address.
	"""
	bank = address / 0x4000
	address &= 0x3fff
	if bank:
		return address + 0x4000
	return address

def get_global_address(address, bank):
	"""
	Return the rom address of a local address and bank.

	This accounts for a quirk in mbc3 where 0:4000-7fff resolves to 1:4000-7fff.
	"""
	if address < 0x8000:
		if address >= 0x4000 and bank > 0:
			return address + (bank - 1) * 0x4000
	
	return address

def created_but_unused_labels_exist(byte_labels):
	"""
	Check whether a label has been created but not used.

	If so, then that means it has to be called or specified later.
	"""
	return (False in [label["definition"] for label in byte_labels.values()])

def all_byte_labels_are_defined(byte_labels):
	"""
	Check whether all labels have already been defined.
	"""
	return (False not in [label["definition"] for label in byte_labels.values()])

def load_rom(path='baserom.gbc'):
	return bytearray(open(path, 'rb').read())

def read_symfile(path='baserom.sym'):
	"""
	Return a list of dicts of label data from an rgbds .sym file.
	"""
	symbols = []
	for line in open(path):
		line = line.strip().split(';')[0]
		if line:
			bank_address, label = line.split(' ')[:2]
			bank, address = bank_address.split(':')
			symbols += [{
				'label': label,
				'bank': int(bank, 16),
				'address': int(address, 16),
			}]
	return symbols

def load_symbols(path):
	sym = {}
	reverse_sym = {}
	wram_sym = {}
	sram_sym = {}
	
	symbols = read_symfile(path)
	for symbol in symbols:
		bank = symbol['bank']
		address = symbol['address']
		label = symbol['label']
		
		if 0x0000 <= address < 0x8000:
			if bank not in sym:
				sym[bank] = {}
			
			sym[bank][address] = label
			reverse_sym[label] = get_global_address(address, bank)
			
		elif 0xa000 <= address < 0xc000:
			if bank not in sram_sym:
				sram_sym[bank] = {}
				
			sram_sym[bank][address] = label
			
		elif address < 0xe000:
			if bank not in wram_sym:
				wram_sym[bank] = {}
			
			wram_sym[bank][address] = label
		else:	
			raise ValueError("Unsupported symfile label type.")
		
	return sym, reverse_sym, wram_sym, sram_sym

def get_symbol(sym, address, bank=0):
	if sym:
		if 0x0000 <= address < 0x4000:
			return sym.get(0, {}).get(address)
		else:
			return sym.get(bank, {}).get(address)
	
	return None

def get_banked_ram_sym(sym, address):
	#if sym:
	#	if 0xc000 <= address < 0xd000:
	#		return sym.get(0, {}).get(address)
	#	else:
	#		return sym.get(bank, {}).get(address)
	if sym:
		for bank in sym.keys():
			temp_sym = sym.get(bank, {}).get(address)
			if temp_sym:
				return temp_sym
		
	return None

def create_address_comment(offset):
	comment_bank = offset / 0x4000
	if comment_bank != 0:
		comment_bank_addr = (offset % 0x4000) + 0x4000
	else:
		comment_bank_addr = offset
		
	return " ; %x (%x:%x)" % (offset, comment_bank, comment_bank_addr)
			
def offset_is_used(labels, offset):
	if offset in labels.keys():
		return 0 < labels[offset]["usage"]

class Disassembler(object):
	"""
	GBC disassembler
	"""

	def __init__(self, config):
		"""
		Setup the class instance.
		"""
		self.config = config
		self.spacing = '\t'
		self.rom = None
		self.sym = None
		self.rsym = None
		self.gbhw = None
		self.vram = None
		self.sram = None
		self.hram = None
		self.wram = None

	def initialize(self, rom, symfile):
		"""
		Setup the disassembler.
		"""
		path = os.path.join(self.config.path, rom)
		self.rom = load_rom(path)
		
		path = os.path.join(self.config.path, symfile)
		if os.path.exists(path):
			self.sym, self.rsym, self.wram, self.sram = load_symbols(path)

		path = os.path.join(self.config.path, 'gbhw.asm')
		
		if os.path.exists(path):
			self.gbhw = read_constants(path)
		else:
			path = os.path.join(self.config.path, "constants/hardware_constants.asm")
			if os.path.exists(path):
				self.gbhw = read_constants(path)
		
		path = os.path.join(self.config.path, 'vram.asm')
		if os.path.exists(path):
			self.vram = read_constants(path)
			
		path = os.path.join(self.config.path, 'hram.asm')
		if os.path.exists(path):
			self.hram = read_constants(path)

	def find_label(self, address, bank=0):
		if type(address) is str:
			address = int(address.replace('$', '0x'), 16)
		elif address is None:
			return address
		
		if 0x0000 <= address < 0x8000:
			label = self.get_symbol(address, bank)
		elif address < 0xa000 and self.vram:
			label = self.vram.get(address)
		elif address < 0xc000:
			label = self.get_sram(address)
		elif address < 0xe000:
			label = self.get_wram(address)
		elif ((0xff00 <= address < 0xff80) or (address == 0xffff)) and self.gbhw:
			label = self.gbhw.get(address)
		elif (0xff80 <= address < 0xffff) and self.hram:
			label = self.hram.get(address)
		else:
			label = None
			
		return label

	def get_symbol(self, address, bank):
		symbol = get_symbol(self.sym, address, bank)
		if symbol == 'NULL' and address == 0 and bank == 0:
			return None
		return symbol

	def get_wram(self, address):
		symbol = get_banked_ram_sym(self.wram, address)
		if symbol == 'NULL' and address == 0:
			return None
		return symbol
		
	def get_sram(self, address):
		symbol = get_banked_ram_sym(self.sram, address)
		if symbol == 'NULL' and address == 0:
			return None
		return symbol
		
	def find_address_from_label(self, label):
		if self.rsym:
			return self.rsym.get(label)
		
		return None

	def output_bank_opcodes(self, start_offset, stop_offset, hard_stop=False, parse_data=False, include_last_address=True):
		"""
		Output bank opcodes.

		fs = current_address
		b = bank_byte
		in = input_data  -- rom
		bank_size = byte_count
		i = offset
		ad = end_address
		a, oa = current_byte_number

		stop_at can be used to supply a list of addresses to not disassemble
		over. This is useful if you know in advance that there are a lot of
		fall-throughs.
		"""
		
		debug = False
				
		bank_id = start_offset / 0x4000
		
		stop_offset_undefined = False
		
		# check if stop_offset isn't defined
		if stop_offset is None:
			stop_offset_undefined = True
			# stop at the end of the current bank if stop_offset is not defined
			stop_offset = (bank_id + 1) * 0x4000 - 1
	
		if debug:
			print("bank id is: " + str(bank_id))

		rom = self.rom

		offset = start_offset
		current_byte_number = 0 #start from the beginning		

		byte_labels = {}
		data_tables = {}
		
		output = "Func_%x:%s\n" % (start_offset,create_address_comment(start_offset))
		is_data = False
		
		while True:
			#first check if this byte already has a label
			#if it does, use the label
			#if not, generate a new label
			
			local_offset = get_local_address(offset)
			
			data_label_used = offset_is_used(data_tables, local_offset)
			byte_label_used = offset_is_used(byte_labels, local_offset)
			data_label_created = local_offset in data_tables.keys()
			byte_label_created = local_offset in byte_labels.keys()
			
			if byte_label_created:
			# if a byte label exists, remove any significance if there is a data label that exists
				if data_label_created:
					data_line_label = data_tables[local_offset]["name"]
					data_tables[local_offset]["usage"] = 0
				else:
					data_line_label = data_label(offset)
					data_tables[local_offset] = {}
					data_tables[local_offset]["name"] = data_line_label
					data_tables[local_offset]["usage"] = 0
					
				line_label = byte_labels[local_offset]["name"]
				byte_labels[local_offset]["usage"] += 1
				output += "\n"
			elif data_label_created and parse_data:
			# go add usage to a data label if it exists
				data_line_label = data_tables[local_offset]["name"]
				data_tables[local_offset]["usage"] += 1
				
				line_label = asm_label(offset)
				byte_labels[local_offset] = {}
				byte_labels[local_offset]["name"] = line_label
				byte_labels[local_offset]["usage"] = 0
				output += "\n"
			else:
			# create both a data and byte label if neither exist
				data_line_label = data_label(offset)
				data_tables[local_offset] = {}
				data_tables[local_offset]["name"] = data_line_label
				data_tables[local_offset]["usage"] = 0
					
				line_label = asm_label(offset)
				byte_labels[local_offset] = {}
				byte_labels[local_offset]["name"] = line_label
				byte_labels[local_offset]["usage"] = 0

			# any labels created not above are now used, so mark them as "defined"
			byte_labels[local_offset]["definition"] = True
			data_tables[local_offset]["definition"] = True
			
			# for now, output the byte and data labels (unused labels will be removed later
			output += line_label + "\n" + data_line_label + "\n"
			
			# get the current byte
			opcode_byte = rom[offset]
			
			# process the current byte if this is code or parse data has not been set
			if not is_data or not parse_data:
				# fetch the opcode string from a predefined table
				opcode_str = z80_table[opcode_byte][0]
				# fetch the number of arguments
				opcode_nargs = z80_table[opcode_byte][1]
				# get opcode arguments in advance (may not be used)
				opcode_arg_1 = rom[offset+1]
				opcode_arg_2 = rom[offset+2]
				
				if opcode_nargs == 0:
				# set output string simply as the opcode
					opcode_output_str = opcode_str
				
				elif opcode_nargs == 1:
				# opcodes with 1 argument
					if opcode_byte != 0xcb: # bit opcodes are handled separately
						
						if opcode_byte in relative_jumps:
						# if the current opcode is a relative jump, generate a label for the address we're jumping to
							# get the address of the location to jump to
							target_address = offset + 2 + c_int8(opcode_arg_1).value
							# get the local address to use as a key for byte_labels and data_tables
							local_target_address = get_local_address(target_address)
							
							if local_target_address in byte_labels.keys():
							# if the label has already been created, increase the usage and set output to the already created label
								byte_labels[local_target_address]["usage"] += 1
								opcode_output_str = byte_labels[local_target_address]["name"]
							elif target_address < start_offset:
							# if we're jumping to an address that is located before the start offset, assume it is a function
								opcode_output_str = "Func_%x" % target_address
							else:
							# create a new label
								opcode_output_str = asm_label(target_address)
								byte_labels[local_target_address] = {}
								byte_labels[local_target_address]["name"] = opcode_output_str
								# we know the label is used once, so set the usage to 1
								byte_labels[local_target_address]["usage"] = 1
								# since the label has not been output yet, mark it as "not defined"
								byte_labels[local_target_address]["definition"] = False
							
							# check if the target address conflicts with any data labels
							if local_target_address in data_tables.keys():
								# if so, remove any instances of it being used and set it as defined
								data_tables[local_target_address]["usage"] = 0
								data_tables[local_target_address]["definition"] = True
							
							# format the resulting argument into the output string
							opcode_output_str = opcode_str.format(opcode_output_str)
							
							# debug function
							if created_but_unused_labels_exist(byte_labels) and debug:
								output += create_address_comment(offset)
						
						elif opcode_byte == 0xe0 or opcode_byte == 0xf0:
						# handle gameboy hram read/write opcodes
							# create the address
							high_ram_address = 0xff00 + opcode_arg_1
							# search for an hram constant if possible
							high_ram_label = self.find_label(high_ram_address, bank_id)
							# if we couldn't find one, default to the address
							if high_ram_label is None:
								high_ram_label = "$%x" % high_ram_address
							
							# format the resulting argument into the output string
							opcode_output_str = opcode_str.format(high_ram_label)
						
						else:
						# if this isn't a relative jump or hram read/write, just format the byte into the opcode string
							opcode_output_str = opcode_str.format(opcode_arg_1)
					
					else:
					# handle bit opcodes by fetching the opcode from a separate table
						opcode_output_str = bit_ops_table[opcode_arg_1]
				
				elif opcode_nargs == 2:
				# opcodes with a pointer as an argument
					# format the two arguments into a little endian 16-bit pointer
					local_target_offset = opcode_arg_2 << 8 | opcode_arg_1
					# get the global offset of the pointer
					target_offset = get_global_address(local_target_offset, bank_id)
					# attempt to look for a matching label
					target_label = self.find_label(target_offset, bank_id)
					
					if opcode_byte in call_commands + absolute_jumps:
						if target_label is None:
						# if this is a call or jump opcode and the target label is not defined, create an undocumented label descriptor
							target_label = "Func_%x" % target_offset

					else:
					# anything that isn't a call or jump is a load-based command
						if target_label is None:
						# handle the case of a label for the current address not existing
						
							# first, check if this is a byte label
							if offset_is_used(byte_labels, local_target_offset):
								# fetch the already created byte label
								target_label = byte_labels[local_target_offset]["name"]
								# prevent this address from being treated as a data label
								if local_target_offset in data_tables.keys():
									data_tables[local_target_offset]["usage"] = 0
								else:
									data_tables[local_target_offset] = {}
									data_tables[local_target_offset]["name"] = target_label
									data_tables[local_target_offset]["usage"] = 0
									data_tables[local_target_offset]["definition"] = True
									
							elif local_target_offset >= 0x8000 or not parse_data:
							# do not create a label if this is a wram label or parse_data is not set
								target_label = "$%x" % local_target_offset
							
							elif local_target_offset in data_tables.keys():
							# if the target offset has been created as a data label, increase usage and use the already defined name
								data_tables[local_target_offset]["usage"] += 1
								target_label = data_tables[local_target_offset]["name"]	
							else:
							# for now, treat this as a data label, but do not set it as used (will be replaced later if unused)
								target_label = data_label(target_offset)
								data_tables[local_target_offset] = {}
								data_tables[local_target_offset]["name"] = target_label
								data_tables[local_target_offset]["usage"] = 0
								data_tables[local_target_offset]["definition"] = False
							
					# format the label that was created into the opcode string
					opcode_output_str = opcode_str.format(target_label)	

				else:
					# error checking
					raise ValueError("Invalid amount of args.")
				
				# append the formatted opcode output string to the output
				output += self.spacing + opcode_output_str + "\n" #+ " ; " + hex(offset)
				# increase the current byte number and offset by the amount of arguments plus 1 (opcode itself)
				current_byte_number += opcode_nargs + 1
				offset += opcode_nargs + 1
				
			else:
				# output a single lined db, using the current byte
				output += self.spacing + "db ${:02x}\n".format(opcode_byte) #+ " ; " + hex(offset)
				# manually increment offset and current byte number
				offset += 1
				current_byte_number += 1
				# stop treating the current code as data if we're parsing over a byte label
				if get_local_address(offset) in byte_labels.keys():
					is_data = False
			
			# update the local offset
			local_offset = get_local_address(offset)
			
			# stop processing regardless of function end if we've passed the stop offset and the hard stop (dry run) flag is set
			if hard_stop and offset >= stop_offset:
				break
			# check if this is the end of the function, or we're processing data
			elif (opcode_byte in unconditional_jumps + unconditional_returns) or is_data:
				# define data if it is located at the current offset
				if local_offset not in byte_labels.keys() and local_offset in data_tables.keys() and created_but_unused_labels_exist(data_tables) and parse_data:
					is_data = True
				#stop reading at a jump, relative jump or return
				elif all_byte_labels_are_defined(byte_labels) and (offset >= stop_offset or stop_offset_undefined):
					break
				# otherwise, add some spacing
				output += "\n"
		
		# before returning output, we need to clean up some things
		
		# first, clean up on unused byte labels
		for label_line in byte_labels.values():
			if label_line["usage"] == 0:
				output = output.replace((label_line["name"] + "\n"), "")
		
		# clean up on unused data labels
		# this is slightly trickier to do as arguments for two byte variables use data labels
		
		# create a list of the output lines including the newlines
		output_lines = [e+"\n" for e in output.split("\n") if e != ""]
		
		# go through each label
		for label_addr in data_tables.keys():
			# get the label dict
			label_line = data_tables[label_addr]
			# check if this label is unused
			if label_line["usage"] == 0:
				# get label name
				label_name = label_line["name"]
				# loop over all output lines
				for i, line in enumerate(output_lines):
					if line.startswith(label_name):
					# remove line if it starts with the current label
						output_lines.pop(i)
					elif label_name in line:
					# if the label is used in a load-based opcode, replace it with the raw hex reference
						output_lines[i] = output_lines[i].replace(label_name, "$%x" % get_local_address(label_addr))
		
		# convert the modified list of lines into a string
		output = "".join(output_lines)
		
		# tone down excessive spacing
		output = output.replace("\n\n\n","\n\n")

		# add the offset of the final location
		if include_last_address:
			output += "; " + hex(offset)
		
		return [output, offset, stop_offset, byte_labels, data_tables]

def get_raw_addr(addr):
	if addr:
		if ":" in addr:
			addr = addr.split(":")
			addr = int(addr[0], 16)*0x4000+(int(addr[1], 16)%0x4000)
		else:
			label_addr = disasm.find_address_from_label(addr)
			if label_addr:
				addr = label_addr
			else:
				addr = int(addr, 16)
	
	return addr

if __name__ == "__main__":
	# argument parser
	ap = argparse.ArgumentParser()
	ap.add_argument("-r", dest="rom", default="baserom.gbc")
	ap.add_argument("-o", dest="filename", default="gbz80disasm_output.asm")
	ap.add_argument("-s", dest="symfile")
	ap.add_argument("-dp", "--use-disasm-path", dest="use_disasm_path", action="store_true")
	ap.add_argument("-q", "--quiet", dest="quiet", action="store_true")
	ap.add_argument("-nw", "--no-write", dest="no_write", action="store_true")
	ap.add_argument("-d", "--dry-run", dest="dry_run", action="store_true")
	ap.add_argument("-pd", "--parse_data", dest="parse_data", action="store_true")
	ap.add_argument('offset')
	ap.add_argument('end', nargs='?')
	
	args = ap.parse_args()
	# if symfile is unspecified, use the rom name as the symfile name
	if args.symfile is None:
		args.symfile = args.rom.split(".")[0] + ".sym"
	
	# flag to determine whether to use the extras submodule path for labels/constants or the disassembly path
	if args.use_disasm_path:
		conf = configuration.Config(path=os.path.abspath(os.path.join(os.getcwd(),"../..")))
	else:
		conf = configuration.Config()
	
	# initialize disassembler
	disasm = Disassembler(conf)
	disasm.initialize(args.rom, args.symfile)
	
	# get global address of the start and stop offsets
	start_addr = get_raw_addr(args.offset)
	stop_addr = get_raw_addr(args.end)
	
	# run the disassembler and return the output
	output = disasm.output_bank_opcodes(start_addr,stop_addr,hard_stop=args.dry_run,parse_data=args.parse_data)[0]
	
	# suppress output if quiet flag is set
	if not args.quiet:
		print(output)
	
	# only write to the output file if the no write flag is unset
	if not args.no_write:
		with open(args.filename, "w") as f:
			f.write(output)