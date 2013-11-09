# -*- coding: utf-8 -*-
"""
VBA automation
"""

import os
import sys
import re
import string
from copy import copy

import unittest

# for converting bytes to readable text
from pokemontools.chars import chars

from pokemontools.map_names import map_names

import keyboard

# just use a default config for now until the globals are removed completely
import pokemontools.configuration as configuration
config = configuration.Config()
project_path = config.path
save_state_path = config.save_state_path
rom_path = config.rom_path

if not os.path.exists(rom_path):
    raise Exception("rom_path is not configured properly; edit vba_config.py? " + str(rom_path))

import vba_wrapper

vba = vba_wrapper.VBA(rom_path)
registers = vba_wrapper.core.registers.Registers(vba)

button_masks = vba_wrapper.core.VBA.button_masks
button_combiner = vba_wrapper.core.VBA.button_combine

def translate_chars(charz):
    result = ""
    for each in charz:
        result += chars[each]
    return result

def press(buttons, holdsteps=1, aftersteps=1):
    """
    Press a button.

    Use steplimit to say for how many steps you want to press
    the button (try leaving it at the default, 1).
    """
    if hasattr(buttons, "__len__"):
        number = button_combiner(buttons)
    elif isinstance(buttons, int):
        number = buttons
    else:
        number = buttons
    for step_counter in range(0, holdsteps):
        Gb.step(number)

    # clear the button press
    if aftersteps > 0:
        for step_counter in range(0, aftersteps):
            Gb.step(0)

def call(bank, address):
    """
    Jumps into a function at a certain address.

    Go into the start menu, pause the game and try call(1, 0x1078) to see a
    string printed to the screen.
    """
    push = [
        registers.pc,
        registers.hl,
        registers.de,
        registers.bc,
        registers.af,
        0x3bb7,
    ]

    for value in push:
        registers.sp -= 2
        set_memory_at(registers.sp + 1, value >> 8)
        set_memory_at(registers.sp, value & 0xFF)
        if get_memory_range(registers.sp, 2) != [value & 0xFF, value >> 8]:
            print "desired memory values: " + str([value & 0xFF, value >> 8] )
            print "actual memory values: " + str(get_memory_range(registers.sp , 2))
            print "wrong value at " + hex(registers.sp) + " expected " + hex(value) + " but got " + hex(get_memory_at(registers.sp))

    if bank != 0:
        registers["af"] = (bank << 8) | (registers["af"] & 0xFF)
        registers["hl"] = address
        registers["pc"] = 0x2d63 # FarJump
    else:
        registers["pc"] = address

def get_stack():
    """
    Return a list of functions on the stack.
    """
    addresses = []
    sp = registers.sp

    for x in range(0, 11):
        sp = sp - (2 * x)
        hi = get_memory_at(sp + 1)
        lo = get_memory_at(sp)
        address = ((hi << 8) | lo)
        addresses.append(address)

    return addresses

class crystal:
    """
    Just a simple namespace to store a bunch of functions for Pokémon Crystal.
    """

    @staticmethod
    def text_wait(step_size=1, max_wait=200, sfx_limit=0, debug=False, callback=None):
        """
        Presses the "A" button when text is done being drawn to screen.

        The `debug` parameter is only useful when debugging this function. It
        enables the `max_wait` feature, which causes the function to exit
        instead of hanging around.

        The `sfx_limit` parameter is useful for when the player is given an
        item during the text. Set it to 1 to not treat the sound as the end of
        text. The next loop around it will return to the normal behavior of the
        function.

        :param step_size: number of steps per wait loop
        :param max_wait: number of wait loops to perform
        """
        while max_wait > 0:
            hi = get_memory_at(registers.sp + 1)
            lo = get_memory_at(registers.sp)
            address = ((hi << 8) | lo)

            if address in range(0xa1b, 0xa46) + range(0xaaf, 0xaf5): #  0xaef:
                print "pressing, then breaking.. address is: " + str(hex(address))

                # set CurSFX
                set_memory_at(0xc2bf, 0)

                press("a", holdsteps=10, aftersteps=1)

                # check if CurSFX is SFX_READ_TEXT_2
                if get_memory_at(0xc2bf) == 0x8:
                    print "cursfx is set to SFX_READ_TEXT_2, looping.."
                    return crystal.text_wait(step_size=step_size, max_wait=max_wait, debug=debug, callback=callback, sfx_limit=sfx_limit)
                else:
                    if sfx_limit > 0:
                        sfx_limit = sfx_limit - 1
                        print "decreasing sfx_limit"
                    else:
                        # probably the last textbox in a sequence
                        print "cursfx is not set to SFX_READ_TEXT_2, so: breaking"

                        break
            else:
                stack = get_stack()

                # yes/no box or the name selection box
                if address in range(0xa46, 0xaaf):
                    print "probably at a yes/no box.. exiting."
                    break

                # date/time box (day choice)
                # 0x47ab is the one from the intro, 0x49ab is the one from mom.
                elif 0x47ab in stack or 0x49ab in stack: # was any([x in stack for x in range(0x46EE, 0x47AB)])
                    print "probably at a date/time box ? exiting."
                    break

                # "How many minutes?" selection box
                elif 0x4826 in stack:
                    print "probably at a \"How many minutes?\" box ? exiting."
                    break

                else:
                    nstep(step_size)

            # if there is a callback, then call the callback and exit when the
            # callback returns True. This is especially useful during the
            # OakSpeech intro where textboxes are running constantly, and then
            # suddenly the player can move around. One way to detect that is to
            # set callback to a function that returns
            # "vba.get_memory_at(0xcfb1) != 0".
            if callback != None:
                result = callback()
                if result == True:
                    print "callback returned True, exiting"
                    return

            # only useful when debugging. When this is left on, text that
            # takes a while to print to screen will cause this function to
            # exit.
            if debug == True:
                max_wait = max_wait - 1

        if max_wait == 0:
            print "max_wait was hit"

    @staticmethod
    def walk_through_walls_slow():
        memory = get_memory()
        memory[0xC2FA] = 0
        memory[0xC2FB] = 0
        memory[0xC2FC] = 0
        memory[0xC2FD] = 0
        set_memory(memory)

    @staticmethod
    def walk_through_walls():
        """
        Lets the player walk all over the map.

        These values are probably reset by some of the map/collision
        functions when you move on to a new location, so this needs
        to be executed each step/tick if continuous walk-through-walls
        is desired.
        """
        set_memory_at(0xC2FA, 0)
        set_memory_at(0xC2FB, 0)
        set_memory_at(0xC2FC, 0)
        set_memory_at(0xC2FD, 0)

    #@staticmethod
    #def set_enemy_level(level):
    #    set_memory_at(0xd213, level)

    @staticmethod
    def nstep(steplimit=500):
        """
        Steps the CPU forward and calls some functions in between each step.

        (For example, to manipulate memory.) This is pretty slow.
        """
        for step_counter in range(0, steplimit):
            crystal.walk_through_walls()
            #call(0x1, 0x1078)
            step()

    @staticmethod
    def disable_triggers():
        set_memory_at(0x23c4, 0xAF)
        set_memory_at(0x23d0, 0xAF);

    @staticmethod
    def disable_callbacks():
        set_memory_at(0x23f2, 0xAF)
        set_memory_at(0x23fe, 0xAF)

    @staticmethod
    def get_map_group_id():
        """
        Returns the current map group.
        """
        return get_memory_at(0xdcb5)

    @staticmethod
    def get_map_id():
        """
        Returns the map number of the current map.
        """
        return get_memory_at(0xdcb6)

    @staticmethod
    def get_map_name():
        """
        Figures out the current map name.
        """
        map_group_id = crystal.get_map_group_id()
        map_id = crystal.get_map_id()
        return map_names[map_group_id][map_id]["name"]

    @staticmethod
    def get_xy():
        """
        (x, y) coordinates of player on map.

        Relative to top-left corner of map.
        """
        x = get_memory_at(0xdcb8)
        y = get_memory_at(0xdcb7)
        return (x, y)

    @staticmethod
    def menu_select(id=1):
        """
        Sets the cursor to the given pokemon in the player's party.

        This is under Start -> PKMN. This is useful for selecting a
        certain pokemon with fly or another skill.

        This probably works on other menus.
        """
        set_memory_at(0xcfa9, id)

    @staticmethod
    def is_in_battle():
        """
        Checks whether or not we're in a battle.
        """
        return (get_memory_at(0xd22d) != 0) or crystal.is_in_link_battle()

    @staticmethod
    def is_in_link_battle():
        return get_memory_at(0xc2dc) != 0

    @staticmethod
    def unlock_flypoints():
        """
        Unlocks different destinations for flying.

        Note: this might start at 0xDCA4 (minus one on all addresses), but not
        sure.
        """
        set_memory_at(0xDCA5, 0xFF)
        set_memory_at(0xDCA6, 0xFF)
        set_memory_at(0xDCA7, 0xFF)
        set_memory_at(0xDCA8, 0xFF)

    @staticmethod
    def get_gender():
        """
        Returns 'male' or 'female'.
        """
        gender = get_memory_at(0xD472)
        if gender == 0:
            return "male"
        elif gender == 1:
            return "female"
        else:
            return gender

    @staticmethod
    def get_player_name():
        """
        Returns the 7 characters making up the player's name.
        """
        bytez = get_memory_range(0xD47D, 7)
        name = translate_chars(bytez)
        return name

    @staticmethod
    def warp(map_group_id, map_id, x, y):
        set_memory_at(0xdcb5, map_group_id)
        set_memory_at(0xdcb6, map_id)
        set_memory_at(0xdcb7, y)
        set_memory_at(0xdcb8, x)
        set_memory_at(0xd001, 0xFF)
        set_memory_at(0xff9f, 0xF1)
        set_memory_at(0xd432, 1)
        set_memory_at(0xd434, 0 & 251)

    @staticmethod
    def warp_pokecenter():
        crystal.warp(1, 1, 3, 3)
        crystal.nstep(200)

    @staticmethod
    def masterballs():
        # masterball
        set_memory_at(0xd8d8, 1)
        set_memory_at(0xd8d9, 99)

        # ultraball
        set_memory_at(0xd8da, 2)
        set_memory_at(0xd8db, 99)

        # pokeballs
        set_memory_at(0xd8dc, 5)
        set_memory_at(0xd8dd, 99)

    @staticmethod
    def get_text():
        """
        Returns alphanumeric text on the screen.

        Other characters will not be shown.
        """
        output = ""
        tiles = get_memory_range(0xc4a0, 1000)
        for each in tiles:
            if each in chars.keys():
                thing = chars[each]
                acceptable = False

                if len(thing) == 2:
                    portion = thing[1:]
                else:
                    portion = thing

                if portion in string.printable:
                    acceptable = True

                if acceptable:
                    output += thing

        # remove extra whitespace
        output = re.sub(" +", " ", output)
        output = output.strip()

        return output

    @staticmethod
    def keyboard_apply(button_sequence):
        """
        Applies a sequence of buttons to the on-screen keyboard.
        """
        for buttons in button_sequence:
            press(buttons)
            nstep(2)
            press([])

    @staticmethod
    def write(something="TrAiNeR"):
        """
        Types out a word.

        Uses a planning algorithm to do this in the most efficient way possible.
        """
        button_sequence = keyboard.plan_typing(something)
        crystal.keyboard_apply([[x] for x in button_sequence])

    @staticmethod
    def set_partymon2():
        """
        This causes corruption, so it's not working yet.
        """
        memory = get_memory()
        memory[0xdcd7] = 2
        memory[0xdcd9] = 0x7

        memory[0xdd0f] = 0x7
        memory[0xdd10] = 0x1

        # moves
        memory[0xdd11] = 0x1
        memory[0xdd12] = 0x2
        memory[0xdd13] = 0x3
        memory[0xdd14] = 0x4

        # id
        memory[0xdd15] = 0x1
        memory[0xdd16] = 0x2

        # experience
        memory[0xdd17] = 0x2
        memory[0xdd18] = 0x3
        memory[0xdd19] = 0x4

        # hp
        memory[0xdd1a] = 0x5
        memory[0xdd1b] = 0x6

        # current hp
        memory[0xdd31] = 0x10
        memory[0xdd32] = 0x25

        # max hp
        memory[0xdd33] = 0x10
        memory[0xdd34] = 0x40

        set_memory(memory)

    @staticmethod
    def wait_for_script_running(debug=False, limit=1000):
        """
        Wait until ScriptRunning isn't -1.
        """
        while limit > 0:
            if get_memory_at(0xd438) != 255:
                print "script is done executing"
                return
            else:
                step()

            if debug:
                limit = limit - 1

        if limit == 0:
            print "limit ran out"

    @staticmethod
    def move(cmd):
        """
        Attempt to move the player.
        """
        press(cmd, holdsteps=10, aftersteps=0)
        press([])

        memory = get_memory()
        #while memory[0xd4e1] == 2 and memory[0xd042] != 0x3e:
        while memory[0xd043] in [0, 1, 2, 3]:
        #while memory[0xd043] in [0, 1, 2, 3] or memory[0xd042] != 0x3e:
            nstep(10)
            memory = get_memory()

class TestEmulator(unittest.TestCase):
    def test_PlaceString(self):
        call(0, 0x1078)

        # where to draw the text
        registers["hl"] = 0xc4a0

        # what text to read from
        registers["de"] = 0x1276

        nstep(10)

        text = crystal.get_text()

        self.assertTrue("TRAINER" in text)

class TestWriter(unittest.TestCase):
    def test_very_basic(self):
        button_sequence = keyboard.plan_typing("an")
        expected_result = ["select", "a", "d", "r", "r", "r", "r", "a"]

        self.assertEqual(len(expected_result), len(button_sequence))
        self.assertEqual(expected_result, button_sequence)

if __name__ == "__main__":
    unittest.main()
