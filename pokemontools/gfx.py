# -*- coding: utf-8 -*-

import os
import sys
import png
from math import sqrt, floor, ceil
import argparse

import configuration
config = configuration.Config()

import pokemon_constants
import trainers
import romstr


def load_rom():
    rom = romstr.RomStr.load(filename=config.rom_path)
    return bytearray(rom)

def rom_offset(bank, address):
    if address < 0x4000 or address >= 0x8000:
        return address
    return bank * 0x4000 + address - 0x4000 * bool(bank)


def split(list_, interval):
    """
    Split a list by length.
    """
    for i in xrange(0, len(list_), interval):
        j = min(i + interval, len(list_))
        yield list_[i:j]


def hex_dump(data, length=0x10):
    """
    just use hexdump -C
    """
    margin = len('%x' % len(data))
    output = []
    address = 0
    for line in split(data, length):
        output += [
            hex(address)[2:].zfill(margin) +
            ' | ' +
            ' '.join('%.2x' % byte for byte in line)
        ]
        address += length
    return '\n'.join(output)


def get_tiles(image):
    """
    Split a 2bpp image into 8x8 tiles.
    """
    return list(split(image, 0x10))

def connect(tiles):
    """
    Combine 8x8 tiles into a 2bpp image.
    """
    return [byte for tile in tiles for byte in tile]

def transpose(tiles, width=None):
    """
    Transpose a tile arrangement along line y=-x.

      00 01 02 03 04 05     00 06 0c 12 18 1e
      06 07 08 09 0a 0b     01 07 0d 13 19 1f
      0c 0d 0e 0f 10 11 <-> 02 08 0e 14 1a 20
      12 13 14 15 16 17     03 09 0f 15 1b 21
      18 19 1a 1b 1c 1d     04 0a 10 16 1c 22
      1e 1f 20 21 22 23     05 0b 11 17 1d 23

      00 01 02 03     00 04 08
      04 05 06 07 <-> 01 05 09
      08 09 0a 0b     02 06 0a
                      03 07 0b
    """
    if width == None:
        width = int(sqrt(len(tiles))) # assume square image
    tiles = sorted(enumerate(tiles), key= lambda (i, tile): i % width)
    return [tile for i, tile in tiles]

def transpose_tiles(image, width=None):
    return connect(transpose(get_tiles(image), width))

def interleave(tiles, width):
    """
      00 01 02 03 04 05     00 02 04 06 08 0a
      06 07 08 09 0a 0b     01 03 05 07 09 0b
      0c 0d 0e 0f 10 11 --> 0c 0e 10 12 14 16
      12 13 14 15 16 17     0d 0f 11 13 15 17
      18 19 1a 1b 1c 1d     18 1a 1c 1e 20 22
      1e 1f 20 21 22 23     19 1b 1d 1f 21 23
    """
    interleaved = []
    left, right = split(tiles[::2], width), split(tiles[1::2], width)
    for l, r in zip(left, right):
        interleaved += l + r
    return interleaved

def deinterleave(tiles, width):
    """
      00 02 04 06 08 0a     00 01 02 03 04 05 
      01 03 05 07 09 0b     06 07 08 09 0a 0b
      0c 0e 10 12 14 16 --> 0c 0d 0e 0f 10 11
      0d 0f 11 13 15 17     12 13 14 15 16 17
      18 1a 1c 1e 20 22     18 19 1a 1b 1c 1d
      19 1b 1d 1f 21 23     1e 1f 20 21 22 23
    """
    deinterleaved = []
    rows = list(split(tiles, width))
    for left, right in zip(rows[::2], rows[1::2]):
        for l, r in zip(left, right):
            deinterleaved += [l, r]
    return deinterleaved

def interleave_tiles(image, width):
    return connect(interleave(get_tiles(image), width))

def deinterleave_tiles(image, width):
    return connect(deinterleave(get_tiles(image), width))


def condense_tiles_to_map(image):
    tiles = get_tiles(image)
    new_tiles = []
    tilemap = []
    for tile in tiles:
        if tile not in new_tiles:
            new_tiles += [tile]
        tilemap += [new_tiles.index(tile)]
    new_image = connect(new_tiles)
    return new_image, tilemap


def to_file(filename, data):
    file = open(filename, 'wb')
    for byte in data:
        file.write('%c' % byte)
    file.close()



"""
A rundown of Pokemon Crystal's compression scheme:

Control commands occupy bits 5-7.
Bits 0-4 serve as the first parameter <n> for each command.
"""
lz_commands = {
    'literal':   0, # n values for n bytes
    'iterate':   1, # one value for n bytes
    'alternate': 2, # alternate two values for n bytes
    'blank':     3, # zero for n bytes
}

"""
Repeater commands repeat any data that was just decompressed.
They take an additional signed parameter <s> to mark a relative starting point.
These wrap around (positive from the start, negative from the current position).
"""
lz_commands.update({
    'repeat':    4, # n bytes starting from s
    'flip':      5, # n bytes in reverse bit order starting from s
    'reverse':   6, # n bytes backwards starting from s
})

"""
The long command is used when 5 bits aren't enough. Bits 2-4 contain a new control code.
Bits 0-1 are appended to a new byte as 8-9, allowing a 10-bit parameter.
"""
lz_commands.update({
    'long':      7, # n is now 10 bits for a new control code
})
max_length = 1 << 10 # can't go higher than 10 bits
lowmax = 1 << 5 # standard 5-bit param

"""
If 0xff is encountered instead of a command, decompression ends.
"""
lz_end = 0xff


class Compressed:

    def __init__(self, data=None, commands=lz_commands, debug=False):
        self.data = list(bytearray(data))
        self.commands = commands
        self.debug = debug
        self.compress()

    def byte_at(self, address):
        if address < len(self.data):
            return self.data[address]
        return None

    def compress(self):
        """
        This algorithm is greedy.
        It aims to match the compressor it's based on as closely as possible.
        It doesn't, but in the meantime the output is smaller.
        """
        self.address = 0
        self.end     = len(self.data)
        self.output  = []
        self.literal = []

        while self.address < self.end:
            # Tally up the number of bytes that can be compressed
            # by a single command from the current address.
            self.scores = {}
            for method in self.commands.keys():
                self.scores[method] = 0

            # The most common byte by far is 0 (whitespace in
            # images and padding in tilemaps and regular data).
            address = self.address
            while self.byte_at(address) == 0x00:
                self.scores['blank'] += 1
                address += 1

            # In the same vein, see how long the same byte repeats for.
            address = self.address
            self.iter = self.byte_at(address)
            while self.byte_at(address) == self.iter:
                self.scores['iterate'] += 1
                address += 1

            # Do it again, but for alternating bytes.
            address = self.address
            self.alts = []
            self.alts += [self.byte_at(address)]
            self.alts += [self.byte_at(address + 1)]
            while self.byte_at(address) == self.alts[(address - self.address) % 2]:
                self.scores['alternate'] += 1
                address += 1

            # Check if we can repeat any data that the
            # decompressor just output (here, the input data).
            # TODO this includes the current command's output
            self.matches = {}
            last_matches = {}
            address = self.address
            min_length = 4 # minimum worthwhile length
            max_length = 9 # any further and the time loss is too significant
            for length in xrange(min_length, min(len(self.data) - address, max_length)):
                keyword = self.data[address:address+length]
                for offset, byte in enumerate(self.data[:address]):
                    # offset ranges are -0x80:-1 and 0:0x7fff
                    if offset > 0x7fff and offset < address - 0x80:
                        continue
                    if byte == keyword[0]:
                        # Straight repeat...
                        if self.data[offset:offset+length] == keyword:
                            if self.scores['repeat'] < length:
                                self.scores['repeat'] = length
                                self.matches['repeat'] = offset
                        # In reverse...
                        if self.data[offset-1:offset-length-1:-1] == keyword:
                            if self.scores['reverse'] < length:
                                self.scores['reverse'] = length
                                self.matches['reverse'] = offset
                    # Or bitflipped
                    if self.bit_flip([byte]) == self.bit_flip([keyword[0]]):
                        if self.bit_flip(self.data[offset:offset+length]) == self.bit_flip(keyword):
                            if self.scores['flip'] < length:
                                self.scores['flip'] = length
                                self.matches['flip'] = offset
                if self.matches == last_matches:
                    break
                last_matches = list(self.matches)

            # If the scores are too low, try again from the next byte.
            if not any(map(lambda x: {
                'blank':     1,
                'iterate':   2,
                'alternate': 3,
                'repeat':    3,
                'reverse':   3,
                'flip':      3,
            }.get(x[0], 10000) < x[1], self.scores.items())):
                self.literal += [self.data[self.address]]
                self.address += 1

            else: # payload
                # bug: literal [00] is a byte longer than blank 1.
                # this bug exists in the target compressor as well,
                # so don't fix until we've given up on replicating it.
                self.do_literal()
                self.do_scored()

        # unload any literals we're sitting on
        self.do_literal()
        self.output += [lz_end]

    def bit_flip(self, data):
        return [sum(((byte >> i) & 1) << (7 - i) for i in xrange(8)) for byte in data]

    def do_literal(self):
        if self.literal:
            cmd = self.commands['literal']
            length = len(self.literal)
            self.do_cmd(cmd, length)
            # self.address has already been
            # incremented in the main loop
            self.literal = []

    def do_cmd(self, cmd, length):
        if length > max_length:
            length = max_length

        cmd_length = length - 1

        if length > lowmax:
            output = [(self.commands['long'] << 5) + (cmd << 2) + (cmd_length >> 8)]
            output += [cmd_length & 0xff]
        else:
            output = [(cmd << 5) + cmd_length]

        if cmd == self.commands['literal']:
            output += self.literal
        elif cmd == self.commands['iterate']:
            output += [self.iter]
        elif cmd == self.commands['alternate']:
            output += self.alts
        else:
            for command in ['repeat', 'reverse', 'flip']:
                if cmd == self.commands[command]:
                    offset = self.matches[command]
                    # negative offsets are a byte shorter
                    if self.address - offset <= 0x80:
                        offset = self.address - offset + 0x80
                        if cmd == self.commands['repeat']:
                            offset -= 1 # this is a hack, but it seems to work
                        output += [offset]
                    else:
                        output += [offset / 0x100, offset % 0x100]

        if self.debug:
            print (
                  dict(map(reversed, self.commands.items()))[cmd],
                  length, '\t',
                  ' '.join(map('{:02x}'.format, output))
            )

        self.output += output
        return length

    def do_scored(self):
        # Which command did the best?
        winner, score = sorted(
            self.scores.items(),
            key=lambda x:(-x[1], [
                'blank',
                'repeat',
                'reverse',
                'flip',
                'iterate',
                'alternate',
                'literal',
                'long', # hack
            ].index(x[0]))
        )[0]
        cmd = self.commands[winner]
        length = self.do_cmd(cmd, score)
        self.address += length



class Decompressed:
    """
    Parse compressed data, usually 2bpp.

    parameters:
        [compressed data]
        [tile arrangement] default: 'vert'
        [size of pic] default: None
        [start] (optional)

    splits output into pic [size] and animation tiles if applicable
    data can be fed in from rom if [start] is specified
    """

    def __init__(self, lz=None, start=0, debug=False):
        # todo: play nice with Compressed

        assert lz, 'need something to decompress!'
        self.lz = bytearray(lz)

        self.byte = None
        self.address = 0
        self.start = start

        self.output = []

        self.decompress()

        self.compressed_data = self.lz[self.start : self.start + self.address]

        # print tuple containing start and end address
        if debug: print '(' + hex(self.start) + ', ' + hex(self.start + self.address+1) + '),'


    def command_list(self):
        """
        Print a list of commands that were used. Useful for debugging.
        """

        data = bytearray(self.lz)
        address = self.address
        while 1:
            cmd_addr = address
            byte = data[address]
            address += 1
            if byte == lz_end: break
            cmd = (byte >> 5) & 0b111
            if cmd == lz_commands['long']:
                cmd = (byte >> 2) & 0b111
                length = (byte & 0b11) << 8
                length += data[address]
                address += 1
            else:
                length = byte & 0b11111
            length += 1
            name = dict(map(reversed, lz_commands.items()))[cmd]
            if name == 'iterate':
                address += 1
            elif name == 'alternate':
                address += 2
            elif name in ['repeat', 'reverse', 'flip']:
                if data[address] < 0x80:
                    address += 2
                else:
                    address += 1
            elif name == 'literal':
                address += length
            print name, length, '\t', ' '.join(map('{:02x}'.format, list(data)[cmd_addr:address]))


    def decompress(self):
        """
        Replica of crystal's decompression.
        """

        self.output = []

        while True:
            self.getCurByte()

            if (self.byte == lz_end):
                self.address += 1
                break

            self.cmd = (self.byte & 0b11100000) >> 5

            if self.cmd == lz_commands['long']: # 10-bit param
                self.cmd = (self.byte & 0b00011100) >> 2
                self.length = (self.byte & 0b00000011) << 8
                self.next()
                self.length += self.byte + 1
            else: # 5-bit param
                self.length = (self.byte & 0b00011111) + 1

            # literals
            if self.cmd == lz_commands['literal']:
                self.doLiteral()
            elif self.cmd == lz_commands['iterate']:
                self.doIter()
            elif self.cmd == lz_commands['alternate']:
                self.doAlt()
            elif self.cmd == lz_commands['blank']:
                self.doZeros()

            else: # repeaters
                self.next()
                if self.byte > 0x7f: # negative
                    self.displacement = self.byte & 0x7f
                    self.displacement = len(self.output) - self.displacement - 1
                else: # positive
                    self.displacement = self.byte * 0x100
                    self.next()
                    self.displacement += self.byte

                if self.cmd == lz_commands['flip']:
                    self.doFlip()
                elif self.cmd == lz_commands['reverse']:
                    self.doReverse()
                else: # lz_commands['repeat']
                    self.doRepeat()

            self.address += 1
            #self.next() # somewhat of a hack


    def getCurByte(self):
        self.byte = self.lz[self.start+self.address]

    def next(self):
        self.address += 1
        self.getCurByte()

    def doLiteral(self):
        """
        Copy data directly.
        """
        for byte in range(self.length):
            self.next()
            self.output.append(self.byte)

    def doIter(self):
        """
        Write one byte repeatedly.
        """
        self.next()
        for byte in range(self.length):
            self.output.append(self.byte)

    def doAlt(self):
        """
        Write alternating bytes.
        """
        self.alts = []
        self.next()
        self.alts.append(self.byte)
        self.next()
        self.alts.append(self.byte)

        for byte in range(self.length):
            self.output.append(self.alts[byte&1])

    def doZeros(self):
        """
        Write zeros.
        """
        for byte in range(self.length):
            self.output.append(0x00)

    def doFlip(self):
        """
        Repeat flipped bytes from output.

        eg  11100100 -> 00100111
        quat 3 2 1 0 ->  0 2 1 3
        """
        for byte in range(self.length):
            flipped = sum(1<<(7-i) for i in range(8) if self.output[self.displacement+byte]>>i&1)
            self.output.append(flipped)

    def doReverse(self):
        """
        Repeat reversed bytes from output.
        """
        for byte in range(self.length):
            self.output.append(self.output[self.displacement-byte])

    def doRepeat(self):
        """
        Repeat bytes from output.
        """
        for byte in range(self.length):
            self.output.append(self.output[self.displacement+byte])



sizes = [
    5, 6, 7, 5, 6, 7, 5, 6, 7, 5, 5, 7, 5, 5, 7, 5,
    6, 7, 5, 6, 5, 7, 5, 7, 5, 7, 5, 6, 5, 6, 7, 5,
    6, 7, 5, 6, 6, 7, 5, 6, 5, 7, 5, 6, 7, 5, 7, 5,
    7, 5, 7, 5, 7, 5, 7, 5, 7, 5, 7, 5, 6, 7, 5, 6,
    7, 5, 7, 7, 5, 6, 7, 5, 6, 5, 6, 6, 6, 7, 5, 7,
    5, 6, 6, 5, 7, 6, 7, 5, 7, 5, 7, 7, 6, 6, 7, 6,
    7, 5, 7, 5, 5, 7, 7, 5, 6, 7, 6, 7, 6, 7, 7, 7,
    6, 6, 7, 5, 6, 6, 7, 6, 6, 6, 7, 6, 6, 6, 7, 7,
    6, 7, 7, 5, 5, 6, 6, 6, 6, 5, 6, 5, 6, 7, 7, 7,
    7, 7, 5, 6, 7, 7, 5, 5, 6, 7, 5, 6, 7, 5, 6, 7,
    6, 6, 5, 7, 6, 6, 5, 7, 7, 6, 6, 5, 5, 5, 5, 7,
    5, 6, 5, 6, 7, 7, 5, 7, 6, 7, 5, 6, 7, 5, 5, 6,
    6, 5, 6, 6, 6, 6, 7, 6, 5, 6, 7, 5, 7, 6, 6, 7,
    6, 6, 5, 7, 5, 6, 6, 5, 7, 5, 6, 5, 6, 6, 5, 6,
    6, 7, 7, 6, 7, 7, 5, 7, 6, 7, 7, 5, 7, 5, 6, 6,
    6, 7, 7, 7, 7, 5, 6, 7, 7, 7, 5,
]

def make_sizes(num_monsters=251):
    """
    Front pics have specified sizes.
    """
    rom = load_rom()
    base_stats = 0x51424

    address = base_stats + 0x11 # pic size
    sizes   = rom[address : address + 0x20 * num_monsters : 0x20]
    sizes   = map(lambda x: str(x & 0xf), sizes)
    return '\n'.join(' ' * 8 + ', '.join(split(sizes, 16)))


def decompress_fx_by_id(i, fxs=0xcfcf6):
    rom = load_rom()
    addr = fxs + i * 4

    num_tiles = rom[addr]
    bank      = rom[addr+1]
    address   = rom[addr+3] * 0x100 + rom[addr+2]

    offset = rom_offset(bank, address)
    fx = Decompressed(rom, start=offset)
    return fx

def rip_compressed_fx(dest='gfx/fx', num_fx=40, fxs=0xcfcf6):
    for i in xrange(num_fx):
        name = '%.3d' % i
        fx = decompress_fx_by_id(i, fxs)
        filename = os.path.join(dest, name + '.2bpp.lz')
        to_file(filename, fx.compressed_data)


monsters = 0x120000
num_monsters = 251

unowns = 0x124000
num_unowns = 26
unown_dex = 201

def decompress_monster_by_id(rom, mon=0, face='front', crystal=True):
    """
    For Unown, use decompress_unown_by_id instead.
    """
    if crystal:
        bank_offset = 0x36
    else:
        bank_offset = 0

    address = monsters + (mon * 2 + {'front': 0, 'back': 1}.get(face, 0)) * 3
    bank    = rom[address] + bank_offset
    address = rom[address+2] * 0x100 + rom[address+1]
    address = bank * 0x4000 + (address - (0x4000 * bool(bank)))
    monster = Decompressed(rom, start=address)
    return monster

def rip_compressed_monster_pics(rom, dest='gfx/pics/', face='both', num_mons=num_monsters, crystal=True):
    """
    Extract <num_mons> compressed Pokemon pics from <rom> to directory <dest>.
    """
    for mon in range(num_mons):

        mon_name = pokemon_constants[mon + 1].lower().replace('__','_')
        size = sizes[mon]

        if mon + 1 == unown_dex:
            rip_compressed_unown_pics(
                rom=rom,
                dest=dest,
                face=face,
                num_letters=num_unowns,
                mon_name=mon_name,
                size=size,
                crystal=crystal,
            )

        if face in ['front', 'both']:
            monster  = decompress_monster_by_id(rom, mon, 'front', crystal)
            filename = 'front.{0}x{0}.2bpp.lz'.format(size)
            path     = os.path.join(dest, mon_name, filename)
            to_file(path, monster.compressed_data)

        if face in ['back', 'both']:
            monster  = decompress_monster_by_id(rom, mon, 'back', crystal)
            filename = 'back.6x6.2bpp.lz'
            path     = os.path.join(dest, mon_name, filename)
            to_file(path, monster.compressed_data)

def decompress_unown_by_id(rom, letter, face='front', crystal=True):
    if crystal:
        bank_offset = 0x36
    else:
        bank_offset = 0

    address = unowns + (letter * 2 + {'front': 0, 'back': 1}.get(face, 0)) * 3
    bank    = rom[address] + bank_offset
    address = rom[address+2] * 0x100 + rom[address+1]
    address = (bank * 0x4000) + (address - (0x4000 * bool(bank)))
    unown   = Decompressed(rom, start=address)
    return unown

def rip_compressed_unown_pics(rom, dest='gfx/pics/', face='both', num_letters=num_unowns, mon_name='unown', size=sizes[201], crystal=True):
    """
    Extract <num_letters> compressed Unown pics from <rom> to directory <dest>.
    """
    for letter in range(num_letters):
        name = mon_name + '_{}'.format(chr(ord('A') + letter))

        if face in ['front', 'both']:
            unown    = decompress_unown_by_id(rom, letter, 'front', crystal)
            filename = 'front.{0}x{0}.2bpp.lz'.format(size)
            path     = os.path.join(dest, name, filename)
            to_file(path, unown.compressed_data)

        if face in ['back', 'both']:
            unown    = decompress_unown_by_id(rom, letter, 'back', crystal)
            filename = 'back.6x6.2bpp.lz'
            path     = os.path.join(dest, name, filename)
            to_file(path, unown.compressed_data)


trainers_offset = 0x128000
num_trainers = 67
trainer_names = [t['constant'] for i, t in trainers.trainer_group_names.items()]

def decompress_trainer_by_id(rom, i, crystal=True):
    rom = load_rom()
    if crystal:
        bank_offset = 0x36
    else:
        bank_offset = 0

    address = trainers_offset + i * 3
    bank    = rom[address] + bank_offset
    address = rom[address+2] * 0x100 + rom[address+1]
    address = rom_offset(bank, address)
    trainer = Decompressed(rom, start=address)
    return trainer

def rip_compressed_trainer_pics(rom):
    for t in xrange(num_trainers):
        trainer_name = trainer_names[t].lower().replace('_','')
        trainer  = decompress_trainer_by_id(t)
        filename = os.path.join('gfx/trainers/', trainer_name + '.6x6.2bpp.lz')
        to_file(filename, trainer.compressed_data)


# in order of use (besides repeats)
intro_gfx = [
    ('logo',          0x109407),
    ('unowns',         0xE5F5D),
    ('pulse',          0xE634D),
    ('background',     0xE5C7D),
    ('pichu_wooper',   0xE592D),
    ('suicune_run',    0xE555D),
    ('suicune_jump',   0xE6DED),
    ('unown_back',     0xE785D),
    ('suicune_close',  0xE681D),
    ('suicune_back',   0xE72AD),
    ('crystal_unowns', 0xE662D),
]

intro_tilemaps = [
    ('001', 0xE641D),
    ('002', 0xE63DD),
    ('003', 0xE5ECD),
    ('004', 0xE5E6D),
    ('005', 0xE647D),
    ('006', 0xE642D),
    ('007', 0xE655D),
    ('008', 0xE649D),
    ('009', 0xE76AD),
    ('010', 0xE764D),
    ('011', 0xE6D0D),
    ('012', 0xE6C3D),
    ('013', 0xE778D),
    ('014', 0xE76BD),
    ('015', 0xE676D),
    ('017', 0xE672D),
]

def rip_compressed_intro(rom, dest='gfx/intro'):

    for name, address in intro_gfx:
        filename = os.path.join(dest, name + '.2bpp.lz')
        rip_compressed_gfx(rom, address, filename)

    for name, address in intro_tilemaps:
        filename = os.path.join(dest, name + '.tilemap.lz')
        rip_compressed_gfx(rom, address, filename)


title_gfx = [
    ('suicune', 0x10EF46),
    ('logo',    0x10F326),
    ('crystal', 0x10FCEE),
]

def rip_compressed_title(rom, dest='gfx/title'):
    for name, address in title_gfx:
        filename = os.path.join(dest, name + '.2bpp.lz')
        rip_compressed_gfx(rom, address, filename)


def rip_compressed_tilesets(rom, dest='gfx/tilesets'):
    tileset_headers = 0x4d596
    len_tileset     = 15
    num_tilesets    = 0x25

    for tileset in xrange(num_tilesets):
        addr = tileset * len_tileset + tileset_headers

        bank     = rom[addr]
        address  = rom[addr + 2] * 0x100 + rom[addr + 1]
        offset   = rom_offset(bank, address)

        filename = os.path.join(dest, tileset_name + '.2bpp.lz')
        rip_compressed_gfx(rom, address, filename)


misc_pics = [
    ('player', 0x2BA1A, '6x6'),
    ('dude',   0x2BBAA, '6x6'),
]

misc = [
    ('town_map',         0xF8BA0),
    ('pokegear',         0x1DE2E4),
    ('pokegear_sprites', 0x914DD),
]

def rip_compressed_misc(rom, dest='gfx/misc'):
    for name, address in misc:
        filename = os.path.join(dest, name+ '.2bpp.lz')
        rip_compressed_gfx(rom, address, filename)
    for name, address, dimensions in misc_pics:
        filename = os.path.join(dest, name + '.' + dimensions + '.2bpp.lz')
        rip_compressed_gfx(rom, address, filename)


def rip_compressed_gfx(rom, address, filename):
    gfx = Decompressed(rom, start=address)
    to_file(filename, gfx.compressed_data)


def rip_bulk_gfx(rom, dest='gfx', crystal=True):
    rip_compressed_monster_pics(rom, dest=os.path.join(dest, 'pics'),     crystal=crystal)
    rip_compressed_trainer_pics(rom, dest=os.path.join(dest, 'trainers'), crystal=crystal)
    rip_compressed_fx          (rom, dest=os.path.join(dest, 'fx'))
    rip_compressed_intro       (rom, dest=os.path.join(dest, 'intro'))
    rip_compressed_title       (rom, dest=os.path.join(dest, 'title'))
    rip_compressed_tilesets    (rom, dest=os.path.join(dest, 'tilesets'))
    rip_compressed_misc        (rom, dest=os.path.join(dest, 'misc'))


def decompress_from_address(address, filename='de.2bpp'):
    """
    Write decompressed data from an address to a 2bpp file.
    """
    rom = load_rom()
    image = Decompressed(rom, start=address)
    to_file(filename, image.output)


def decompress_file(filein, fileout=None):
    image = bytearray(open(filein).read())
    de = Decompressed(image)

    if fileout == None:
        fileout = os.path.splitext(filein)[0]
    to_file(fileout, de.output)


def compress_file(filein, fileout=None):
    image = bytearray(open(filein).read())
    lz = Compressed(image)

    if fileout == None:
        fileout = filein + '.lz'
    to_file(fileout, lz.output)



def get_uncompressed_gfx(start, num_tiles, filename):
    """
    Grab tiles directly from rom and write to file.
    """
    rom = load_rom()
    bytes_per_tile = 0x10
    length = num_tiles * bytes_per_tile
    end    = start + length
    image  = rom[start:end]
    to_file(filename, image)



def bin_to_rgb(word):
    red   = word & 0b11111
    word >>= 5
    green = word & 0b11111
    word >>= 5
    blue  = word & 0b11111
    return (red, green, blue)

def rgb_from_rom(address, length=0x80):
    rom = load_rom()
    return convert_binary_pal_to_text(rom[address:address+length])

def convert_binary_pal_to_text_by_filename(filename):
    pal = bytearray(open(filename).read())
    return convert_binary_pal_to_text(pal)

def convert_binary_pal_to_text(pal):
    output = ''
    words = [hi * 0x100 + lo for lo, hi in zip(pal[::2], pal[1::2])]
    for word in words:
        red, green, blue = ['%.2d' % c for c in bin_to_rgb(word)]
        output += '\tRGB ' + ', '.join((red, green, blue))
        output += '\n'
    return output

def read_rgb_macros(lines):
    colors = []
    for line in lines:
        macro = line.split(" ")[0].strip()
        if macro == 'RGB':
            params = ' '.join(line.split(" ")[1:]).split(',')
            red, green, blue = [int(v) for v in params]
            colors += [[red, green, blue]]
    return colors


def rewrite_binary_pals_to_text(filenames):
    for filename in filenames:
        pal_text = convert_binary_pal_to_text_by_filename(filename)
        with open(filename, 'w') as out:
            out.write(pal_text)


def dump_monster_pals():
    rom = load_rom()

    pals = 0xa8d6
    pal_length = 0x4
    for mon in range(251):

        name     = pokemon_constants.pokemon_constants[mon+1].title().replace('_','')
        num      = str(mon+1).zfill(3)
        dir      = 'gfx/pics/'+num+'/'

        address  = pals + mon*pal_length*2


        pal_data = []
        for byte in range(pal_length):
            pal_data.append(rom[address])
            address += 1

        filename = 'normal.pal'
        to_file('../'+dir+filename, pal_data)

        spacing  = ' ' * (15 - len(name))
        #print name+'Palette:'+spacing+' INCBIN "'+dir+filename+'"'


        pal_data = []
        for byte in range(pal_length):
            pal_data.append(rom[address])
            address += 1

        filename = 'shiny.pal'
        to_file('../'+dir+filename, pal_data)

        spacing  = ' ' * (10 - len(name))
        #print name+'ShinyPalette:'+spacing+' INCBIN "'+dir+filename+'"'


def dump_trainer_pals():
    rom = load_rom()

    pals = 0xb0d2
    pal_length = 0x4
    for trainer in range(67):

        name = trainers.trainer_group_names[trainer+1]['constant'].title().replace('_','')
        num  = str(trainer).zfill(3)
        dir  = 'gfx/trainers/'

        address = pals + trainer*pal_length

        pal_data = []
        for byte in range(pal_length):
            pal_data.append(rom[address])
            address += 1

        filename = num+'.pal'
        to_file('../'+dir+filename, pal_data)

        spacing = ' ' * (12 - len(name))
        print name+'Palette:'+spacing+' INCBIN"'+dir+filename+'"'



def flatten(planar):
    """
    Flatten planar 2bpp image data into a quaternary pixel map.
    """
    strips = []
    for bottom, top in split(planar, 2):
        bottom = bottom
        top = top
        strip = []
        for i in xrange(7,-1,-1):
            color = (
                (bottom >> i & 1) +
                (top *2 >> i & 2)
            )
            strip += [color]
        strips += strip
    return strips


def to_lines(image, width):
    """
    Convert a tiled quaternary pixel map to lines of quaternary pixels.
    """
    tile_width = 8
    tile_height = 8
    num_columns = width / tile_width
    height = len(image) / width

    lines = []
    for cur_line in xrange(height):
        tile_row = cur_line / tile_height
        line = []
        for column in xrange(num_columns):
            anchor = (
                num_columns * tile_row * tile_width * tile_height +
                column * tile_width * tile_height +
                cur_line % tile_height * tile_width
            )
            line += image[anchor : anchor + tile_width]
        lines += [line]
    return lines


def dmg2rgb(word):
    """
    For PNGs.
    """
    def shift(value):
        while True:
            yield value & (2**5 - 1)
            value >>= 5
    word = shift(word)
    # distribution is less even w/ << 3
    red, green, blue = [int(color * 8.25) for color in [word.next() for _ in xrange(3)]]
    alpha = 255
    return (red, green, blue, alpha)


def rgb_to_dmg(color):
    """
    For PNGs.
    """
    word =  (color['r'] / 8)
    word += (color['g'] / 8) << 5
    word += (color['b'] / 8) << 10
    return word


def pal_to_png(filename):
    """
    Interpret a .pal file as a png palette.
    """
    with open(filename) as rgbs:
        colors = read_rgb_macros(rgbs.readlines())
    a = 255
    palette = []
    for color in colors:
        # even distribution over 000-255
        r, g, b = [int(hue * 8.25) for hue in color]
        palette += [(r, g, b, a)]
    white = (255,255,255,255)
    black = (000,000,000,255)
    if white not in palette and len(palette) < 4:
        palette = [white] + palette
    if black not in palette and len(palette) < 4:
        palette = palette + [black]
    return palette


def png_to_rgb(palette):
    """
    Convert a png palette to rgb macros.
    """
    output = ''
    for color in palette:
        r, g, b = [color[c] / 8 for c in 'rgb']
        output += '\tRGB ' + ', '.join(['%.2d' % hue for hue in (r, g, b)])
        output += '\n'
    return output


def read_filename_arguments(filename):
    int_args = {
        'w': 'width',
        'h': 'height',
        't': 'tile_padding',
    }
    parsed_arguments = {}
    arguments = os.path.splitext(filename)[0].split('.')[1:]
    for argument in arguments:
        arg   = argument[0]
        param = argument[1:]
        if param.isdigit():
            arg = int_args.get(arg, False)
            if arg:
                parsed_arguments[arg] = int(param)
        elif len(argument) == 3:
            w, x, h = argument[:3]
            if w.isdigit() and h.isdigit() and x == 'x':
                parsed_arguments['pic_dimensions'] = (int(w), int(h))
        elif argument == 'interleave':
            parsed_arguments['interleave'] = True
        elif argument == 'norepeat':
            parsed_arguments['norepeat'] = True
        elif argument == 'arrange':
            parsed_arguments['norepeat'] = True
            parsed_arguments['tilemap']  = True
    return parsed_arguments


def export_2bpp_to_png(filein, fileout=None, pal_file=None, height=0, width=0, tile_padding=0, pic_dimensions=None):

    if fileout == None:
        fileout = os.path.splitext(filein)[0] + '.png'

    image = open(filein, 'rb').read()

    arguments = {
        'width': width,
        'height': height,
        'pal_file': pal_file,
        'tile_padding': tile_padding,
        'pic_dimensions': pic_dimensions,
    }
    arguments.update(read_filename_arguments(filein))

    if pal_file == None:
        if os.path.exists(os.path.splitext(fileout)[0]+'.pal'):
            arguments['pal_file'] = os.path.splitext(fileout)[0]+'.pal'

    result = convert_2bpp_to_png(image, **arguments)
    width, height, palette, greyscale, bitdepth, px_map = result

    w = png.Writer(
        width,
        height,
        palette=palette,
        compression=9,
        greyscale=greyscale,
        bitdepth=bitdepth
    )
    with open(fileout, 'wb') as f:
        w.write(f, px_map)


def convert_2bpp_to_png(image, **kwargs):
    """
    Convert a planar 2bpp graphic to png.
    """

    image = bytearray(image)

    pad_color = bytearray([0])

    width          = kwargs.get('width', 0)
    height         = kwargs.get('height', 0)
    tile_padding   = kwargs.get('tile_padding', 0)
    pic_dimensions = kwargs.get('pic_dimensions', None)
    pal_file       = kwargs.get('pal_file', None)
    interleave     = kwargs.get('interleave', False)

    # Width must be specified to interleave.
    if interleave and width:
        image = interleave_tiles(image, width / 8)

    # Pad the image by a given number of tiles if asked.
    image += pad_color * 0x10 * tile_padding

    # Some images are transposed in blocks.
    if pic_dimensions:
        w, h  = pic_dimensions
        if not width: width = w * 8

        pic_length = w * h * 0x10

        trailing = len(image) % pic_length

        pic = []
        for i in xrange(0, len(image) - trailing, pic_length):
            pic += transpose_tiles(image[i:i+pic_length], h)
        image = bytearray(pic) + image[len(image) - trailing:]

        # Pad out trailing lines.
        image += pad_color * 0x10 * ((w - (len(image) / 0x10) % h) % w)

    def px_length(img):
        return len(img) * 4
    def tile_length(img):
        return len(img) * 4 / (8*8)

    if width and height:
        tile_width = width / 8
        more_tile_padding = (tile_width - (tile_length(image) % tile_width or tile_width))
        image += pad_color * 0x10 * more_tile_padding

    elif width and not height:
        tile_width = width / 8
        more_tile_padding = (tile_width - (tile_length(image) % tile_width or tile_width))
        image += pad_color * 0x10 * more_tile_padding
        height = px_length(image) / width

    elif height and not width:
        tile_height = height / 8
        more_tile_padding = (tile_height - (tile_length(image) % tile_height or tile_height))
        image += pad_color * 0x10 * more_tile_padding
        width = px_length(image) / height

    # at least one dimension should be given
    if width * height != px_length(image):
        # look for possible combos of width/height that would form a rectangle
        matches = []
        # Height need not be divisible by 8, but width must.
        # See pokered gfx/minimize_pic.1bpp.
        for w in range(8, px_length(image) / 2 + 1, 8):
            h = px_length(image) / w
            if w * h == px_length(image):
                matches += [(w, h)]
        # go for the most square image
        if len(matches):
            width, height = sorted(matches, key= lambda (w, h): (h % 8 != 0, w + h))[0] # favor height
        else:
            raise Exception, 'Image can\'t be divided into tiles (%d px)!' % (px_length(image))

    # convert tiles to lines
    lines = to_lines(flatten(image), width)

    if pal_file == None:
        palette   = None
        greyscale = True
        bitdepth  = 2
        px_map    = [[3 - pixel for pixel in line] for line in lines]

    else: # gbc color
        palette   = pal_to_png(pal_file)
        greyscale = False
        bitdepth  = 8
        px_map    = [[pixel for pixel in line] for line in lines]

    return width, height, palette, greyscale, bitdepth, px_map


def export_png_to_2bpp(filein, fileout=None, palout=None, tile_padding=0, pic_dimensions=None):

    arguments = {
        'tile_padding': tile_padding,
        'pic_dimensions': pic_dimensions,
    }
    arguments.update(read_filename_arguments(filein))

    image, palette, tmap = png_to_2bpp(filein, **arguments)

    if fileout == None:
        fileout = os.path.splitext(filein)[0] + '.2bpp'
    to_file(fileout, image)

    if tmap != None:
        mapout = os.path.splitext(fileout)[0] + '.tilemap'
        to_file(mapout, tmap)

    if palout == None:
        palout = os.path.splitext(fileout)[0] + '.pal'
    export_palette(palette, palout)


def get_image_padding(width, height, wstep=8, hstep=8):

    padding = {
        'left':   0,
        'right':  0,
        'top':    0,
        'bottom': 0,
    }

    if width % wstep and width >= wstep:
       pad = float(width % wstep) / 2
       padding['left']   = int(ceil(pad))
       padding['right']  = int(floor(pad))

    if height % hstep and height >= hstep:
       pad = float(height % hstep) / 2
       padding['top']    = int(ceil(pad))
       padding['bottom'] = int(floor(pad))

    return padding


def png_to_2bpp(filein, **kwargs):
    """
    Convert a png image to planar 2bpp.
    """

    tile_padding   = kwargs.get('tile_padding', 0)
    pic_dimensions = kwargs.get('pic_dimensions', None)
    interleave     = kwargs.get('interleave', False)
    norepeat       = kwargs.get('norepeat', False)
    tilemap        = kwargs.get('tilemap', False)

    with open(filein, 'rb') as data:
        width, height, rgba, info = png.Reader(data).asRGBA8()
        rgba = list(rgba)
        greyscale = info['greyscale']

    # png.Reader returns flat pixel data. Nested is easier to work with
    len_px  = 4 # rgba
    image   = []
    palette = []
    for line in rgba:
        newline = []
        for px in xrange(0, len(line), len_px):
            color = { 'r': line[px  ],
                      'g': line[px+1],
                      'b': line[px+2],
                      'a': line[px+3], }
            newline += [color]
            if color not in palette:
                palette += [color]
        image += [newline]

    assert len(palette) <= 4, 'Palette should be 4 colors, is really %d' % len(palette)

    # Pad out smaller palettes with greyscale colors
    hues = {
        'white': { 'r': 0xff, 'g': 0xff, 'b': 0xff, 'a': 0xff },
        'black': { 'r': 0x00, 'g': 0x00, 'b': 0x00, 'a': 0xff },
        'grey':  { 'r': 0x55, 'g': 0x55, 'b': 0x55, 'a': 0xff },
        'gray':  { 'r': 0xaa, 'g': 0xaa, 'b': 0xaa, 'a': 0xff },
    }
    for hue in hues.values():
        if len(palette) >= 4:
            break
        if hue not in palette:
            palette += [hue]

    # Sort palettes by luminance
    def luminance(color):
        rough = { 'r':  4.7,
                  'g':  1.4,
                  'b': 13.8, }
        return sum(color[key] * rough[key] for key in rough.keys())
    palette.sort(key=luminance)

    # Game Boy palette order
    palette.reverse()

    # Map pixels to quaternary color ids
    padding = get_image_padding(width, height)
    width += padding['left'] + padding['right']
    height += padding['top'] + padding['bottom']
    pad = bytearray([0])

    qmap = []
    qmap += pad * width * padding['top']
    for line in image:
        qmap += pad * padding['left']
        for color in line:
            qmap += [palette.index(color)]
        qmap += pad * padding['right']
    qmap += pad * width * padding['bottom']

    # Graphics are stored in tiles instead of lines
    tile_width  = 8
    tile_height = 8
    num_columns = max(width, tile_width) / tile_width
    num_rows = max(height, tile_height) / tile_height
    image = []

    for row in xrange(num_rows):
        for column in xrange(num_columns):

            # Split it up into strips to convert to planar data
            for strip in xrange(min(tile_height, height)):
                anchor = (
                    row * num_columns * tile_width * tile_height +
                    column * tile_width +
                    strip * width
                )
                line = qmap[anchor : anchor + tile_width]
                bottom, top = 0, 0
                for bit, quad in enumerate(line):
                    bottom += (quad & 1) << (7 - bit)
                    top += (quad /2 & 1) << (7 - bit)
                image += [bottom, top]

    if pic_dimensions:
        w, h = pic_dimensions

        tiles = get_tiles(image)
        pic_length = w * h
        tile_width = width / 8
        trailing = len(tiles) % pic_length
        new_image = []
        for block in xrange(len(tiles) / pic_length):
            offset = (h * tile_width) * ((block * w) / tile_width) + ((block * w) % tile_width)
            pic = []
            for row in xrange(h):
                index = offset + (row * tile_width)
                pic += tiles[index:index + w]
            new_image += transpose(pic, w)
        new_image += tiles[len(tiles) - trailing:]
        image = connect(new_image)

    # Remove any tile padding used to make the png rectangular.
    image = image[:len(image) - tile_padding * 0x10]

    if interleave:
        image = deinterleave_tiles(image, num_columns)

    if norepeat:
        image, tmap = condense_tiles_to_map(image)
    if not tilemap:
        tmap = None

    return image, palette, tmap


def export_palette(palette, filename):
    """
    Export a palette from png to rgb macros in a .pal file.
    """

    if os.path.exists(filename):

        # Pic palettes are 2 colors (black/white are added later).
        with open(filename) as rgbs:
            colors = read_rgb_macros(rgbs.readlines())

        if len(colors) == 2:
            palette = palette[1:3]

        text = png_to_rgb(palette)
        with open(filename, 'w') as out:
            out.write(text)


def png_to_lz(filein):

    name = os.path.splitext(filein)[0]

    export_png_to_2bpp(filein)
    image = open(name+'.2bpp', 'rb').read()
    to_file(name+'.2bpp'+'.lz', Compressed(image).output)



def convert_2bpp_to_1bpp(data):
    """
    Convert planar 2bpp image data to 1bpp. Assume images are two colors.
    """
    return data[::2]

def convert_1bpp_to_2bpp(data):
    """
    Convert 1bpp image data to planar 2bpp (black/white).
    """
    output = []
    for i in data:
        output += [i, i]
    return output


def export_2bpp_to_1bpp(filename):
    name, extension = os.path.splitext(filename)
    image = open(filename, 'rb').read()
    image = convert_2bpp_to_1bpp(image)
    to_file(name + '.1bpp', image)

def export_1bpp_to_2bpp(filename):
    name, extension = os.path.splitext(filename)
    image = open(filename, 'rb').read()
    image = convert_1bpp_to_2bpp(image)
    to_file(name + '.2bpp', image)


def export_1bpp_to_png(filename, fileout=None):

    if fileout == None:
        fileout = os.path.splitext(filename)[0] + '.png'

    arguments = read_filename_arguments(filename)

    image = open(filename, 'rb').read()
    image = convert_1bpp_to_2bpp(image)

    result = convert_2bpp_to_png(image, **arguments)
    width, height, palette, greyscale, bitdepth, px_map = result

    w = png.Writer(width, height, palette=palette, compression=9, greyscale=greyscale, bitdepth=bitdepth)
    with open(fileout, 'wb') as f:
        w.write(f, px_map)


def export_png_to_1bpp(filename, fileout=None):

    if fileout == None:
        fileout = os.path.splitext(filename)[0] + '.1bpp'

    arguments = read_filename_arguments(filename)
    image = png_to_1bpp(filename, **arguments)

    to_file(fileout, image)

def png_to_1bpp(filename, **kwargs):
    image, palette, tmap = png_to_2bpp(filename, **kwargs)
    return convert_2bpp_to_1bpp(image)


def mass_to_png(directory='gfx'):
    # greyscale
    for root, dirs, files in os.walk('./gfx/'):
        convert_to_png(map(lambda x: os.path.join(root, x), files))

def mass_to_colored_png(directory='gfx'):
    # greyscale, unless a palette is detected
    for root, dirs, files in os.walk(directory):
        for name in files:

            if os.path.splitext(name)[1] == '.2bpp':
                pal = None
                if 'pics' in root:
                   pal = 'normal.pal'
                elif 'trainers' in root:
                   pal = os.path.splitext(name)[0] + '.pal'
                if pal != None:
                    pal = os.path.join(root, pal)
                export_2bpp_to_png(os.path.join(root, name), pal_file=pal)

            elif os.path.splitext(name)[1] == '.1bpp':
                export_1bpp_to_png(os.path.join(root, name))


def append_terminator_to_lzs(directory='gfx'):
    """
    Add a terminator to any lz files that were extracted without one.
    """
    for root, dirs, files in os.walk(directory):
        for filename in files:
            path = os.path.join(root, filename)
            if os.path.splitext(path)[1] == '.lz':
                data = bytearray(open(path,'rb').read())

                # don't mistake padding for a missing terminator
                i = 1
                while data[-i] == 0:
                    i += 1

                if data[-i] != 0xff:
                    data += [0xff]
                    with open(path, 'wb') as out:
                        out.write(data)


def expand_binary_pic_palettes(directory):
    """
    Add white and black to palette files with fewer than 4 colors.

    Pokemon Crystal only defines two colors for a pic palette to
    save space, filling in black/white at runtime.
    Instead of managing palette files of varying length, black
    and white are added to pic palettes and excluded from incbins.
    """
    for root, dirs, files in os.walk(directory):
        if os.path.join(directory, 'pics') in root or os.path.join(directory, '/trainers') in root:
            for name in files:
                if os.path.splitext(name)[1] == '.pal':
                    filename = os.path.join(root, name)
                    palette = bytearray(open(filename, 'rb').read())
                    w = bytearray([0xff, 0x7f])
                    b = bytearray([0x00, 0x00])
                    if len(palette) == 4:
                        with open(filename, 'wb') as out:
                            out.write(w + palette + b)


def convert_to_2bpp(filenames=[]):
    for filename in filenames:
        filename, name, extension = try_decompress(filename)
        if extension == '.1bpp':
            export_1bpp_to_2bpp(filename)
        elif extension == '.2bpp':
            pass
        elif extension == '.png':
            export_png_to_2bpp(filename)
        else:
            raise Exception, "Don't know how to convert {} to 2bpp!".format(filename)

def convert_to_1bpp(filenames=[]):
    for filename in filenames:
        filename, name, extension = try_decompress(filename)
        if extension == '.1bpp':
            pass
        elif extension == '.2bpp':
            export_2bpp_to_1bpp(filename)
        elif extension == '.png':
            export_png_to_1bpp(filename)
        else:
            raise Exception, "Don't know how to convert {} to 1bpp!".format(filename)

def convert_to_png(filenames=[]):
    for filename in filenames:
        filename, name, extension = try_decompress(filename)
        if extension == '.1bpp':
            export_1bpp_to_png(filename)
        elif extension == '.2bpp':
            export_2bpp_to_png(filename)
        elif extension == '.png':
            pass
        else:
            raise Exception, "Don't know how to convert {} to png!".format(filename)

def compress(filenames=[]):
    for filename in filenames:
        data = open(filename, 'rb').read()
        lz_data = Compressed(data).output
        to_file(filename + '.lz', lz_data)

def decompress(filenames=[]):
    for filename in filenames:
        name, extension = os.path.splitext(filename)
        lz_data = open(filename, 'rb').read()
        data = Decompressed(lz_data).output
        to_file(name, data)

def try_decompress(filename):
    """
    Try to decompress a graphic when determining the filetype.
    This skips the manual unlz step when attempting
    to convert lz-compressed graphics to png.
    """
    name, extension = os.path.splitext(filename)
    if extension == '.lz':
        decompress([filename])
        filename = name
        name, extension = os.path.splitext(filename)
    return filename, name, extension


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('filenames', nargs='*')
    args = ap.parse_args()

    method = {
        '2bpp': convert_to_2bpp,
        '1bpp': convert_to_1bpp,
        'png':  convert_to_png,
        'lz':   compress,
        'unlz': decompress,
    }.get(args.mode, None)

    if method == None:
        raise Exception, "Unknown conversion method!"

    method(args.filenames)


if __name__ == "__main__":
    main()

