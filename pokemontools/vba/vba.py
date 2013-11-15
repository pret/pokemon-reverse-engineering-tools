# -*- coding: utf-8 -*-
"""
VBA automation
"""

import os
import sys
import re
import string
from copy import copy

# for converting bytes to readable text
from pokemontools.chars import (
    chars,
)

from pokemontools.map_names import (
    map_names,
)

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

button_masks = vba_wrapper.core.VBA.button_masks
button_combiner = vba_wrapper.core.VBA.button_combine

def calculate_bank(address):
    """
    Which bank does this address exist in?
    """
    return address / 0x4000

def calculate_address(address):
    """
    Gives the relative address once the bank is loaded.

    This is not the same as the calculate_pointer in the
    pokemontools.crystal.pointers module.
    """
    return (address % 0x4000) + 0x4000

def translate_chars(charz):
    """
    Translate a string from the in-game format to readable form. This is
    accomplished through the same lookup table that the preprocessors use.
    """
    result = ""
    for each in charz:
        result += chars[each]
    return result

def translate_text(text, chars=chars):
    """
    Converts text to the in-game byte coding.
    """
    output = []
    for given_char in text:
        for (byte, char) in chars.iteritems():
            if char == given_char:
                output.append(byte)
                break
        else:
            raise Exception(
                "no match for {0}".format(given_char)
            )
    return output

class crystal(object):
    """
    Just a simple namespace to store a bunch of functions for Pokémon Crystal.
    There can only be one running instance of the emulator per process because
    it's a poorly written shared library.
    """

    def __init__(self, config=None):
        """
        Launch the VBA controller.
        """
        if not config:
            config = configuration.Config()

        self.config = config

        self.vba = vba_wrapper.VBA(self.config.rom_path)
        self.registers = vba_wrapper.core.registers.Registers(self.vba)

        if not os.path.exists(self.config.rom_path):
            raise Exception("rom_path is not configured properly; edit vba_config.py? " + str(rom_path))

    def shutdown(self):
        """
        Reset the emulator.
        """
        self.vba.shutdown()

    def save_state(self, name, state=None, override=False):
        """
        Saves the given state to save_state_path.

        The file format must be ".sav", and this will be appended to your
        string if necessary.
        """
        if state == None:
            state = self.vba.state

        if len(name) < 4 or name[-4:] != ".sav":
            name += ".sav"

        save_path = os.path.join(self.config.save_state_path, name)

        if not override and os.path.exists(save_path):
            raise Exception("oops, save state path already exists: {0}".format(save_path))

        with open(save_path, "wb") as file_handler:
            file_handler.write(state)

    def load_state(self, name, loadit=True):
        """
        Read a state from file based on the name of the state.

        Looks in save_state_path for a file with this name (".sav" is
        optional).

        @param loadit: whether or not to set the emulator to this state
        """
        save_path = os.path.join(self.config.save_state_path, name)

        if not os.path.exists(save_path):
            if len(name) < 4 or name[-4:] != ".sav":
                name += ".sav"
                save_path = os.path.join(self.config.save_state_path, name)

        with open(save_path, "rb") as file_handler:
            state = file_handler.read()

        if loadit:
            self.vba.state = state

        return state

    def call(self, address, bank=None):
        """
        Jumps into a function at a certain address.

        Go into the start menu, pause the game and try call(1, 0x1078) to see a
        string printed to the screen.
        """
        if bank is None:
            bank = calculate_bank(address)

        push = [
            self.registers.pc,
            self.registers.hl,
            self.registers.de,
            self.registers.bc,
            self.registers.af,
            0x3bb7,
        ]

        self.push_stack(push)

        if bank != 0:
            self.registers["af"] = (bank << 8) | (self.registers["af"] & 0xFF)
            self.registers["hl"] = address
            self.registers["pc"] = 0x2d63 # FarJump
        else:
            self.registers["pc"] = address

    def push_stack(self, push):
        for value in push:
            self.registers["sp"] -= 2
            self.vba.write_memory_at(self.registers.sp + 1, value >> 8)
            self.vba.write_memory_at(self.registers.sp, value & 0xFF)
            if list(self.vba.memory[self.registers.sp : self.registers.sp + 2]) != [value & 0xFF, value >> 8]:
                print "desired memory values: " + str([value & 0xFF, value >> 8] )
                print "actual memory values: " + str(list(self.vba.memory[self.registers.sp : self.registers.sp + 2]))
                print "wrong value at " + hex(self.registers.sp) + " expected " + hex(value) + " but got " + hex(self.vba.read_memory_at(self.registers.sp))

    def get_stack(self):
        """
        Return a list of functions on the stack.
        """
        addresses = []
        sp = self.registers.sp

        for x in range(0, 11):
            sp = sp - (2 * x)
            hi = self.vba.read_memory_at(sp + 1)
            lo = self.vba.read_memory_at(sp)
            address = ((hi << 8) | lo)
            addresses.append(address)

        return addresses

    def inject_asm_into_rom(self, asm=[], address=0x75 * 0x4000, has_finished_address=0xdb75):
        """
        Writes asm to the loaded ROM. Calls the asm.

        :param address: ROM address for where to store the injected asm script.
        The default value is an address in pokecrystal that isn't used for
        anything.

        :param has_finished_address: address for where to store whether the
        script executed or not. This value is restored when the script has been
        confirmed to work. It's conceivable that some injected asm might need
        to change that address if the asm needs to access the original wram
        value itself.
        """
        if len(asm) > 0x4000:
            raise Exception("too much asm")

        # temporarily use wram
        cached_wram_value = self.vba.memory[has_finished_address]

        # set the value at has_finished_address to 0
        reset_wram_mem = list(self.vba.memory)
        reset_wram_mem[has_finished_address] = 0
        self.vba.memory = reset_wram_mem

        # set a value to indicate that the script has executed
        set_has_finished = [
            # push af
            0xf5,

            # ld a, 1
            0x3e, 1,

            # ld [has_finished], a
            0xea, has_finished_address & 0xff, has_finished_address >> 8,

            # pop af
            0xf1,

            # ret
            0xc9,
        ]

        # TODO: check if asm ends with a byte that causes a return or call or
        # other "ender". Raise an exception if it already returns on its own.

        # combine the given asm with the setter bytes
        total_asm = asm + set_has_finished

        # get a copy of the current rom
        rom = list(self.vba.rom)

        # inject the asm
        rom[address : address + len(total_asm)] = total_asm

        # set the rom with the injected asm
        self.vba.rom = rom

        # call the injected asm
        self.call(calculate_address(address), bank=calculate_bank(address))

        # make the emulator step forward
        self.vba.step(count=20)

        # check if the script has executed (see below)
        current_mem = self.vba.memory

        # reset the wram value to its original value
        another_mem = list(self.vba.memory)
        another_mem[has_finished_address] = cached_wram_value
        self.vba.memory = another_mem

        # check if the script has actually executed
        # TODO: should this raise an exception if the script didn't finish?
        if current_mem[has_finished_address] == 0:
            return False
        elif current_mem[has_finished_address] == 1:
            return True
        else:
            raise Exception(
                "has_finished_address at {has_finished_address} was overwritten with an unexpected value {value}".format(
                    has_finished_address=hex(has_finished_address),
                    value=current_mem[has_finished_address],
                )
            )

    def inject_asm_into_wram(self, asm=[], address=0xdfcf):
        """
        Writes asm to memory. Makes the emulator run the asm.

        This function will append "ret" to the list of bytes. Before returning,
        it updates the value at the first byte to indicate that the function
        has executed.

        The first byte at the given address is reserved for whether the asm has
        finished executing.
        """
        memory = list(self.vba.memory)

        # the first byte is reserved for whether the script has finished
        has_finished = address
        memory[has_finished] = 0

        # the second byte is where the script will be stored
        script_address = address + 1

        # TODO: error checking; make sure the last byte doesn't already return.
        # Use some functions from gbz80disasm to perform this check.

        # set a value to indicate that the script has executed
        set_has_finished = [
            # push af
            0xf5,

            # ld a, 1
            0x3e, 1,

            # ld [has_finished], a
            0xea, has_finished & 0xff, has_finished >> 8,

            # pop af
            0xf1,

            # ret
            0xc9,
        ]

        # append the last opcodes to the script
        asm = bytearray(asm) + bytearray(set_has_finished)

        memory[script_address : script_address + len(asm)] = asm
        self.vba.memory = memory

        # make the emulator call the script
        self.call(script_address, bank=0)

        # make the emulator step forward
        self.vba.step(count=50)

        # check if the script has executed
        # TODO: should this raise an exception if the script didn't finish?
        if self.vba.memory[has_finished] == 0:
            return False
        elif self.vba.memory[has_finished] == 1:
            return True
        else:
            raise Exception(
                "has_finished at {has_finished} was overwritten with an unexpected value {value}".format(
                    has_finished=hex(has_finished),
                    value=self.vba.memory[has_finished],
                )
            )

    def call_script(self, address, bank=None, wram=False, force=False):
        """
        Sets wram values so that the engine plays a script.

        :param address: address of the map script
        :param bank: override for bank calculation (based on address)
        :param wram: force bank to 0
        :param force: override an already-running script
        """

        ScriptFlags      = 0xd434
        ScriptMode       = 0xd437
        ScriptRunning    = 0xd438
        ScriptBank       = 0xd439
        ScriptPos        = 0xd43a
        NumScriptParents = 0xd43c
        ScriptParents    = 0xd43d

        num_possible_parents = 4
        len_parent = 3

        mem = list(self.vba.memory)

        if mem[ScriptRunning] == 0xff:
            if force:
                # wipe the parent routine array
                mem[NumScriptParents] = 0
                for i in xrange(num_possible_parents * len_parent):
                    mem[ScriptParents + i] = 0
            else:
                raise Exception("a script is already running, use force=True")

        if wram:
            bank = 0
        elif not bank:
            bank = calculate_bank(address)
            address = address % 0x4000 + 0x4000 * bool(bank)

        mem[ScriptFlags]  |= 4
        mem[ScriptMode]    = 1
        mem[ScriptRunning] = 0xff

        mem[ScriptBank]    = bank
        mem[ScriptPos]     = address % 0x100
        mem[ScriptPos+1]   = address / 0x100

        self.vba.memory = mem

    def text_wait(self, step_size=1, max_wait=200, sfx_limit=0, debug=False, callback=None):
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
            hi = self.vba.read_memory_at(self.registers.sp + 1)
            lo = self.vba.read_memory_at(self.registers.sp)
            address = ((hi << 8) | lo)

            if address in range(0xa1b, 0xa46) + range(0xaaf, 0xaf5): #  0xaef:
                print "pressing, then breaking.. address is: " + str(hex(address))

                # set CurSFX
                self.vba.write_memory_at(0xc2bf, 0)

                self.vba.press("a", hold=10, after=50)

                # check if CurSFX is SFX_READ_TEXT_2
                if self.vba.read_memory_at(0xc2bf) == 0x8:
                    if "CANCEL Which" in self.get_text():
                        print "probably the 'switch pokemon' menu"
                        return
                    else:
                        print "cursfx is set to SFX_READ_TEXT_2, looping.."
                        print self.get_text()
                        return self.text_wait(step_size=step_size, max_wait=max_wait, debug=debug, callback=callback, sfx_limit=sfx_limit)
                else:
                    if sfx_limit > 0:
                        sfx_limit = sfx_limit - 1
                        print "decreasing sfx_limit"
                    else:
                        # probably the last textbox in a sequence
                        print "cursfx is not set to SFX_READ_TEXT_2, so: breaking"

                        break
            else:
                stack = self.get_stack()

                # yes/no box or the name selection box
                if address in range(0xa46, 0xaaf):
                    print "probably at a yes/no box.. exiting."
                    break

                # date/time box (day choice)
                # 0x47ab is the one from the intro, 0x49ab is the one from mom.
                elif 0x47ab in stack or 0x49ab in stack: # was any([x in stack for x in range(0x46EE, 0x47AB)])
                    if not self.is_in_battle():
                        print "probably at a date/time box ? exiting."
                        break

                # "How many minutes?" selection box
                elif 0x4826 in stack:
                    print "probably at a \"How many minutes?\" box ? exiting."
                    break

                self.vba.step(count=step_size)

            # if there is a callback, then call the callback and exit when the
            # callback returns True. This is especially useful during the
            # OakSpeech intro where textboxes are running constantly, and then
            # suddenly the player can move around. One way to detect that is to
            # set callback to a function that returns
            # "vba.read_memory_at(0xcfb1) != 0".
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

    def walk_through_walls_slow(self):
        memory = self.vba.memory
        memory[0xC2FA] = 0
        memory[0xC2FB] = 0
        memory[0xC2FC] = 0
        memory[0xC2FD] = 0
        self.vba.memory = memory

    def walk_through_walls(self):
        """
        Lets the player walk all over the map.

        These values are probably reset by some of the map/collision
        functions when you move on to a new location, so this needs
        to be executed each step/tick if continuous walk-through-walls
        is desired.
        """
        self.vba.write_memory_at(0xC2FA, 0)
        self.vba.write_memory_at(0xC2FB, 0)
        self.vba.write_memory_at(0xC2FC, 0)
        self.vba.write_memory_at(0xC2FD, 0)

    def lower_enemy_hp(self):
        """
        Dramatically lower the enemy's HP.
        """
        self.vba.write_memory_at(0xd216, 0)
        self.vba.write_memory_at(0xd217, 1)

    def set_battle_mon_hp(self, hp):
        """
        Set the BattleMonHP variable to the given hp.
        """
        self.vba.write_memory_at(0xc63c, hp / 0x100)
        self.vba.write_memory_at(0xc63c + 1, hp % 0x100)

    def nstep(self, steplimit=500):
        """
        Steps the CPU forward and calls some functions in between each step.

        (For example, to manipulate memory.) This is pretty slow.
        """
        for step_counter in range(0, steplimit):
            self.walk_through_walls()
            #call(0x1078)
            self.vba.step()

    def disable_triggers(self):
        self.vba.write_memory_at(0x23c4, 0xAF)
        self.vba.write_memory_at(0x23d0, 0xAF);

    def disable_callbacks(self):
        self.vba.write_memory_at(0x23f2, 0xAF)
        self.vba.write_memory_at(0x23fe, 0xAF)

    def get_map_group_id(self):
        """
        Returns the current map group.
        """
        return self.vba.read_memory_at(0xdcb5)

    def get_map_id(self):
        """
        Returns the map number of the current map.
        """
        return self.vba.read_memory_at(0xdcb6)

    def get_map_name(self, map_names=map_names):
        """
        Figures out the current map name.
        """
        map_group_id = self.get_map_group_id()
        map_id = self.get_map_id()
        return map_names[map_group_id][map_id]["name"]

    def get_xy(self):
        """
        (x, y) coordinates of player on map.

        Relative to top-left corner of map.
        """
        x = self.vba.read_memory_at(0xdcb8)
        y = self.vba.read_memory_at(0xdcb7)
        return (x, y)

    def menu_select(self, id=1):
        """
        Sets the cursor to the given pokemon in the player's party.

        This is under Start -> PKMN. This is useful for selecting a
        certain pokemon with fly or another skill.

        This probably works on other menus.
        """
        self.vba.write_memory_at(0xcfa9, id)

    def is_in_battle(self):
        """
        Checks whether or not we're in a battle.
        """
        return (self.vba.read_memory_at(0xd22d) != 0) or self.is_in_link_battle()

    def is_in_link_battle(self):
        return self.vba.read_memory_at(0xc2dc) != 0

    def is_trainer_switch_prompt(self):
        """
        Checks if the game is currently displaying the yes/no prompt for
        whether or not to switch pokemon. This happens when the trainer is
        switching pokemon out.
        """
        # TODO: this method should return False if the game options have been
        # set to not use the battle switching style.

        # get on-screen text
        text = self.get_text()

        requirements = [
            "YES",
            "NO",
            "Will ",
            "change POKMON?",
        ]

        return all([requirement in text for requirement in requirements])

    def is_wild_switch_prompt(self):
        """
        Detects if the battle is waiting for the player to choose whether or
        not to continue to fight the wild pokemon.
        """
        # get on-screen text
        screen_text = self.get_text()

        requirements = [
            "YES",
            "NO",
            "Use next POKMON?",
        ]

        return all([requirement in screen_text for requirement in requirements])

    def is_switch_prompt(self):
        """
        Detects both the trainer-style switch prompt and the wild-style switch
        prompt. This is the yes/no prompt for whether to switch pokemon.
        """
        return self.is_trainer_switch_prompt() or self.is_wild_switch_prompt()

    def unlock_flypoints(self):
        """
        Unlocks different destinations for flying.

        Note: this might start at 0xDCA4 (minus one on all addresses), but not
        sure.
        """
        self.vba.write_memory_at(0xDCA5, 0xFF)
        self.vba.write_memory_at(0xDCA6, 0xFF)
        self.vba.write_memory_at(0xDCA7, 0xFF)
        self.vba.write_memory_at(0xDCA8, 0xFF)

    def set_battle_type(self, battle_type):
        """
        Changes the battle type value.
        """
        self.vba.write_memory_at(0xd230, battle_type)

    def get_gender(self):
        """
        Returns 'male' or 'female'.
        """
        gender = self.vba.read_memory_at(0xD472)
        if gender == 0:
            return "male"
        elif gender == 1:
            return "female"
        else:
            return gender

    def get_player_name(self):
        """
        Returns the 7 characters making up the player's name.
        """
        bytez = self.vba.memory[0xD47D:0xD47D + 7]
        name = translate_chars(bytez)
        return name

    def warp(self, map_group_id, map_id, x, y):
        """
        Warp into another map.
        """
        self.vba.write_memory_at(0xdcb5, map_group_id)
        self.vba.write_memory_at(0xdcb6, map_id)
        self.vba.write_memory_at(0xdcb7, y)
        self.vba.write_memory_at(0xdcb8, x)
        self.vba.write_memory_at(0xd001, 0xFF)
        self.vba.write_memory_at(0xff9f, 0xF1)
        self.vba.write_memory_at(0xd432, 1)
        self.vba.write_memory_at(0xd434, 0 & 251)

    def warp_pokecenter(self):
        """
        Warp straight into a pokecenter.
        """
        self.warp(1, 1, 3, 3)
        self.nstep(200)

    def masterballs(self):
        """
        Deposit some pokeballs into the first few slots of the pack. This
        overrides whatever items were previously there.
        """
        # masterball
        self.vba.write_memory_at(0xd8d8, 1)
        self.vba.write_memory_at(0xd8d9, 99)

        # ultraball
        self.vba.write_memory_at(0xd8da, 2)
        self.vba.write_memory_at(0xd8db, 99)

        # pokeballs
        self.vba.write_memory_at(0xd8dc, 5)
        self.vba.write_memory_at(0xd8dd, 99)

    def get_text(self, chars=chars, offset=0, bounds=1000):
        """
        Returns alphanumeric text on the screen.

        Other characters will not be shown.
        """
        output = ""
        tiles = self.vba.memory[0xc4a0 + offset:0xc4a0 + offset + bounds]
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

    def is_showing_stats_screen(self):
        """
        This is meant to detect whether or not the stats screen is showing.
        This is the menu that pops up after leveling up.
        """
        # These words must be on the screen if the stats screen is currently
        # displayed.
        parts = [
            "ATTACK",
            "DEFENSE",
            "SPCL.ATK",
            "SPCL.DEF",
            "SPEED",
        ]

        # get the current text on the screen
        text = self.get_text()

        if all([part in text for part in parts]):
            return True
        else:
            return False

    def handle_stats_screen(self, force=False):
        """
        Attempts to bypass a stats screen. Set force=True if you want to make
        the attempt regardless of whether or not the system thinks a stats
        screen is showing.
        """
        if self.is_showing_stats_screen() or force:
            self.vba.press("a")
            self.vba.step(count=20)

    def keyboard_apply(self, button_sequence):
        """
        Applies a sequence of buttons to the on-screen keyboard.
        """
        for buttons in button_sequence:
            self.vba.press(buttons)

            if buttons == "select":
                self.vba.step(count=5)
            else:
                self.vba.step(count=2)

            self.vba.press([])

    def write(self, something="TrAiNeR"):
        """
        Types out a word.

        Uses a planning algorithm to do this in the most efficient way possible.
        """
        button_sequence = keyboard.plan_typing(something)
        self.vba.step(count=10)
        self.keyboard_apply([[x] for x in button_sequence])
        return button_sequence

    def set_partymon2(self):
        """
        This causes corruption, so it's not working yet.
        """
        memory = self.vba.memory
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

        self.vba.memory = memory

    def wait_for_script_running(self, debug=False, limit=1000):
        """
        Wait until ScriptRunning isn't -1.
        """
        while limit > 0:
            if self.vba.read_memory_at(0xd438) != 255:
                print "script is done executing"
                return
            else:
                self.vba.step()

            if debug:
                limit = limit - 1

        if limit == 0:
            print "limit ran out"

    def move(self, cmd):
        """
        Attempt to move the player.
        """
        if isinstance(cmd, list):
            for command in cmd:
                self.move(command)
        else:
            self.vba.press(cmd, hold=10, after=0)
            self.vba.press([])

            memory = self.vba.memory
            #while memory[0xd4e1] == 2 and memory[0xd042] != 0x3e:
            while memory[0xd043] in [0, 1, 2, 3]:
            #while memory[0xd043] in [0, 1, 2, 3] or memory[0xd042] != 0x3e:
                self.vba.step(count=10)
                memory = self.vba.memory

    def get_enemy_hp(self):
        """
        Returns the HP of the current enemy.
        """
        hp = ((self.vba.memory[0xd218] << 8) | self.vba.memory[0xd217])
        return hp

    def start_trainer_battle_lamely(self, map_group=0x1, map_id=0xc, x=6, y=8, direction="l", loop_limit=10):
        """
        Starts a trainer battle by warping into a map at the designated
        coordinates, pressing the direction button for a full walk step (which
        ideally should be blocked, this is mainly to establish direction), and
        then pressing "a" to initiate the trainer battle.

        Consider using start_trainer_battle instead.
        """
        self.warp(map_group, map_id, x, y)

        # finish loading the map, might not be necessary?
        self.nstep(100)

        # face towards the trainer (or whatever direction was specified). If
        # this direction is blocked, then this will only change which direction
        # the character is facing. However, if this direction is not blocked by
        # the map or by an npc, then this will cause an entire step to be
        # taken.
        self.vba.press([direction])

        # talk to the trainer, don't assume line of sight will be triggered
        self.vba.press(["a"])
        self.vba.press([])

        # trainer might talk, skip any text until the player can choose moves
        while not self.is_in_battle() and loop_limit > 0:
            self.text_wait()
            loop_limit -= 1

    def start_trainer_battle(self, trainer_group=0x1, trainer_id=0x1, text_win="YOU WIN", text_address=0xdb90):
        """
        Start a trainer battle with the trainer located by trainer_group and
        trainer_id.

        :param trainer_group: trainer group id
        :param trainer_id: trainer id within the group
        :param text_win: text to show if player wins
        :param text_address: where to store text_win in wram
        """
        # where the script will be written
        rom_address = 0x75 * 0x4000

        # battle win message
        translated_text = translate_text(text_win)

        # also include the first and last bytes needed for text
        translated_text = [0] + translated_text + [0x57]

        mem = self.vba.memory

        # create a backup of the current data
        wram_backup = mem[text_address : text_address + len(translated_text)]

        # manipulate the memory
        mem[text_address : text_address + len(translated_text)] = translated_text
        self.vba.memory = mem

        text_pointer_hi = text_address / 0x100
        text_pointer_lo = text_address % 0x100

        script = [
            # loadfont
            #0x47,

            # winlosstext address, address
            0x64, text_pointer_lo, text_pointer_hi, 0, 0,

            # loadtrainer group, id
            0x5e, trainer_group, trainer_id,

            # startbattle
            0x5f,

            # returnafterbattle
            0x60,

            # reloadmapmusic
            0x83,

            # reloadmap
            0x7B,
        ]

        # Now make the script restore wram at the end (after the text has been
        # used). The assumption here is that this particular subset of wram
        # data would not be needed during the bulk of the script.
        address = text_address
        for byte in wram_backup:
            address_hi = address / 0x100
            address_lo = address % 0x100

            script += [
                # loadvar
                0x1b, address_lo, address_hi, byte,
            ]

            address += 1

        script += [
            # end
            0x91,
        ]

        # Use a different wram address because the default is something related
        # to trainers.
        # use a higher loop limit because otherwise it doesn't start fast enough?
        self.inject_script_into_rom(asm=script, rom_address=rom_address, wram_address=0xdb75, limit=1000)

    def set_script(self, address):
        """
        Sets the current script in wram to whatever address.
        """
        ScriptBank = 0xd439
        ScriptPos = 0xd43a

        memory = self.vba.memory
        memory[ScriptBank] = calculate_bank(address)
        pointer = calculate_address(address)
        memory[ScriptPos] = (calculate_address(address) & 0xff00) >> 8
        memory[ScriptPos] = calculate_address(address) & 0xff

        # TODO: determine if this is necessary
        #memory[ScriptRunning] = 0xff

        self.vba.memory = memory

    def inject_script_into_rom(self, asm=[0x91], rom_address=0x75 * 0x4000, wram_address=0xd280, limit=50):
        """
        Writes a script to the ROM in a blank location. Calls call_script to
        make the game engine aware of the script. Then executes the script and
        looks for confirmation thta the script has started to run.

        The script must end itself.

        :param asm: scripting command bytes
        :param rom_address: rom location to write asm to
        :param wram_address: temporary storage for indicating if the script has
        started yet
        :param limit: number of frames to emulate before giving up on the start
        script
        """
        execution_pending = 0
        execution_started = 1
        valid_execution_states = (execution_pending, execution_started)

        # location for byte for whether script has started executing
        execution_indicator_address = wram_address

        # backup whatever exists at the current wram location
        backup_wram = self.vba.read_memory_at(execution_indicator_address)

        # .. and set it to "pending"
        self.vba.write_memory_at(execution_indicator_address, execution_pending)

        # initial script that runs first to tell python that execution started
        execution_indicator_script = [
            # loadvar address, value
            0x1b, execution_indicator_address & 0xff, execution_indicator_address >> 8, execution_started,
        ]

        # make the indicator script run before the user script
        full_script = execution_indicator_script + asm

        # inject the asm
        rom = list(self.vba.rom)
        rom[rom_address : rom_address + len(full_script)] = full_script

        # set the rom with the injected bytes
        self.vba.rom = rom

        # setup the script for execution
        self.call_script(rom_address)

        status = execution_pending
        while status != execution_started and limit > 0:
            # emulator time travel
            self.vba.step(count=1)

            # get latest wram
            status = self.vba.read_memory_at(execution_indicator_address)
            if status not in valid_execution_states:
                raise Exception(
                    "The execution indicator at {addr} has invalid state {value}".format(
                        addr=hex(execution_indicator_address),
                        value=status,
                    )
                )
            elif status == execution_started:
                break # hooray

            limit -= 1

        if status == execution_pending and limit == 0:
            raise Exception(
                "Emulation timeout while waiting for script to start."
            )

        # The script has started so it's okay to reset wram back to whatever it
        # was.
        self.vba.write_memory_at(execution_indicator_address, backup_wram)

        return True

    def givepoke(self, pokemon_id, level, nickname=None, wram=False):
        """
        Give the player a pokemon.
        """
        if isinstance(nickname, str):
            if len(nickname) == 0:
                raise Exception("invalid nickname")
            elif len(nickname) > 11:
                raise Exception("nickname too long")
        else:
            if not nickname:
                nickname = False
            else:
                raise Exception("nickname needs to be a string, False or None")

        # script to inject into wram
        script = [
            0x47, # loadfont
            #0x55, # keeptextopen

            # givepoke pokemon_id, level, 0, 0
            0x2d, pokemon_id, level, 0, 0,

            #0x54, # closetext
            0x49, # loadmovesprites
            0x91, # end
        ]

        # picked this region of wram because it looks like it's probably unused
        # in situations where givepoke will work.
        #address = 0xd073
        #address = 0xc000
        #address = 0xd8f1
        address = 0xd280

        if not wram:
            self.inject_script_into_rom(asm=script, wram_address=address)
        else:
            # TODO: move this into a separate function. Maybe use a context
            # manager to restore wram at the end.
            mem = list(self.vba.memory)
            backup_wram = mem[address : address + len(script)]
            mem[address : address + len(script)] = script
            self.vba.memory = mem

            self.call_script(address, wram=True)

        # "would you like to give it a nickname?"
        self.text_wait()

        if nickname:
            # yes
            self.vba.press("a", hold=10)

            # wait for the keyboard to appear
            # TODO: this wait should be moved into write()
            self.vba.step(count=20)

            # type the requested nicknameb
            self.write(nickname)

            self.vba.press("start", hold=5, after=10)
            self.vba.press("a", hold=5, after=50)
        else:
            # no nickname
            self.vba.press("b", hold=10, after=20)

        if wram:
            # Wait for the script to end in the engine before copying the original
            # wram values back in.
            self.vba.step(count=100)

            # reset whatever was in wram before this script was called
            mem = list(self.vba.memory)
            mem[address : address + len(script)] = backup_wram
            self.vba.memory = mem

    def start_random_battle_by_rocksmash_battle_script(self):
        """
        Initiates a wild battle using the same function that using rocksmash
        would call.
        """
        RockSmashBattleScript_address = 0x97cf9
        self.call_script(RockSmashBattleScript_address)
