# coding: utf-8

import os
from new import classobj

import configuration
conf = configuration.Config()

from crystal import (
	SingleByteParam,
	PointerLabelParam,
	DecimalParam,
	BigEndianParam,
	Command,
	load_rom
)

from gbz80disasm import get_local_address, get_global_address
from audio import sort_asms


from wram import read_constants

rom = bytearray(load_rom())

sfx_constants = read_constants(os.path.join(conf.path, 'constants/sfx_constants.asm'))
class SoundEffectParam(SingleByteParam):
	def to_asm(self):
		if self.byte in sfx_constants.keys():
			sfx_constant = sfx_constants[self.byte]
			return sfx_constant
		return SingleByteParam.to_asm(self)

anim_gfx_constants = read_constants(os.path.join(conf.path, 'constants/gfx_constants.asm'))
class AnimGFXParam(SingleByteParam):
	def to_asm(self):
		if self.byte in anim_gfx_constants.keys():
			return anim_gfx_constants[self.byte]
		return SingleByteParam.to_asm(self)

anims = read_constants(os.path.join(conf.path, 'constants/animation_constants.asm'))
objs  = { k: v for k, v in anims.items() if 'ANIM_OBJ' in v }
bgs   = { k: v for k, v in anims.items() if 'ANIM_BG'  in v }
anims = { k: v.replace('ANIM_','') for k, v in anims.items() }
from move_constants import moves
anims.update(moves)

class AnimObjParam(SingleByteParam):
	def to_asm(self):
		if self.byte in objs.keys():
			return objs[self.byte]
		return SingleByteParam.to_asm(self)

class BGEffectParam(SingleByteParam):
	def to_asm(self):
		if self.byte in bgs.keys():
			return bgs[self.byte]
		return SingleByteParam.to_asm(self)


battle_animation_commands = {
	0xd0: ['anim_obj', ['obj', AnimObjParam], ['x', DecimalParam], ['y', DecimalParam], ['param', SingleByteParam]],
	0xd1: ['anim_1gfx', ['gfx1', AnimGFXParam]],
	0xd2: ['anim_2gfx', ['gfx1', AnimGFXParam], ['gfx2', AnimGFXParam]],
	0xd3: ['anim_3gfx', ['gfx1', AnimGFXParam], ['gfx2', AnimGFXParam], ['gfx3', AnimGFXParam]],
	0xd4: ['anim_4gfx', ['gfx1', AnimGFXParam], ['gfx2', AnimGFXParam], ['gfx3', AnimGFXParam], ['gfx4', AnimGFXParam]],
	0xd5: ['anim_5gfx', ['gfx1', AnimGFXParam], ['gfx2', AnimGFXParam], ['gfx3', AnimGFXParam], ['gfx4', AnimGFXParam], ['gfx5', AnimGFXParam]],
	0xd6: ['anim_incobj', ['id', SingleByteParam]],
	0xd7: ['anim_setobj', ['id', SingleByteParam], ['obj', AnimObjParam]], # bug: second param is interpreted as a command if not found in the object array
	0xd8: ['anim_incbgeffect', ['effect', BGEffectParam]],
	0xd9: ['anim_enemyfeetobj'],
	0xda: ['anim_playerheadobj'],
	0xdb: ['anim_checkpokeball'],
	0xdc: ['anim_transform'],
	0xdd: ['anim_raisesub'],
	0xde: ['anim_dropsub'],
	0xdf: ['anim_resetobp0'],
	0xe0: ['anim_sound', ['tracks', SingleByteParam], ['id', SoundEffectParam]],
	0xe1: ['anim_cry', ['pitch', SingleByteParam]],
	0xe2: ['anim_minimizeopp'], # unused
	0xe3: ['anim_oamon'],
	0xe4: ['anim_oamoff'],
	0xe5: ['anim_clearobjs'],
	0xe6: ['anim_beatup'],
	0xe7: ['anim_0xe7'], # nothing
	0xe8: ['anim_updateactorpic'],
	0xe9: ['anim_minimize'],
	0xea: ['anim_0xea'], # nothing
	0xeb: ['anim_0xeb'], # nothing
	0xec: ['anim_0xec'], # nothing
	0xed: ['anim_0xed'], # nothing
	0xee: ['anim_jumpand', ['value', SingleByteParam], ['address', PointerLabelParam]],
	0xef: ['anim_jumpuntil', ['address', PointerLabelParam]],
	0xf0: ['anim_bgeffect', ['effect', BGEffectParam], ['unknown', SingleByteParam], ['unknown', SingleByteParam], ['unknown', SingleByteParam]],
	0xf1: ['anim_bgp', ['colors', SingleByteParam]],
	0xf2: ['anim_obp0', ['colors', SingleByteParam]],
	0xf3: ['anim_obp1', ['colors', SingleByteParam]],
	0xf4: ['anim_clearsprites'],
	0xf5: ['anim_0xf5'], # nothing
	0xf6: ['anim_0xf6'], # nothing
	0xf7: ['anim_0xf7'], # nothing
	0xf8: ['anim_jumpif', ['value', SingleByteParam], ['address', PointerLabelParam]],
	0xf9: ['anim_setvar', ['value', SingleByteParam]],
	0xfa: ['anim_incvar'],
	0xfb: ['anim_jumpvar', ['value', SingleByteParam], ['address', PointerLabelParam]],
	0xfc: ['anim_jump', ['address', PointerLabelParam]],
	0xfd: ['anim_loop', ['count', SingleByteParam], ['address', PointerLabelParam]],
	0xfe: ['anim_call', ['address', PointerLabelParam]],
	0xff: ['anim_ret'],
}

battle_animation_enders = [
	'anim_jump',
	'anim_ret',
]

def create_battle_animation_classes():
	classes = []
	for cmd, command in battle_animation_commands.items():
		cmd_name = command[0]
		params = {
			'id': cmd,
			'size': 1,
			'end': cmd_name in battle_animation_enders,
			'macro_name': cmd_name,
			'param_types': {},
		}
		for i, (name, class_) in enumerate(command[1:]):
			params['param_types'][i] = {'name': name, 'class': class_}
			params['size'] += class_.size
		class_name = cmd_name + 'Command'
		class_ = classobj(class_name, (Command,), params)
		globals()[class_name] = class_
		classes += [class_]
	return classes

battle_animation_classes = create_battle_animation_classes()


class BattleAnimWait(Command):
	macro_name = 'anim_wait'
	size = 1
	end = macro_name in battle_animation_enders
	param_types = {
		0: {'name': 'duration', 'class': DecimalParam},
	}
	override_byte_check = True


class BattleAnim:
	"""
	A list of battle animation commands read from a given address.

	Results in a list of commands (self.output) and a list of labels (self.labels).
	Format is (address, asm, last_address). Includes any subroutines and their output.

	To convert to text, use self.to_asm().

	For combining multiple BattleAnims, take self.output + self.labels from each
	and sort with sort_asms.
	"""

	def __init__(self, address, base_label=None, label=None, used_labels=[], macros=[]):
		self.start_address = address
		self.address = address

		self.base_label = base_label
		if self.base_label == None:
			self.base_label = 'BattleAnim_' + hex(self.start_address)

		self.label = label
		if self.label == None:
			self.label = self.base_label

		self.used_labels = used_labels

		self.output = []
		self.labels = []
		self.label_asm = (
			self.start_address,
			'%s: ; %x' % (self.label, self.start_address),
			self.start_address
		)
		self.labels += [self.label_asm]
		self.used_labels += [self.label_asm]

		self.macros = macros

		self.parse()

	def parse(self):

		done = False
		while not done:
			cmd = rom[self.address]
			class_ = self.get_command_class(cmd)(address=self.address)
			asm = class_.to_asm()

			# label jumps/calls
			for key, param in class_.param_types.items():
				if param['class'] == PointerLabelParam:
					label_address = class_.params[key].parsed_address
					label = '%s_branch_%x' % (self.base_label, label_address)
					label_def = '%s: ; %x' % (label, label_address)
					label_asm = (label_address, label_def, label_address)
					if label_asm not in self.used_labels:
						self.labels += [label_asm]
					asm = asm.replace('$%x' % get_local_address(label_address), label)

			self.output += [(self.address, '\t' + asm, self.address + class_.size)]
			self.address += class_.size

			done = class_.end
			# infinite loops are enders
			if class_.macro_name == 'anim_loop':
				if class_.params[0].byte == 0:
					done = True

		# last_address comment
		self.output += [(self.address, '; %x\n' % self.address, self.address)]

		# parse any other branches too
		self.labels = list(set(self.labels))
		for address, asm, last_address in self.labels:
			if not (self.start_address <= address < self.address) and (address, asm, last_address) not in self.used_labels:
				self.used_labels += [(address, asm, last_address)]
				sub = BattleAnim(
					address=address,
					base_label=self.base_label,
					label=asm.split(':')[0],
					used_labels=self.used_labels,
					macros=self.macros
				)
				self.output += sub.output
				self.labels += sub.labels

		self.output = list(set(self.output))
		self.labels = list(set(self.labels))

	def to_asm(self):
		output = sort_asms(self.output + self.labels)
		text = ''
		for (address, asm, last_address) in output:
			text += asm + '\n'
		return text

	def get_command_class(self, cmd):
		if cmd < 0xd0:
			return BattleAnimWait
		for class_ in self.macros:
			if class_.id == cmd:
				return class_
		return None


def battle_anim_label(i):
	"""
	Return a label matching the name of a battle animation by id.
	"""
	if i in anims.keys():
		base_label = 'BattleAnim_%s' % anims[i].title().replace('_','')
	else:
		base_label = 'BattleAnim_%d' % i
	return base_label

def dump_battle_anims(table_address=0xc906f, num_anims=278, macros=battle_animation_classes):
	"""
	Dump each battle animation from a pointer table.
	"""

	asms = []

	asms += [(table_address, 'BattleAnimations: ; %x' % table_address, table_address)]

	address = table_address
	bank = address / 0x4000

	for i in xrange(num_anims):
		pointer_address = address
		anim_address = rom[pointer_address] + rom[pointer_address + 1] * 0x100
		anim_address = get_global_address(anim_address, bank)
		base_label = battle_anim_label(i)
		address += 2

		# anim pointer
		asms += [(pointer_address, '\tdw %s' % base_label, address)]

		# anim script
		anim = BattleAnim(
			address=anim_address,
			base_label=base_label,
			macros=macros
		)
		asms += anim.output + anim.labels

	asms += [(address, '; %x\n' % address, address)]

	# jp sonicboom
	anim = BattleAnim(
		address=0xc9c00,
		base_label='BattleAnim_Sonicboom_JP',
		macros=macros
	)
	asms += anim.output + anim.labels

	asms = sort_asms(asms)
	return asms

def asm_list_to_text(asms):
	output = ''
	last = asms[0][0]
	for addr, asm, last_addr in asms:
		if addr > last:
			# incbin any unknown areas
			output += '\nINCBIN "baserom.gbc", $%x, $%x - $%x\n\n\n' % (last, addr, last)
		if addr >= last:
			output += asm + '\n'
		last = last_addr
	return output

if __name__ == '__main__':
	asms = dump_battle_anims()
	print asm_list_to_text(asms)

