# coding: utf-8
"""
RGBDS BSS section and constant parsing.
"""

import os
import os.path


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

class BSSReader:
    """
    Read rgbasm BSS/WRAM sections and associate labels with addresses.
    Also reads constants/variables, even in macros.
    """
    sections  = []
    section   = None
    address   = None
    macros    = {}
    constants = {}

    section_types = {
        'VRAM':  0x8000,
        'SRAM':  0xa000,
        'WRAM0': 0xc000,
        'WRAMX': 0xd000,
        'HRAM':  0xff80,
    }

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def read_bss_line(self, l):
        parts = l.strip().split(' ')
        token = parts[0].strip()
        params = ' '.join(parts[1:]).split(',')

        if token in ['ds', 'db', 'dw']:
            if any(params):
                length = eval(rgbasm_to_py(params[0]), self.constants.copy())
            else:
                length = {'ds': 1, 'db': 1, 'dw': 2}[token]
            self.address += length
            # assume adjacent labels to use the same space
            for label in self.section['labels'][::-1]:
                if label['length'] == 0:
                    label['length'] = length
                else:
                    break

        elif token in self.macros.keys():
            macro_text = '\n'.join(self.macros[token]) + '\n'
            for i, p in enumerate(params):
                macro_text = macro_text.replace('\\'+str(i+1),p)
            macro_text = macro_text.split('\n')
            macro_reader = BSSReader(
                sections  = list(self.sections),
                section   = dict(self.section),
                address   = self.address,
                constants = self.constants,
            )
            macro_sections = macro_reader.read_bss_sections(macro_text)
            self.section = macro_sections[-1]
            if self.section['labels']:
                self.address = self.section['labels'][-1]['address'] + self.section['labels'][-1]['length']


    def read_bss_sections(self, bss):

        if self.section is None:
            self.section = {
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
            split_line = line.split()
            split_line_upper = map(str.upper, split_line)

            if not line:
                pass

            elif line[-4:].upper() == 'ENDM':
                macro = False
                macro_name = None

            elif macro:
                self.macros[macro_name] += [line]

            elif line[-5:].upper() == 'MACRO':
                macro_name = line.split(':')[0]
                macro = True
                self.macros[macro_name] = []

            elif 'INCLUDE' == line[:7].upper():
                filename = line.split('"')[1]
                if os.path.exists("src/"):
                    self.read_bss_sections(open("src/" + filename).readlines())
                else:
                    self.read_bss_sections(open(filename).readlines())

            elif 'SECTION' == line[:7].upper():
                if self.section: # previous
                    self.sections += [self.section]

                section_def = line.split(',')
                name  = section_def[0].split('"')[1]
                type_ = section_def[1].strip()
                if len(section_def) > 2:
                    bank = bracket_value(section_def[2])
                else:
                    bank = None

                if '[' in type_:
                    self.address = int(rgbasm_to_py(bracket_value(type_)), 16)
                else:
                    if self.address == None or bank != self.section['bank'] or self.section['type'] != type_:
                        self.address = self.section_types.get(type_, self.address)
                    # else: keep going from this address

                self.section = {
                    'name': name,
                    'type': type_,
                    'bank': bank,
                    'start': self.address,
                    'labels': [],
                }

            elif ':' in line:
                # rgbasm allows labels without :, but prefer convention
                label = line[:line.find(':')]
                if '\\' in label:
                    raise Exception, line + ' ' + label
                if ';' not in label:
                    section_label = {
                        'label': label,
                        'address': self.address,
                        'length': 0,
                    }
                    self.section['labels'] += [section_label]
                    self.read_bss_line(line.split(':')[-1])

            elif any(x in split_line_upper for x in ['EQU', '=', 'SET']): # TODO: refactor
                for x in ['EQU', '=', 'SET']:
                    if x in split_line_upper:
                        index = split_line_upper.index(x)
                        real = split_line[index]
                        name, value = map(' '.join, [split_line[:index], split_line[index+1:]])
                        value = rgbasm_to_py(value)
                        self.constants[name] = eval(value, self.constants.copy())

            else:
                self.read_bss_line(line)

        self.sections += [self.section]
        return self.sections

def read_bss_sections(bss):
    reader = BSSReader()
    return reader.read_bss_sections(bss)


def constants_to_dict(constants):
    """Deprecated. Use BSSReader."""
    return dict((eval(rgbasm_to_py(constant[constant.find('EQU')+3:constant.find(';')])), constant[:constant.find('EQU')].strip()) for constant in constants)

def scrape_constants(text):
    if type(text) is not list:
        text = text.split('\n')
    bss = BSSReader()
    bss.read_bss_sections(text)
    constants = bss.constants
    return {v: k for k, v in constants.items()}

def read_constants(filepath):
    """
    Load lines from a file and grab any constants using BSSReader.
    """
    lines = []
    if os.path.exists(filepath):
        with open(filepath, "r") as file_handler:
            lines = file_handler.readlines()
    return scrape_constants(lines)

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

        if os.path.exists("src/"):
            path = "src/"
        else:
            path = ""

        if hasattr(self.config, "wram"):
            self.paths["wram"] = self.config.wram
        else:
            self.paths["wram"] = os.path.join(self.config.path, path + "wram.asm")

        if hasattr(self.config, "hram"):
            self.paths["hram"] = self.config.hram
        else:
            self.paths["hram"] = os.path.join(self.config.path, path + "hram.asm")

        if hasattr(self.config, "gbhw"):
            self.paths["gbhw"] = self.config.gbhw
        else:
            self.paths["gbhw"] = os.path.join(self.config.path, path + "gbhw.asm")

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
