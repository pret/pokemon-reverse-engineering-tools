"""
Map-related graphic functions.
"""

import os

from PIL import (
    Image,
)

import crystal
import gfx

tile_width = 8
tile_height = 8
block_width = 4
block_height = 4

# use the same configuration
gfx.config = crystal.conf
config = gfx.config

def add_pokecrystal_paths_to_configuration(config=config):
    """
    Assumes that the current working directory is the pokecrystal project path.
    """
    config.gfx_dir = os.path.join(os.path.abspath("."), "gfx/tilesets/")
    config.block_dir = os.path.join(os.path.abspath("."), "tilesets/")
    config.palmap_dir = config.block_dir
    config.palette_dir = config.block_dir

add_pokecrystal_paths_to_configuration(config=config)

def read_map_blockdata(map_header):
    """
    Reads out the list of bytes representing the blockdata for the current map.
    """
    width = map_header.second_map_header.blockdata.width.byte
    height = map_header.second_map_header.blockdata.height.byte

    start_address = map_header.second_map_header.blockdata.address
    end_address = start_address + (width * height)

    blockdata = crystal.rom[start_address : end_address]

    return [ord(x) for x in blockdata]

def load_png(filepath):
    """
    Makes an image object from file.
    """
    return Image.open(filepath)

def read_blocks(tileset_id, config=config):
    """
    Makes a list of blocks, such that each block is a list of tiles by id, for
    the given tileset.
    """
    blocks = []

    block_width = 4
    block_height = 4
    block_length = block_width * block_height

    filename = "{id}{ext}".format(id=str(tileset_id).zfill(2), ext="_metatiles.bin")
    filepath = os.path.join(config.block_dir, filename)

    blocksetdata = bytearray(open(filepath, "rb").read())

    for blockbyte in xrange(len(blocksetdata) / block_length):
        block_num = blockbyte * block_length
        block = blocksetdata[block_num : block_num + block_length]
        blocks += [block]

    return blocks

def colorize_tile(tile, palette):
    """
    Make the tile have colors.
    """
    (width, height) = tile.size
    tile = tile.convert("RGB")
    px = tile.load()

    for y in xrange(height):
        for x in xrange(width):
            # assume greyscale
            which_color = 3 - (px[x, y][0] / 0x55)
            (r, g, b) = [v * 8 for v in palette[which_color]]
            px[x, y] = (r, g, b)

    return tile

def read_tiles(tileset_id, palette_map, palettes, config=config):
    """
    Opens the tileset png file and reads bytes for each tile in the tileset.
    """
    tile_width = 8
    tile_height = 8

    tiles = []

    filename = "{id}.{ext}".format(id=str(tileset_id).zfill(2), ext="png")
    filepath = os.path.join(config.gfx_dir, filename)

    image = load_png(filepath)
    (image.width, image.height) = image.size

    cur_tile = 0

    for y in xrange(0, image.height, tile_height):
        for x in xrange(0, image.width, tile_width):
            tile = image.crop((x, y, x + tile_width, y + tile_height))

            # palette maps are padded to make vram mapping easier
            pal = palette_map[cur_tile + 0x20 if cur_tile > 0x60 else cur_tile] & 0x7
            tile = colorize_tile(tile, palettes[pal])

            tiles.append(tile)

            cur_tile += 1

    return tiles

def read_palette_map(tileset_id, config=config):
    """
    Loads a palette map.
    """
    filename = "{id}{ext}".format(id=str(tileset_id).zfill(2), ext="_palette_map.bin")
    filepath = os.path.join(config.palmap_dir, filename)

    palette_map = []

    palmap = bytearray(open(filepath, "rb").read())

    for i in xrange(len(palmap)):
        palette_map += [palmap[i] & 0xf]
        palette_map += [(palmap[i] >> 4) & 0xf]

    return palette_map

def read_palettes(time_of_day=1, config=config):
    """
    Loads up the .pal file?
    """
    palettes = []

    actual_time_of_day = ["morn", "day", "nite"][time_of_day]
    filename = "{}.pal".format(actual_time_of_day)
    filepath = os.path.join(config.palette_dir, filename)

    num_colors = 4
    color_length = 2
    palette_length = num_colors * color_length

    pals = bytearray(open(filepath, "rb").read())
    num_pals = len(pals) / palette_length

    for pal in xrange(num_pals):
        palettes += [[]]

        for color in xrange(num_colors):
            i = pal * palette_length
            i += color * color_length
            word = pals[i] + pals[i+1] * 0x100

            palettes[pal] += [[
                c & 0x1f for c in [
                    word >> 0,
                    word >> 5,
                    word >> 10,
                ]
            ]]

    return palettes

def draw_map(map_group_id, map_id, config=config):
    """
    Makes a picture of a map.
    """
    # extract data from the ROM
    crystal.cachably_parse_rom()

    map_header = crystal.map_names[map_group_id][map_id]["header_new"]
    second_map_header = map_header.second_map_header

    width = second_map_header.blockdata.width.byte
    height = second_map_header.blockdata.height.byte

    tileset_id = map_header.tileset.byte
    blockdata = read_map_blockdata(map_header)

    palette_map = read_palette_map(tileset_id, config=config)
    palettes = read_palettes(config=config)

    tileset_blocks = read_blocks(tileset_id, config=config)
    tileset_images = read_tiles(tileset_id, palette_map, palettes, config=config)

    map_image = Image.new("RGB", (width * tile_width * block_width, height * tile_height * block_height))

    for block_num in xrange(len(blockdata)):
        block_x = block_num % width
        block_y = block_num / width

        block = blockdata[block_y * width + block_x]

        for (tile_num, tile) in enumerate(tileset_blocks[block]):
            # tile gfx are split in half to make vram mapping easier
            if tile >= 0x80:
                tile -= 0x20

            tile_x = block_x * 32 + (tile_num % 4) * 8
            tile_y = block_y * 32 + (tile_num / 4) * 8

            tile_image = tileset_images[tile]

            map_image.paste(tile_image, (tile_x, tile_y))

    return map_image

def save_map(map_group_id, map_id, savedir, config=config):
    """
    Makes a map and saves it to a file in savedir.
    """
    # this could be moved into a decorator
    crystal.cachably_parse_rom()

    map_name = crystal.map_names[map_group_id][map_id]["label"]
    filename = "{name}.{ext}".format(name=map_name, ext="png")
    filepath = os.path.join(savedir, filename)

    print "Drawing {}".format(map_name)
    map_image = draw_map(map_group_id, map_id, config)
    map_image.save(filepath)

    return map_image

def save_maps(savedir, config=config):
    """
    Draw as many maps as possible.
    """
    crystal.cachably_parse_rom()

    for map_group_id in crystal.map_names.keys():
        for map_id in crystal.map_names[map_group_id].keys():
            image = save_map(map_group_id, map_id, savedir, config)
