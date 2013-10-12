import os

from Tkinter import *
import ttk
from ttk import Frame, Style
import PIL
from PIL import Image, ImageTk

import config
conf = config.Config()


#version = 'crystal'
version = 'red'

if version == 'crystal':
	map_dir = os.path.join(conf.path, 'maps/')
	gfx_dir = os.path.join(conf.path, 'gfx/tilesets/')
	to_gfx_name = lambda x : '%.2d' % x
	block_dir = os.path.join(conf.path, 'tilesets/')
	block_ext = '_metatiles.bin'

	palettes_on = True
	palmap_dir = os.path.join(conf.path, 'tilesets/')
	palette_dir = os.path.join(conf.path, 'tilesets/')

	asm_dir = os.path.join(conf.path, 'maps/')

	constants_dir = os.path.join(conf.path, 'constants/')
	constants_filename = os.path.join(constants_dir, 'map_constants.asm')

	header_dir = os.path.join(conf.path, 'maps/')

elif version == 'red':
	map_dir = os.path.join(conf.path, 'maps/')
	gfx_dir = os.path.join(conf.path, 'gfx/tilesets/')
	to_gfx_name = lambda x : '%.2x' % x
	block_dir = os.path.join(conf.path, 'gfx/blocksets/')
	block_ext = '.bst'

	palettes_on = False

	asm_path = os.path.join(conf.path, 'main.asm')

	constants_filename = os.path.join(conf.path, 'constants.asm')

	header_path = os.path.join(conf.path, 'main.asm')

else:
	raise Exception, 'version must be "crystal" or "red"'


def get_constants():
	lines = open(constants_filename, 'r').readlines()
	for line in lines:
		if ' EQU ' in line:
			name, value = [s.strip() for s in line.split(' EQU ')]
			globals()[name] = eval(value.split(';')[0].replace('$','0x').replace('%','0b'))
get_constants()


class Application(Frame):
	def __init__(self, master=None):
		self.display_connections = False
		Frame.__init__(self, master)
		self.grid()
		Style().configure("TFrame", background="#444")
		self.paint_tile = 1
		self.init_ui()

	def init_ui(self):
		self.connections = {}
		self.button_frame = Frame(self)
		self.button_frame.grid(row=0, column=0, columnspan=2)
		self.map_frame = Frame(self)
		self.map_frame.grid(row=1, column=0, padx=5, pady=5)
		self.picker_frame = Frame(self)
		self.picker_frame.grid(row=1, column=1)

		self.new = Button(self.button_frame)
		self.new["text"] = "New"
		self.new["command"] = self.new_map
		self.new.grid(row=0, column=0, padx=2)

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
		self.available_maps = sorted(m for m in get_available_maps())
		self.map_list = ttk.Combobox(self.button_frame, height=24, width=24, values=self.available_maps)
		if len(self.available_maps):
			self.map_list.set(self.available_maps[0])

	def new_map(self):
		self.map_name = None
		self.init_map()
		self.map.blockdata = [self.paint_tile] * 20 * 20
		self.map.width = 20
		self.map.height = 20
		self.draw_map()
		self.init_picker()

	def open_map(self):
		self.map_name = self.map_list.get()
		self.init_map()
		self.draw_map()
		self.init_picker()

	def save_map(self):
		if hasattr(self, 'map'):
			if self.map.blockdata_filename:
				with open(self.map.blockdata_filename, 'wb') as save:
					save.write(self.map.blockdata)
				print 'blockdata saved as %s' % self.map.blockdata_filename
			else:
				print 'dunno how to save this'
		else:
			print 'nothing to save'

	def init_map(self):
		if hasattr(self, 'map'):
			self.map.kill_canvas()
		self.map = Map(self.map_frame, self.map_name)
		self.init_map_connections()

	def draw_map(self):
		self.map.init_canvas(self.map_frame)
		self.map.canvas.pack() #.grid(row=1,column=1)
		self.map.draw()
		self.map.canvas.bind('<Button-1>', self.paint)
		self.map.canvas.bind('<B1-Motion>', self.paint)

	def init_picker(self):
		
		self.current_tile = Map(self.button_frame, tileset_id=self.map.tileset_id)
		self.current_tile.blockdata = [self.paint_tile]
		self.current_tile.width = 1
		self.current_tile.height = 1
		self.current_tile.init_canvas()
		self.current_tile.draw()
		self.current_tile.canvas.grid(row=0, column=4, padx=4)

		if hasattr(self, 'picker'):
			self.picker.kill_canvas()
		self.picker = Map(self, tileset_id=self.map.tileset_id)
		self.picker.blockdata = range(len(self.picker.tileset.blocks))
		self.picker.width = 4
		self.picker.height = len(self.picker.blockdata) / self.picker.width
		self.picker.init_canvas(self.picker_frame)

		if hasattr(self.picker_frame, 'vbar'):
			self.picker_frame.vbar.destroy()
		self.picker_frame.vbar = Scrollbar(self.picker_frame, orient=VERTICAL)
		self.picker_frame.vbar.pack(side=RIGHT, fill=Y)
		self.picker_frame.vbar.config(command=self.picker.canvas.yview)


		self.picker.canvas.config(scrollregion=(0,0,self.picker.canvas_width, self.picker.canvas_height))
		self.map_frame.update()
		self.picker.canvas.config(height=self.map_frame.winfo_height())
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
		block_x = int(self.picker.canvas.canvasx(event.x)) / (self.picker.tileset.block_width * self.picker.tileset.tile_width)
		block_y = int(self.picker.canvas.canvasy(event.y)) / (self.picker.tileset.block_height * self.picker.tileset.tile_height)
		i = block_y * self.picker.width + block_x
		self.paint_tile = self.picker.blockdata[i]

		self.current_tile.blockdata = [self.paint_tile]
		self.current_tile.draw()

	def paint(self, event):
		block_x = event.x / (self.map.tileset.block_width * self.map.tileset.tile_width)
		block_y = event.y / (self.map.tileset.block_height * self.map.tileset.tile_height)
		i = block_y * self.map.width + block_x
		if 0 <= i < len(self.map.blockdata):
			self.map.blockdata[i] = self.paint_tile
			self.map.draw_block(block_x, block_y)

	def init_map_connections(self):
		if not display_connections:
			return
		for direction in self.map.connections.keys():
			if direction in self.connections.keys():
				if hasattr(self.connections[direction], 'canvas'):
					self.connections[direction].kill_canvas()
			if self.map.connections[direction] == {}:
				self.connections[direction] = {}
				continue
			self.connections[direction] = Map(self, self.map.connections[direction]['map_name'])

			if direction in ['north', 'south']:
				x1 = 0
				y1 = 0
				x2 = x1 + eval(self.map.connections[direction]['strip_length'])
				y2 = y1 + 3
			else: # east, west
				x1 = 0
				y1 = 0
				x2 = x1 + 3
				y2 = y1 + eval(self.map.connections[direction]['strip_length'])

			self.connections[direction].crop(x1, y1, x2, y2)
			self.connections[direction].init_canvas(self.map_frame)
			self.connections[direction].canvas.pack(side={'west':LEFT,'east':RIGHT}[direction])
			self.connections[direction].draw()


class Map:
	def __init__(self, parent, name=None, width=20, height=20, tileset_id=2, blockdata_filename=None):
		self.parent = parent

		self.name = name

		self.blockdata_filename = blockdata_filename
		if not self.blockdata_filename and self.name:
			self.blockdata_filename = os.path.join(map_dir, self.name + '.blk')
		elif not self.blockdata_filename:
			self.blockdata_filename = ''

		asm_filename = ''
		if self.name:
			if 'asm_dir' in globals().keys():
				asm_filename = os.path.join(asm_dir, self.name + '.asm')
			elif 'asm_path' in globals().keys():
				asm_filename = asm_path

		if os.path.exists(asm_filename):
			for props in [map_header(self.name), second_map_header(self.name)]:
				self.__dict__.update(props)
			self.asm = open(asm_filename, 'r').read()
			self.events = event_header(self.asm, self.name)
			self.scripts = script_header(self.asm, self.name)

			self.tileset_id = eval(self.tileset_id)

			self.width = eval(self.width)
			self.height = eval(self.height)

		else:
			self.width = width
			self.height = height
			self.tileset_id = tileset_id

		if self.blockdata_filename:
			self.blockdata = bytearray(open(self.blockdata_filename, 'rb').read())
		else:
			self.blockdata = []

		self.tileset = Tileset(self.tileset_id)

	def init_canvas(self, parent=None):
		if parent == None:
			parent = self.parent
		if not hasattr(self, 'canvas'):
			self.canvas_width = self.width * 32
			self.canvas_height = self.height * 32
			self.canvas = Canvas(parent, width=self.canvas_width, height=self.canvas_height)
			self.canvas.xview_moveto(0)
			self.canvas.yview_moveto(0)

	def kill_canvas(self):
		if hasattr(self, 'canvas'):
			self.canvas.destroy()

	def crop(self, x1, y1, x2, y2):
		blockdata = self.blockdata
		start = y1 * self.width + x1
		width = x2 - x1
		height = y2 - y1
		self.blockdata = []
		for y in xrange(height):
			for x in xrange(width):
				self.blockdata += [blockdata[start + y * self.width + x]]
		self.blockdata = bytearray(self.blockdata)
		self.width = width
		self.height = height

	def draw(self):
		for i in xrange(len(self.blockdata)):
			block_x = i % self.width
			block_y = i / self.width
			self.draw_block(block_x, block_y)

	def draw_block(self, block_x, block_y):
		# the canvas starts at 4, 4 for some reason
		# probably something to do with a border
		index, indey = 4, 4

		# Draw one block (4x4 tiles)
		block = self.blockdata[block_y * self.width + block_x]
		for j, tile in enumerate(self.tileset.blocks[block]):
			try:
				# Tile gfx are split in half to make vram mapping easier
				if tile >= 0x80:
					tile -= 0x20
				tile_x = block_x * 32 + (j % 4) * 8
				tile_y = block_y * 32 + (j / 4) * 8
				self.canvas.create_image(index + tile_x, indey + tile_y, image=self.tileset.tiles[tile])
			except:
				pass


class Tileset:
	def __init__(self, tileset_id=0):
		self.id = tileset_id

		self.tile_width   = 8
		self.tile_height  = 8
		self.block_width  = 4
		self.block_height = 4

		self.alpha = 255

		if palettes_on:
			self.get_palettes()
			self.get_palette_map()

		self.get_blocks()
		self.get_tiles()

	def get_tileset_gfx_filename(self):
		filename = None

		if version == 'red':
			tileset_defs = open(os.path.join(conf.path, 'main.asm'), 'r').read()
			incbin = asm_at_label(tileset_defs, 'Tset%.2X_GFX' % self.id)
			print incbin
			filename = read_header_macros(incbin, ['filename'], ['INCBIN'])[0][0].replace('"','').replace('.2bpp','.png')
			filename = os.path.join(conf.path, filename)
			print filename

		if not filename:
			filename = os.path.join(
				gfx_dir,
				to_gfx_name(self.id) + '.png'
			)

		return filename

	def get_tiles(self):
		filename = self.get_tileset_gfx_filename()
		if not os.path.exists(filename):
			import gfx
			gfx.to_png(filename.replace('.png','.2bpp'), filename)
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
		filename = os.path.join(
			block_dir,
			to_gfx_name(self.id) + block_ext
		)
		self.blocks = []
		block_length = self.block_width * self.block_height
		blocks = bytearray(open(filename, 'rb').read())
		for block in xrange(len(blocks) / (block_length)):
			i = block * block_length
			self.blocks += [blocks[i : i + block_length]]

	def get_palette_map(self):
		filename = os.path.join(
			palmap_dir,
			str(self.id).zfill(2) + '_palette_map.bin'
		)
		self.palette_map = []
		palmap = bytearray(open(filename, 'rb').read())
		for i in xrange(len(palmap)):
			self.palette_map += [palmap[i] & 0xf]
			self.palette_map += [(palmap[i] >> 4) & 0xf]

	def get_palettes(self):
		filename = os.path.join(
			palette_dir,
			['morn', 'day', 'nite'][time_of_day] + '.pal'
		)
		self.palettes = get_palettes(filename)


time_of_day = 1


def get_palettes(filename):
	pals = bytearray(open(filename, 'rb').read())

	num_colors = 4
	color_length = 2

	palette_length = num_colors * color_length

	num_pals = len(pals) / palette_length

	palettes = []
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



def get_available_maps():
	for root, dirs, files in os.walk(map_dir):
		for filename in files:
			base_name, ext = os.path.splitext(filename)
			if ext == '.blk':
				yield base_name


def map_header(name):
	if version == 'crystal':
		headers = open(os.path.join(header_dir, 'map_headers.asm'), 'r').read()
		label = name + '_MapHeader'
		header = asm_at_label(headers, label)
		macros = [ 'db', 'db', 'db', 'dw', 'db', 'db', 'db', 'db' ]
		attributes = [
			'bank',
			'tileset_id',
			'permission',
			'second_map_header',
			'world_map_location',
			'music',
			'time_of_day',
			'fishing_group',
		]
		values, l = read_header_macros(header, attributes, macros)
		attrs = dict(zip(attributes, values))
		return attrs

	elif version == 'red':
		headers = open(header_path, 'r').read()

		# there has to be a better way to do this
		lower_label = name + '_h'
		i = headers.lower().find(lower_label)
		if i == -1:
			return {}
		label = headers[i:i+len(lower_label)]

		header = asm_at_label(headers, label)
		macros = [ 'db', 'db', 'db', 'dw', 'dw', 'dw', 'db' ]
		attributes = [
			'tileset_id',
			'height',
			'width',
			'blockdata_label',
			'text_label',
			'script_label',
			'which_connections',
		]
		values, l = read_header_macros(header, attributes, macros)

		attrs = dict(zip(attributes, values))
		attrs['connections'], l = connections(attrs['which_connections'], header, l)

		macros = [ 'dw' ]
		attributes = [
			'object_label',
		]
		values, l = read_header_macros(header[l:], attributes, macros)
		attrs.update(dict(zip(attributes, values)))

		return attrs

	return {}

def second_map_header(name):
	if version == 'crystal':
		headers = open(os.path.join(header_dir, 'second_map_headers.asm'), 'r').read()
		label = name + '_SecondMapHeader'
		header = asm_at_label(headers, label)
		macros = [ 'db', 'db', 'db', 'db', 'dw', 'db', 'dw', 'dw', 'db' ]
		attributes = [
			'border_block',
			'height',
			'width',
			'blockdata_bank',
			'blockdata_label',
			'script_header_bank',
			'script_header_label',
			'map_event_header_label',
			'which_connections',
		]

		values, l = read_header_macros(header, attributes, macros)
		attrs = dict(zip(attributes, values))
		attrs['connections'], l = connections(attrs['which_connections'], header, l)
		return attrs

	return {}

def connections(which_connections, header, l=0):
	directions = { 'north': {}, 'south': {}, 'west': {}, 'east': {} }

	if version == 'crystal':
		macros = [ 'db', 'db' ] 
		attributes = [
			'map_group',
			'map_no',
		]

	elif version == 'red':
		macros = [ 'db' ]
		attributes = [
			'map_id',
		]

	macros += [ 'dw', 'dw', 'db', 'db', 'db', 'db', 'dw' ]
	attributes += [
		'strip_pointer',
		'strip_destination',
		'strip_length',
		'map_width',
		'y_offset',
		'x_offset',
		'window',
	]
	for d in directions.keys():
		if d.upper() in which_connections:
			values, l = read_header_macros(header, attributes, macros)
			header = header[l:]
			directions[d] = dict(zip(attributes, values))
			if version == 'crystal':
				directions[d]['map_name'] = directions[d]['map_group'].replace('GROUP_', '').title().replace('_','')
			elif version == 'red':
				directions[d]['map_name'] = directions[d]['map_id'].title().replace('_','')
	return directions, l

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
	values = line[line.find(macro) + len(macro):].split(',')
	values = [v.replace('$','0x').strip() for v in values]
	if values[0] == 'w': # dbw
		values = values[1:]
	return values

def db_value(line):
	macro = 'db'
	return macro_values(line, macro)

def db_values(line):
	macro = 'db'
	return macro_values(line, macro)


from preprocessor import separate_comment

def asm_at_label(asm, label):
	label_def = label + ':'
	lines = asm.split('\n')
	for line in lines:
		if line.startswith(label_def):
			lines = lines[lines.index(line):]
			lines[0] = lines[0][len(label_def):]
			break
	# go until the next label
	content = []
	for line in lines:
		l, comment = separate_comment(line + '\n')
		if ':' in l:
			break
		content += [[l, comment]]
	return content

def main():
    """
    Launches the map editor.
    """
    root = Tk()
    root.wm_title("MAP EDITOR")
    app = Application(master=root)

    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass

    try:
        root.destroy()
    except TclError:
        pass

if __name__ == "__main__":
    main()
