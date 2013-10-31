# coding: utf-8

import os

from math import ceil

from gbz80disasm import get_global_address, get_local_address

import crystal
from crystal import music_classes as sound_classes
from crystal import Command

from crystal import load_rom
rom = load_rom()
rom = bytearray(rom)

import config
conf = config.Config()


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

class HiNybbleParam(NybbleParam):
	which = 'hi'
	def to_asm(self):
		return '%d' % self.nybble

class LoNybbleParam(NybbleParam):
	which = 'lo'
	def to_asm(self):
		return '%d' % self.nybble

class PitchParam(HiNybbleParam):
	def to_asm(self):
		if self.nybble == 0:
			pitch = 'Rst'
		else:
			pitch = 'CDEFGAB'[(self.nybble - 1) / 2]
			if not self.nybble & 1:
				pitch += '#'
		return pitch


class Note(Command):
	macro_name = "note"
	size = 0
	end = False
	param_types = {
		0: {"name": "pitch", "class": PitchParam},
		1: {"name": "duration", "class": LoNybbleParam},
	}
	allowed_lengths = [2]

	def parse(self):
		self.params = []
		byte = rom[self.address]
		current_address = self.address
		for (key, param_type) in self.param_types.items():
			name = param_type["name"]
			class_ = param_type["class"]

			# by making an instance, obj.parse() is called
			obj = class_(address=int(current_address), name=name)
			self.params += [obj]

			current_address += obj.size
			self.size += obj.size

		self.params = dict(enumerate(self.params))

		# obj sizes were 0.5, but were working with ints
		current_address = int(ceil(current_address))
		self.size = int(ceil(self.size))

		self.last_address = current_address
		return True



class Channel:
	"""A sound channel data parser."""

	def __init__(self, address, channel=1, base_label='Sound'):
		self.start_address = address
		self.address = address
		self.channel = channel
		self.base_label = base_label
		self.output = []
		self.parse()

	def parse(self):
		noise = False
		done = False
		while not done:
			cmd = rom[self.address]

			class_ = self.get_sound_class(cmd)(address=self.address)

			# notetype loses the intensity param on channel 4
			if class_.macro_name == 'notetype':
				if self.channel in [4, 8]:
					class_.size -= 1
					class_.params = dict(class_.params.items()[:-1])

			# togglenoise only has a param when toggled on
			elif class_.macro_name in ['togglenoise', 'sfxtogglenoise']:
				if noise:
					class_.size -= 1
					class_.params = dict(class_.params.items()[:-1])
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
						'%s: ; %x' % (label, label_address)
					)
					if label_output not in self.output:
						self.output += [label_output]
					asm = asm.replace(
						'$%x' % (get_local_address(label_address)),
						label
					)

			self.output += [(self.address, '\t' + asm)]
			self.address += class_.size

			done = class_.end
			# infinite loops are enders
			if class_.macro_name == 'loopchannel':
				if class_.params[0].byte == 0:
					done = True

			# keep going past enders if theres more to parse
			if any(self.address <= address for address, asm in self.output):
				if done:
					self.output += [(self.address, '; %x' % self.address)]
				done = False

			# dumb safety checks
			if (
				self.address >= len(rom) or
				self.address / 0x4000 != self.start_address / 0x4000
			) and not done:
				done = True
				raise Exception, 'reached the end of the bank without finishing!'

	def to_asm(self):
		self.output = sorted(
			self.output,
			# comment then label then asm
			key=lambda (x, y):(x, not y.startswith(';'), ':' not in y)
		)
		text = ''
		for i, (address, asm) in enumerate(self.output):
			if ':' in asm:
				# dont print labels for empty chunks
				for (x, y) in self.output[i:]:
					if ':' not in y:
						text += '\n' + asm + '\n'
						break
			else:
				text += asm + '\n'
		text += '; %x' % (address + 1) + '\n'
		return text

	def get_sound_class(self, i):
		for class_ in sound_classes:
			if class_.id == i:
				return class_
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

	def to_asm(self):
		asms = {}

		text = ''
		text += '%s: ; %x' % (self.base_label, self.start_address) + '\n'
		for num, channel in self.channels:
			text += '\tchannel %d, %s_Ch%d' % (num, self.base_label, num) + '\n'
		text += '; %x' % self.address + '\n'
		asms[self.start_address] = text

		text = ''
		for ch, (num, channel) in enumerate(self.channels):
			text += '%s_Ch%d: ; %x' % (
				self.base_label,
				num,
				channel.start_address
			) + '\n'
			# stack labels at the same address
			if ch < len(self.channels) - 1:
				next_channel = self.channels[ch + 1][1]
				if next_channel.start_address == channel.start_address:
					continue
			text += channel.to_asm()
			asms[channel.start_address] = text
			text = ''

		return '\n'.join(asm for address, asm in sorted(asms.items()))


def dump_sounds(origin, names, path, base_label='Sound_'):
	"""Dump sound data from a pointer table."""
	for i, name in enumerate(names):
		addr = origin + i * 3
		bank, address = rom[addr], rom[addr+1] + rom[addr+2] * 0x100
		sound_at = get_global_address(address, bank)

		sound = Sound(sound_at, base_label + name)
		output = sound.to_asm()

		filename = name.lower() + '.asm'
		with open(os.path.join(path, filename), 'w') as out:
			out.write(output)

def dump_crystal_music():
	from song_names import song_names
	dump_sounds(0xe906e, song_names, os.path.join(conf.path, 'audio', 'music'), 'Music_')

def dump_crystal_sfx():
	from sfx_names import sfx_names
	dump_sounds(0xe927c, sfx_names, os.path.join(conf.path, 'audio', 'sfx'), 'Sfx_')


if __name__ == '__main__':
	dump_crystal_music()
	dump_crystal_sfx()

