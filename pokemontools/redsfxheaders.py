import config
config = config.Config()
rom = bytearray(open(config.rom_path, "r").read())

headerlist = (
	["sfxheaders02.asm", 0x8003, 0x822e],
	["sfxheaders08.asm", 0x20003, 0x202be],
	["sfxheaders1f.asm", 0x7c003, 0x7c249],
	)

numberofchannels = {
	0x0: 1,
	0x4: 2,
	0x8: 3,
	0xC: 4,
	}

def printsfxheaders(filename, address, end):
	file = open(filename, 'w')
	bank = address / 0x4000
	byte = rom[address]
	sfx = 1
	channel = 1
	file.write("SFX_Headers_{:02x}:\n".format(bank))
	file.write("\tdb $ff, $ff, $ff ; padding\n")
	while address != end:
		left = numberofchannels[byte >> 4]
		file.write("\nSFX_{:02x}_{:02x}: ; {:02x} ({:0x}:{:02x})\n".format(bank, sfx, address, bank, address % 0x4000 + 0x4000))
		while left != 0:
			pointer = rom[address + 2] * 0x100 + rom[address + 1]
			if byte >> 4 != 0: file.write("	db ( ${:0x}0 | CH{:0x} )\n".format(byte >> 4, byte % 0x10))
			else: file.write("\tdb CH{:0x}\n".format(byte))
			file.write("\tdw SFX_{:02x}_{:02x}_Ch{}\n".format(bank, sfx, channel))
			address += 3
			byte = rom[address]
			channel += 1
			left -= 1
		channel = 1
		sfx += 1
	file.write("\n; {}".format(hex(address)))

for header in headerlist:
	printsfxheaders(header[0], header[1], header[2])