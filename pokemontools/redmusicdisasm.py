#!/usr/bin/env python

rom = None

# songs in RBY
songs = [
	# song group 1
	"PalletTown",
	"Pokecenter",
	"Gym",
	"Cities1",
	"Cities2",
	"Celadon",
	"Cinnabar",
	"Vermilion",
	"Lavender",
	"SSAnne",
	"MeetProfOak",
	"MeetRival",
	"MuseumGuy",
	"SafariZone",
	"PkmnHealed",
	"Routes1",
	"Routes2",
	"Routes3",
	"Routes4",
	"IndigoPlateau",
	# song group 2
	"GymLeaderBattle",
	"TrainerBattle",
	"WildBattle",
	"FinalBattle",
	"DefeatedTrainer",
	"DefeatedWildMon",
	"DefeatedGymLeader",
	# song group 3
	"TitleScreen",
	"Credits",
	"HallOfFame",
	"OaksLab",
	"JigglypuffSong",
	"BikeRiding",
	"Surfing",
	"GameCorner",
	"IntroBattle",
	"Dungeon1",
	"Dungeon2",
	"Dungeon3",
	"CinnabarMansion",
	"PokemonTower",
	"SilphCo",
	"MeetEvilTrainer",
	"MeetFemaleTrainer",
	"MeetMaleTrainer",
	"UnusedSong",
]

# songs exclusively in Yellow
songs_yellow = [
	# song group 4
	"YellowIntro",
	# song group 5
	"SurfingPikachu",
	"MeetJessieJames",
	"YellowUnusedSong",
]

# starting addresses of all 5 song groups
header_addresses = {
	"PalletTown":      0x0822e,
	"GymLeaderBattle": 0x202be,
	"TitleScreen":     0x7c249,
	"YellowIntro":     0x7c294,
	"SurfingPikachu":  0x801cb,
}

# songs with an alternate start not pointed to by a song header
alternate_start_songs = [
	"Cities1",
	"MeetRival",
]

# music command names and parameter lists
music_commands = {
	0x00: { "name": "note",                 "params": [ "note", "lower_nibble_off_by_one" ] },
	0xb0: { "name": "dnote",                "params": [ "byte", "lower_nibble_off_by_one" ] },
	0xc0: { "name": "rest",                 "params": [ "lower_nibble_off_by_one" ] },
	0xd0: { "name": "note_type",            "params": [ "lower_nibble", "nibbles_unsigned_signed" ] },
	0xd1: { "name": "dspeed",               "params": [ "lower_nibble" ] },
	0xe0: { "name": "octave",               "params": [ "octave" ] },
	0xe8: { "name": "toggle_perfect_pitch", "params": [] },
	0xea: { "name": "vibrato",              "params": [ "byte", "nibbles" ] },
	0xeb: { "name": "pitch_slide",          "params": [ "byte_off_by_one", "nibbles_octave_note" ] },
	0xec: { "name": "duty_cycle",           "params": [ "byte" ] },
	0xed: { "name": "tempo",                "params": [ "word" ] },
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

def get_base_command_id(command_id, channel):
	# dnote
	if command_id < 0xc0 and channel == 4:
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

# return True if the command at address is a loop command
#   and the loop count is 0 (infinite)
#   and the destination address is "backwards" (less than the command address)
def is_infinite_loop(address):
	return rom[address] == 0xfe and rom[address + 1] == 0 and get_pointer(address + 2) <= address

# scan a single channel of a song
# returns: a set of all unique addresses pointed to by calls and loops
#   and the end address of the channel
def scan_for_labels(start_address, song_name, channel, final_channel, header):
	# pass 1, build a list of all addresses pointed to by calls and loops
	address = start_address
	all_labels = set()
	future_labels = set()
	# MeetRival has some labels that cannot be seen by calls and loops
	if song_name == "MeetRival":
		if channel == 1:
			all_labels.add(0xb19b)
			future_labels.add(0xb19b)
			all_labels.add(0xb1a2)
			future_labels.add(0xb1a2)
		if channel == 2:
			all_labels.add(0xb21d)
			future_labels.add(0xb21d)
		if channel == 3:
			all_labels.add(0xb2b5)
			future_labels.add(0xb2b5)
	while 1:
		command_id = get_base_command_id(rom[address], channel)
		command_length = get_command_length(command_id)
		# if call or loop
		if command_id == 0xfd or command_id == 0xfe:
			label = get_pointer(address + command_length - 2)
			all_labels.add(label)
			if label > address:
				future_labels.add(label)
		future_labels.discard(address)
		address += command_length
		# we are only finished when there are no more unvisited labels
		#   and we hit an infinite loop or a ret command
		#   and also channel 1 of an alternate start song must advance at least 7 bytes
		if (len(future_labels) == 0 and
			(is_infinite_loop(address - command_length) or command_id == 0xff) and
			(song_name not in alternate_start_songs or channel != 1 or address > start_address + 7)):
			break
	# some songs have an extra ret command after an infinite loop
	if rom[address] == 0xff and song_name != "MeetJessieJames":
		address += 1
	# if this is not the last channel of the song,
	#   then the end address is simply the start address of the next channel
	# otherwise, use the computed end address
	if channel != final_channel and song_name != "UnusedSong":
		address = get_pointer(header + 4)
	return all_labels, address

# using the list of labels and end address from pass 1, parse a single channel of a song
# returns a string of all labels and commands
def dump_channel(start_address, end_address, song_name, channel, labels):
	address = start_address
	output = ""
	# if song has an alternate start to channel 1, print a label and set start_address to true channel start
	if song_name in alternate_start_songs and channel == 1:
		output += "Music_{}_branch_{:x}::\n".format(song_name, address)
		start_address += 7
	# pass 2, print commands and labels for addresses that are in labels
	while address != end_address:
		if address == start_address:
			if song_name in alternate_start_songs and channel == 1:
				output += "\n"
			output += "Music_{}_Ch{}::\n".format(song_name, channel)
		elif address in labels:
			output += "\nMusic_{}_branch_{:x}::\n".format(song_name, address)
		command_id = rom[address]
		command = music_commands[get_base_command_id(command_id, channel)]
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
				output += " {}, {}".format(param >> 4, (param & 0b0111) * (-1 if param & 0b1000 else 1))
			elif param_type == "nibbles_octave_note":
				output += " {}, {}".format(8 - (param >> 4), music_notes[param & 0b1111])
			elif param_type == "byte":
				output += " {}".format(param)
			elif param_type == "byte_off_by_one":
				output += " {}".format(param + 1)
			elif param_type == "word":
				output += " {}".format(param * 0x100 + rom[address + 1])
			elif param_type == "label":
				param = get_pointer(address)
				if param == start_address:
					output += " Music_{}_Ch{}".format(song_name, channel)
				else:
					output += " Music_{}_branch_{:x}".format(song_name, param)
			address += param_length
			if i < len(command["params"]) - 1:
				output += ","
		output += "\n"
	return output

def dump_all_songs(song_names, path):
	for song_name in song_names:
		if song_name in header_addresses:
			header = header_addresses[song_name]
		# UnusedSong does not have a header
		if song_name == "UnusedSong":
			final_channel = 2
			start_address = 0xa913
		else:
			final_channel = (rom[header] >> 6) + 1
			start_address = get_pointer(header + 1)
		if song_name in alternate_start_songs:
			start_address -= 7
		cur_channel = 1
		output = ""
		while 1:
			labels, end_address = scan_for_labels(start_address, song_name, cur_channel, final_channel, header)
			output += dump_channel(start_address, end_address, song_name, cur_channel, labels)
			header += 3
			if cur_channel == final_channel:
				break
			cur_channel += 1
			output += "\n\n"
			start_address = end_address
		song_file = open(path + song_name.lower() + ".asm", "w")
		song_file.write(output)
		song_file.close()

def dump_all_songs_from_rom(rom_file, song_names, path):
	import os
	global rom
	try:
		print("Parsing {}...".format(rom_file))
		rom = bytearray(open(rom_file, "rb").read())
		os.makedirs(path, exist_ok=True)
		dump_all_songs(song_names, path)
	except IOError as ex:
		print("Error parsing {}".format(rom_file))
		print(ex)

if __name__ == "__main__":
	dump_all_songs_from_rom("pokered.gbc", songs, "audio/music/")
	dump_all_songs_from_rom("pokeyellow.gbc", songs_yellow, "audio/music/yellow/")
