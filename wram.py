# coding: utf-8
"""
RGBDS BSS section and constant parsing.
"""

import os
path = os.path.dirname(os.path.abspath(__file__))

def read_bss_sections(bss):
    sections = []
    section = {
        "labels": [],
    }
    address = None
    if type(bss) is not list: bss = bss.split('\n')
    for line in bss:
        line = line.lstrip()
        if 'SECTION' in line:
            if section: sections.append(section) # last section

            address = eval(line[line.find('[')+1:line.find(']')].replace('$','0x'))
            section = {
                'name': line.split('"')[1],
                #'type': line.split(',')[1].split('[')[0].strip(),
                'start': address,
                'labels': [],
            }

        elif ':' in line:
            # rgbds allows labels without :, but prefer convention
            label = line[:line.find(':')]
            if ';' not in label:
                section['labels'] += [{
                    'label': label,
                    'address': address,
                    'length': 0,
                }]

        elif line[:3] == 'ds ':
            length = eval(line[3:line.find(';')].replace('$','0x'))
            address += length
            # adjacent labels use the same space
            for label in section['labels'][::-1]:
                if label['length'] == 0:
                    label['length'] = length
                else:
                    break

        elif 'EQU' in line:
            # some space is defined using constants
            name, value = line.split('EQU')
            name, value = name.strip(), value.strip().replace('$','0x').replace('%','0b')
            globals()[name] = eval(value)

    sections.append(section)
    return sections

def read_wram_sections():
    """
    Opens the wram file and calls read_bss_sections.
    """
    wram_content = None
    wram_file_path = os.path.join(os.path.dirname(path), 'wram.asm')
    try:
        wram_file_handler = open(wram_file_path, 'r')
    except IOError as exception:
        wram_content = [""]
    else:
        wram_content = wram_file_handler.readlines()
    wram_sections = read_bss_sections(wram_content)
    return wram_sections

wram_sections = read_wram_sections()

def make_wram_labels():
    wram_labels = {}
    for section in wram_sections:
        for label in section['labels']:
            if label['address'] not in wram_labels.keys():
                wram_labels[label['address']] = []
            wram_labels[label['address']] += [label['label']]
    return wram_labels

wram_labels = make_wram_labels()

def constants_to_dict(constants):
    return dict((eval(constant[constant.find('EQU')+3:constant.find(';')].replace('$','0x')), constant[:constant.find('EQU')].strip()) for constant in constants)

def scrape_constants(text):
    if type(text) is not list:
        text = text.split('\n')
    return constants_to_dict([line for line in text if 'EQU' in line[:line.find(';')]])

def read_constants(filepath):
    """
    Load lines from a file and call scrape_constants.
    """
    try:
        file_handler = open(filepath, "r")
    except IOError as exception:
        lines = [""]
    else:
        lines = file_handler.readlines()
    constants = scrape_constants(lines)
    return constants

def read_hram_constants():
    """
    Load constants from hram.asm.
    """
    hram_path = os.path.join(os.path.dirname(path), 'hram.asm')
    return read_constants(hram_path)

# TODO: get rid of this global
hram_constants = read_hram_constants()

def read_gbhw_constants():
    """
    Load constants from gbhw.asm.
    """
    gbhw_path = os.path.join(os.path.dirname(path), 'gbhw.asm')
    return read_constants(gbhw_path)

# TODO: get rid of this global
gbhw_constants = read_gbhw_constants()
