import configuration
config = configuration.Config()
rom = bytearray(open(config.rom_path, "r").read())

songs = [
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
	"GymLeaderBattle",
	"TrainerBattle",
	"WildBattle",
	"FinalBattle",
	"DefeatedTrainer",
	"DefeatedWildMon",
	"DefeatedGymLeader",
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
"""
songs = [
	"YellowIntro",
	"SurfingPikachu",
	"MeetJessieJames",
	"YellowUnusedSong",
	]
"""
music_commands = {
	0xd0: ["notetype", {"type": "nibble"}, 2],
	0xe0: ["octave", 1],
	0xe8: ["toggleperfectpitch", 1],
	0xea: ["vibrato", {"type": "byte"}, {"type": "nibble"}, 3],
	0xeb: ["pitchbend", {"type": "byte"}, {"type": "byte"}, 3],
	0xec: ["duty", {"type": "byte"}, 2],
	0xed: ["tempo", {"type": "word"}, 3],
	0xee: ["stereopanning", {"type": "byte"}, 2],
	0xf0: ["volume", {"type": "nibble"}, 2],
	0xf8: ["executemusic", 1],
	0xfc: ["dutycycle", {"type": "byte"}, 2],
	0xfd: ["callchannel", {"type": "label"}, 3],
	0xfe: ["loopchannel", {"type": "byte"}, {"type": "label"}, 4],
	0xff: ["endchannel", 1],
	}

param_lengths = {
	"nibble": 1,
	"byte": 1,
	"word": 2,
	"label": 2,
	}

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

def printnoisechannel(songname, songfile, startingaddress, bank, output):
	noise_commands = {
		0xfd: ["callchannel", {"type": "label"}, 3],
		0xfe: ["loopchannel", {"type": "byte"}, {"type": "label"}, 4],
		0xff: ["endchannel", 1],
		}
	
	noise_instruments = {
		0x01: "snare1",
		0x02: "snare2",
		0x03: "snare3",
		0x04: "snare4",
		0x05: "snare5",
		0x06: "triangle1",
		0x07: "triangle2",
		0x08: "snare6",
		0x09: "snare7",
		0x0a: "snare8",
		0x0b: "snare9",
		0x0c: "cymbal1",
		0x0d: "cymbal2",
		0x0e: "cymbal3",
		0x0f: "mutedsnare1",
		0x10: "triangle3",
		0x11: "mutedsnare2",
		0x12: "mutedsnare3",
		0x13: "mutedsnare4",
		}
	
	# pass 1, build a list of all addresses pointed to by calls and loops
	address = startingaddress
	labels = []
	labelsleft= []
	while 1:
		byte = rom[address]
		if byte < 0xc0:
			command_length = 2
		elif byte < 0xe0:
			command_length = 1
		else:
			command_length = noise_commands[byte][-1]
			if byte == 0xfd or byte == 0xfe:
				label = rom[address + command_length - 1] * 0x100 + rom[address + command_length - 2]
				labels.append(label)
				if label > address % 0x4000 + 0x4000: labelsleft.append(label)
		address += command_length
		if len(labelsleft) == 0 and (byte == 0xfe and rom[address - command_length + 1] == 0 and rom[address - 1] * 0x100 + rom[address - 2] < address % 0x4000 + 0x4000 or byte == 0xff): break
		while address % 0x4000 + 0x4000 in labelsleft: labelsleft.remove(address % 0x4000 + 0x4000)
	# once the loop ends, start over from first address
	if rom[address] == 0xff: address += 1
	end = address
	address = startingaddress
	byte = rom[address]
	output += "Music_{}_Ch4:: ; {:02x} ({:0x}:{:02x})\n".format(songname, address, bank, address % 0x4000 + 0x4000)
	# pass 2, print commands and labels for addresses that are in labels
	while address != end:
		if address % 0x4000 + 0x4000 in labels and address != startingaddress:
			output += "\nMusic_{}_branch_{:02x}::\n".format(songname, address)
		if byte < 0xc0:
			output += "\t{} {}".format(noise_instruments[rom[address + 1]], byte % 0x10 + 1)
			command_length = 2
		elif byte < 0xd0:
			output += "\trest {}".format(byte % 0x10 + 1)
			command_length = 1
		elif byte < 0xe0:
			output += "\tdspeed {}".format(byte % 0x10)
			command_length = 1
		else:
			command = noise_commands[byte]
			output += "\t{}".format(command[0])
			command_length = 1
			params = 1
			# print all params for current command
			while params != len(noise_commands[byte]) - 1:
				param_type = noise_commands[byte][params]["type"]
				address += command_length
				command_length = param_lengths[param_type]
				param = rom[address]
				if param_type == "byte":
					output += " {}".format(param)
				else:
					param += rom[address + 1] * 0x100 - 0x4000 + (bank * 0x4000)
					if param == startingaddress: output += " Music_{}_Ch4".format(songname)
					else: output += " Music_{}_branch_{:02x}".format(songname, param)
				params += 1
				if params != len(noise_commands[byte]) - 1: output += ","
		output += "\n"
		address += command_length
		byte = rom[address]
	output += "; {}\n".format(hex(address))
	songfile.write(output)

for i, songname in enumerate(songs):
	songfile  = open("music/" + songname.lower() + ".asm", 'a')
	if songname == "PalletTown": header = 0x822e
	if songname == "GymLeaderBattle": header = 0x202be
	if songname == "TitleScreen": header = 0x7c249
	if songname == "YellowIntro": header = 0x7c294
	if songname == "SurfingPikachu": header = 0x801cb
	bank = header / 0x4000
	startingaddress = rom[header + 2] * 0x100 + rom[header + 1] - 0x4000 + (0x4000 * bank)
	curchannel = 1
	lastchannel = (rom[header] >> 6) + 1
	exception = False
	if songname == "MeetRival" or songname == "Cities1":
		startingaddress -= 7
		exception = True
	if songname == "UnusedSong":
		bank = 2
		startingaddress = 0xa913
		lastchannel = 2
	output = ''
	while 1:
		# pass 1, build a list of all addresses pointed to by calls and loops
		address = startingaddress
		labels = []
		labelsleft = []
		if songname == "MeetRival":
			if curchannel == 1:
				labels.append(0x719b)
				labelsleft.append(0x719b)
				labels.append(0x71a2)
				labelsleft.append(0x71a2)
			if curchannel == 2:
				labels.append(0x721d)
				labelsleft.append(0x721d)
			if curchannel == 3:
				labels.append(0x72b5)
				labelsleft.append(0x72b5)
		while 1:
			byte = rom[address]
			if byte < 0xd0:
				command_length = 1
			elif byte < 0xe0:
				command_length = 2
			elif byte < 0xe8:
				command_length = 1
			else:
				command_length = music_commands[byte][-1]
				if byte == 0xfd or byte == 0xfe:
					label = rom[address + command_length - 1] * 0x100 + rom[address + command_length - 2]
					labels.append(label)
					if label > address % 0x4000 + 0x4000: labelsleft.append(label)
			address += command_length
			if len(labelsleft) == 0 and (exception == False or address > startingaddress + 7) and (byte == 0xfe and rom[address - command_length + 1] == 0 and rom[address - 1] * 0x100 + rom[address - 2] < address % 0x4000 + 0x4000 or byte == 0xff): break
			while address % 0x4000 + 0x4000 in labelsleft: labelsleft.remove(address % 0x4000 + 0x4000)
		# once the loop breaks, start over from first address
		if rom[address] == 0xff: address += 1
		end = address
		if curchannel != lastchannel and songname != "UnusedSong": end = rom[header + 5] * 0x100 + rom[header + 4] + (0x4000 * (bank - 1))
		address = startingaddress
		byte = rom[address]
		# if song has an alternate start to channel 1, print a label and set startingaddress to true channel start
		if exception:
			output += "Music_{}_branch_{:02x}::\n".format(songname, address)
			startingaddress += 7
		# pass 2, print commands and labels for addresses that are in labels
		while address != end:
			if address == startingaddress:
				if exception: output += "\n"
				output += "Music_{}_Ch{}:: ; {:02x} ({:0x}:{:02x})\n".format(songname, curchannel, address, bank, address % 0x4000 + 0x4000)
			elif address % 0x4000 + 0x4000 in labels:
				output += "\nMusic_{}_branch_{:02x}::\n".format(songname, address)
			if byte < 0xc0:
				output += "\t{} {}".format(music_notes[byte >> 4], byte % 0x10 + 1)
				command_length = 1
			elif byte < 0xd0:
				output += "\trest {}".format(byte % 0x10 + 1)
				command_length = 1
			else:
				if byte < 0xe0:
					command = music_commands[0xd0]
					output += "\t{} {},".format(command[0], byte % 0x10)
					byte = 0xd0
				elif byte < 0xe8:
					command = music_commands[0xe0]
					output += "\t{} {}".format(command[0], 0xe8 - byte)
					byte = 0xe0
				else:
					command = music_commands[byte]
					output += "\t{}".format(command[0])
				command_length = 1
				params = 1
				# print all params for current command
				while params != len(music_commands[byte]) - 1:
					param_type = music_commands[byte][params]["type"]
					address += command_length
					command_length = param_lengths[param_type]
					param = rom[address]
					if param_type == "nibble":
						output += " {}, {}".format(param >> 4, param % 0x10)
					elif param_type == "byte":
						output += " {}".format(param)
					elif param_type == "word":
						output += " {}".format(param * 0x100 + rom[address + 1])
					else:
						param += rom[address + 1] * 0x100 - 0x4000 + (bank * 0x4000)
						if param == startingaddress: output += " Music_{}_Ch{}".format(songname, curchannel)
						else: output += " Music_{}_branch_{:02x}".format(songname, param)
					params += 1
					if params != len(music_commands[byte]) - 1: output += ","
			output += "\n"
			address += command_length
			byte = rom[address]
		header += 3
		if curchannel == lastchannel:
			output += "; {}\n".format(hex(address))
			songfile.write(output)
			break
		curchannel += 1
		output += "\n\n"
		startingaddress = end
		exception = False
		if curchannel == 4:
			printnoisechannel(songname, songfile, startingaddress, bank, output)
			header += 3
			break