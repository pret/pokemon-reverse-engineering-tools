"""
Some old methods rescued from crystal.py
"""

import pokemontools.pointers as pointers

map_header_byte_size = 9

all_map_headers = []

def old_parse_map_script_header_at(address, map_group=None, map_id=None, debug=True):
    logging.debug("starting to parse the map's script header..")
    #[[Number1 of pointers] Number1 * [2byte pointer to script][00][00]]
    ptr_line_size = 4 #[2byte pointer to script][00][00]
    trigger_ptr_cnt = ord(rom[address])
    trigger_pointers = helpers.grouper(rom_interval(address+1, trigger_ptr_cnt * ptr_line_size, strings=False), count=ptr_line_size)
    triggers = {}
    for index, trigger_pointer in enumerate(trigger_pointers):
        logging.debug("parsing a trigger header...")
        byte1 = trigger_pointer[0]
        byte2 = trigger_pointer[1]
        ptr   = byte1 + (byte2 << 8)
        trigger_address = pointers.calculate_pointer(ptr, pointers.calculate_bank(address))
        trigger_script  = parse_script_engine_script_at(trigger_address, map_group=map_group, map_id=map_id)
        triggers[index] = {
            "script": trigger_script,
            "address": trigger_address,
            "pointer": {"1": byte1, "2": byte2},
        }

    # bump ahead in the byte stream
    address += trigger_ptr_cnt * ptr_line_size + 1

    #[[Number2 of pointers] Number2 * [hook number][2byte pointer to script]]
    callback_ptr_line_size = 3
    callback_ptr_cnt = ord(rom[address])
    callback_ptrs = helpers.grouper(rom_interval(address+1, callback_ptr_cnt * callback_ptr_line_size, strings=False), count=callback_ptr_line_size)
    callback_pointers = {}
    callbacks = {}
    for index, callback_line in enumerate(callback_ptrs):
        logging.debug("parsing a callback header..")
        hook_byte = callback_line[0] # 1, 2, 3, 4, 5
        callback_byte1 = callback_line[1]
        callback_byte2 = callback_line[2]
        callback_ptr = callback_byte1 + (callback_byte2 << 8)
        callback_address = pointers.calculate_pointer(callback_ptr, pointers.calculate_bank(address))
        callback_script = parse_script_engine_script_at(callback_address)
        callback_pointers[len(callback_pointers.keys())] = [hook_byte, callback_ptr]
        callbacks[index] = {
            "script": callback_script,
            "address": callback_address,
            "pointer": {"1": callback_byte1, "2": callback_byte2},
        }

    # XXX do these triggers/callbacks call asm or script engine scripts?
    return {
        #"trigger_ptr_cnt": trigger_ptr_cnt,
        "trigger_pointers": trigger_pointers,
        #"callback_ptr_cnt": callback_ptr_cnt,
        #"callback_ptr_scripts": callback_ptrs,
        "callback_pointers": callback_pointers,
        "trigger_scripts": triggers,
        "callback_scripts": callbacks,
    }


def old_parse_map_header_at(address, map_group=None, map_id=None, debug=True):
    """parses an arbitrary map header at some address"""
    logging.debug("parsing a map header at {0}".format(hex(address)))
    bytes = rom_interval(address, map_header_byte_size, strings=False, debug=debug)
    bank = bytes[0]
    tileset = bytes[1]
    permission = bytes[2]
    second_map_header_address = pointers.calculate_pointer(bytes[3] + (bytes[4] << 8), 0x25)
    location_on_world_map = bytes[5] # pokegear world map location
    music = bytes[6]
    time_of_day = bytes[7]
    fishing_group = bytes[8]

    map_header = {
        "bank": bank,
        "tileset": tileset,
        "permission": permission, # map type?
        "second_map_header_pointer": {"1": bytes[3], "2": bytes[4]},
        "second_map_header_address": second_map_header_address,
        "location_on_world_map": location_on_world_map, # area
        "music": music,
        "time_of_day": time_of_day,
        "fishing": fishing_group,
    }
    logging.debug("second map header address is {0}".format(hex(second_map_header_address)))
    map_header["second_map_header"] = old_parse_second_map_header_at(second_map_header_address, debug=debug)
    event_header_address = map_header["second_map_header"]["event_address"]
    script_header_address = map_header["second_map_header"]["script_address"]
    # maybe event_header and script_header should be put under map_header["second_map_header"]
    map_header["event_header"] = old_parse_map_event_header_at(event_header_address, map_group=map_group, map_id=map_id, debug=debug)
    map_header["script_header"] = old_parse_map_script_header_at(script_header_address, map_group=map_group, map_id=map_id, debug=debug)
    return map_header

all_second_map_headers = []

def old_parse_second_map_header_at(address, map_group=None, map_id=None, debug=True):
    """each map has a second map header"""
    bytes = rom_interval(address, second_map_header_byte_size, strings=False)
    border_block = bytes[0]
    height = bytes[1]
    width = bytes[2]
    blockdata_bank = bytes[3]
    blockdata_pointer = bytes[4] + (bytes[5] << 8)
    blockdata_address = pointers.calculate_pointer(blockdata_pointer, blockdata_bank)
    script_bank = bytes[6]
    script_pointer = bytes[7] + (bytes[8] << 8)
    script_address = pointers.calculate_pointer(script_pointer, script_bank)
    event_bank = script_bank
    event_pointer = bytes[9] + (bytes[10] << 8)
    event_address = pointers.calculate_pointer(event_pointer, event_bank)
    connections = bytes[11]
    return {
        "border_block": border_block,
        "height": height,
        "width": width,
        "blockdata_bank": blockdata_bank,
        "blockdata_pointer": {"1": bytes[4], "2": bytes[5]},
        "blockdata_address": blockdata_address,
        "script_bank": script_bank,
        "script_pointer": {"1": bytes[7], "2": bytes[8]},
        "script_address": script_address,
        "event_bank": event_bank,
        "event_pointer": {"1": bytes[9], "2": bytes[10]},
        "event_address": event_address,
        "connections": connections,
    }

def old_parse_warp_bytes(some_bytes, debug=True):
    """parse some number of warps from the data"""
    assert len(some_bytes) % warp_byte_size == 0, "wrong number of bytes"
    warps = []
    for bytes in helpers.grouper(some_bytes, count=warp_byte_size):
        y = int(bytes[0], 16)
        x = int(bytes[1], 16)
        warp_to = int(bytes[2], 16)
        map_group = int(bytes[3], 16)
        map_id = int(bytes[4], 16)
        warps.append({
            "y": y,
            "x": x,
            "warp_to": warp_to,
            "map_group": map_group,
            "map_id": map_id,
        })
    return warps

def old_parse_signpost_bytes(some_bytes, bank=None, map_group=None, map_id=None, debug=True):
    assert len(some_bytes) % signpost_byte_size == 0, "wrong number of bytes"
    signposts = []
    for bytes in helpers.grouper(some_bytes, count=signpost_byte_size):
        y = int(bytes[0], 16)
        x = int(bytes[1], 16)
        func = int(bytes[2], 16)

        additional = {}
        if func in [0, 1, 2, 3, 4]:
            logging.debug(
                "parsing signpost script.. signpost is at x={x} y={y}"
                .format(x=x, y=y)
            )
            script_ptr_byte1 = int(bytes[3], 16)
            script_ptr_byte2 = int(bytes[4], 16)
            script_pointer = script_ptr_byte1 + (script_ptr_byte2 << 8)

            script_address = None
            script = None

            script_address = pointers.calculate_pointer(script_pointer, bank)
            script = parse_script_engine_script_at(script_address, map_group=map_group, map_id=map_id)

            additional = {
            "script_ptr": script_pointer,
            "script_pointer": {"1": script_ptr_byte1, "2": script_ptr_byte2},
            "script_address": script_address,
            "script": script,
            }
        elif func in [5, 6]:
            logging.debug(
                "parsing signpost script.. signpost is at x={x} y={y}"
                .format(x=x, y=y)
            )

            ptr_byte1 = int(bytes[3], 16)
            ptr_byte2 = int(bytes[4], 16)
            pointer = ptr_byte1 + (ptr_byte2 << 8)
            address = pointers.calculate_pointer(pointer, bank)
            bit_table_byte1 = ord(rom[address])
            bit_table_byte2 = ord(rom[address+1])
            script_ptr_byte1 = ord(rom[address+2])
            script_ptr_byte2 = ord(rom[address+3])
            script_address = calculate_pointer_from_bytes_at(address+2, bank=bank)
            script = parse_script_engine_script_at(script_address, map_group=map_group, map_id=map_id)

            additional = {
            "bit_table_bytes": {"1": bit_table_byte1, "2": bit_table_byte2},
            "script_ptr": script_ptr_byte1 + (script_ptr_byte2 << 8),
            "script_pointer": {"1": script_ptr_byte1, "2": script_ptr_byte2},
            "script_address": script_address,
            "script": script,
            }
        else:
            logging.debug(".. type 7 or 8 signpost not parsed yet.")

        spost = {
            "y": y,
            "x": x,
            "func": func,
        }
        spost.update(additional)
        signposts.append(spost)
    return signposts

def old_parse_people_event_bytes(some_bytes, address=None, map_group=None, map_id=None, debug=True):
    """parse some number of people-events from the data
    see http://hax.iimarck.us/files/scriptingcodes_eng.htm#Scripthdr

    For example, map 1.1 (group 1 map 1) has four person-events.

        37 05 07 06 00 FF FF 00 00 02 40 FF FF
        3B 08 0C 05 01 FF FF 00 00 05 40 FF FF
        3A 07 06 06 00 FF FF A0 00 08 40 FF FF
        29 05 0B 06 00 FF FF 00 00 0B 40 FF FF
    """
    assert len(some_bytes) % people_event_byte_size == 0, "wrong number of bytes"

    # address is not actually required for this function to work...
    bank = None 
    if address:
        bank = pointers.calculate_bank(address)

    people_events = [] 
    for bytes in helpers.grouper(some_bytes, count=people_event_byte_size):
        pict = int(bytes[0], 16)
        y = int(bytes[1], 16)    # y from top + 4
        x = int(bytes[2], 16)    # x from left + 4
        face = int(bytes[3], 16) # 0-4 for regular, 6-9 for static facing
        move = int(bytes[4], 16)
        clock_time_byte1 = int(bytes[5], 16)
        clock_time_byte2 = int(bytes[6], 16)
        color_function_byte = int(bytes[7], 16) # Color|Function
        trainer_sight_range = int(bytes[8], 16)

        lower_bits = color_function_byte & 0xF
        #lower_bits_high = lower_bits >> 2
        #lower_bits_low = lower_bits & 3
        higher_bits = color_function_byte >> 4
        #higher_bits_high = higher_bits >> 2
        #higher_bits_low = higher_bits & 3

        is_regular_script = lower_bits == 00
        # pointer points to script
        is_give_item = lower_bits == 01
        # pointer points to [Item no.][Amount]
        is_trainer = lower_bits == 02
        # pointer points to trainer header

        # goldmap called these next two bytes "text_block" and "text_bank"?
        script_pointer_byte1 = int(bytes[9], 16)
        script_pointer_byte2 = int(bytes[10], 16)
        script_pointer = script_pointer_byte1 + (script_pointer_byte2 << 8)
        # calculate the full address by assuming it's in the current bank
        # but what if it's not in the same bank?
        extra_portion = {}
        if bank:
            ptr_address = pointers.calculate_pointer(script_pointer, bank)
            if is_regular_script:
                logging.debug(
                    "parsing a person-script at x={x} y={y} address={address}"
                    .format(
                        x=(x-4),
                        y=(y-4),
                        address=hex(ptr_address),
                    )
                )
                script = parse_script_engine_script_at(ptr_address, map_group=map_group, map_id=map_id)
                extra_portion = {
                    "script_address": ptr_address,
                    "script": script,
                    "event_type": "script",
                }
            if is_give_item:
                logging.debug("not parsing give item event.. [item id][quantity]")
                extra_portion = {
                    "event_type": "give_item",
                    "give_item_data_address": ptr_address,
                    "item_id": ord(rom[ptr_address]),
                    "item_qty": ord(rom[ptr_address+1]),
                }
            if is_trainer:
                logging.debug(
                    "parsing a trainer (person-event) at x={x} y={y}"
                    .format(x=x, y=y)
                )
                parsed_trainer = parse_trainer_header_at(ptr_address, map_group=map_group, map_id=map_id)
                extra_portion = {
                    "event_type": "trainer",
                    "trainer_data_address": ptr_address,
                    "trainer_data": parsed_trainer,
                }

        # XXX not sure what's going on here
        # bit no. of bit table 1 (hidden if set)
        # note: FFFF for none
        when_byte = int(bytes[11], 16)
        hide = int(bytes[12], 16)

        bit_number_of_bit_table1_byte2 = int(bytes[11], 16)
        bit_number_of_bit_table1_byte1 = int(bytes[12], 16)
        bit_number_of_bit_table1 = bit_number_of_bit_table1_byte1 + (bit_number_of_bit_table1_byte2 << 8)

        people_event = {
            "pict": pict,
            "y": y,                      # y from top + 4
            "x": x,                      # x from left + 4
            "face": face,                # 0-4 for regular, 6-9 for static facing
            "move": move,
            "clock_time": {"1": clock_time_byte1,
                           "2": clock_time_byte2},       # clock/time setting byte 1
            "color_function_byte": color_function_byte,  # Color|Function
            "trainer_sight_range": trainer_sight_range,  # trainer range of sight
            "script_pointer": {"1": script_pointer_byte1,
                               "2": script_pointer_byte2},

            #"text_block": text_block,   # script pointer byte 1
            #"text_bank": text_bank,     # script pointer byte 2
            "when_byte": when_byte,      # bit no. of bit table 1 (hidden if set)
            "hide": hide,                # note: FFFF for none

            "is_trainer": is_trainer,
            "is_regular_script": is_regular_script,
            "is_give_item": is_give_item,
        }
        people_event.update(extra_portion)
        people_events.append(people_event)
    return people_events

def old_parse_trainer_header_at(address, map_group=None, map_id=None, debug=True):
    bank = pointers.calculate_bank(address)
    bytes = rom_interval(address, 12, strings=False)
    bit_number = bytes[0] + (bytes[1] << 8)
    trainer_group = bytes[2]
    trainer_id = bytes[3]
    text_when_seen_ptr = calculate_pointer_from_bytes_at(address+4, bank=bank)
    text_when_seen = parse_text_engine_script_at(text_when_seen_ptr, map_group=map_group, map_id=map_id, debug=debug)
    text_when_trainer_beaten_ptr = calculate_pointer_from_bytes_at(address+6, bank=bank)
    text_when_trainer_beaten = parse_text_engine_script_at(text_when_trainer_beaten_ptr, map_group=map_group, map_id=map_id, debug=debug)

    if [ord(rom[address+8]), ord(rom[address+9])] == [0, 0]:
        script_when_lost_ptr = 0
        script_when_lost = None
    else:
        logging.debug("parsing script-when-lost")
        script_when_lost_ptr = calculate_pointer_from_bytes_at(address+8, bank=bank)
        script_when_lost = None
        silver_avoids = [0xfa53]
        if script_when_lost_ptr > 0x4000 and not script_when_lost_ptr in silver_avoids:
            script_when_lost = parse_script_engine_script_at(script_when_lost_ptr, map_group=map_group, map_id=map_id, debug=debug)

    logging.debug("parsing script-talk-again") # or is this a text?
    script_talk_again_ptr = calculate_pointer_from_bytes_at(address+10, bank=bank)
    script_talk_again = None
    if script_talk_again_ptr > 0x4000:
        script_talk_again = parse_script_engine_script_at(script_talk_again_ptr, map_group=map_group, map_id=map_id, debug=debug)

    return {
        "bit_number": bit_number,
        "trainer_group": trainer_group,
        "trainer_id": trainer_id,
        "text_when_seen_ptr": text_when_seen_ptr,
        "text_when_seen": text_when_seen,
        "text_when_trainer_beaten_ptr": text_when_trainer_beaten_ptr,
        "text_when_trainer_beaten": text_when_trainer_beaten,
        "script_when_lost_ptr": script_when_lost_ptr,
        "script_when_lost": script_when_lost,
        "script_talk_again_ptr": script_talk_again_ptr,
        "script_talk_again": script_talk_again,
    }

def old_parse_map_event_header_at(address, map_group=None, map_id=None, debug=True):
    """parse crystal map event header byte structure thing"""
    returnable = {}

    bank = pointers.calculate_bank(address)

    logging.debug("event header address is {0}".format(hex(address)))
    filler1 = ord(rom[address])
    filler2 = ord(rom[address+1])
    returnable.update({"1": filler1, "2": filler2})

    # warps
    warp_count = ord(rom[address+2])
    warp_byte_count = warp_byte_size * warp_count
    warps = rom_interval(address+3, warp_byte_count)
    after_warps = address + 3 + warp_byte_count
    returnable.update({"warp_count": warp_count, "warps": old_parse_warp_bytes(warps)})

    # triggers (based on xy location)
    trigger_count = ord(rom[after_warps])
    trigger_byte_count = trigger_byte_size * trigger_count
    triggers = rom_interval(after_warps+1, trigger_byte_count)
    after_triggers = after_warps + 1 + trigger_byte_count
    returnable.update({"xy_trigger_count": trigger_count, "xy_triggers": old_parse_xy_trigger_bytes(triggers, bank=bank, map_group=map_group, map_id=map_id)})

    # signposts
    signpost_count = ord(rom[after_triggers])
    signpost_byte_count = signpost_byte_size * signpost_count
    signposts = rom_interval(after_triggers+1, signpost_byte_count)
    after_signposts = after_triggers + 1 + signpost_byte_count
    returnable.update({"signpost_count": signpost_count, "signposts": old_parse_signpost_bytes(signposts, bank=bank, map_group=map_group, map_id=map_id)})

    # people events
    people_event_count = ord(rom[after_signposts])
    people_event_byte_count = people_event_byte_size * people_event_count
    people_events_bytes = rom_interval(after_signposts+1, people_event_byte_count)
    people_events = old_parse_people_event_bytes(people_events_bytes, address=after_signposts+1, map_group=map_group, map_id=map_id)
    returnable.update({"people_event_count": people_event_count, "people_events": people_events})

    return returnable
