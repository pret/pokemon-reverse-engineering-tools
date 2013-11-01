import configuration
config = configuration.Config()
rom = bytearray(open(config.rom_path, "r").read())

banks = {
	0x02: 0x60,
	0x08: 0x78,
	0x1f: 0x68,
	}

music_commands = {
	0xd0: ["notetype", {"type": "nibble"}, 2],
	0xe0: ["octave", 1],
	0xe8: ["togglecall", 1],
	0xea: ["vibrato", {"type": "byte"}, {"type": "nibble"}, 3],
	0xec: ["duty", {"type": "byte"}, 2],
	0xed: ["tempo", {"type": "byte"}, {"type": "byte"}, 3],
	0xf0: ["stereopanning", {"type": "byte"}, 2],
	0xf8: ["executemusic", 1],
	0xfc: ["dutycycle", {"type": "byte"}, 2],
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
		sfxfile = open("music/sfx/" + sfxname.lower() + ".asm", 'w')
		startingaddress = rom[header + 2] * 0x100 + rom[header + 1] + (0x4000 * (bank - 1))
		end = 0
		curchannel = 1
		lastchannel = (rom[header] >> 6) + 1
		channelnumber = rom[header] % 0x10
		output = ''
		while 1:
			address = startingaddress
			if curchannel != lastchannel:
				end = rom[header + 5] * 0x100 + rom[header + 4] + (0x4000 * (bank - 1))
			byte = rom[address]
			if byte == 0xf8 or (bank == 2 and sfx == 0x5e): executemusic = True
			else: executemusic = False
			output += "{}_Ch{}: ; {:02x} ({:0x}:{:02x})\n".format(sfxname, curchannel, address, bank, address % 0x4000 + 0x4000)
			while 1:
				if address == 0x2062a or address == 0x2063d or address == 0x20930:
					output += "\n{}_branch_{:02x}:\n".format(sfxname, address)
				if byte == 0x10 and not executemusic:
					output += "\tunknownsfx0x{:02x} {}".format(byte, rom[address + 1])
					command_length = 2
				elif byte < 0x30 and not executemusic:
					if channelnumber == 7:
						output += "\tunknownnoise0x20 {}, {}, {}".format(byte % 0x10, rom[address + 1], rom[address + 2])
						command_length = 3
					else:
						output += "\tunknownsfx0x20 {}, {}, {}, {}".format(byte % 0x10, rom[address + 1], rom[address + 2], rom[address + 3])
						command_length = 4
				elif byte < 0xc0:
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
				if byte == 0xff or address == end: break
				byte = rom[address]
			header += 3
			channelnumber = rom[header]
			if curchannel == lastchannel:
				output += "; {}".format(hex(address))
				sfxfile.write(output)
				break
			output += "\n\n"
			startingaddress = address
			curchannel += 1