# coding: utf-8

import os
import re
import sys
import json

def make_sym_from_json(filename = 'pokecrystal.sym', j = 'labels.json'):
    output = ''
    labels = json.load(open(j))
    for label in labels:
        output += '{0:x}:{1:x} {2}\n'.format(label['bank'], label['address'], label['label'])
    with open(filename, 'w') as sym:
        sym.write(output)

def make_json_from_mapfile(filename='labels.json', mapfile='pokecrystal.map'):
    output = []
    labels = filter_wram_addresses(read_mapfile(mapfile))
    with open(filename, 'w') as out:
        out.write(json.dumps(labels))

def read_mapfile(filename='pokecrystal.map'):
    """
    Scrape label addresses from an rgbds mapfile.
    """

    labels = []

    with open(filename, 'r') as mapfile:
        lines = mapfile.readlines()

    for line in lines:
        if line[0].strip(): # section type def
            section_type = line.split(' ')[0]
            if section_type == 'Bank': # ROM
                cur_bank = int(line.split(' ')[1].split(':')[0][1:])
            elif section_type in ['WRAM0', 'HRAM']:
                cur_bank = 0
            elif section_type in ['WRAM, VRAM']:
                cur_bank = int(line.split(' ')[2].split(':')[0][1:])
                cur_bank = int(line.split(' ')[2].split(':')[0][1:])

        # label definition
        elif '=' in line:
            address, label = line.split('=')
            address = int(address.lstrip().replace('$', '0x'), 16)
            label = label.strip()

            bank = cur_bank
            offset = address
            if address < 0x8000 and bank: # ROM
                offset += (bank - 1) * 0x4000

            labels += [{
                'label': label,
                'bank': bank,
                'address': offset,
                'offset': offset,
                'local_address': address,
            }]

    return labels

def filter_wram_addresses(labels):
    filtered_labels = []
    for label in labels:
        if label['local_address'] < 0x8000:
            filtered_labels += [label]
    return filtered_labels

def make_sym_from_mapfile(filename = '../pokecrystal.sym', mapfile = '../mapfile.txt'):
    # todo: sort label definitions by address

    output = ''
    labels = read_mapfile()

    # convert to sym format (bank:addr label)
    for label in labels:
        output += '%.2x:%.4x %s\n' % (label['bank'], label['address'], label['label'])

    # dump contents to symfile
    with open(filename, 'w') as sym:
        sym.write(output)

def read_symfile(filename='pokecrystal.sym'):
    """
    Scrape label addresses from an rgbds .sym file.
    """
    labels = []

    with open(filename, 'r') as symfile:
        lines = symfile.readlines()

    # Example line from sym file:  "06:5531 Func_19531"
    label_regex = re.compile('([0-9A-Fa-f]+):([0-9A-Fa-f]+) (\S+)')

    for line in lines:
        match = label_regex.match(line)
        if match:
            bank = int(match.group(1), 16)
            local_address = int(match.group(2), 16)
            label = match.group(3)
            absolute_address = local_address

            if local_address < 0x8000 and bank > 0:
                absolute_address += (bank - 1) * 0x4000

            labels += [{
                'label': label,
                'bank': bank,
                'address': absolute_address,
                'offset': absolute_address,
                'local_address': local_address,
            }]

    return labels


if __name__ == "__main__":
    #if os.path.exists('../pokecrystal.sym'):
    #    sys.exit()
    #elif os.path.exists('../pokecrystal.map'):
    #    make_sym_from_mapfile()
    #elif os.path.exists('labels.json'):
    #    make_sym_from_json()
    make_json_from_mapfile()
