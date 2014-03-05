# coding: utf-8
"""
RGBDS BSS section and constant parsing.
"""

import os

# TODO: parse these constants from constants.asm
NUM_OBJECTS = 0x10
OBJECT_LENGTH = 0x10


def separate_comment(line):
    if ';' in line:
        i = line.find(';')
        return line[:i], line[i:]
    return line, None


def rgbasm_to_py(text):
    return text.replace('$', '0x').replace('%', '0b')


def make_wram_labels(wram_sections):
    wram_labels = {}
    for section in wram_sections:
        for label in section['labels']:
            if label['address'] not in wram_labels.keys():
                wram_labels[label['address']] = []
            wram_labels[label['address']] += [label['label']]
    return wram_labels

def bracket_value(string, i=0):
    return string.split('[')[1 + i*2].split(']')[0]

def read_bss_sections(bss, sections=[], section=None, address=None, macros={}):

    if section is None:
        section = {
            "labels": [],
        }

    if type(bss) is str:
        bss = bss.split('\n')

    macro = False
    macro_name = None
    for line in bss:
        line = line.lstrip()
        line, comment = separate_comment(line)
        line = line.strip()

        if line[-4:].upper() == 'ENDM':
            macro = False
            macro_name = None

        elif macro:
            macros[macro_name] += [line]

        elif line[-5:].upper() == 'MACRO':
            macro_name = line.split(':')[0]
            macro = True
            macros[macro_name] = []

        elif 'SECTION' == line[:7]:
            if section: # previous
                sections += [section]

            section_def = line.split(',')
            name  = section_def[0].split('"')[1]
            type_ = section_def[1].strip()
            if len(section_def) > 2:
                bank = bracket_value(section_def[2])
            else:
                bank = None

            if '[' in type_:
                address = int(rgbasm_to_py(bracket_value(type_)), 16)
            else:
                types = {
                    'VRAM':  0x8000,
                    'SRAM':  0xa000,
                    'WRAM0': 0xc000,
                    'WRAMX': 0xd000,
                    'HRAM':  0xff80,
                }
                if address == None or bank != section['bank'] or section['type'] != type_:
                    if type_ in types.keys():
                        address = types[type_]
                # else: keep going from this address

            section = {
                'name': name,
                'type': type_,
                'bank': bank,
                'start': address,
                'labels': [],
            }

        elif ':' in line:
            # rgbasm allows labels without :, but prefer convention
            label = line[:line.find(':')]
            if '\\' in label:
                raise Exception, line + ' ' + label
            if ';' not in label:
                section['labels'] += [{
                    'label': label,
                    'address': address,
                    'length': 0,
                }]

        elif 'EQU' in line.split():
            # some space is defined using constants
            name, value = line.split('EQU')
            name, value = name.strip(), value.strip().replace('$','0x').replace('%','0b')
            globals()[name] = eval(value)

        elif line.strip():
            parts = line.strip().split(' ')
            token = parts[0].strip()
            params = ' '.join(parts[1:]).split(',')

            if token in ['ds', 'db', 'dw']:
                if len(params):
                    length = eval(rgbasm_to_py(params[0]))
                else:
                    length = {'ds': 1, 'db': 1, 'dw': 2}[token]
                    address += length
                # assume adjacent labels to use the same space
                for label in section['labels'][::-1]:
                    if label['length'] == 0:
                        label['length'] = length
                    else:
                        break

            elif token in macros.keys():
                macro_text = '\n'.join(macros[token]) + '\n'
                for i, p in enumerate(params):
                    macro_text = macro_text.replace('\\'+str(i+1),p)
                macro_text = macro_text.split('\n')
                macro_sections = read_bss_sections(macro_text, sections=sections, section=section, address=address)
                section = macro_sections[-1]
                address = section['labels'][-1]['address'] + section['labels'][-1]['length']
                del macro_sections[-1]

    sections.append(section)
    return sections

def constants_to_dict(constants):
    return dict((eval(rgbasm_to_py(constant[constant.find('EQU')+3:constant.find(';')])), constant[:constant.find('EQU')].strip()) for constant in constants)

def scrape_constants(text):
    if type(text) is not list:
        text = text.split('\n')
    return constants_to_dict([line for line in text if 'EQU' in line[:line.find(';')]])

def read_constants(filepath):
    """
    Load lines from a file and call scrape_constants.
    """
    lines = []
    if os.path.exists(filepath):
        with open(filepath, "r") as file_handler:
            lines = file_handler.readlines()

    constants = scrape_constants(lines)
    return constants

class WRAMProcessor(object):
    """
    RGBDS BSS section and constant parsing.
    """

    def __init__(self, config):
        """
        Setup for WRAM parsing.
        """
        self.config = config

        self.paths = {}

        if hasattr(self.config, "wram"):
            self.paths["wram"] = self.config.wram
        else:
            self.paths["wram"] = os.path.join(self.config.path, "wram.asm")

        if hasattr(self.config, "hram"):
            self.paths["hram"] = self.config.hram
        else:
            self.paths["hram"] = os.path.join(self.config.path, "hram.asm")

        if hasattr(self.config, "gbhw"):
            self.paths["gbhw"] = self.config.gbhw
        else:
            self.paths["gbhw"] = os.path.join(self.config.path, "gbhw.asm")

    def initialize(self):
        """
        Read constants.
        """
        self.setup_wram_sections()
        self.setup_wram_labels()
        self.setup_hram_constants()
        self.setup_gbhw_constants()

        self.reformat_wram_labels()

    def read_wram_sections(self):
        """
        Opens the wram file and calls read_bss_sections.
        """
        wram_content = None
        wram_file_path = self.paths["wram"]

        with open(wram_file_path, "r") as wram:
            wram_content = wram.readlines()

        wram_sections = read_bss_sections(wram_content)
        return wram_sections

    def setup_wram_sections(self):
        """
        Call read_wram_sections and set a variable.
        """
        self.wram_sections = self.read_wram_sections()
        return self.wram_sections

    def setup_wram_labels(self):
        """
        Make wram labels based on self.wram_sections as input.
        """
        self.wram_labels = make_wram_labels(self.wram_sections)
        return self.wram_labels

    def read_hram_constants(self):
        """
        Read constants from hram.asm using read_constants.
        """
        hram_constants = read_constants(self.paths["hram"])
        return hram_constants

    def setup_hram_constants(self):
        """
        Call read_hram_constants and set a variable.
        """
        self.hram_constants = self.read_hram_constants()
        return self.hram_constants

    def read_gbhw_constants(self):
        """
        Read constants from gbhw.asm using read_constants.
        """
        gbhw_constants = read_constants(self.paths["gbhw"])
        return gbhw_constants

    def setup_gbhw_constants(self):
        """
        Call read_gbhw_constants and set a variable.
        """
        self.gbhw_constants = self.read_gbhw_constants()
        return self.gbhw_constants

    def reformat_wram_labels(self):
        """
        Flips the wram_labels dictionary the other way around to access
        addresses by label.
        """
        self.wram = {}

        for (address, labels) in self.wram_labels.iteritems():
            for label in labels:
                self.wram[label] = address
