# -*- coding: utf-8 -*-

import os
import sys
import png
from math import sqrt, floor, ceil
import argparse
import yaml
import operator

import configuration
config = configuration.Config()

from pokemon_constants import pokemon_constants
import trainers
import romstr

from lz import Compressed, Decompressed



def load_rom(filename=config.rom_path):
    rom = romstr.RomStr.load(filename=filename)
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


def condense_tiles_to_map(image, pic=0):
    tiles = get_tiles(image)

    # Leave the first frame intact for pics.
    new_tiles = tiles[:pic]
    tilemap   = range(pic)

    for i, tile in enumerate(tiles[pic:]):
        if tile not in new_tiles:
            new_tiles += [tile]

        # Match the first frame where possible.
        if tile == new_tiles[i % pic]:
            tilemap += [i % pic]
        else:
            tilemap += [new_tiles.index(tile)]

    new_image = connect(new_tiles)
    return new_image, tilemap


def to_file(filename, data):
    """
    Apparently open(filename, 'wb').write(bytearray(data)) won't work.
    """
    file = open(filename, 'wb')
    for byte in data:
        file.write('%c' % byte)
    file.close()





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

        name     = pokemon_constants[mon+1].title().replace('_','')
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


def read_yaml_arguments(filename, yaml_filename = os.path.join(config.path, 'gfx.yaml'), path_arguments = ['pal_file']):

    parsed_arguments = {}

    # Read arguments from gfx.yaml if it exists.
    if os.path.exists(yaml_filename):
        yargs = yaml.load(open(yaml_filename))
        dirs = os.path.splitext(filename)[0].split('/')
        current_path = os.path.dirname(filename)
        path = []
        while yargs:
            for key, value in yargs.items():
                # Follow directories to the bottom while picking up keys.
                # Try not to mistake other files for keys.
                parsed_path = os.path.join( * (path + [key]) )
                for guessed_path in map(parsed_path.__add__, ['', '.png']):
                    if os.path.exists(guessed_path) or '.' in key:
                        if guessed_path != filename:
                            continue
                if key in path_arguments:
                    value = os.path.join(current_path, value)
                parsed_arguments[key] = value
            if not dirs:
                break
            yargs = yargs.get(dirs[0], {})
            path.append(dirs.pop(0))

    return parsed_arguments

def read_filename_arguments(filename, yaml_filename = os.path.join(config.path, 'gfx.yaml'), path_arguments = ['pal_file']):
    """
    Infer graphics conversion arguments given a filename.

    If it exists, ./gfx.yaml is traversed for arguments.
    Then additional arguments within the filename (separated with ".") are grabbed.
    """
    parsed_arguments = {}

    parsed_arguments.update(read_yaml_arguments(
        filename,
        yaml_filename  = yaml_filename,
        path_arguments = path_arguments
    ))

    int_arguments = {
        'w': 'width',
        'h': 'height',
        't': 'tile_padding',
    }
    # Filename arguments override yaml.
    arguments = os.path.splitext(filename)[0].lstrip('.').split('.')[1:]
    for argument in arguments:

        # Check for integer arguments first (i.e. "w128").
        arg   = argument[0]
        param = argument[1:]
        if param.isdigit():
            arg = int_arguments.get(arg, False)
            if arg:
                parsed_arguments[arg] = int(param)

        elif argument == 'arrange':
            parsed_arguments['norepeat'] = True
            parsed_arguments['tilemap']  = True

        # Pic dimensions (i.e. "6x6").
        elif 'x' in argument and any(map(str.isdigit, argument)):
            w, h = argument.split('x')
            if w.isdigit() and h.isdigit():
                parsed_arguments['pic_dimensions'] = (int(w), int(h))

        else:
            parsed_arguments[argument] = True

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


def get_pic_animation(tmap, w, h):
    """
    Generate pic animation data from a combined tilemap of each frame.
    """
    frame_text = ''
    bitmask_text = ''

    frames = list(split(tmap, w * h))
    base = frames.pop(0)
    bitmasks = []

    for i in xrange(len(frames)):
        frame_text += '\tdw .frame{}\n'.format(i + 1)

    for i, frame in enumerate(frames):
        bitmask = map(operator.eq, frame, base)
        if bitmask not in bitmasks:
            bitmasks.append(bitmask)
        which_bitmask = bitmasks.index(bitmask)

        mask = iter(bitmask)
        masked_frame = filter(mask.next, frame)

        frame_text += '.frame{}\n'.format(i + 1)
        frame_text += '\tdb ${:02x} ; bitmask\n'.format(which_bitmask)
        if masked_frame:
            frame_text += '\tdb {}\n'.format(', '.join(
                map('${:02x}'.format, masked_frame)
            ))
        frame_text += '\n'

    for i, bitmask in enumerate(bitmasks):
        bitmask_text += '; {}\n'.format(i)
        for byte in split(bitmask, 8):
            byte = int(''.join(map(int.__repr__, reversed(byte))), 2)
            bitmask_text += '\tdb %{:08b}\n'.format(byte)

    return frame_text, bitmask_text


def dump_pic_animations(addresses={'bitmasks': 'BitmasksPointers', 'frames': 'FramesPointers'}, pokemon=pokemon_constants, rom=None):
    """
    The code to dump pic animations from rom is mysteriously absent.
    Here it is again, but now it dumps images instead of text.
    Said text can then be derived from the images.
    """

    if rom is None: rom = load_rom()

    # Labels can be passed in instead of raw addresses.
    for which, offset in addresses.items():
        if type(offset) is str:
            for line in open('pokecrystal.sym').readlines():
                if offset in line.split():
                    addresses[which] = rom_offset(*map(lambda x: int(x, 16), line[:7].split(':')))
                    break

    for i, name in pokemon.items():
        if name.lower() == 'unown': continue

        i -= 1

        directory = os.path.join('gfx', 'pics', name.lower())
        size = sizes[i]

        if i > 151 - 1:
            bank = 0x36
        else:
            bank = 0x35
        address = addresses['frames'] + i * 2
        address = rom_offset(bank, rom[address] + rom[address + 1] * 0x100)
        addrs = []
        while address not in addrs:
            addr = rom[address] + rom[address + 1] * 0x100
            addrs.append(rom_offset(bank, addr))
            address += 2
        num_frames = len(addrs)

        # To go any further, we need bitmasks.
        # Bitmasks need the number of frames, which we now have.

        bank = 0x34
        address = addresses['bitmasks'] + i * 2
        address = rom_offset(bank, rom[address] + rom[address + 1] * 0x100)
        length = size ** 2
        num_bytes = (length + 7) / 8
        bitmasks = []
        for _ in xrange(num_frames):
            bitmask = []
            bytes_ = rom[ address : address + num_bytes ]
            for byte in bytes_:
                bits = map(int, bin(byte)[2:].zfill(8))
                bits.reverse()
                bitmask += bits
            bitmasks.append(bitmask)
            address += num_bytes

        # Back to frames:
        frames = []
        for addr in addrs:
            bitmask = bitmasks[rom[addr]]
            num_tiles = len(filter(int, bitmask))
            frame = (rom[addr], rom[addr + 1 : addr + 1 + num_tiles])
            frames.append(frame)

        tmap = range(length) * (len(frames) + 1)
        for i, frame in enumerate(frames):
            bitmask = bitmasks[frame[0]]
            tiles = (x for x in frame[1])
            for j, bit in enumerate(bitmask):
                if bit:
                    tmap[(i + 1) * length + j] = tiles.next()

        filename = os.path.join(directory, 'front.{0}x{0}.2bpp.lz'.format(size))
        tiles = get_tiles(Decompressed(open(filename).read()).output)
        new_tiles = map(tiles.__getitem__, tmap)
        new_image = connect(new_tiles)
        filename = os.path.splitext(filename)[0]
        to_file(filename, new_image)
        export_2bpp_to_png(filename)


def export_png_to_2bpp(filein, fileout=None, palout=None, **kwargs):

    arguments = {
        'tile_padding': 0,
        'pic_dimensions': None,
        'animate': False,
        'stupid_bitmask_hack': [],
    }
    arguments.update(kwargs)
    arguments.update(read_filename_arguments(filein))

    image, arguments = png_to_2bpp(filein, **arguments)

    if fileout == None:
        fileout = os.path.splitext(filein)[0] + '.2bpp'
    to_file(fileout, image)

    tmap = arguments.get('tmap')

    if tmap != None and arguments['animate'] and arguments['pic_dimensions']:
        # Generate pic animation data.
        frame_text, bitmask_text = get_pic_animation(tmap, *arguments['pic_dimensions'])

        frames_path = os.path.join(os.path.split(fileout)[0], 'frames.asm')
        with open(frames_path, 'w') as out:
            out.write(frame_text)

        bitmask_path = os.path.join(os.path.split(fileout)[0], 'bitmask.asm')

        # The following Pokemon have a bitmask dummied out.
        for exception in arguments['stupid_bitmask_hack']:
           if exception in bitmask_path:
                bitmasks = bitmask_text.split(';')
                bitmasks[-1] = bitmasks[-1].replace('1', '0')
                bitmask_text = ';'.join(bitmasks)

        with open(bitmask_path, 'w') as out:
            out.write(bitmask_text)

    elif tmap != None and arguments.get('tilemap', False):
        tilemap_path = os.path.splitext(fileout)[0] + '.tilemap'
        to_file(tilemap_path, tmap)

    palette = arguments.get('palette')
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

    arguments = {
        'tile_padding': 0,
        'pic_dimensions': False,
        'interleave': False,
        'norepeat': False,
        'tilemap': False,
    }
    arguments.update(kwargs)

    if type(filein) is str:
        filein = open(filein)

    assert type(filein) is file

    width, height, rgba, info = png.Reader(filein).asRGBA8()

    # png.Reader returns flat pixel data. Nested is easier to work with
    len_px  = len('rgba')
    image   = []
    palette = []
    for line in rgba:
        newline = []
        for px in xrange(0, len(line), len_px):
            color = dict(zip('rgba', line[px:px+len_px]))
            if color not in palette:
                if len(palette) < 4:
                    palette += [color]
                else:
                    # TODO Find the nearest match
                    print 'WARNING: %s: Color %s truncated to' % (filein, color),
                    color = sorted(palette, key=lambda x: sum(x.values()))[0]
                    print color
            newline += [color]
        image += [newline]

    assert len(palette) <= 4, '%s: palette should be 4 colors, is really %d (%s)' % (filein, len(palette), palette)

    # Pad out smaller palettes with greyscale colors
    greyscale = {
        'black': { 'r': 0x00, 'g': 0x00, 'b': 0x00, 'a': 0xff },
        'grey':  { 'r': 0x55, 'g': 0x55, 'b': 0x55, 'a': 0xff },
        'gray':  { 'r': 0xaa, 'g': 0xaa, 'b': 0xaa, 'a': 0xff },
        'white': { 'r': 0xff, 'g': 0xff, 'b': 0xff, 'a': 0xff },
    }
    preference = 'white', 'black', 'grey', 'gray'
    for hue in map(greyscale.get, preference):
        if len(palette) >= 4:
            break
        if hue not in palette:
            palette += [hue]

    palette.sort(key=lambda x: sum(x.values()))

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

    dim = arguments['pic_dimensions']
    if dim:
        if type(dim) in (tuple, list):
            w, h = dim
        else:
            # infer dimensions based on width.
            w = width / tile_width
            h = height / tile_height
            if h % w == 0:
                h = w

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
    image = image[:len(image) - arguments['tile_padding'] * 0x10]

    tmap = None

    if arguments['interleave']:
        image = deinterleave_tiles(image, num_columns)

    if arguments['pic_dimensions']:
        image, tmap = condense_tiles_to_map(image, w * h)
    elif arguments['norepeat']:
        image, tmap = condense_tiles_to_map(image)
        if not arguments['tilemap']:
            tmap = None

    arguments.update({ 'palette': palette, 'tmap': tmap, })

    return image, arguments


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
    image, kwargs = png_to_2bpp(filename, **kwargs)
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

