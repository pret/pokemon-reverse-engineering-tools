import config
config = config.Config()
rom = bytearray(open(config.rom_path, "r").read())

banks = {
	0x02: 0x60,
	0x08: 0x78,
	0x1f: 0x68,
	}

music_commands = {
	0xd0: ["notetype", {"type": "nibble"}, 2],
	0xe0: ["octave", 1],
	0xe8: ["unknownmusic0xe8", 1],
	0xe9: ["unknownmusic0xe9", 1],
	0xea: ["vibrato", {"type": "byte"}, {"type": "nibble"}, 3],
	0xeb: ["pitchbend", {"type": "byte"}, {"type": "byte"}, 3],
	0xec: ["duty", {"type": "byte"}, 2],
	0xed: ["tempo", {"type": "byte"}, {"type": "byte"}, 3],
	0xee: ["unknownmusic0xee", {"type": "byte"}, 2],
	0xef: ["unknownmusic0xef", 1],
	0xf0: ["stereopanning", {"type": "byte"}, 2],
	0xf1: ["unknownmusic0xf1", 1],
	0xf2: ["unknownmusic0xf2", 1],
	0xf3: ["unknownmusic0xf3", 1],
	0xf4: ["unknownmusic0xf4", 1],
	0xf5: ["unknownmusic0xf5", 1],
	0xf6: ["unknownmusic0xf6", 1],
	0xf7: ["unknownmusic0xf7", 1],
	0xf8: ["unknownmusic0xf8", 1],
	0xf9: ["unknownmusic0xf9", 1],
	0xfa: ["unknownmusic0xfa", 1],
	#0xfb: ["unknownmusic0xfb", 1],
	0xfc: ["dutycycle", {"type": "byte"}, 2],
	0xfd: ["callchannel", {"type": "label"}, 3],
	0xfe: ["loopchannel", {"type": "byte"}, {"type": "label"}, 4],
	0xff: ["endchannel", 1],
	}

param_lengths = {
	"nibble": 1,
	"byte": 1,
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

for bank in banks:
	header = bank * 0x4000 + 3
	for sfx in range(1,banks[bank]):
		sfxname = "SFX_{:02x}_{:02x}".format(bank, sfx)
		sfxfile = open("music/sfx/" + sfxname.lower() + ".asm", 'a')
		startingaddress = rom[header + 2] * 0x100 + rom[header + 1] + (0x4000 * (bank - 1))
		curchannel = 1
		lastchannel = (rom[header] >> 6) + 1
		output = ''
		while 1:
			# pass 1, build a list of all addresses pointed to by calls and loops
			address = startingaddress
			labels = []
			labelsleft = []
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
				if len(labelsleft) == 0 and (byte == 0xfe and rom[address - command_length + 1] == 0 and rom[address - 1] * 0x100 + rom[address - 2] < address % 0x4000 + 0x4000 or byte == 0xff): break
				while address % 0x4000 + 0x4000 in labelsleft: labelsleft.remove(address % 0x4000 + 0x4000)
			# once the loop breaks, start over from first address
			end = address
			if curchannel != lastchannel: end = rom[header + 5] * 0x100 + rom[header + 4] + (0x4000 * (bank - 1))
			address = startingaddress
			byte = rom[address]
			# pass 2, print commands and labels for addresses that are in labels
			while address != end:
				if address == startingaddress:
					output += "{}_Ch{}: ; {:02x} ({:0x}:{:02x})\n".format(sfxname, curchannel, address, bank, address % 0x4000 + 0x4000)
				elif address % 0x4000 + 0x4000 in labels:
					output += "\n{}_branch_{:02x}:\n".format(sfxname, address)
				if byte < 0xc0:
					output += "\tnote {}, {}".format(music_notes[byte >> 4], byte % 0x10 + 1)
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
						else:
							param += rom[address + 1] * 0x100 - 0x4000 + (bank * 0x4000)
							if param == startingaddress: output += " {}_Ch{}".format(sfxname, curchannel)
							else: output += " {}_branch_{:02x}".format(sfxname, param)
						params += 1
						if params != len(music_commands[byte]) - 1: output += ","
				output += "\n"
				address += command_length
				byte = rom[address]
			header += 3
			if curchannel == lastchannel:
				output += "; {}".format(hex(address))
				sfxfile.write(output)
				break
			output += "\n\n"
			startingaddress = end
			curchannel += 1