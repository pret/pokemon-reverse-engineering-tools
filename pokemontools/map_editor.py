import os
import sys
import logging
import argparse

from Tkinter import (
    Tk,
    Button,
    Canvas,
    Scrollbar,
    VERTICAL,
    HORIZONTAL,
    RIGHT,
    LEFT,
    TOP,
    BOTTOM,
    BOTH,
    Y,
    X,
    N, S, E, W,
    TclError,
    Menu,
)
import tkFileDialog

from ttk import (
    Frame,
    Style,
    Combobox,
)

# This is why requirements.txt says to install pillow instead of the original
# PIL.
from PIL import (
    Image,
    ImageTk,
)

import gfx
import wram
import preprocessor
import configuration
config = configuration.Config()


def config_open(self, filename):
    return open(os.path.join(self.path, filename))

configuration.Config.open = config_open


def setup_logging():
    """
    Temporary function that configures logging to go straight to console.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(console)
    root.setLevel(logging.DEBUG)


def read_incbin_in_file(label, filename='main.asm', config=config):
    asm = config.open(filename).read()
    return read_incbin(asm, label)

def read_incbin(asm, label):
    incbin = asm_at_label(asm, label)
    filename = read_header_macros_2(
        incbin,
        [('filename', 'INCBIN')]
    )[0]['filename']
    filename = filename.split('"')[1]
    return filename


def red_gfx_name(tset):
    if type(tset) is int:
        return [
            'overworld',
            'redshouse1',
            'mart',
	    'forest',
            'redshouse2',
            'dojo',
            'pokecenter',
            'gym',
            'house',
            'forestgate',
            'museum',
            'underground',
            'gate',
            'ship',
            'shipport',
            'cemetery',
            'interior',
            'cavern',
            'lobby',
            'mansion',
            'lab',
            'club',
            'facility',
            'plateau',
        ][tset]

    elif type(tset) is str:
        return tset.lower().replace('_', '')


def configure_for_pokered(config=config):
    """
    Sets default configuration values for pokered. These should eventually be
    moved into the configuration module.
    """
    attrs = {
        "version": "red",

        "map_dir": os.path.join(config.path, 'maps/'),
        "gfx_dir": os.path.join(config.path, 'gfx/tilesets/'),
        "to_gfx_name": red_gfx_name,
        "block_dir": os.path.join(config.path, 'gfx/blocksets/'), # not used
        "block_ext": '.bst', # not used

        "palettes_on": False,

        "constants_filename": os.path.join(config.path, 'constants.asm'),

        "time_of_day": 1,
    }
    return attrs

def configure_for_pokecrystal(config=config):
    """
    Sets default configuration values for pokecrystal. These should eventually
    be moved into the configuration module.
    """
    attrs = {
        "version": "crystal",

        "map_dir": os.path.join(config.path, 'maps/'),
        "gfx_dir": os.path.join(config.path, 'gfx/tilesets/'),
        "to_gfx_name": lambda x : '%.2d' % x,
        "block_dir": os.path.join(config.path, 'tilesets/'),
        "block_ext": '_metatiles.bin',

        "palettes_on": True,
        "palmap_dir": os.path.join(config.path, 'tilesets/'),
        "palette_dir": os.path.join(config.path, 'tilesets/'),

        "asm_dir": os.path.join(config.path, 'maps/'),

        "constants_filename": os.path.join(config.path, 'constants.asm'),

        "header_dir": os.path.join(config.path, 'maps/'),

        "time_of_day": 1,
    }
    return attrs

def configure_for_version(version, config=config):
    """
    Overrides default values from the configuration with additional attributes.
    """
    if version == "red":
        attrs = configure_for_pokered(config)
    elif version == "crystal":
        attrs = configure_for_pokecrystal(config)
    else:
        # TODO: pick a better exception
        raise Exception(
            "Can't configure for this version."
        )

    for (key, value) in attrs.iteritems():
        setattr(config, key, value)

    # not really needed since it's modifying the same object
    return config

def get_constants(config=config):
    bss = wram.BSSReader()
    bss.read_bss_sections(open(config.constants_filename).readlines())
    config.constants = bss.constants
    return config.constants


class Application(Frame):
    def __init__(self, master=None, config=config):
        self.config = config
        self.log = logging.getLogger("{0}.{1}".format(self.__class__.__name__, id(self)))
        self.display_connections = True

        Frame.__init__(self, master)
        self.pack(fill=BOTH, expand=True)
        Style().configure("TFrame", background="#444")

        self.paint_tile = 1
        self.init_ui()

    def init_ui(self):
        self.connections = {}
        self.button_frame = Frame(self)
        self.button_frame.grid(row=0, column=0, columnspan=2)
        self.map_frame = Frame(self)
        self.map_frame.grid(row=1, column=0, padx=5, pady=5, sticky=N+S+E+W)
        self.picker_frame = Frame(self)
        self.picker_frame.grid(row=1, column=1)

        self.button_new = Button(self.button_frame)
        self.button_new["text"] = "New"
        self.button_new["command"] = self.new_map
        self.button_new.grid(row=0, column=0, padx=2)

        self.menubar = Menu(self)

        menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New")
        menu.add_command(label="Open")
        menu.add_command(label="Save")

        self.open = Button(self.button_frame)
        self.open["text"] = "Open"
        self.open["command"] = self.open_map
        self.open.grid(row=0, column=1, padx=2)

        self.save = Button(self.button_frame)
        self.save["text"] = "Save"
        self.save["command"] = self.save_map
        self.save.grid(row=0, column=2, padx=2)

        self.get_map_list()
        self.map_list.grid(row=0, column=3, padx=2)


    def get_map_list(self):
        self.available_maps = sorted(m for m in get_available_maps(config=self.config))
        self.map_list = Combobox(self.button_frame, height=24, width=24, values=self.available_maps)
        if len(self.available_maps):
            self.map_list.set(self.available_maps[0])

    def new_map(self):
        self.map_name = None
        self.init_map()
        self.map.map.blockdata = bytearray([self.paint_tile] * 20 * 20)
        self.map.map.width = 20
        self.map.map.height = 20
        self.draw_map()
        self.init_picker()

    def open_map(self):
        self.map_name = self.map_list.get()
        self.init_map()
        self.draw_map()
        self.init_picker()

    def save_map(self):
        if hasattr(self, 'map'):
            if self.map.map.blk_path:
                initial = self.map.map.blk_path
            else:
                initial = self.config.path
            filename = tkFileDialog.asksaveasfilename(initialfile=initial)
            if filename:
                with open(filename, 'wb') as save:
                    save.write(self.map.map.blockdata)
                self.log.info('blockdata saved as {}'.format(filename))
        else:
            self.log.info('nothing to save')

    def init_map(self):
        if hasattr(self, 'map'):
            self.map.kill_canvas()
        self.map = MapRenderer(self.config, parent=self.map_frame, name=self.map_name)
        self.init_map_connections()

    def draw_map(self):
        self.map.init_canvas(self.map_frame)
        self.map.canvas.pack() #.grid(row=1,column=1)
        self.map.draw()
        self.map.canvas.bind('<Button-1>', self.paint)
        self.map.canvas.bind('<B1-Motion>', self.paint)

    def init_picker(self):
        """This should really be its own class."""
        self.current_tile = MapRenderer(self.config, parent=self.button_frame, tileset=Tileset(id=self.map.map.tileset.id))
        self.current_tile.map.blockdata = [self.paint_tile]
        self.current_tile.map.width = 1
        self.current_tile.map.height = 1
        self.current_tile.init_canvas()
        self.current_tile.draw()
        self.current_tile.canvas.grid(row=0, column=4, padx=4)

        if hasattr(self, 'picker'):
            self.picker.kill_canvas()
        self.picker = MapRenderer(self.config, parent=self, tileset=Tileset(id=self.map.map.tileset.id))
        self.picker.map.blockdata = range(len(self.picker.map.tileset.blocks))
        self.picker.map.width = 4
        self.picker.map.height = len(self.picker.map.blockdata) / self.picker.map.width
        self.picker.init_canvas(self.picker_frame)

        if hasattr(self.picker_frame, 'vbar'):
            self.picker_frame.vbar.destroy()
        self.picker_frame.vbar = Scrollbar(self.picker_frame, orient=VERTICAL)
        self.picker_frame.vbar.pack(side=RIGHT, fill=Y)
        self.picker_frame.vbar.config(command=self.picker.canvas.yview)

        self.picker.canvas.config(scrollregion=(0,0,self.picker.canvas_width, self.picker.canvas_height))
        self.map_frame.update()

        # overwriting a property is probably a bad idea
        self.picker.canvas_height = self.map_frame.winfo_height()

        self.picker.canvas.config(yscrollcommand=self.picker_frame.vbar.set)
        self.picker.canvas.pack(side=LEFT, expand=True)

        self.picker.canvas.bind('<4>', lambda event : self.scroll_picker(event))
        self.picker.canvas.bind('<5>', lambda event : self.scroll_picker(event))
        self.picker_frame.vbar.bind('<4>', lambda event : self.scroll_picker(event))
        self.picker_frame.vbar.bind('<5>', lambda event : self.scroll_picker(event))

        self.picker.draw()
        self.picker.canvas.bind('<Button-1>', self.pick_block)

    def scroll_picker(self, event):
        if event.num == 4:
            self.picker.canvas.yview('scroll', -1, 'units')
        elif event.num == 5:
            self.picker.canvas.yview('scroll', 1, 'units')


    def pick_block(self, event):
        block_x = int(self.picker.canvas.canvasx(event.x)) / (self.picker.map.tileset.block_width * self.picker.map.tileset.tile_width)
        block_y = int(self.picker.canvas.canvasy(event.y)) / (self.picker.map.tileset.block_height * self.picker.map.tileset.tile_height)
        i = block_y * self.picker.map.width + block_x
        self.paint_tile = self.picker.map.blockdata[i]

        self.current_tile.map.blockdata = [self.paint_tile]
        self.current_tile.draw()

    def paint(self, event):
        block_x = event.x / (self.map.map.tileset.block_width * self.map.map.tileset.tile_width)
        block_y = event.y / (self.map.map.tileset.block_height * self.map.map.tileset.tile_height)
        i = block_y * self.map.map.width + block_x
        if 0 <= i < len(self.map.map.blockdata):
            self.map.map.blockdata[i] = self.paint_tile
            self.map.draw_block(block_x, block_y)

    def init_map_connections(self):
        if not self.display_connections:
            return

        for direction in self.map.map.connections.keys():

            if direction in self.connections.keys():
                if hasattr(self.connections[direction], 'canvas'):
                    self.connections[direction].kill_canvas()

            if self.map.map.connections[direction] == {}:
                self.connections[direction] = {}
                continue

            self.connections[direction] = MapRenderer(self.config, parent=self, name=self.map.map.connections[direction]['map_name'])

            attrs = self.map.map.connections[direction]
            if direction in ['north', 'south']:
                if direction == 'north':
                    x1 = 0
                    if self.config.version == 'red':
                        y1 = eval(attrs['other_height'], self.config.constants) - 3
                    elif self.config.version == 'crystal':
                        y1 = eval(attrs['map'] + '_HEIGHT', self.config.constants) - 3
                else: # south
                    x1 = 0
                    y1 = 0
                x2 = x1 + eval(attrs['strip_length'], self.config.constants)
                y2 = y1 + 3
            else:
                if direction == 'east':
                    x1 = 0
                    y1 = 0
                else: # west
                    x1 = -3
                    y1 = 1
                x2 = x1 + 3
                y2 = y1 + eval(attrs['strip_length'], self.config.constants)

            self.connections[direction].init_canvas(self.map_frame)
            self.connections[direction].canvas.pack(side={'north':TOP, 'south':BOTTOM, 'west':LEFT,'east':RIGHT}[direction])
            self.connections[direction].map.crop(x1, y1, x2, y2)
            self.connections[direction].draw()


class MapRenderer:
    def __init__(self, config=config, **kwargs):
        self.config = config
        self.__dict__.update(kwargs)
        self.map = Map(**kwargs)

    @property
    def canvas_width(self):
        return self.map.width * self.map.block_width

    @property
    def canvas_height(self):
        return self.map.height * self.map.block_height

    def init_canvas(self, parent=None):
        if parent == None:
            parent = self.parent
        if hasattr(self, 'canvas'):
            pass
        else:
            self.canvas = Canvas(parent)
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def kill_canvas(self):
        if hasattr(self, 'canvas'):
            self.canvas.destroy()

    def draw(self):
        self.canvas.configure(width=self.canvas_width, height=self.canvas_height)
        for i in xrange(len(self.map.blockdata)):
            block_x = i % self.map.width
            block_y = i / self.map.width
            self.draw_block(block_x, block_y)

    def draw_block(self, block_x, block_y):
        # the canvas starts at 4, 4 for some reason
        # probably something to do with a border
        index, indey = 4, 4

        # Draw one block (4x4 tiles)
        block = self.map.blockdata[block_y * self.map.width + block_x]

        # Ignore nonexistent blocks.
        if block >= len(self.map.tileset.blocks): return

        for j, tile in enumerate(self.map.tileset.blocks[block]):
            try:
                # Tile gfx are split in half to make vram mapping easier
                if tile >= 0x80:
                    tile -= 0x20
                tile_x = block_x * self.map.block_width + (j % 4) * 8
                tile_y = block_y * self.map.block_height + (j / 4) * 8
                self.canvas.create_image(index + tile_x, indey + tile_y, image=self.map.tileset.tiles[tile])
            except:
                pass

    def crop(self, *args, **kwargs):
        self.map.crop(*args, **kwargs)
        self.draw()


class Map:
    width = 20
    height = 20
    block_width = 32
    block_height = 32

    def __init__(self, config=config, **kwargs):
        self.parent = None
        self.name = ''
        self.blk_path = ''
        self.tileset = Tileset(config=config)
        self.blockdata = []
        self.connections = {'north': {}, 'south': {}, 'west': {}, 'east': {}}

        self.__dict__.update(kwargs)
        self.config = config

        self.log = logging.getLogger("{0}.{1}".format(self.__class__.__name__, id(self)))

        if not self.blk_path and self.name:
            self.blk_path = os.path.join(self.config.map_dir, self.name + '.blk')
        if os.path.exists(self.blk_path) and self.blockdata == []:
            self.blockdata = bytearray(open(self.blk_path).read())

        if self.config.version == 'red':
            if self.name:
                attrs = map_header(self.name, config=self.config)
                self.tileset = Tileset(id=attrs['tileset_id'], config=self.config)
                self.height = eval(attrs['height'], self.config.constants)
                self.width = eval(attrs['width'], self.config.constants)
                self.connections = attrs['connections']

        elif self.config.version == 'crystal':

            asm_filename = ''
            if self.name:
                asm_filename = os.path.join(self.config.asm_dir, self.name + '.asm')

            if os.path.exists(asm_filename):
                for props in [
                    map_header(self.name, config=self.config),
                    second_map_header(self.name, config=self.config)
                ]:
                    self.__dict__.update(props)

                self.asm = open(asm_filename, 'r').read()
                self.events = event_header(self.asm, self.name)
                self.scripts = script_header(self.asm, self.name)

                self.tileset = Tileset(id=self.tileset_id, config=self.config)

                self.width = eval(self.width, self.config.constants)
                self.height = eval(self.height, self.config.constants)

    def crop(self, x1=0, y1=0, x2=None, y2=None):
        if x2 is None: x2 = self.width
        if y2 is None: y2 = self.height
        start = y1 * self.width + x1
        width = x2 - x1
        height = y2 - y1
        blockdata = []
        for y in xrange(height):
            index = start + y * self.width
            blockdata.extend( self.blockdata[index : index + width] )
        self.blockdata = bytearray(blockdata)
        self.width = width
        self.height = height


class Tileset:
    def __init__(self, config=config, **kwargs):
        if config.version == 'red':
            self.id = 0
        elif config.version == 'crystal':
            self.id = 2

        self.tile_width   = 8
        self.tile_height  = 8
        self.block_width  = 4
        self.block_height = 4

        self.alpha = 255

        self.__dict__.update(kwargs)
        self.id = eval(str(self.id), config.constants)

        self.config = config
        self.log = logging.getLogger("{0}.{1}".format(self.__class__.__name__, id(self)))

        if self.config.palettes_on:
            self.get_palettes()
            self.get_palette_map()

        self.get_blocks()
        self.get_tiles()

    def read_header(self):
        if self.config.version == 'red':
            tileset_headers = self.config.open('data/tileset_headers.asm').readlines()
            tileset_header = map(str.strip, tileset_headers[self.id + 1].split('\ttileset')[1].split(','))
            return tileset_header

    def get_tileset_gfx_filename(self):
        filename = None

        if self.config.version == 'red':
            gfx_label = self.read_header()[1]
            filename = read_incbin_in_file(gfx_label, filename='main.asm', config=self.config)
            filename = filename.replace('.2bpp','.png')
            filename = os.path.join(self.config.path, filename)

        if not filename: # last resort
            filename = os.path.join(
                self.config.gfx_dir,
                self.config.to_gfx_name(self.id) + '.png'
            )

        return filename

    def get_tiles(self):
        filename = self.get_tileset_gfx_filename()
        if not os.path.exists(filename):
            # Crystal still isn't ready for pngs.
            if self.config.version == 'crystal':
                gfx.convert_to_png([filename.replace('.png', '.2bpp.lz')])
        self.img = Image.open(filename)
        self.img.width, self.img.height = self.img.size
        self.tiles = []
        cur_tile = 0
        for y in xrange(0, self.img.height, self.tile_height):
            for x in xrange(0, self.img.width, self.tile_width):
                tile = self.img.crop((x, y, x + self.tile_width, y + self.tile_height))

                if hasattr(self, 'palette_map') and hasattr(self, 'palettes'):
                    # Palette maps are padded to make vram mapping easier.
                    pal = self.palette_map[cur_tile + 0x20 if cur_tile >= 0x60 else cur_tile] & 0x7
                    tile = self.colorize_tile(tile, self.palettes[pal])

                self.tiles += [ImageTk.PhotoImage(tile)]
                cur_tile += 1

    def colorize_tile(self, tile, palette):
        width, height = tile.size
        tile = tile.convert("RGB")
        px = tile.load()
        for y in xrange(height):
            for x in xrange(width):
                # assume greyscale
                which_color = 3 - (px[x, y][0] / 0x55)
                r, g, b = [v * 8 for v in palette[which_color]]
                px[x, y] = (r, g, b)
        return tile

    def get_blocks(self):
        if self.config.version == 'crystal':
            filename = os.path.join(
                self.config.block_dir,
                self.config.to_gfx_name(self.id) + self.config.block_ext
            )

        elif self.config.version == 'red':
            block_label = self.read_header()[0]
            filename = read_incbin_in_file(block_label, 'main.asm', config=self.config)

        self.blocks = []
        block_length = self.block_width * self.block_height
        blocks = bytearray(open(filename, 'rb').read())
        for block in xrange(len(blocks) / (block_length)):
            i = block * block_length
            self.blocks += [blocks[i : i + block_length]]

    def get_palette_map(self):
        filename = os.path.join(
            self.config.palmap_dir,
            str(self.id).zfill(2) + '_palette_map.bin'
        )
        self.palette_map = []
        palmap = bytearray(open(filename, 'rb').read())
        for i in xrange(len(palmap)):
            self.palette_map += [palmap[i] & 0xf]
            self.palette_map += [(palmap[i] >> 4) & 0xf]

    def get_palettes(self):
        filename = os.path.join(
            self.config.palette_dir,
            ['morn', 'day', 'nite'][self.config.time_of_day] + '.pal'
        )
        self.palettes = get_palettes(filename)

def get_palettes(filename):
    lines = open(filename, 'r').readlines()
    colors = gfx.read_rgb_macros(lines)
    palettes = [colors[i:i+4] for i in xrange(0, len(colors), 4)]
    return palettes

def get_available_maps(config=config):
    for root, dirs, files in os.walk(config.map_dir):
        for filename in files:
            base_name, ext = os.path.splitext(filename)
            if ext == '.blk':
                yield base_name

def map_header(name, config=config):
    if config.version == 'crystal':
        headers = open(os.path.join(config.header_dir, 'map_headers.asm'), 'r').read()
        label = name
        header = asm_at_label(headers, '\tmap_header ' + label, colon=',')
        attributes = [
            ('label',              'map_header'),
            ('tileset_id',         'db'),
            ('permission',         'db'),
            ('world_map_location', 'db'),
            ('music',              'db'),
            ('time_of_day',        'db'),
            ('fishing_group',      'db'),
        ]
        attrs, l = read_header_macros_2(header, attributes)
        return attrs

    elif config.version == 'red':
        header = config.open('data/mapHeaders/{0}.asm'.format(name)).read()
        header = split_comments(header.split('\n'))
        attributes = [
            ('tileset_id',        'db'),
            ('height',            'db'),
            ('width',             'db'),
            ('blockdata_label',   'dw'),
            ('text_label',        'dw'),
            ('script_label',      'dw'),
            ('which_connections', 'db'),
        ]

        attrs, l = read_header_macros_2(header, attributes)

        attrs['connections'], l = connections(attrs['which_connections'], header, l, config=config)

        attributes = [('object_label', 'dw')]
        more_attrs, l = read_header_macros_2(header[l:], attributes)
        attrs.update(more_attrs)

        return attrs

    return {}

def second_map_header(name, config=config):
    if config.version == 'crystal':
        headers = open(os.path.join(config.header_dir, 'second_map_headers.asm'), 'r').read()
        label = '\tmap_header_2 ' + name
        header = asm_at_label(headers, label, colon=',')

        attributes = [
            ('second_label',           'map_header_2'),
            ('dimension_base',         'db'),
            ('border_block',           'db'),
            ('which_connections',      'db'),
        ]

        attrs, l = read_header_macros_2(header, attributes)

        # hack to use dimension constants, eventually dimensions will be here for real
        attrs['height'] = attrs['dimension_base'] + '_HEIGHT'
        attrs['width']  = attrs['dimension_base'] + '_WIDTH'

        attrs['connections'], l = connections(attrs['which_connections'], header, l, config=config)
        return attrs

    return {}

def connections(which_connections, header, l=0, config=config):
    directions = { 'north': {}, 'south': {}, 'west': {}, 'east': {} }

    if config.version == 'crystal':
        attributes = [
            ('map',               'map'),
            ('strip_pointer',     'dw'),
            ('strip_destination', 'dw'),
            ('strip_length',      'db'),
            ('map_width',         'db'),
            ('y_offset',          'db'),
            ('x_offset',          'db'),
            ('window',            'dw'),
        ]

    elif config.version == 'red':
        conn_attrs = {
            'north': ['map_id', 'other_width', 'other_height', 'x_offset', 'strip_offset', 'strip_length', 'other_blocks'],
            'south': ['map_id', 'other_width', 'x_offset', 'strip_offset', 'strip_length', 'other_blocks', 'width', 'height'],
            'east':  ['map_id', 'other_width', 'y_offset', 'strip_offset', 'strip_length', 'other_blocks', 'width'],
            'west':  ['map_id', 'other_width', 'y_offset', 'strip_offset', 'strip_length', 'other_blocks', 'width'],
        }

    for d in ['north', 'south', 'west', 'east']:
        if d.upper() in which_connections:

            if config.version == 'crystal':
                attrs, l2 = read_header_macros_2(header[l:], attributes)
                l += l2
                directions[d] = attrs
                directions[d]['map_name'] = directions[d]['map'].title().replace('_','')

            elif config.version == 'red':
                attrs, l2 = read_header_macros_2(header[l:], zip(conn_attrs[d], [d.upper() + '_MAP_CONNECTION'] * len(conn_attrs[d])))
                l += l2
                directions[d] = attrs
                directions[d]['map_name'] = directions[d]['map_id'].lower().replace('_','')

    return directions, l

def read_header_macros_2(header, attributes):
    values, l = read_header_macros(header, [x[0] for x in attributes], [x[1] for x in attributes])
    return dict(zip([x[0] for x in attributes], values)), l

def read_header_macros(header, attributes, macros):
    values = []
    i = 0
    l = 0
    for l, (asm, comment) in enumerate(header):
        if asm.strip() != '':
            mvalues = macro_values(asm, macros[i])
            values += mvalues
            i += len(mvalues)
        if len(values) >= len(attributes):
            l += 1
            break
    return values, l

def event_header(asm, name):
    return {}

def script_header(asm, name):
    return {}

def macro_values(line, macro):
    values = macro.join(line.split(macro)[1:]).split(',')
    #values = line[line.find(macro) + len(macro):].split(',')
    values = [v.replace('$','0x').strip() for v in values]
    if values[0] == 'w': # dbw
        values = values[1:]
    return values

def asm_at_label(asm, label, colon=':'):
    label_def = label + colon
    lines = asm.split('\n')
    for i, line in enumerate(lines):
        if label_def in line:
            lines = lines[i:]
            break
    return split_comments(lines)

def split_comments(lines):
    content = []
    for line in lines:
        l, comment = preprocessor.separate_comment(line + '\n')
        # skip over labels? this should be in macro_values
        while ':' in l:
            l = l[l.index(':') + 1:]
        content += [[l, comment]]
    return content


def main(config=config):
    """
    Creates an application instance.
    """
    root = Tk()
    root.columnconfigure(0, weight=1)
    root.wm_title("ayy lmap")
    app = Application(master=root, config=config)
    return app

def init(config=config, version='crystal'):
    """
    Launches a map editor instance.
    """
    setup_logging()
    configure_for_version(version, config)
    get_constants(config=config)
    return main(config=config)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('version', nargs='?', default='crystal')
    args = ap.parse_args()
    app = init(config=config, version=args.version)
    app.mainloop()
