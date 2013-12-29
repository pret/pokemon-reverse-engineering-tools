# coding: utf-8

import os

from math import ceil

from gbz80disasm import get_global_address, get_local_address

import crystal
from crystal import music_classes as sound_classes

from crystal import (
    Command,
    SingleByteParam,
    MultiByteParam,
    load_rom,
)

rom = load_rom()
rom = bytearray(rom)

import configuration
conf = configuration.Config()


def is_label(asm):
	return ':' in asm

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
		not is_label(asm),
		asm
	)

def sort_asms(asms):
	"""
	Sort and remove duplicates from an asm list.

	Format: [(address, asm, last_address), ...]
	"""
	return sorted(set(asms), key=asm_sort)


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


class Noise(Note):
	macro_name = "noise"
	end = False
	param_types = {
		0: {"name": "duration", "class": LoNybbleParam},
		1: {"name": "intensity", "class": SingleByteParam},
		2: {"name": "frequency", "class": MultiByteParam},
	}
	allowed_lengths = [2,3]
	override_byte_check = True
	is_rgbasm_macro = False



class Channel:
	"""A sound channel data parser."""

	def __init__(self, address, channel=1, base_label='Sound'):
		self.start_address = address
		self.address = address
		self.channel = channel
		self.base_label = base_label
		self.output = []
		self.labels = []
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

			asm = class_.to_asm()

			# label any jumps or calls
			for key, param in class_.param_types.items():
				if param['class'] == crystal.PointerLabelParam:
					label_address = class_.params[key].parsed_address
					label = '%s_branch_%x' % (
						self.base_label,
						label_address
					)
					label_output = (
						label_address,
						'\n%s: ; %x' % (label, label_address),
						label_address
					)
					self.labels += [label_output]
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

			# keep going past enders if theres more to parse
			if any(self.address <= address for address, asm, last_address in self.output + self.labels):
				if done:
					self.output += [(self.address, '; %x' % self.address, self.address)]
				done = False

			# dumb safety checks
			if (
				self.address >= len(rom) or
				self.address / 0x4000 != self.start_address / 0x4000
			) and not done:
				done = True
				raise Exception, 'reached the end of the bank without finishing!'

	def to_asm(self):
		output = sort_asms(self.output + self.labels)
		text = ''
		for i, (address, asm, last_address) in enumerate(output):
			if is_label(asm):
				# dont print labels for empty chunks
				for (address_, asm_, last_address_) in output[i:]:
					if not is_label(asm_):
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
		if self.channel == 8: return Noise
		return Note


class Sound:
	"""Interprets a sound data header."""

	def __init__(self, address, name=''):
		self.start_address = address
		self.bank = address / 0x4000
		self.address = address

		self.name = name
		self.base_label = 'Sound_%x' % self.start_address
		if self.name != '':
			self.base_label = self.name

		self.output = []
		self.labels = []
		self.asms = []
		self.parse()

	def parse(self):
		self.num_channels = (rom[self.address] >> 6) + 1
		self.channels = []
		for ch in xrange(self.num_channels):
			current_channel = (rom[self.address] & 0xf) + 1
			self.address += 1
			address = rom[self.address] + rom[self.address + 1] * 0x100
			address = self.bank * 0x4000 + address % 0x4000
			self.address += 2
			channel = Channel(address, current_channel, self.base_label)
			self.channels += [(current_channel, channel)]

			self.labels += channel.labels

			label_text = '\n%s_Ch%d: ; %x' % (
				self.base_label,
				current_channel,
				channel.start_address
			)
			label_output = (channel.start_address, label_text, channel.start_address)
			self.labels += [label_output]

		asms = []

		text = '%s: ; %x' % (self.base_label, self.start_address) + '\n'
		for i, (num, channel) in enumerate(self.channels):
			channel_id = num - 1
			if i == 0:
				channel_id += (len(self.channels) - 1) << 6
			text += '\tdbw $%.2x, %s_Ch%d' % (channel_id, self.base_label, num) + '\n'
		text += '; %x\n' % self.address
		asms += [(self.start_address, text, self.start_address + len(self.channels) * 3)]

		for num, channel in self.channels:
			asms += channel.output

		asms = sort_asms(asms)
		self.last_address = asms[-1][2]
		asms += [(self.last_address,'; %x' % self.last_address, self.last_address)]

		self.asms += asms

	def to_asm(self, labels=[]):
		"""insert outside labels here"""
		asms = self.asms

		# incbins dont really count as parsed data
		incbins = []
		for i, (address, asm, last_address) in enumerate(asms):
			if i + 1 < len(asms):
                                next_address = asms[i + 1][0]
				if last_address != next_address:
					incbins += [(last_address, 'INCBIN "baserom.gbc", $%x, $%x - $%x' % (last_address, next_address, last_address), next_address)]
		asms += incbins
		for label in self.labels + labels:
			if self.start_address <= label[0] < self.last_address:
				asms += [label]

		return '\n'.join(asm for address, asm, last_address in sort_asms(asms))


def read_bank_address_pointer(addr):
	bank, address = rom[addr], rom[addr+1] + rom[addr+2] * 0x100
	return get_global_address(address, bank)
	

def dump_sounds(origin, names, base_label='Sound_'):
	"""Dump sound data from a pointer table."""

	# first pass to grab labels and boundaries
	labels = []
	addresses = []
	for i, name in enumerate(names):
		sound_at = read_bank_address_pointer(origin + i * 3)
		sound = Sound(sound_at, base_label + name)
		labels += sound.labels
		addresses += [(sound.start_address, sound.last_address)]
	addresses = sorted(addresses)

	outputs = []
	for i, name in enumerate(names):
		sound_at = read_bank_address_pointer(origin + i * 3)
		sound = Sound(sound_at, base_label + name)
		output = sound.to_asm(labels) + '\n'
		# incbin trailing commands that didnt get picked up
		index = addresses.index((sound.start_address, sound.last_address))
		if index + 1 < len(addresses):
			next_address = addresses[index + 1][0]
			if 5 > next_address - sound.last_address > 0:
				if next_address / 0x4000 == sound.last_address / 0x4000:
					output += '\nINCBIN "baserom.gbc", $%x, $%x - $%x\n' % (sound.last_address, next_address, sound.last_address)

		filename = name.lower() + '.asm'
		outputs += [(filename, output)]
	return outputs


def export_sounds(origin, names, path, base_label='Sound_'):
	for filename, output in dump_sounds(origin, names, base_label):
		with open(os.path.join(path, filename), 'w') as out:
			out.write(output)


def dump_sound_clump(origin, names, base_label='Sound_'):
	"""some sounds are grouped together and/or share most components.
	these can't reasonably be split into files for each sound."""

	output = []
	for i, name in enumerate(names):
		sound_at = read_bank_address_pointer(origin + i * 3)
		sound = Sound(sound_at, base_label + name)
		output += sound.asms + sound.labels
	output = sort_asms(output)
	return output


def export_sound_clump(origin, names, path, base_label='Sound_'):
	output = dump_sound_clump(origin, names, base_label)
	with open(path, 'w') as out:
		out.write('\n'.join(asm for address, asm, last_address in output))


def dump_crystal_music():
	from song_names import song_names
	export_sounds(0xe906e, song_names, os.path.join(conf.path, 'audio', 'music'), 'Music_')

def generate_crystal_music_pointers():
	from song_names import song_names
	return '\n'.join('\tdbw BANK({0}), {0}'.format('Music_' + label) for label in song_names)

def dump_crystal_sfx():
	from sfx_names import sfx_names
	export_sound_clump(0xe927c, sfx_names, os.path.join(conf.path, 'audio', 'sfx.asm'), 'Sfx_')

def generate_crystal_sfx_pointers():
	from sfx_names import sfx_names
	return '\n'.join('\tdbw BANK({0}), {0}'.format('Sfx_' + label) for label in sfx_names)

def dump_crystal_cries():
	from cry_names import cry_names
	export_sound_clump(0xe91b0, cry_names, os.path.join(conf.path, 'audio', 'cries.asm'), 'Cry_')

def generate_crystal_cry_pointers():
	from cry_names import cry_names
	return '\n'.join('\tdbw BANK({0}), {0}'.format('Cry_' + label) for label in cry_names)


if __name__ == '__main__':
	dump_crystal_music()

