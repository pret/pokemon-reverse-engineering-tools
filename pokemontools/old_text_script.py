"""
An old implementation of TextScript that may not be useful anymore.
"""

import pointers

class OldTextScript:
    "a text is a sequence of commands different from a script-engine script"
    base_label = "UnknownText_"
    def __init__(self, address, map_group=None, map_id=None, debug=True, show=True, force=False, label=None):
        self.address = address
        self.map_group, self.map_id, self.debug, self.show, self.force = map_group, map_id, debug, show, force
        if not label:
            label = self.base_label + hex(address)
        self.label = Label(name=label, address=address, object=self)
        self.dependencies = []
        self.parse_text_at(address)

    @staticmethod
    def find_addresses():
        """returns a list of text pointers
        useful for testing parse_text_engine_script_at

        Note that this list is not exhaustive. There are some texts that
        are only pointed to from some script that a current script just
        points to. So find_all_text_pointers_in_script_engine_script will
        have to recursively follow through each script to find those.
        .. it does this now :)
        """
        addresses = set()
        # for each map group
        for map_group in map_names:
            # for each map id
            for map_id in map_names[map_group]:
                # skip the offset key
                if map_id == "offset": continue
                # dump this into smap
                smap = map_names[map_group][map_id]
                # signposts
                signposts = smap["signposts"]
                # for each signpost
                for signpost in signposts:
                    if signpost["func"] in [0, 1, 2, 3, 4]:
                        # dump this into script
                        script = signpost["script"]
                    elif signpost["func"] in [05, 06]:
                        script = signpost["script"]
                    else: continue
                    # skip signposts with no bytes
                    if len(script) == 0: continue
                    # find all text pointers in script
                    texts = find_all_text_pointers_in_script_engine_script(script, smap["event_bank"])
                    # dump these addresses in
                    addresses.update(texts)
                # xy triggers
                xy_triggers = smap["xy_triggers"]
                # for each xy trigger
                for xy_trigger in xy_triggers:
                    # dump this into script
                    script = xy_trigger["script"]
                    # find all text pointers in script
                    texts = find_all_text_pointers_in_script_engine_script(script, smap["event_bank"])
                    # dump these addresses in
                    addresses.update(texts)
                # trigger scripts
                triggers = smap["trigger_scripts"]
                # for each trigger
                for (i, trigger) in triggers.items():
                    # dump this into script
                    script = trigger["script"]
                    # find all text pointers in script
                    texts = find_all_text_pointers_in_script_engine_script(script, pointers.calculate_bank(trigger["address"]))
                    # dump these addresses in
                    addresses.update(texts)
                # callback scripts
                callbacks = smap["callback_scripts"]
                # for each callback
                for (k, callback) in callbacks.items():
                    # dump this into script
                    script = callback["script"]
                    # find all text pointers in script
                    texts = find_all_text_pointers_in_script_engine_script(script, pointers.calculate_bank(callback["address"]))
                    # dump these addresses in
                    addresses.update(texts)
                # people-events
                events = smap["people_events"]
                # for each event
                for event in events:
                    if event["event_type"] == "script":
                        # dump this into script
                        script = event["script"]
                        # find all text pointers in script
                        texts = find_all_text_pointers_in_script_engine_script(script, smap["event_bank"])
                        # dump these addresses in
                        addresses.update(texts)
                    if event["event_type"] == "trainer":
                        trainer_data = event["trainer_data"]
                        addresses.update([trainer_data["text_when_seen_ptr"]])
                        addresses.update([trainer_data["text_when_trainer_beaten_ptr"]])
                        trainer_bank = pointers.calculate_bank(event["trainer_data_address"])
                        script1 = trainer_data["script_talk_again"]
                        texts1 = find_all_text_pointers_in_script_engine_script(script1, trainer_bank)
                        addresses.update(texts1)
                        script2 = trainer_data["script_when_lost"]
                        texts2 = find_all_text_pointers_in_script_engine_script(script2, trainer_bank)
                        addresses.update(texts2)
        return addresses

    def parse_text_at(self, address):
        """parses a text-engine script ("in-text scripts")
        http://hax.iimarck.us/files/scriptingcodes_eng.htm#InText

        This is presently very broken.

        see parse_text_at2, parse_text_at, and process_00_subcommands
        """
        global rom, text_count, max_texts, texts, script_parse_table
        if rom == None:
            direct_load_rom()
        if address == None:
            return "not a script"
        map_group, map_id, debug, show, force = self.map_group, self.map_id, self.debug, self.show, self.force
        commands = {}

        if is_script_already_parsed_at(address) and not force:
            logging.debug("text is already parsed at this location: {0}".format(hex(address)))
            raise Exception("text is already parsed, what's going on ?")
            return script_parse_table[address]

        total_text_commands = 0
        command_counter = 0
        original_address = address
        offset = address
        end = False
        script_parse_table[original_address:original_address+1] = "incomplete text"
        while not end:
            address = offset
            command = {}
            command_byte = ord(rom[address])
            if debug:
                logging.debug(
                    "TextScript.parse_script_at has encountered a command byte {0} at {1}"
                    .format(hex(command_byte), hex(address))
                )
            end_address = address + 1
            if  command_byte == 0:
                # read until $57, $50 or $58
                jump57 = how_many_until(chr(0x57), offset, rom)
                jump50 = how_many_until(chr(0x50), offset, rom)
                jump58 = how_many_until(chr(0x58), offset, rom)

                # whichever command comes first
                jump = min([jump57, jump50, jump58])

                end_address = offset + jump # we want the address before $57

                lines = process_00_subcommands(offset+1, end_address, debug=debug)

                if show and debug:
                    text = parse_text_at2(offset+1, end_address-offset+1, debug=debug)
                    logging.debug("output of parse_text_at2 is {0}".format(text))

                command = {"type": command_byte,
                           "start_address": offset,
                           "end_address": end_address,
                           "size": jump,
                           "lines": lines,
                          }

                offset += jump
            elif command_byte == 0x17:
                # TX_FAR [pointer][bank]
                pointer_byte1 = ord(rom[offset+1])
                pointer_byte2 = ord(rom[offset+2])
                pointer_bank = ord(rom[offset+3])

                pointer = (pointer_byte1 + (pointer_byte2 << 8))
                pointer = extract_maps.calculate_pointer(pointer, pointer_bank)

                text = TextScript(pointer, map_group=self.map_group, map_id=self.amp_id, debug=self.debug, \
                                  show=self.debug, force=self.debug, label="Target"+self.label.name)
                if text.is_valid():
                    self.dependencies.append(text)

                command = {"type": command_byte,
                           "start_address": offset,
                           "end_address": offset + 3, # last byte belonging to this command
                           "pointer": pointer, # parameter
                           "text": text,
                          }

                offset += 3 + 1
            elif command_byte == 0x50 or command_byte == 0x57 or command_byte == 0x58: # end text
                command = {"type": command_byte,
                           "start_address": offset,
                           "end_address": offset,
                          }

                # this byte simply indicates to end the script
                end = True

                # this byte simply indicates to end the script
                if command_byte == 0x50 and ord(rom[offset+1]) == 0x50: # $50$50 means end completely
                    end = True
                    commands[command_counter+1] = command

                    # also save the next byte, before we quit
                    commands[command_counter+1]["start_address"] += 1
                    commands[command_counter+1]["end_address"] += 1
                    add_command_byte_to_totals(command_byte)
                elif command_byte == 0x50: # only end if we started with $0
                    if len(commands.keys()) > 0:
                        if commands[0]["type"] == 0x0: end = True
                elif command_byte == 0x57 or command_byte == 0x58: # end completely
                    end = True
                    offset += 1 # go past this 0x50
            elif command_byte == 0x1:
                # 01 = text from RAM. [01][2-byte pointer]
                size = 3 # total size, including the command byte
                pointer_byte1 = ord(rom[offset+1])
                pointer_byte2 = ord(rom[offset+2])

                command = {"type": command_byte,
                           "start_address": offset+1,
                           "end_address": offset+2, # last byte belonging to this command
                           "pointer": [pointer_byte1, pointer_byte2], # RAM pointer
                          }

                # view near these bytes
                # subsection = rom[offset:offset+size+1] #peak ahead
                #for x in subsection:
                #    print hex(ord(x))
                #print "--"

                offset += 2 + 1 # go to the next byte

                # use this to look at the surrounding bytes
                if debug:
                    logging.debug("next command is {0}".format(hex(ord(rom[offset]))))
                    logging.debug(
                        ".. current command number is {counter} near {offset} on map_id={map_id}"
                        .format(
                            counter=command_counter,
                            offset=hex(offset),
                            map_id=map_id,
                        )
                    )
            elif command_byte == 0x7:
                # 07 = shift texts 1 row above (2nd line becomes 1st line); address for next text = 2nd line. [07]
                size = 1
                command = {"type": command_byte,
                           "start_address": offset,
                           "end_address": offset,
                          }
                offset += 1
            elif command_byte == 0x3:
                # 03 = set new address in RAM for text. [03][2-byte RAM address]
                size = 3
                command = {"type": command_byte, "start_address": offset, "end_address": offset+2}
                offset += size
            elif command_byte == 0x4: # draw box
                # 04 = draw box. [04][2-Byte pointer][height Y][width X]
                size = 5 # including the command
                command = {
                            "type": command_byte,
                            "start_address": offset,
                            "end_address": offset + size,
                            "pointer_bytes": [ord(rom[offset+1]), ord(rom[offset+2])],
                            "y": ord(rom[offset+3]),
                            "x": ord(rom[offset+4]),
                          }
                offset += size + 1
            elif command_byte == 0x5:
                # 05 = write text starting at 2nd line of text-box. [05][text][ending command]
                # read until $57, $50 or $58
                jump57 = how_many_until(chr(0x57), offset, rom)
                jump50 = how_many_until(chr(0x50), offset, rom)
                jump58 = how_many_until(chr(0x58), offset, rom)

                # whichever command comes first
                jump = min([jump57, jump50, jump58])

                end_address = offset + jump # we want the address before $57

                lines = process_00_subcommands(offset+1, end_address, debug=debug)

                if show and debug:
                    text = parse_text_at2(offset+1, end_address-offset+1, debug=debug)
                    logging.debug("parse_text_at2 text is {0}".format(text))

                command = {"type": command_byte,
                           "start_address": offset,
                           "end_address": end_address,
                           "size": jump,
                           "lines": lines,
                          }
                offset = end_address + 1
            elif command_byte == 0x6:
                # 06 = wait for keypress A or B (put blinking arrow in textbox). [06]
                command = {"type": command_byte, "start_address": offset, "end_address": offset}
                offset += 1
            elif command_byte == 0x7:
                # 07 = shift texts 1 row above (2nd line becomes 1st line); address for next text = 2nd line. [07]
                command = {"type": command_byte, "start_address": offset, "end_address": offset}
                offset += 1
            elif command_byte == 0x8:
                # 08 = asm until whenever
                command = {"type": command_byte, "start_address": offset, "end_address": offset}
                offset += 1
                end = True
            elif command_byte == 0x9:
                # 09 = write hex-to-dec number from RAM to textbox [09][2-byte RAM address][byte bbbbcccc]
                #  bbbb = how many bytes to read (read number is big-endian)
                #  cccc = how many digits display (decimal)
                #(note: max of decimal digits is 7,i.e. max number correctly displayable is 9999999)
                ram_address_byte1 = ord(rom[offset+1])
                ram_address_byte2 = ord(rom[offset+2])
                read_byte = ord(rom[offset+3])

                command = {
                            "type": command_byte,
                            "address": [ram_address_byte1, ram_address_byte2],
                            "read_byte": read_byte, # split this up when we make a macro for this
                          }

                offset += 4
            else:
                #if len(commands) > 0:
                #   print "Unknown text command " + hex(command_byte) + " at " + hex(offset) + ", script began with " + hex(commands[0]["type"])
                if debug:
                    logging.debug(
                        "Unknown text command at {offset} - command: {command} on map_id={map_id}"
                        .format(
                            offset=hex(offset),
                            command=hex(ord(rom[offset])),
                            map_id=map_id,
                        )
                    )

                # end at the first unknown command
                end = True
            commands[command_counter] = command
            command_counter += 1
        total_text_commands += len(commands)

        text_count += 1
        #if text_count >= max_texts:
        #    sys.exit()

        self.commands = commands
        self.last_address = offset
        script_parse_table[original_address:offset] = self
        all_texts.append(self)
        self.size = self.byte_count = self.last_address - original_address
        return commands

    def get_dependencies(self, recompute=False, global_dependencies=set()):
        global_dependencies.update(self.dependencies)
        return self.dependencies

    def to_asm(self, label=None):
        address = self.address
        start_address = address
        if label == None: label = self.label.name
        # using deepcopy because otherwise additional @s get appended each time
        # like to the end of the text for TextScript(0x5cf3a)
        commands = deepcopy(self.commands)
        # apparently this isn't important anymore?
        needs_to_begin_with_0 = True
        # start with zero please
        byte_count = 0
        # where we store all output
        output = ""
        had_text_end_byte = False
        had_text_end_byte_57_58 = False
        had_db_last = False
        xspacing = ""
        # reset this pretty fast..
        first_line = True
        # for each command..
        for this_command in commands.keys():
            if not "lines" in commands[this_command].keys():
                command = commands[this_command]
                if not "type" in command.keys():
                    logging.debug("ERROR in command: {0}".format(command))
                    continue # dunno what to do here?

                if   command["type"] == 0x1: # TX_RAM
                    p1 = command["pointer"][0]
                    p2 = command["pointer"][1]

                    # remember to account for big endian -> little endian
                    output += "\n" + xspacing + "TX_RAM $%.2x%.2x" %(p2, p1)
                    byte_count += 3
                    had_db_last = False
                elif command["type"] == 0x17: # TX_FAR
                    #p1 = command["pointer"][0]
                    #p2 = command["pointer"][1]
                    output += "\n" + xspacing + "TX_FAR _" + label + " ; " + hex(command["pointer"])
                    byte_count += 4 # $17, bank, address word
                    had_db_last = False
                elif command["type"] == 0x9: # TX_RAM_HEX2DEC
                    # address, read_byte
                    output += "\n" + xspacing + "TX_NUM $%.2x%.2x, $%.2x" % (command["address"][1], command["address"][0], command["read_byte"])
                    had_db_last = False
                    byte_count += 4
                elif command["type"] == 0x50 and not had_text_end_byte:
                    # had_text_end_byte helps us avoid repeating $50s
                    if had_db_last:
                        output += ", $50"
                    else:
                        output += "\n" + xspacing + "db $50"
                    byte_count += 1
                    had_db_last = True
                elif command["type"] in [0x57, 0x58] and not had_text_end_byte_57_58:
                    if had_db_last:
                        output += ", $%.2x" % (command["type"])
                    else:
                        output += "\n" + xspacing + "db $%.2x" % (command["type"])
                    byte_count += 1
                    had_db_last = True
                elif command["type"] in [0x57, 0x58] and had_text_end_byte_57_58:
                    pass # this is ok
                elif command["type"] == 0x50 and had_text_end_byte:
                    pass # this is also ok
                elif command["type"] == 0x0b:
                    if had_db_last:
                        output += ", $0b"
                    else:
                        output += "\n" + xspacing + "db $0B"
                    byte_count += 1
                    had_db_last = True
                elif command["type"] == 0x11:
                    if had_db_last:
                        output += ", $11"
                    else:
                        output += "\n" + xspacing + "db $11"
                    byte_count += 1
                    had_db_last = True
                elif command["type"] == 0x6: # wait for keypress
                    if had_db_last:
                        output += ", $6"
                    else:
                        output += "\n" + xspacing + "db $6"
                    byte_count += 1
                    had_db_last = True
                else:
                    logging.debug("ERROR in command: {0}".format(hex(command["type"])))
                    had_db_last = False

                # everything else is for $0s, really
                continue
            lines = commands[this_command]["lines"]

            # reset this in case we have non-$0s later
            had_db_last = False

            # add the ending byte to the last line- always seems $57
            # this should already be in there, but it's not because of a bug in the text parser
            lines[len(lines.keys())-1].append(commands[len(commands.keys())-1]["type"])

            first = True # first byte
            for line_id in lines:
                line = lines[line_id]
                output += xspacing + "db "
                if first and needs_to_begin_with_0:
                    output += "$0, "
                    first = False
                    byte_count += 1

                quotes_open = False
                first_byte = True
                was_byte = False
                for byte in line:
                    if byte == 0x50:
                        had_text_end_byte = True # don't repeat it
                    if byte in [0x58, 0x57]:
                        had_text_end_byte_57_58 = True

                    if byte in chars.chars:
                        if not quotes_open and not first_byte: # start text
                            output += ", \""
                            quotes_open = True
                            first_byte = False
                        if not quotes_open and first_byte: # start text
                            output += "\""
                            quotes_open = True
                        output += chars.chars[byte]
                    elif byte in constant_abbreviation_bytes:
                        if quotes_open:
                            output += "\""
                            quotes_open = False
                        if not first_byte:
                            output += ", "
                        output += constant_abbreviation_bytes[byte]
                    else:
                        if quotes_open:
                            output += "\""
                            quotes_open = False

                        # if you want the ending byte on the last line
                        #if not (byte == 0x57 or byte == 0x50 or byte == 0x58):
                        if not first_byte:
                            output += ", "

                        output += "$" + hex(byte)[2:]
                        was_byte = True

                        # add a comma unless it's the end of the line
                        #if byte_count+1 != len(line):
                        #    output += ", "

                    first_byte = False
                    byte_count += 1
                # close final quotes
                if quotes_open:
                    output += "\""
                    quotes_open = False

                output += "\n"
        #include_newline = "\n"
        #if len(output)!=0 and output[-1] == "\n":
        #    include_newline = ""
        #output += include_newline + "; " + hex(start_address) + " + " + str(byte_count) + " bytes = " + hex(start_address + byte_count)
        if len(output) > 0 and output[-1] == "\n":
            output = output[:-1]
        self.size = self.byte_count = byte_count
        return output
