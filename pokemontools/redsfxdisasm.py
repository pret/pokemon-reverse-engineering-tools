#!/usr/bin/env python

rom = bytearray(open("baserom.gbc", "rb").read())

sfx_names_1 = [
	"Noise_Instrument01_1",
	"Noise_Instrument02_1",
	"Noise_Instrument03_1",
	"Noise_Instrument04_1",
	"Noise_Instrument05_1",
	"Noise_Instrument06_1",
	"Noise_Instrument07_1",
	"Noise_Instrument08_1",
	"Noise_Instrument09_1",
	"Noise_Instrument10_1",
	"Noise_Instrument11_1",
	"Noise_Instrument12_1",
	"Noise_Instrument13_1",
	"Noise_Instrument14_1",
	"Noise_Instrument15_1",
	"Noise_Instrument16_1",
	"Noise_Instrument17_1",
	"Noise_Instrument18_1",
	"Noise_Instrument19_1",
	"Cry00_1",
	"Cry01_1",
	"Cry02_1",
	"Cry03_1",
	"Cry04_1",
	"Cry05_1",
	"Cry06_1",
	"Cry07_1",
	"Cry08_1",
	"Cry09_1",
	"Cry0A_1",
	"Cry0B_1",
	"Cry0C_1",
	"Cry0D_1",
	"Cry0E_1",
	"Cry0F_1",
	"Cry10_1",
	"Cry11_1",
	"Cry12_1",
	"Cry13_1",
	"Cry14_1",
	"Cry15_1",
	"Cry16_1",
	"Cry17_1",
	"Cry18_1",
	"Cry19_1",
	"Cry1A_1",
	"Cry1B_1",
	"Cry1C_1",
	"Cry1D_1",
	"Cry1E_1",
	"Cry1F_1",
	"Cry20_1",
	"Cry21_1",
	"Cry22_1",
	"Cry23_1",
	"Cry24_1",
	"Cry25_1",
	"Get_Item1_1",
	"Get_Item2_1",
	"Tink_1",
	"Heal_HP_1",
	"Heal_Ailment_1",
	"Start_Menu_1",
	"Press_AB_1",
	"Pokedex_Rating_1",
	"Get_Key_Item_1",
	"Poisoned_1",
	"Trade_Machine_1",
	"Turn_On_PC_1",
	"Turn_Off_PC_1",
	"Enter_PC_1",
	"Shrink_1",
	"Switch_1",
	"Healing_Machine_1",
	"Teleport_Exit1_1",
	"Teleport_Enter1_1",
	"Teleport_Exit2_1",
	"Ledge_1",
	"Teleport_Enter2_1",
	"Fly_1",
	"Denied_1",
	"Arrow_Tiles_1",
	"Push_Boulder_1",
	"SS_Anne_Horn_1",
	"Withdraw_Deposit_1",
	"Cut_1",
	"Go_Inside_1",
	"Swap_1",
	"59_1",
	"Purchase_1",
	"Collision_1",
	"Go_Outside_1",
	"Save_1",
	"Pokeflute",
	"Safari_Zone_PA",
]

sfx_names_2 = [
	"Noise_Instrument01_2",
	"Noise_Instrument02_2",
	"Noise_Instrument03_2",
	"Noise_Instrument04_2",
	"Noise_Instrument05_2",
	"Noise_Instrument06_2",
	"Noise_Instrument07_2",
	"Noise_Instrument08_2",
	"Noise_Instrument09_2",
	"Noise_Instrument10_2",
	"Noise_Instrument11_2",
	"Noise_Instrument12_2",
	"Noise_Instrument13_2",
	"Noise_Instrument14_2",
	"Noise_Instrument15_2",
	"Noise_Instrument16_2",
	"Noise_Instrument17_2",
	"Noise_Instrument18_2",
	"Noise_Instrument19_2",
	"Cry00_2",
	"Cry01_2",
	"Cry02_2",
	"Cry03_2",
	"Cry04_2",
	"Cry05_2",
	"Cry06_2",
	"Cry07_2",
	"Cry08_2",
	"Cry09_2",
	"Cry0A_2",
	"Cry0B_2",
	"Cry0C_2",
	"Cry0D_2",
	"Cry0E_2",
	"Cry0F_2",
	"Cry10_2",
	"Cry11_2",
	"Cry12_2",
	"Cry13_2",
	"Cry14_2",
	"Cry15_2",
	"Cry16_2",
	"Cry17_2",
	"Cry18_2",
	"Cry19_2",
	"Cry1A_2",
	"Cry1B_2",
	"Cry1C_2",
	"Cry1D_2",
	"Cry1E_2",
	"Cry1F_2",
	"Cry20_2",
	"Cry21_2",
	"Cry22_2",
	"Cry23_2",
	"Cry24_2",
	"Cry25_2",
	"Level_Up",
	"Get_Item2_2",
	"Tink_2",
	"Heal_HP_2",
	"Heal_Ailment_2",
	"Start_Menu_2",
	"Press_AB_2",
	"Ball_Toss",
	"Ball_Poof",
	"Faint_Thud",
	"Run",
	"Dex_Page_Added",
	"Caught_Mon",
	"Peck",
	"Faint_Fall",
	"Battle_09",
	"Pound",
	"Battle_0B",
	"Battle_0C",
	"Battle_0D",
	"Battle_0E",
	"Battle_0F",
	"Damage",
	"Not_Very_Effective",
	"Battle_12",
	"Battle_13",
	"Battle_14",
	"Vine_Whip",
	"Battle_16",
	"Battle_17",
	"Battle_18",
	"Battle_19",
	"Super_Effective",
	"Battle_1B",
	"Battle_1C",
	"Doubleslap",
	"Battle_1E",
	"Horn_Drill",
	"Battle_20",
	"Battle_21",
	"Battle_22",
	"Battle_23",
	"Battle_24",
	"Battle_25",
	"Battle_26",
	"Battle_27",
	"Battle_28",
	"Battle_29",
	"Battle_2A",
	"Battle_2B",
	"Battle_2C",
	"Psybeam",
	"Battle_2E",
	"Battle_2F",
	"Psychic_M",
	"Battle_31",
	"Battle_32",
	"Battle_33",
	"Battle_34",
	"Battle_35",
	"Battle_36",
	"Silph_Scope",
]

sfx_names_3 = [
	"Noise_Instrument01_3",
	"Noise_Instrument02_3",
	"Noise_Instrument03_3",
	"Noise_Instrument04_3",
	"Noise_Instrument05_3",
	"Noise_Instrument06_3",
	"Noise_Instrument07_3",
	"Noise_Instrument08_3",
	"Noise_Instrument09_3",
	"Noise_Instrument10_3",
	"Noise_Instrument11_3",
	"Noise_Instrument12_3",
	"Noise_Instrument13_3",
	"Noise_Instrument14_3",
	"Noise_Instrument15_3",
	"Noise_Instrument16_3",
	"Noise_Instrument17_3",
	"Noise_Instrument18_3",
	"Noise_Instrument19_3",
	"Cry00_3",
	"Cry01_3",
	"Cry02_3",
	"Cry03_3",
	"Cry04_3",
	"Cry05_3",
	"Cry06_3",
	"Cry07_3",
	"Cry08_3",
	"Cry09_3",
	"Cry0A_3",
	"Cry0B_3",
	"Cry0C_3",
	"Cry0D_3",
	"Cry0E_3",
	"Cry0F_3",
	"Cry10_3",
	"Cry11_3",
	"Cry12_3",
	"Cry13_3",
	"Cry14_3",
	"Cry15_3",
	"Cry16_3",
	"Cry17_3",
	"Cry18_3",
	"Cry19_3",
	"Cry1A_3",
	"Cry1B_3",
	"Cry1C_3",
	"Cry1D_3",
	"Cry1E_3",
	"Cry1F_3",
	"Cry20_3",
	"Cry21_3",
	"Cry22_3",
	"Cry23_3",
	"Cry24_3",
	"Cry25_3",
	"Get_Item1_3",
	"Get_Item2_3",
	"Tink_3",
	"Heal_HP_3",
	"Heal_Ailment_3",
	"Start_Menu_3",
	"Press_AB_3",
	"Pokedex_Rating_3",
	"Get_Key_Item_3",
	"Poisoned_3",
	"Trade_Machine_3",
	"Turn_On_PC_3",
	"Turn_Off_PC_3",
	"Enter_PC_3",
	"Shrink_3",
	"Switch_3",
	"Healing_Machine_3",
	"Teleport_Exit1_3",
	"Teleport_Enter1_3",
	"Teleport_Exit2_3",
	"Ledge_3",
	"Teleport_Enter2_3",
	"Fly_3",
	"Denied_3",
	"Arrow_Tiles_3",
	"Push_Boulder_3",
	"SS_Anne_Horn_3",
	"Withdraw_Deposit_3",
	"Cut_3",
	"Go_Inside_3",
	"Swap_3",
	"59_3",
	"Purchase_3",
	"Collision_3",
	"Go_Outside_3",
	"Save_3",
	"Intro_Lunge",
	"Intro_Hip",
	"Intro_Hop",
	"Intro_Raise",
	"Intro_Crash",
	"Intro_Whoosh",
	"Slots_Stop_Wheel",
	"Slots_Reward",
	"Slots_New_Spin",
	"Shooting_Star",
]

sfx_groups = {
	0x02: sfx_names_1,
	0x08: sfx_names_2,
	0x1f: sfx_names_3,
}

# music command names and parameter lists
music_commands = {
	0x00: { "name": "note",                 "params": [ "note", "lower_nibble_off_by_one" ] },
	0x10: { "name": "pitch_sweep",          "params": [ "nibbles_unsigned_signed" ] },
	0x20: { "name": "square_note",          "params": [ "lower_nibble", "nibbles_unsigned_signed", "word" ] },
	0x21: { "name": "noise_note",           "params": [ "lower_nibble", "nibbles_unsigned_signed", "byte" ] },
	0xb0: { "name": "dnote",                "params": [ "byte", "lower_nibble_off_by_one" ] },
	0xc0: { "name": "rest",                 "params": [ "lower_nibble_off_by_one" ] },
	0xd0: { "name": "note_type",            "params": [ "lower_nibble", "nibbles_unsigned_signed" ] },
	0xd1: { "name": "dspeed",               "params": [ "lower_nibble" ] },
	0xe0: { "name": "octave",               "params": [ "octave" ] },
	0xe8: { "name": "toggle_perfect_pitch", "params": [] },
	0xea: { "name": "vibrato",              "params": [ "byte", "nibbles" ] },
	0xeb: { "name": "pitch_slide",          "params": [ "byte_off_by_one", "nibbles_octave_note" ] },
	0xec: { "name": "duty_cycle",           "params": [ "byte" ] },
	0xed: { "name": "tempo",                "params": [ "word_big_endian" ] },
	0xee: { "name": "stereo_panning",       "params": [ "nibbles_binary" ] },
	0xf0: { "name": "volume",               "params": [ "nibbles" ] },
	0xf8: { "name": "execute_music",        "params": [] },
	0xfc: { "name": "duty_cycle_pattern",   "params": [ "crumbs" ] },
	0xfd: { "name": "sound_call",           "params": [ "label" ] },
	0xfe: { "name": "sound_loop",           "params": [ "byte", "label" ] },
	0xff: { "name": "sound_ret",            "params": [] },
}

# length in bytes of each type of parameter
param_lengths = {
	"note":                    0,
	"lower_nibble":            0,
	"lower_nibble_off_by_one": 0,
	"octave":                  0,
	"crumbs":                  1,
	"nibbles":                 1,
	"nibbles_binary":          1,
	"nibbles_unsigned_signed": 1,
	"nibbles_octave_note":     1,
	"byte":                    1,
	"byte_off_by_one":         1,
	"word":                    2,
	"word_big_endian":         2,
	"label":                   2,
}

# constants used for note commands
music_notes = {
	0x0: "C_",
	0x1: "C#",
	0x2: "D_",
	0x3: "D#",
	0x4: "E_",
	0x5: "F_",
	0x6: "F#",
	0x7: "G_",
	0x8: "G#",
	0x9: "A_",
	0xa: "A#",
	0xb: "B_",
}

# get length in bytes of a music command by ID
# returns 1 (command ID) + length of all params
def get_command_length(command_id):
	length = 1
	for param in music_commands[command_id]["params"]:
		length += param_lengths[param]
	return length

def get_base_command_id(command_id, channel, execute_music):
	# pitch_sweep
	if command_id == 0x10 and not execute_music:
		return 0x10
	# noise_note
	elif command_id < 0x30 and not execute_music and channel == 8:
		return 0x21
	# square_note
	elif command_id < 0x30 and not execute_music:
		return 0x20
	# dnote
	elif command_id < 0xc0 and channel == 4:
		return 0xb0
	# dspeed
	elif command_id >= 0xd0 and command_id < 0xe0 and channel == 4:
		return 0xd1
	# note
	elif command_id < 0xc0:
		return 0x00
	# rest
	elif command_id < 0xd0:
		return 0xc0
	# notetype
	elif command_id < 0xe0:
		return 0xd0
	# octave
	elif command_id < 0xe8:
		return 0xe0
	else:
		return command_id

# get absolute pointer stored at an address in the rom
# assumes the pointer refers to the same bank as the bank it is located in
def get_pointer(address):
	bank = int(address / 0x4000)
	return (rom[address + 1] * 0x100 + rom[address]) % 0x4000 + bank * 0x4000

def dump_sfx_channel(start_address, sfx_name, sfx, channel, final_channel, channel_number, header, bank):
	address = start_address
	end_address = 0
	if channel != final_channel:
		end_address = get_pointer(header + 4)
	execute_music = False
	if rom[address] == 0xf8 or sfx_name == "Pokeflute":
		execute_music = True
	output = "SFX_{}_Ch{}:\n".format(sfx_name, channel_number)
	while 1:
		if address == 0x2062a or address == 0x2063d or address == 0x20930:
			output += "\nSFX_{}_branch_{:02x}:\n".format(sfx_name, address)
		command_id = rom[address]
		command = music_commands[get_base_command_id(command_id, channel_number, execute_music)]
		output += "\t{}".format(command["name"])
		address += 1
		# print all params for current command
		for i in range(len(command["params"])):
			param = rom[address]
			param_type = command["params"][i]
			param_length = param_lengths[param_type]
			if param_type == "note":
				output += " {}".format(music_notes[command_id >> 4])
			elif param_type == "lower_nibble":
				output += " {}".format(command_id & 0b1111)
			elif param_type == "lower_nibble_off_by_one":
				output += " {}".format((command_id & 0b1111) + 1)
			elif param_type == "octave":
				output += " {}".format(8 - (command_id & 0b1111))
			elif param_type == "crumbs":
				output += " {}, {}, {}, {}".format((param >> 6) & 0b11, (param >> 4) & 0b11, (param >> 2) & 0b11, (param >> 0) & 0b11)
			elif param_type == "nibbles":
				output += " {}, {}".format(param >> 4, param & 0b1111)
			elif param_type == "nibbles_binary":
				output += " %{:b}, %{:b}".format(param >> 4, param & 0b1111)
			elif param_type == "nibbles_unsigned_signed":
				output += " {}, {}".format(param >> 4, param & 0b1111 if param & 0b1111 <= 8 else (param & 0b0111) * -1)
			elif param_type == "nibbles_octave_note":
				output += " {}, {}".format(8 - (param >> 4), music_notes[param & 0b1111])
			elif param_type == "byte":
				output += " {}".format(param)
			elif param_type == "byte_off_by_one":
				output += " {}".format(param + 1)
			elif param_type == "word":
				output += " {}".format(param + rom[address + 1] * 0x100)
			elif param_type == "word_big_endian":
				output += " {}".format(param * 0x100 + rom[address + 1])
			elif param_type == "label":
				param = get_pointer(address)
				if param == start_address:
					output += " SFX_{}_Ch{}".format(sfx_name, channel_number)
				else:
					output += " SFX_{}_branch_{:x}".format(sfx_name, param)
			address += param_length
			if i < len(command["params"]) - 1:
				output += ","
		output += "\n"
		if command_id == 0xff or address == end_address:
			break
	return output, address

def dump_all_sfx_in_bank(bank, sfx_names, path):
	header = bank * 0x4000 + 3
	for sfx in range(0, len(sfx_names)):
		sfx_name = sfx_names[sfx]
		final_channel = (rom[header] >> 6) + 1
		channel_number = rom[header] % 0x10 + 1
		start_address = get_pointer(header + 1)
		cur_channel = 1
		output = ""
		while 1:
			channel_output, end_address = dump_sfx_channel(start_address, sfx_name, sfx, cur_channel, final_channel, channel_number, header, bank)
			output += channel_output
			header += 3
			if cur_channel == final_channel:
				break
			cur_channel += 1
			channel_number = rom[header] + 1
			output += "\n\n"
			start_address = end_address
		sfx_file = open(path + sfx_name.lower() + ".asm", "w")
		sfx_file.write(output)
		sfx_file.close()

def dump_all_sfx(path):
	import os
	os.makedirs(path, exist_ok=True)
	for bank in sfx_groups:
		dump_all_sfx_in_bank(bank, sfx_groups[bank], path)

if __name__ == "__main__":
	dump_all_sfx("audio/sfx/")
