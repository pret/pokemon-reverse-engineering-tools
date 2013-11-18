# -*- coding: utf-8 -*-

import os
import sys
import png
from math import sqrt, floor, ceil

import crystal
import pokemon_constants
import trainers

if __name__ != "__main__":
    rom = crystal.load_rom()


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
    """
    if width == None:
        width = int(sqrt(len(tiles))) # assume square image
    tiles = sorted(enumerate(tiles), key= lambda (i, tile): i % width)
    return [tile for i, tile in tiles]


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

    """
    Compress 2bpp data.
    """

    def __init__(self, image=None, mode='horiz', size=None):
        assert image, 'need something to compress!'
        image = list(image)
        self.image = image
        self.pic = []
        self.animtiles = []

        # only transpose pic (animtiles were never transposed in decompression)
        if size != None:
            for byte in range((size*size)*16):
                self.pic += image[byte]
            for byte in range(((size*size)*16),len(image)):
                self.animtiles += image[byte]
        else:
            self.pic = image

        if mode == 'vert':
            self.tiles = get_tiles(self.pic)
            self.tiles = transpose(self.tiles)
            self.pic = connect(self.tiles)

        self.image = self.pic + self.animtiles

        self.end = len(self.image)

        self.byte = None
        self.address = 0

        self.stream = []

        self.zeros = []
        self.alts = []
        self.iters = []
        self.repeats = []
        self.flips = []
        self.reverses = []
        self.literals = []

        self.output = []

        self.compress()


    def compress(self):
        """
        Incomplete, but outputs working compressed data.
        """

        self.address = 0

        # todo
        #self.scanRepeats()

        while ( self.address < self.end ):

            #if (self.repeats):
            #   self.doRepeats()

            #if (self.flips):
            #   self.doFlips()

            #if (self.reverses):
            #   self.doReverses

            if (self.checkWhitespace()):
                self.doLiterals()
                self.doWhitespace()

            elif (self.checkIter()):
                self.doLiterals()
                self.doIter()

            elif (self.checkAlts()):
                self.doLiterals()
                self.doAlts()

            else: # doesn't fit any pattern -> literal
                self.addLiteral()
                self.next()

            self.doStream()

        # add any literals we've been sitting on
        self.doLiterals()

        # done
        self.output.append(lz_end)


    def getCurByte(self):
        if self.address < self.end:
            self.byte = ord(self.image[self.address])
        else: self.byte = None

    def next(self):
        self.address += 1
        self.getCurByte()

    def addLiteral(self):
        self.getCurByte()
        self.literals.append(self.byte)
        if len(self.literals) > max_length:
            raise Exception, "literals exceeded max length and the compressor didn't catch it"
        elif len(self.literals) == max_length:
            self.doLiterals()

    def doLiterals(self):
        if len(self.literals) > lowmax:
            self.output.append( (lz_commands['long'] << 5) | (lz_commands['literal'] << 2) | ((len(self.literals) - 1) >> 8) )
            self.output.append( (len(self.literals) - 1) & 0xff )
        elif len(self.literals) > 0:
            self.output.append( (lz_commands['literal'] << 5) | (len(self.literals) - 1) )
        for byte in self.literals:
            self.output.append(byte)
        self.literals = []

    def doStream(self):
        for byte in self.stream:
            self.output.append(byte)
        self.stream = []


    def scanRepeats(self):
        """
        Works, but doesn't do flipped/reversed streams yet.

        This takes up most of the compress time and only saves a few bytes.
        It might be more effective to exclude it entirely.
        """

        self.repeats = []
        self.flips = []
        self.reverses = []

        # make a 5-letter word list of the sequence
        letters = 5 # how many bytes it costs to use a repeat over a literal
        # any shorter and it's not worth the trouble
        num_words = len(self.image) - letters
        words = []
        for i in range(self.address,num_words):
            word = []
            for j in range(letters):
                word.append( ord(self.image[i+j]) )
            words.append((word, i))

            zeros = []
            for zero in range(letters):
                zeros.append( 0 )

        # check for matches
        def get_matches():
        # TODO:
        # append to 3 different match lists instead of yielding to one
        #
        #flipped = []
        #for byte in enumerate(this[0]):
        #   flipped.append( sum(1<<(7-i) for i in range(8) if (this[0][byte])>>i&1) )
        #reversed = this[0][::-1]
        #
            for whereabout, this in enumerate(words):
                for that in range(whereabout+1,len(words)):
                    if words[that][0] == this[0]:
                        if words[that][1] - this[1] >= letters:
                            # remove zeros
                            if this[0] != zeros:
                                yield [this[0], this[1], words[that][1]]

        matches = list(get_matches())

        # remove more zeros
        buffer = []
        for match in matches:
            # count consecutive zeros in a word
            num_zeros = 0
            highest = 0
            for j in range(letters):
                if match[0][j] == 0:
                    num_zeros += 1
                else:
                    if highest < num_zeros: highest = num_zeros
                    num_zeros = 0
            if highest < 4:
                # any more than 3 zeros in a row isn't worth it
                # (and likely to already be accounted for)
                buffer.append(match)
        matches = buffer

        # combine overlapping matches
        buffer = []
        for this, match in enumerate(matches):
            if this < len(matches) - 1: # special case for the last match
                if matches[this+1][1] <= (match[1] + len(match[0])): # check overlap
                    if match[1] + len(match[0]) < match[2]:
                        # next match now contains this match's bytes too
                        # this only appends the last byte (assumes overlaps are +1
                        match[0].append(matches[this+1][0][-1])
                        matches[this+1] = match
                    elif match[1] + len(match[0]) == match[2]:
                        # we've run into the thing we matched
                        buffer.append(match)
                    # else we've gone past it and we can ignore it
                else: # no more overlaps
                    buffer.append(match)
            else: # last match, so there's nothing to check
                buffer.append(match)
        matches = buffer

        # remove alternating sequences
        buffer = []
        for match in matches:
            for i in range(6 if letters > 6 else letters):
                if match[0][i] != match[0][i&1]:
                    buffer.append(match)
                    break
        matches = buffer

        self.repeats = matches


    def doRepeats(self):
        """doesn't output the right values yet"""

        unusedrepeats = []
        for repeat in self.repeats:
            if self.address >= repeat[2]:

                # how far in we are
                length = (len(repeat[0]) - (self.address - repeat[2]))

                # decide which side we're copying from
                if (self.address - repeat[1]) <= 0x80:
                    self.doLiterals()
                    self.stream.append( (lz_commands['repeat'] << 5) | length - 1 )

                    # wrong?
                    self.stream.append( (((self.address - repeat[1])^0xff)+1)&0xff )

                else:
                    self.doLiterals()
                    self.stream.append( (lz_commands['repeat'] << 5) | length - 1 )

                    # wrong?
                    self.stream.append(repeat[1]>>8)
                    self.stream.append(repeat[1]&0xff)

                #print hex(self.address) + ': ' + hex(len(self.output)) + ' ' + hex(length)
                self.address += length

            else: unusedrepeats.append(repeat)

        self.repeats = unusedrepeats


    def checkWhitespace(self):
        self.zeros = []
        self.getCurByte()
        original_address = self.address

        if ( self.byte == 0 ):
            while ( self.byte == 0 ) & ( len(self.zeros) <= max_length ):
                self.zeros.append(self.byte)
                self.next()
            if len(self.zeros) > 1:
                return True
        self.address = original_address
        return False

    def doWhitespace(self):
        if (len(self.zeros) + 1) >= lowmax:
            self.stream.append( (lz_commands['long'] << 5) | (lz_commands['blank'] << 2) | ((len(self.zeros) - 1) >> 8) )
            self.stream.append( (len(self.zeros) - 1) & 0xff )
        elif len(self.zeros) > 1:
            self.stream.append( lz_commands['blank'] << 5 | (len(self.zeros) - 1) )
        else:
            raise Exception, "checkWhitespace() should prevent this from happening"


    def checkAlts(self):
        self.alts = []
        self.getCurByte()
        original_address = self.address
        num_alts = 0

        # make sure we don't check for alts at the end of the file
        if self.address+3 >= self.end: return False

        self.alts.append(self.byte)
        self.alts.append(ord(self.image[self.address+1]))

        # are we onto smething?
        if ( ord(self.image[self.address+2]) == self.alts[0] ):
            cur_alt = 0
            while (ord(self.image[(self.address)+1]) == self.alts[num_alts&1]) & (num_alts <= max_length):
                num_alts += 1
                self.next()
            # include the last alternated byte
            num_alts += 1
            self.address = original_address
            if num_alts > lowmax:
                return True
            elif num_alts > 2:
                return True
        return False

    def doAlts(self):
        original_address = self.address
        self.getCurByte()

        #self.alts = []
        #num_alts = 0

        #self.alts.append(self.byte)
        #self.alts.append(ord(self.image[self.address+1]))

        #i = 0
        #while (ord(self.image[self.address+1]) == self.alts[i^1]) & (num_alts <= max_length):
        #   num_alts += 1
        #   i ^=1
        #   self.next()
        ## include the last alternated byte
        #num_alts += 1

        num_alts = len(self.iters) + 1

        if num_alts > lowmax:
            self.stream.append( (lz_commands['long'] << 5) | (lz_commands['alternate'] << 2) | ((num_alts - 1) >> 8) )
            self.stream.append( num_alts & 0xff )
            self.stream.append( self.alts[0] )
            self.stream.append( self.alts[1] )
        elif num_alts > 2:
            self.stream.append( (lz_commands['alternate'] << 5) | (num_alts - 1) )
            self.stream.append( self.alts[0] )
            self.stream.append( self.alts[1] )
        else:
            raise Exception, "checkAlts() should prevent this from happening"

        self.address = original_address
        self.address += num_alts


    def checkIter(self):
        self.iters = []
        self.getCurByte()
        iter = self.byte
        original_address = self.address
        while (self.byte == iter) & (len(self.iters) < max_length):
            self.iters.append(self.byte)
            self.next()
        self.address = original_address
        if len(self.iters) > 3:
            # 3 or fewer isn't worth the trouble and actually longer
            # if part of a larger literal set
            return True

        return False

    def doIter(self):
        self.getCurByte()
        iter = self.byte
        original_address = self.address

        self.iters = []
        while (self.byte == iter) & (len(self.iters) < max_length):
            self.iters.append(self.byte)
            self.next()

        if (len(self.iters) - 1) >= lowmax:
            self.stream.append( (lz_commands['long'] << 5) | (lz_commands['iterate'] << 2) | ((len(self.iters)-1) >> 8) )
            self.stream.append( (len(self.iters) - 1) & 0xff )
            self.stream.append( iter )
        elif len(self.iters) > 3:
            # 3 or fewer isn't worth the trouble and actually longer
            # if part of a larger literal set
            self.stream.append( (lz_commands['iterate'] << 5) | (len(self.iters) - 1) )
            self.stream.append( iter )
        else:
            self.address = original_address
            raise Exception, "checkIter() should prevent this from happening"


class Decompressed:
    """
    Parse compressed 2bpp data.

    parameters:
        [compressed 2bpp data]
        [tile arrangement] default: 'vert'
        [size of pic] default: None
        [start] (optional)

    splits output into pic [size] and animation tiles if applicable
    data can be fed in from rom if [start] is specified
    """

    def __init__(self, lz=None, mode=None, size=None, start=0):
        # todo: play nice with Compressed

        assert lz, 'need something to compress!'
        self.lz = lz

        self.byte = None
        self.address = 0
        self.start = start

        self.output = []

        self.decompress()

        debug = False
        # print tuple containing start and end address
        if debug: print '(' + hex(self.start) + ', ' + hex(self.start + self.address+1) + '),'

        # only transpose pic
        self.pic = []
        self.animtiles = []

        if size != None:
            self.tiles = get_tiles(self.output)
            self.pic = connect(self.tiles[:(size*size)])
            self.animtiles = connect(self.tiles[(size*size):])
        else: self.pic = self.output

        if mode == 'vert':
            self.tiles = get_tiles(self.pic)
            self.tiles = transpose(self.tiles)
            self.pic = connect(self.tiles)

        self.output = self.pic + self.animtiles


    def decompress(self):
        """
        Replica of crystal's decompression.
        """

        self.output = []

        while True:
            self.getCurByte()

            if (self.byte == lz_end):
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
        self.byte = ord(self.lz[self.start+self.address])

    def next(self):
        self.address += 1
        self.getCurByte()

    def doLiteral(self):
        """
        Copy 2bpp data directly.
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
        Repeat flipped bytes from 2bpp output.

        eg  11100100 -> 00100111
        quat 3 2 1 0 ->  0 2 1 3
        """
        for byte in range(self.length):
            flipped = sum(1<<(7-i) for i in range(8) if self.output[self.displacement+byte]>>i&1)
            self.output.append(flipped)

    def doReverse(self):
        """
        Repeat reversed bytes from 2bpp output.
        """
        for byte in range(self.length):
            self.output.append(self.output[self.displacement-byte])

    def doRepeat(self):
        """
        Repeat bytes from 2bpp output.
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

def make_sizes():
    """
    Front pics have specified sizes.
    """
    top = 251
    base_stats = 0x51424
    # print monster sizes
    address = base_stats + 0x11

    output = ''

    for id in range(top):
        size = (ord(rom[address])) & 0x0f
        if id % 16 == 0: output += '\n\t'
        output += str(size) + ', '
        address += 0x20

    print output



fxs = 0xcfcf6
num_fx = 40

def decompress_fx_by_id(id):
    address = fxs + id*4 # len_fxptr
    # get size
    num_tiles = ord(rom[address]) # # tiles
    # get pointer
    bank = ord(rom[address+1])
    address = (ord(rom[address+3]) << 8) + ord(rom[address+2])
    address = (bank * 0x4000) + (address & 0x3fff)
    # decompress
    fx = Decompressed(rom, 'horiz', num_tiles, address)
    return fx

def decompress_fx():
    for id in range(num_fx):
        fx = decompress_fx_by_id(id)
        filename = './gfx/fx/' + str(id).zfill(3) + '.2bpp' # ./gfx/fx/039.2bpp
        to_file(filename, fx.pic)


num_pics = 2
front = 0
back = 1

monsters = 0x120000
num_monsters = 251

unowns = 0x124000
num_unowns = 26
unown_dex = 201

def decompress_monster_by_id(id=0, type=front):
    # no unowns here
    if id + 1 == unown_dex: return None
    # get size
    if type == front:
        size = sizes[id]
    else: size = None
    # get pointer
    address = monsters + (id*2 + type)*3 # bank, address
    bank = ord(rom[address]) + 0x36 # crystal
    address = (ord(rom[address+2]) << 8) + ord(rom[address+1])
    address = (bank * 0x4000) + (address & 0x3fff)
    # decompress
    monster = Decompressed(rom, 'vert', size, address)
    return monster

def decompress_monsters(type=front):
    for id in range(num_monsters):
        # decompress
        monster = decompress_monster_by_id(id, type)
        if monster != None: # no unowns here
            if not type: # front
                filename = 'front.2bpp'
                folder = './gfx/pics/' + str(id+1).zfill(3) + '/'
                to_file(folder+filename, monster.pic)
                filename = 'tiles.2bpp'
                folder = './gfx/pics/' + str(id+1).zfill(3) + '/'
                to_file(folder+filename, monster.animtiles)
            else: # back
                filename = 'back.2bpp'
                folder = './gfx/pics/' + str(id+1).zfill(3) + '/'
                to_file(folder+filename, monster.pic)


def decompress_unown_by_id(letter, type=front):
    # get size
    if type == front:
        size = sizes[unown_dex-1]
    else: size = None
    # get pointer
    address = unowns + (letter*2 + type)*3 # bank, address
    bank = ord(rom[address]) + 0x36 # crystal
    address = (ord(rom[address+2]) << 8) + ord(rom[address+1])
    address = (bank * 0x4000) + (address & 0x3fff)
    # decompress
    unown = Decompressed(rom, 'vert', size, address)
    return unown

def decompress_unowns(type=front):
    for letter in range(num_unowns):
        # decompress
        unown = decompress_unown_by_id(letter, type)

        if not type: # front
            filename = 'front.2bpp'
            folder = './gfx/pics/' + str(unown_dex).zfill(3) + chr(ord('a') + letter) + '/'
            to_file(folder+filename, unown.pic)
            filename = 'tiles.2bpp'
            folder = './gfx/anim/'
            to_file(folder+filename, unown.animtiles)
        else: # back
            filename = 'back.2bpp'
            folder = './gfx/pics/' + str(unown_dex).zfill(3) + chr(ord('a') + letter) + '/'
            to_file(folder+filename, unown.pic)


trainers = 0x128000
num_trainers = 67

def decompress_trainer_by_id(id):
    # get pointer
    address = trainers + id*3 # bank, address
    bank = ord(rom[address]) + 0x36 # crystal
    address = (ord(rom[address+2]) << 8) + ord(rom[address+1])
    address = (bank * 0x4000) + (address & 0x3fff)
    # decompress
    trainer = Decompressed(rom, 'vert', None, address)
    return trainer

def decompress_trainers():
    for id in range(num_trainers):
        # decompress
        trainer = decompress_trainer_by_id(id)
        filename = './gfx/trainers/' + str(id).zfill(3) + '.2bpp' # ./gfx/trainers/066.2bpp
        to_file(filename, trainer.pic)


# in order of use (sans repeats)
intro_gfx = [
    ('logo', 0x109407),
    ('001', 0xE641D), # tilemap
    ('unowns', 0xE5F5D),
    ('pulse', 0xE634D),
    ('002', 0xE63DD), # tilemap
    ('003', 0xE5ECD), # tilemap
    ('background', 0xE5C7D),
    ('004', 0xE5E6D), # tilemap
    ('005', 0xE647D), # tilemap
    ('006', 0xE642D), # tilemap
    ('pichu_wooper', 0xE592D),
    ('suicune_run', 0xE555D),
    ('007', 0xE655D), # tilemap
    ('008', 0xE649D), # tilemap
    ('009', 0xE76AD), # tilemap
    ('suicune_jump', 0xE6DED),
    ('unown_back', 0xE785D),
    ('010', 0xE764D), # tilemap
    ('011', 0xE6D0D), # tilemap
    ('suicune_close', 0xE681D),
    ('012', 0xE6C3D), # tilemap
    ('013', 0xE778D), # tilemap
    ('suicune_back', 0xE72AD),
    ('014', 0xE76BD), # tilemap
    ('015', 0xE676D), # tilemap
    ('crystal_unowns', 0xE662D),
    ('017', 0xE672D), # tilemap
]

def decompress_intro():
    for name, address in intro_gfx:
        filename = './gfx/intro/' + name + '.2bpp'
        gfx = Decompressed( rom, 'horiz', None, address )
        to_file(filename, gfx.output)


title_gfx = [
    ('suicune', 0x10EF46),
    ('logo', 0x10F326),
    ('crystal', 0x10FCEE),
]

def decompress_title():
    for name, address in title_gfx:
        filename = './gfx/title/' + name + '.2bpp'
        gfx = Decompressed( rom, 'horiz', None, address )
        to_file(filename, gfx.output)

def decompress_tilesets():
    tileset_headers = 0x4d596
    len_tileset = 15
    num_tilesets = 0x25
    for tileset in range(num_tilesets):
        ptr = tileset*len_tileset + tileset_headers
        address = (ord(rom[ptr])*0x4000) + (((ord(rom[ptr+1]))+ord(rom[ptr+2])*0x100)&0x3fff)
        tiles = Decompressed( rom, 'horiz', None, address )
        filename = './gfx/tilesets/'+str(tileset).zfill(2)+'.2bpp'
        to_file( filename, tiles.output )
        #print '(' + hex(address) + ', '+ hex(address+tiles.address+1) + '),'

misc = [
    ('player', 0x2BA1A, 'vert'),
    ('dude', 0x2BBAA, 'vert'),
    ('town_map', 0xF8BA0, 'horiz'),
    ('pokegear', 0x1DE2E4, 'horiz'),
    ('pokegear_sprites', 0x914DD, 'horiz'),
]
def decompress_misc():
    for name, address, mode in misc:
        filename = './gfx/misc/' + name + '.2bpp'
        gfx = Decompressed( rom, mode, None, address )
        to_file(filename, gfx.output)

def decompress_all(debug=False):
    """
    Decompress all known compressed data in baserom.
    """

    if debug: print 'fronts'
    decompress_monsters(front)
    if debug: print 'backs'
    decompress_monsters(back)
    if debug: print 'unown fronts'
    decompress_unowns(front)
    if debug: print 'unown backs'
    decompress_unowns(back)

    if debug: print 'trainers'
    decompress_trainers()

    if debug: print 'fx'
    decompress_fx()

    if debug: print 'intro'
    decompress_intro()

    if debug: print 'title'
    decompress_title()

    if debug: print 'tilesets'
    decompress_tilesets()

    if debug: print 'misc'
    decompress_misc()

    return


def decompress_from_address(address, mode='horiz', filename='de.2bpp', size=None):
    """
    Write decompressed data from an address to a 2bpp file.
    """
    image = Decompressed(rom, mode, size, address)
    to_file(filename, image.pic)


def decompress_file(filein, fileout, mode='horiz', size=None):
    f = open(filein, 'rb')
    image = f.read()
    f.close()

    de = Decompressed(image, mode, size)

    to_file(fileout, de.pic)


def compress_file(filein, fileout, mode='horiz'):
    f = open(filein, 'rb')
    image = f.read()
    f.close()

    lz = Compressed(image, mode)

    to_file(fileout, lz.output)




def compress_monster_frontpic(id, fileout):
    mode = 'vert'

    fpic = './gfx/pics/' + str(id).zfill(3) + '/front.2bpp'
    fanim = './gfx/pics/' + str(id).zfill(3) + '/tiles.2bpp'

    pic = open(fpic, 'rb').read()
    anim = open(fanim, 'rb').read()
    image = pic + anim

    lz = Compressed(image, mode, sizes[id-1])

    out = './gfx/pics/' + str(id).zfill(3) + '/front.lz'

    to_file(out, lz.output)



def get_uncompressed_gfx(start, num_tiles, filename):
    """
    Grab tiles directly from rom and write to file.
    """
    bytes_per_tile = 0x10
    length = num_tiles*bytes_per_tile
    end = start + length
    rom = load_rom()
    image = []
    for address in range(start,end):
        image.append(ord(rom[address]))
    to_file(filename, image)



def hex_to_rgb(word):
    red = word & 0b11111
    word >>= 5
    green = word & 0b11111
    word >>= 5
    blue = word & 0b11111
    return (red, green, blue)

def grab_palettes(address, length=0x80):
    output = ''
    for word in range(length/2):
        color = ord(rom[address+1])*0x100 + ord(rom[address])
        address += 2
        color = hex_to_rgb(color)
        red = str(color[0]).zfill(2)
        green = str(color[1]).zfill(2)
        blue = str(color[2]).zfill(2)
        output += '\tRGB '+red+', '+green+', '+blue
        output += '\n'
    return output







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
            pal_data.append(ord(rom[address]))
            address += 1

        filename = 'normal.pal'
        to_file('../'+dir+filename, pal_data)

        spacing  = ' ' * (15 - len(name))
        #print name+'Palette:'+spacing+' INCBIN "'+dir+filename+'"'


        pal_data = []
        for byte in range(pal_length):
            pal_data.append(ord(rom[address]))
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
            pal_data.append(ord(rom[address]))
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
        bottom = ord(bottom)
        top = ord(top)
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
    word =  (color['r'] / 8)
    word += (color['g'] / 8) << 5
    word += (color['b'] / 8) << 10
    return word


def png_pal(filename):
    with open(filename, 'rb') as pal_data:
        words = pal_data.read()
    dmg_pals = []
    for word in range(len(words)/2):
        dmg_pals.append(ord(words[word*2]) + ord(words[word*2+1])*0x100)
    palette = []
    white = (255,255,255,255)
    black = (000,000,000,255)
    for word in dmg_pals: palette += [dmg2rgb(word)]
    if white not in dmg_pals and len(palette) < 4: palette = [white] + palette
    if black not in dmg_pals and len(palette) < 4: palette += [black]
    return palette


def export_2bpp_to_png(filein, fileout=None, pal_file=None, height=0, width=0):
    if fileout == None:
        fileout = os.path.splitext(filein)[0] + '.png'
    image = open(filein, 'rb').read()

    if pal_file == None:
        if os.path.exists(os.path.splitext(fileout)[0]+'.pal'):
            pal_file = os.path.splitext(fileout)[0]+'.pal'

    width, height, palette, greyscale, bitdepth, px_map = convert_2bpp_to_png(image, width=width, height=height, pal_file=pal_file)

    w = png.Writer(width, height, palette=palette, compression=9, greyscale=greyscale, bitdepth=bitdepth)
    with open(fileout, 'wb') as f:
        w.write(f, px_map)


def convert_2bpp_to_png(image, width=0, height=0, pal_file=None):
    """
    Convert a planar 2bpp graphic to png.
    """
    num_pixels = len(image) * 4
    assert num_pixels > 0, 'empty image!'

    # at least one dimension should be given
    if height == 0 and width != 0:
        height = num_pixels / width
    elif width == 0 and height != 0:
        width = num_pixels / height

    if width * height != num_pixels:
        # look for possible combos of width/height that would form a rectangle
        matches = []
        for w in range(8, num_pixels / 2 + 1, 8):
            h = num_pixels / w
            if w * h == num_pixels:
                matches += [(w, h)]
        # go for the most square image
        if len(matches):
            width, height = sorted(matches, key= lambda (w, h): w + h)[0] # favor height

    # if it still isn't rectangular then the image isn't made of tiles
    if width * height != num_pixels:
        raise Exception, 'Image can\'t be divided into tiles (%d px)!' % (num_pixels)

    # convert tiles to lines
    lines = to_lines(flatten(image), width)

    if pal_file == None:
        palette   = None
        greyscale = True
        bitdepth  = 2
        px_map    = [[3 - pixel for pixel in line] for line in lines]

    else: # gbc color
        palette   = png_pal(pal_file)
        greyscale = False
        bitdepth  = 8
        px_map    = [[pixel for pixel in line] for line in lines]

    return width, height, palette, greyscale, bitdepth, px_map


def export_png_to_2bpp(filein, fileout=None, palout=None):
    image, palette = png_to_2bpp(filein)

    if fileout == None:
        fileout = os.path.splitext(filein)[0] + '.2bpp'
    to_file(fileout, image)

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

    if width % wstep:
       pad = float(width % wstep) / 2
       padding['left']   = int(ceil(pad))
       padding['right']  = int(floor(pad))

    if height % hstep:
       pad = float(height % hstep) / 2
       padding['top']    = int(ceil(pad))
       padding['bottom'] = int(floor(pad))

    return padding


def png_to_2bpp(filein):
    """
    Convert a png image to planar 2bpp.
    """

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
    pad = [0]

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
    num_columns = width / tile_width
    num_rows = height / tile_height
    image = []

    for row in xrange(num_rows):
        for column in xrange(num_columns):

            # Split it up into strips to convert to planar data
            for strip in xrange(tile_height):
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

    return image, palette


def export_palette(palette, filename):
    if os.path.exists(filename):
        output = []
        for color in palette:
            word = rgb_to_dmg(color)
            output += [word & 0xff]
            output += [word >> 8]
        to_file(filename, output)


def png_to_lz(filein):

    name = os.path.splitext(filein)[0]

    export_png_to_2bpp(filein)
    image = open(name+'.2bpp', 'rb').read()
    to_file(name+'.lz', Compressed(image).output)



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


def export_1bpp_to_png(filename, fileout=None):

    if fileout == None:
        fileout = os.path.splitext(filename)[0] + '.png'

    image = open(filename, 'rb').read()
    image = convert_1bpp_to_2bpp(image)

    width, height, palette, greyscale, bitdepth, px_map = convert_2bpp_to_png(image)

    w = png.Writer(width, height, palette=palette, compression=9, greyscale=greyscale, bitdepth=bitdepth)
    with open(fileout, 'wb') as f:
        w.write(f, px_map)


def mass_to_png(debug=False):
    # greyscale
    for root, dirs, files in os.walk('./gfx/'):
        for name in files:
            if debug: print os.path.splitext(name), os.path.join(root, name)
            if os.path.splitext(name)[1] == '.2bpp':
                export_2bpp_to_png(os.path.join(root, name))

def mass_to_colored_png(debug=False):
    # greyscale, unless a palette is detected
    for root, dirs, files in os.walk('./gfx/'):
        if 'pics' not in root and 'trainers' not in root:
            for name in files:
                if debug: print os.path.splitext(name), os.path.join(root, name)
                if os.path.splitext(name)[1] == '.2bpp':
                    export_2bpp_to_png(os.path.join(root, name))
                    os.utime(os.path.join(root, name), None)
                elif os.path.splitext(name)[1] == '.1bpp':
                    export_1bpp_to_png(os.path.join(root, name))
                    os.utime(os.path.join(root, name), None)

    # only monster and trainer pics for now
    for root, dirs, files in os.walk('./gfx/pics/'):
        for name in files:
            if debug: print os.path.splitext(name), os.path.join(root, name)
            if os.path.splitext(name)[1] == '.2bpp':
                if 'normal.pal' in files:
                    export_2bpp_to_png(os.path.join(root, name), None, os.path.join(root, 'normal.pal'))
                else:
                    export_2bpp_to_png(os.path.join(root, name))
                os.utime(os.path.join(root, name), None)

    for root, dirs, files in os.walk('./gfx/trainers/'):
        for name in files:
            if debug: print os.path.splitext(name), os.path.join(root, name)
            if os.path.splitext(name)[1] == '.2bpp':
                export_2bpp_to_png(os.path.join(root, name))
                os.utime(os.path.join(root, name), None)


def mass_decompress(debug=False):
    for root, dirs, files in os.walk('./gfx/'):
        for name in files:
            if 'lz' in name:
                if '/pics' in root:
                    if 'front' in name:
                        id = root.split('pics/')[1][:3]
                        if id != 'egg':
                            with open(os.path.join(root, name), 'rb') as lz: de = Decompressed(lz.read(), 'vert', sizes[int(id)-1])
                        else:
                            with open(os.path.join(root, name), 'rb') as lz: de = Decompressed(lz.read(), 'vert', 4)
                        to_file(os.path.join(root, 'front.2bpp'), de.pic)
                        to_file(os.path.join(root, 'tiles.2bpp'), de.animtiles)
                    elif 'back' in name:
                        with open(os.path.join(root, name), 'rb') as lz: de = Decompressed(lz.read(), 'vert')
                        to_file(os.path.join(root, 'back.2bpp'), de.output)
                elif '/trainers' in root or '/fx' in root:
                    with open(os.path.join(root, name), 'rb') as lz: de = Decompressed(lz.read(), 'vert')
                    to_file(os.path.join(root, os.path.splitext(name)[0]+'.2bpp'), de.output)
                else:
                    with open(os.path.join(root, name), 'rb') as lz: de = Decompressed(lz.read())
                    to_file(os.path.join(root, os.path.splitext(name)[0]+'.2bpp'), de.output)
                os.utime(os.path.join(root, name), None)

def append_terminator_to_lzs(directory):
    # fix lzs that were extracted with a missing terminator
    for root, dirs, files in os.walk(directory):
        for file in files:
            if '.lz' in file:
                data = open(root+file,'rb').read()
                if data[-1] != chr(0xff):
                    data += chr(0xff)
                    new = open(root+file,'wb')
                    new.write(data)
                    new.close()

def export_lz_to_png(filename):
    """
    Convert a lz file to png. Dump a 2bpp file too.
    """
    assert filename[-3:] == ".lz"
    lz_data = open(filename, "rb").read()
    bpp = Decompressed(lz_data).output
    bpp_filename = filename.replace(".lz", ".2bpp")
    to_file(bpp_filename, bpp)
    export_2bpp_to_png(bpp_filename)

def dump_tileset_pngs():
    """
    Convert .lz format tilesets into .png format tilesets.

    Also, leaves a bunch of wonderful .2bpp files everywhere for your amusement.
    """
    for tileset_id in range(37):
        tileset_filename = "./gfx/tilesets/" + str(tileset_id).zfill(2) + ".lz"
        export_lz_to_png(tileset_filename)

def decompress_frontpic(lz_file):
    """
    Convert the pic portion of front.lz to front.2bpp
    """
    lz = open(lz_file, 'rb').read()
    to_file(Decompressed(lz).pic, os.path.splitext(filein)[0] + '.2bpp')

def decompress_frontpic_anim(lz_file):
    """
    Convert the animation tile portion of front.lz to tiles.2bpp
    """
    lz = open(lz_file, 'rb').read()
    to_file(Decompressed(lz).animtiles, 'tiles.2bpp')

def expand_pic_palettes():
    """
    Add white and black to palette files with fewer than 4 colors.

    Pokemon Crystal only defines two colors for a pic palette to
    save space, filling in black/white at runtime.
    Instead of managing palette files of varying length, black
    and white are added to pic palettes and excluded from incbins.
    """
    for root, dirs, files in os.walk('./gfx/'):
        if 'gfx/pics' in root or 'gfx/trainers' in root:
            for name in files:
                if os.path.splitext(name)[1] == '.pal':
                    filename = os.path.join(root, name)
                    palette = bytearray(open(filename, 'rb').read())
                    w = bytearray([0xff, 0x7f])
                    b = bytearray([0x00, 0x00])
                    if len(palette) == 4:
                        with open(filename, 'wb') as out:
                            out.write(w + palette + b)

if __name__ == "__main__":
    debug = False

    argv = [None] * 5
    for i, arg in enumerate(sys.argv):
        argv[i] = arg

    if argv[1] == 'dump-pngs':
        mass_to_colored_png()

    elif argv[1] == 'mass-decompress':
        mass_decompress()

    elif argv[1] == 'front-to-2bpp':
        decompress_frontpic(argv[2])

    elif argv[1] == 'anim-from-front':
        decompress_frontpic_anim(argv[2])

    elif argv[1] == 'lz-to-2bpp':
        name = os.path.splitext(argv[3])[0]
        lz = open(name+'.lz', 'rb').read()
        if argv[2] == '--vert':
            to_file(name+'.2bpp', Decompressed(lz, 'vert').output)
        else:
            to_file(name+'.2bpp', Decompressed(lz).output)

    elif argv[1] == 'lz-to-png':
        if argv[2] == '--vert':
            name = os.path.splitext(argv[3])[0]
            lz = open(name+'.lz', 'rb').read()
            to_file(name+'.2bpp', Decompressed(lz, 'vert').output)
            pic = open(name+'.2bpp', 'rb').read()
            to_file(name+'.png', export_2bpp_to_png(pic))
        else:
            export_lz_to_png(argv[2])

    elif argv[1] == 'png-to-lz':
        # python gfx.py png-to-lz [--front anim(2bpp) | --vert] [png]
        if argv[2] == '--front':
            # front.2bpp and tiles.2bpp are combined before compression,
            # so we have to pass in the anim file and pic size
            name = os.path.splitext(argv[4])[0]
            export_png_to_2bpp(name+'.png', name+'.2bpp')
            pic  = open(name+'.2bpp', 'rb').read()
            anim = open(argv[3], 'rb').read()
            size = int(sqrt(len(pic)/16)) # assume square pic
            to_file(name+'.lz', Compressed(pic + anim, 'vert', size).output)
        elif argv[2] == '--vert':
            name = os.path.splitext(argv[3])[0]
            export_png_to_2bpp(name+'.png', name+'.2bpp')
            pic = open(name+'.2bpp', 'rb').read()
            to_file(name+'.lz', Compressed(pic, 'vert').output)
        else:
            png_to_lz(argv[2])

    elif argv[1] == 'png-to-2bpp':
        export_png_to_2bpp(argv[2])

    elif argv[1] == '2bpp-to-lz':
        if argv[2] == '--vert':
            filein = argv[3]
            fileout = argv[4]
            compress_file(filein, fileout, 'vert')
        else:
            filein = argv[2]
            fileout = argv[3]
            compress_file(filein, fileout)

    elif argv[1] == '2bpp-to-png':
        export_2bpp_to_png(argv[2])
