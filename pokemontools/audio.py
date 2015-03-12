# coding: utf-8

import os

from math import ceil

from song_names import song_names
from sfx_names import sfx_names
from cry_names import cry_names

from gbz80disasm import get_global_address, get_local_address
from labels import line_has_label
from crystal import music_classes as sound_classes
from crystal import (
    Command,
    SingleByteParam,
    MultiByteParam,
    PointerLabelParam,
    load_rom,
)

rom = load_rom()
rom = bytearray(rom)

import configuration
conf = configuration.Config()


def is_comment(asm):
	return asm.startswith(';')

def asm_sort(asm_def):
	"""
	Sort key for asm lists.

	Usage:
		list.sort(key=asm_sort)
		sorted(list, key=asm_sort)
	"""
	address, asm, last_address = asm_def
	return (
		address,
		last_address,
		not is_comment(asm),
		not line_has_label(asm),
		asm
	)

def sort_asms(asms):
	"""
	Sort and remove duplicates from an asm list.

	Format: [(address, asm, last_address), ...]
	"""
	asms = sorted(set(asms), key=asm_sort)
	trimmed = []
	address, last_address = None, None
	for asm in asms:
		if asm == (address, asm[1], last_address) and last_address - address:
			continue
		trimmed += [asm]
		address, last_address = asm[0], asm[2]
	return trimmed

def insert_asm_incbins(asms):
	"""
	Insert baserom incbins between address gaps in asm lists.
	"""
	new_asms = []
	for i, asm in enumerate(asms):
		new_asms += [asm]
		if i + 1 < len(asms):
			last_address, next_address = asm[2], asms[i + 1][0]
			if last_address < next_address and last_address / 0x4000 == next_address / 0x4000:
				new_asms += [generate_incbin_asm(last_address, next_address)]
	return new_asms

def generate_incbin_asm(start_address, end_address):
	"""
	Return baserom incbin text for an address range.

	Format: 'INCBIN "baserom.gbc", {start}, {end} - {start}'
	"""
	incbin = (
		start_address,
		'\nINCBIN "baserom.gbc", $%x, $%x - $%x\n\n' % (
			start_address, end_address, start_address
		),
		end_address
	)
	return incbin

def generate_label_asm(label, address):
	"""
	Return label definition text at a given address.

	Format: '{label}: ; {address}'
	"""
	label_text = '%s: ; %x' % (label, address)
	return (address, label_text, address)


class NybbleParam:
	size = 0.5
	byte_type = 'dn'
	which = None

	def __init__(self, address, name):
		if self.which == None:
			self.which = {0.0: 'lo', 0.5: 'hi'}[address % 1]
		self.address = int(address)
		self.name = name
		self.parse()

	def parse(self):
		self.nybble = (rom[self.address] >> {'lo': 0, 'hi': 4}[self.which]) & 0xf

	def to_asm(self):
		return '%d' % self.nybble

	@staticmethod
	def from_asm(value):
		return value

class HiNybbleParam(NybbleParam):
	which = 'hi'

class LoNybbleParam(NybbleParam):
	which = 'lo'

class PitchParam(HiNybbleParam):
	def to_asm(self):
		"""E and B cant be sharp"""
		if self.nybble == 0:
			pitch = '__'
		else:
			pitch = 'CCDDEFFGGAAB'[(self.nybble - 1)]
			if self.nybble in [2, 4, 7, 9, 11]:
				pitch += '#'
			else:
				pitch += '_'
		return pitch

class NoteDurationParam(LoNybbleParam):
	def to_asm(self):
		self.nybble += 1
		return LoNybbleParam.to_asm(self)

	@staticmethod
	def from_asm(value):
		value = str(int(value) - 1)
		return LoNybbleParam.from_asm(value)

class Note(Command):
	macro_name = "note"
	size = 0
	end = False
	param_types = {
		0: {"name": "pitch", "class": PitchParam},
		1: {"name": "duration", "class": NoteDurationParam},
	}
	allowed_lengths = [2]
	override_byte_check = True
	is_rgbasm_macro = True

	def parse(self):
		self.params = []
		byte = rom[self.address]
		current_address = self.address
		size = 0
		for (key, param_type) in self.param_types.items():
			name = param_type["name"]
			class_ = param_type["class"]

			# by making an instance, obj.parse() is called
			obj = class_(address=int(current_address), name=name)
			self.params += [obj]

			current_address += obj.size
			size += obj.size

			# can't fit bytes into nybbles
			if obj.size > 0.5:
				if current_address % 1:
					current_address = int(ceil(current_address))
				if size % 1:
					size = int(ceil(size))

		self.params = dict(enumerate(self.params))

		# obj sizes were 0.5, but we're working with ints
		current_address = int(ceil(current_address))
		self.size += int(ceil(size))

		self.last_address = current_address
		return True


class SoundCommand(Note):
	macro_name = "sound"
	end = False
	param_types = {
		0: {"name": "duration", "class": SingleByteParam},
		1: {"name": "intensity", "class": SingleByteParam},
		2: {"name": "frequency", "class": MultiByteParam},
	}
	allowed_lengths = [3]
	override_byte_check = True
	is_rgbasm_macro = False

class Noise(SoundCommand):
	macro_name = "noise"
	param_types = {
		0: {"name": "duration", "class": SingleByteParam},
		1: {"name": "intensity", "class": SingleByteParam},
		2: {"name": "frequency", "class": SingleByteParam},
	}


class Channel:
	"""A sound channel data parser."""

	def __init__(self, address, channel=1, base_label=None, sfx=False, label=None, used_labels=[]):
		self.start_address = address
		self.address = address
		self.channel = channel

		self.base_label = base_label
		if self.base_label == None:
			self.base_label = 'Sound_' + hex(self.start_address)

		self.label = label
		if self.label == None:
			self.label = self.base_label

		self.sfx = sfx

		self.used_labels = used_labels
		self.labels = []
		used_label = generate_label_asm(self.label, self.start_address)
		self.labels += [used_label]
		self.used_labels += [used_label]

		self.output = []
		self.parse()

	def parse(self):
		noise = False
		done = False
		while not done:
			cmd = rom[self.address]

			class_ = self.get_sound_class(cmd)(address=self.address, channel=self.channel)

			# notetype loses the intensity param on channel 4
			if class_.macro_name == 'notetype':
				if self.channel in [4, 8]:
					class_.size -= 1
					del class_.params[class_.size - 1]

			# togglenoise only has a param when toggled on
			elif class_.macro_name in ['togglenoise', 'sfxtogglenoise']:
				if noise:
					class_.size -= 1
					del class_.params[class_.size - 1]
				noise = not noise

			elif class_.macro_name == 'togglesfx':
				self.sfx = not self.sfx

			asm = class_.to_asm()

			# label any jumps or calls
			for key, param in class_.param_types.items():
				if param['class'] == PointerLabelParam:
					label_address = class_.params[key].parsed_address
					label = '%s_branch_%x' % (
						self.base_label,
						label_address
					)
					self.labels += [generate_label_asm(label, label_address)]
					asm = asm.replace(
						'$%x' % (get_local_address(label_address)),
						label
					)

			self.output += [(self.address, '\t' + asm, self.address + class_.size)]
			self.address += class_.size

			done = class_.end
			# infinite loops are enders
			if class_.macro_name == 'loopchannel':
				if class_.params[0].byte == 0:
					done = True

			# dumb safety checks
			if (
				self.address >= len(rom) or
				self.address / 0x4000 != self.start_address / 0x4000
			) and not done:
				done = True
				raise Exception, self.label + ': reached the end of the bank without finishing!'

		self.output += [(self.address, '; %x\n' % self.address, self.address)]

		# parse any other branches too
		self.labels = list(set(self.labels))
		for address, asm, last_address in self.labels:
			if (
				address >= self.address
				and (address, asm, last_address) not in self.used_labels
			):

				self.used_labels += [(address, asm, last_address)]
				sub = Channel(
					address=address,
					channel=self.channel,
					base_label=self.base_label,
					label=asm.split(':')[0],
					used_labels=self.used_labels,
					sfx=self.sfx,
				)
				self.output += sub.output
				self.labels += sub.labels

	def to_asm(self):
		output = sort_asms(self.output + self.labels)
		text = ''
		for i, (address, asm, last_address) in enumerate(output):
			if line_has_label(asm):
				# dont print labels for empty chunks
				for (address_, asm_, last_address_) in output[i:]:
					if not line_has_label(asm_):
						text += '\n' + asm + '\n'
						break
			else:
				text += asm + '\n'
		text += '; %x' % (last_address) + '\n'
		return text

	def get_sound_class(self, i):
		for class_ in sound_classes:
			if class_.id == i:
				return class_
		if self.sfx:
			if self.channel in [4, 8]:
				return Noise
			return SoundCommand
		return Note


class Sound:
	"""
	Interprets a sound data header and its channel data.
	"""

	def __init__(self, address, name='', sfx=False):
		self.start_address = address
		self.bank = address / 0x4000
		self.address = address
		self.sfx = sfx

		self.name = name
		self.base_label = 'Sound_%x' % self.start_address
		if self.name != '':
			self.base_label = self.name

		self.output = []
		self.labels = []
		self.asms = []
		self.parse()


	def parse_header(self):
		self.num_channels = (rom[self.address] >> 6) + 1
		self.channels = []
		for ch in xrange(self.num_channels):
			current_channel = (rom[self.address] & 0xf) + 1
			self.address += 1
			address = rom[self.address] + rom[self.address + 1] * 0x100
			address = self.bank * 0x4000 + address % 0x4000
			self.address += 2
			channel = Channel(address, current_channel, self.base_label, self.sfx, label='%s_Ch%d' % (self.base_label, current_channel))
			self.channels += [(current_channel, channel)]
			self.labels += channel.labels


	def make_header(self):
		asms = []

		for i, (num, channel) in enumerate(self.channels):
			channel_id = num - 1
			if i == 0:
				channel_id += (len(self.channels) - 1) << 6
			address = self.start_address + i * 3
			text = '\tdbw $%.2x, %s_Ch%d' % (channel_id, self.base_label, num)
			asms += [(address, text, address + 3)]

		comment_text = '; %x\n' % self.address
		asms += [(self.address, comment_text, self.address)]
		return asms


	def parse(self):
		self.parse_header()

		asms = []

		asms += [generate_label_asm(self.base_label, self.start_address)]
		asms += self.make_header()

		for num, channel in self.channels:
			asms += channel.output

		asms = sort_asms(asms)
		_, _, self.last_address = asms[-1]
		asms += [(self.last_address,'; %x\n' % self.last_address, self.last_address)]

		self.asms += asms


	def to_asm(self, labels=[]):
		"""insert outside labels here"""
		asms = self.asms

		# Incbin trailing commands that didnt get picked up
		asms = insert_asm_incbins(asms)

		for label in self.labels + labels:
			if self.start_address <= label[0] < self.last_address:
				asms += [label]

		return '\n'.join(asm for address, asm, last_address in sort_asms(asms))


def read_bank_address_pointer(addr):
	"""
	Return a bank and address at a given rom offset.
	"""
	bank, address = rom[addr], rom[addr+1] + rom[addr+2] * 0x100
	return get_global_address(address, bank)
	

def dump_sounds(origin, names, base_label='Sound_'):
	"""
	Dump sound data from a pointer table.
	"""

	# Some songs share labels.
	# Do an extra pass to grab shared labels before writing output.

	sounds = []
	labels = []
	addresses = []
	for i, name in enumerate(names):
		sound_at = read_bank_address_pointer(origin + i * 3)
		sound = Sound(sound_at, base_label + name)
		sounds += [sound]
		labels += sound.labels
		addresses += [sound_at]
	addresses.sort()

	outputs = []
	for i, name in enumerate(names):
		sound = sounds[i]

		# Place a dummy asm at the end to catch end-of-file incbins.
		index = addresses.index(sound.start_address) + 1
		if index < len(addresses):
			next_address = addresses[index]
			max_command_length = 5
			if next_address - sound.last_address <= max_command_length:
				sound.asms += [(next_address, '', next_address)]

		output = sound.to_asm(labels) + '\n'
		filename = name.lower() + '.asm'
		outputs += [(filename, output)]

	return outputs


def export_sounds(origin, names, path, base_label='Sound_'):
	for filename, output in dump_sounds(origin, names, base_label):
		with open(os.path.join(path, filename), 'w') as out:
			out.write(output)


def dump_sound_clump(origin, names, base_label='Sound_', sfx=False):
	"""
	Some sounds are grouped together and/or share most components.
	These can't reasonably be split into separate files for each sound.
	"""

	output = []
	for i, name in enumerate(names):
		sound_at = read_bank_address_pointer(origin + i * 3)
		sound = Sound(sound_at, base_label + name, sfx)
		output += sound.asms + sound.labels
	output = sort_asms(output)
	return output


def export_sound_clump(origin, names, path, base_label='Sound_', sfx=False):
	"""
	Dump and export a sound clump to a given file path.
	"""
	output = dump_sound_clump(origin, names, base_label, sfx)
	output = insert_asm_incbins(output)
	with open(path, 'w') as out:
		out.write('\n'.join(asm for address, asm, last_address in output))


def dump_crystal_music():
	"""
	Dump and export Pokemon Crystal music to files in audio/music/.
	"""
	export_sounds(0xe906e, song_names, os.path.join(conf.path, 'audio', 'music'), 'Music_')

def generate_crystal_music_pointers():
	"""
	Return a pointer table for Pokemon Crystal music.
	"""
	return '\n'.join('\tdbw BANK({0}), {0}'.format('Music_' + label) for label in song_names)

def dump_crystal_sfx():
	"""
	Dump and export Pokemon Crystal sound effects to audio/sfx.asm and audio/sfx_crystal.asm.
	"""
	sfx_pointers_address = 0xe927c

	sfx = dump_sound_clump(sfx_pointers_address, sfx_names, 'Sfx_', sfx=True)

	unknown_sfx = Sound(0xf0d5f, 'UnknownSfx', sfx=True)
	sfx += unknown_sfx.asms + unknown_sfx.labels

	sfx = sort_asms(sfx)
	sfx = insert_asm_incbins(sfx)

	# Split up sfx and crystal sfx.
	crystal_sfx = None
	for i, asm in enumerate(sfx):
		address, content, last_address = asm
		if i + 1 < len(sfx):
			next_address = sfx[i + 1][0]
			if next_address > last_address and last_address / 0x4000 != next_address / 0x4000:
				crystal_sfx = sfx[i + 1:]
				sfx = sfx[:i + 1]
				break
	if crystal_sfx:
		path = os.path.join(conf.path, 'audio', 'sfx_crystal.asm')
		with open(path, 'w') as out:
			out.write('\n'.join(asm for address, asm, last_address in crystal_sfx))

	path = os.path.join(conf.path, 'audio', 'sfx.asm')
	with open(path, 'w') as out:
		out.write('\n'.join(asm for address, asm, last_address in sfx))


def generate_crystal_sfx_pointers():
	"""
	Return a pointer table for Pokemon Crystal sound effects.
	"""
	lines = ['\tdbw BANK({0}), {0}'.format('Sfx_' + label) for label in sfx_names]
	first_crystal_sfx = 190
	lines = lines[:first_crystal_sfx] + ['\n; Crystal adds the following SFX:\n'] + lines[first_crystal_sfx:]
	return '\n'.join(lines)

def dump_crystal_cries():
	"""
	Dump and export Pokemon Crystal cries to audio/cries.asm.
	"""
	path = os.path.join(conf.path, 'audio', 'cries.asm')

	cries = dump_sound_clump(0xe91b0, cry_names, 'Cry_', sfx=True)

	# Unreferenced cry channel data.
	cry_2e_ch8      = Channel(0xf3134, channel=8, sfx=True).output + [generate_label_asm('Cry_2E_Ch8',      0xf3134)]
	unknown_cry_ch5 = Channel(0xf35d3, channel=5, sfx=True).output + [generate_label_asm('Unknown_Cry_Ch5', 0xf35d3)]
	unknown_cry_ch6 = Channel(0xf35ee, channel=6, sfx=True).output + [generate_label_asm('Unknown_Cry_Ch6', 0xf35ee)]
	unknown_cry_ch8 = Channel(0xf3609, channel=8, sfx=True).output + [generate_label_asm('Unknown_Cry_Ch8', 0xf3609)]

	cries += cry_2e_ch8 + unknown_cry_ch5 + unknown_cry_ch6 + unknown_cry_ch8
	cries = sort_asms(cries)
	cries = insert_asm_incbins(cries)

	with open(path, 'w') as out:
		out.write('\n'.join(asm for address, asm, last_address in cries))


def generate_crystal_cry_pointers():
	"""
	Return a pointer table for Pokemon Crystal cries.
	"""
	return '\n'.join('\tdbw BANK({0}), {0}'.format('Cry_' + label) for label in cry_names)


if __name__ == '__main__':
	dump_crystal_music()
	dump_crystal_cries()
	dump_crystal_sfx()

