"""
Map-related graphic functions.
"""

import os
import png
from io import BytesIO

from PIL import (
    Image,
    ImageDraw,
)

import crystal
import gfx

tile_width = 8
tile_height = 8
block_width = 4
block_height = 4

WALKING_SPRITE = 1
STANDING_SPRITE = 2
STILL_SPRITE = 3

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
    config.sprites_dir = os.path.join(os.path.abspath("."), "gfx/overworld/")

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

all_blocks = {}
def read_blocks(tileset_id, config=config):
    """
    Makes a list of blocks, such that each block is a list of tiles by id, for
    the given tileset.
    """
    if tileset_id in all_blocks.keys():
        return all_blocks[tileset_id]

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

    all_blocks[tileset_id] = blocks

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

pre_cropped = {}
def read_tiles(tileset_id, palette_map, palettes, config=config):
    """
    Opens the tileset png file and reads bytes for each tile in the tileset.
    """

    if tileset_id not in pre_cropped.keys():
        pre_cropped[tileset_id] = {}

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
            if (x, y) in pre_cropped[tileset_id].keys():
                tile = pre_cropped[tileset_id][(x, y)]
            else:
                tile = image.crop((x, y, x + tile_width, y + tile_height))
                pre_cropped[tileset_id][(x, y)] = tile

            # palette maps are padded to make vram mapping easier
            pal = palette_map[cur_tile + 0x20 if cur_tile > 0x60 else cur_tile] & 0x7
            tile = colorize_tile(tile, palettes[pal])

            tiles.append(tile)

            cur_tile += 1

    return tiles

all_palette_maps = {}
def read_palette_map(tileset_id, config=config):
    """
    Loads a palette map.
    """
    if tileset_id in all_palette_maps.keys():
        return all_palette_maps[tileset_id]

    filename = "{id}{ext}".format(id=str(tileset_id).zfill(2), ext="_palette_map.bin")
    filepath = os.path.join(config.palmap_dir, filename)

    palette_map = []

    palmap = bytearray(open(filepath, "rb").read())

    for i in xrange(len(palmap)):
        palette_map += [palmap[i] & 0xf]
        palette_map += [(palmap[i] >> 4) & 0xf]

    all_palette_maps[tileset_id] = palette_map

    return palette_map

def read_palettes(time_of_day=1, config=config):
    """
    Loads up the .pal file?
    """
    palettes = []

    actual_time_of_day = ["morn", "day", "nite"][time_of_day]
    filename = "{}.pal".format(actual_time_of_day)
    filepath = os.path.join(config.palette_dir, filename)

    lines = open(filepath, "r").readlines()
    colors = gfx.read_rgb_macros(lines)
    palettes = [colors[i:i+4] for i in xrange(0, len(colors), 4)]
    return palettes

def load_sprite_image(address, config=config):
    """
    Make standard file path.
    """
    pal_file = os.path.join(config.block_dir, "day.pal")

    length = 0x40

    image = crystal.rom[address:address + length]
    width, height, palette, greyscale, bitdepth, px_map = gfx.convert_2bpp_to_png(image, width=16, height=16, pal_file=pal_file)
    w = png.Writer(16, 16, palette=palette, compression=9, greyscale=greyscale, bitdepth=bitdepth)
    some_buffer = BytesIO()
    w.write(some_buffer, px_map)
    some_buffer.seek(0)

    sprite_image = Image.open(some_buffer)

    return sprite_image

sprites = {}
def load_all_sprite_images(config=config):
    """
    Loads all images for each sprite in each direction.
    """
    crystal.direct_load_rom()

    sprite_headers_address = 0x14736
    sprite_header_size = 6
    sprite_count = 102
    frame_size = 0x40

    current_address = sprite_headers_address

    current_image_id = 0

    for sprite_id in xrange(1, sprite_count):
        rom_bytes = crystal.rom[current_address : current_address + sprite_header_size]
        header = [ord(x) for x in rom_bytes]

        bank = header[3]

        lo = header[0]
        hi = header[1]
        sprite_address = (hi * 0x100) + lo - 0x4000
        sprite_address += 0x4000 * bank

        sprite_size = header[2]
        sprite_type = header[4]
        sprite_palette = header[5]
        image_count = sprite_size / frame_size

        sprite = {
            "size": sprite_size,
            "image_count": image_count,
            "type": sprite_type,
            "palette": sprite_palette,
            "images": {},
        }

        if sprite_type in [WALKING_SPRITE, STANDING_SPRITE]:
            # down, up, left, move down, move up, move left
            sprite["images"]["down"] = load_sprite_image(sprite_address, config=config)
            sprite["images"]["up"] = load_sprite_image(sprite_address + 0x40, config=config)
            sprite["images"]["left"] = load_sprite_image(sprite_address + (0x40 * 2), config=config)

            if sprite_type == WALKING_SPRITE:
                current_image_id += image_count * 2
            elif sprite_type == STANDING_SPRITE:
                current_image_id += image_count * 1
        elif sprite_type == STILL_SPRITE:
            # just one image
            sprite["images"]["still"] = load_sprite_image(sprite_address, config=config)

            current_image_id += image_count * 1

        # store the actual metadata
        sprites[sprite_id] = sprite

        current_address += sprite_header_size

    return sprites

def draw_map_sprites(map_header, map_image, config=config):
    """
    Show NPCs and items on the map.
    """

    events = map_header.second_map_header.event_header.people_events

    for event in events:
        sprite_image_id = event.params[0].byte
        y = (event.params[1].byte - 4) * 4
        x = (event.params[2].byte - 4) * 4
        facing = event.params[3].byte
        movement = event.params[4].byte
        sight_range = event.params[8].byte
        some_pointer = event.params[9]
        bit_table_bit_number = event.params[10]

        other_args = {}

        if sprite_image_id not in sprites.keys() or sprite_image_id > 0x66:
            print "sprite_image_id {} is not in sprites".format(sprite_image_id)

            sprite_image = Image.new("RGBA", (16, 16))

            draw = ImageDraw.Draw(sprite_image, "RGBA")
            draw.rectangle([(0, 0), (16, 16)], fill=(0, 0, 0, 127))

            other_args["mask"] = sprite_image
        else:
            sprite = sprites[sprite_image_id]

            # TODO: pick the correct direction based on "facing"
            sprite_image = sprite["images"].values()[0]

        # TODO: figure out how to calculate the correct position
        map_image.paste(sprite_image, (x * 4, y * 4), **other_args)

def draw_map(map_group_id, map_id, palettes, show_sprites=True, config=config):
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

    tileset_blocks = read_blocks(tileset_id, config=config)
    tileset_images = read_tiles(tileset_id, palette_map, palettes, config=config)

    map_image = Image.new("RGB", (width * tile_width * block_width, height * tile_height * block_height))

    # draw each block on the map
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

    # draw each sprite on the map
    draw_map_sprites(map_header, map_image, config=config)

    return map_image

def save_map(map_group_id, map_id, savedir, show_sprites=True, config=config):
    """
    Makes a map and saves it to a file in savedir.
    """
    # this could be moved into a decorator
    crystal.cachably_parse_rom()

    map_name = crystal.map_names[map_group_id][map_id]["label"]
    filename = "{name}.{ext}".format(name=map_name, ext="png")
    filepath = os.path.join(savedir, filename)

    palettes = read_palettes(config=config)

    print "Drawing {}".format(map_name)
    map_image = draw_map(map_group_id, map_id, palettes, show_sprites=show_sprites, config=config)
    map_image.save(filepath)

    return map_image

def save_maps(savedir, show_sprites=True, config=config):
    """
    Draw as many maps as possible.
    """
    crystal.cachably_parse_rom()

    for map_group_id in crystal.map_names.keys():
        for map_id in crystal.map_names[map_group_id].keys():
            if isinstance(map_id, int):
                image = save_map(map_group_id, map_id, savedir, show_sprites=show_sprites, config=config)
