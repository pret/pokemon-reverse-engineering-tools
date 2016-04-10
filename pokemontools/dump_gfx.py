from gfx import *
from pokemon_constants import pokemon_constants
import trainers
import romstr

def load_rom(filename=config.rom_path):
    rom = romstr.RomStr.load(filename=filename)
    return bytearray(rom)

def rom_offset(bank, address):
    if address < 0x4000 or address >= 0x8000:
        return address
    return bank * 0x4000 + address - 0x4000 * bool(bank)

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

def rgb_from_rom(address, length=0x80):
    rom = load_rom()
    return convert_binary_pal_to_text(rom[address:address+length])

def decompress_from_address(address, filename='de.2bpp'):
    """
    Write decompressed data from an address to a 2bpp file.
    """
    rom = load_rom()
    image = Decompressed(rom, start=address)
    to_file(filename, image.output)
