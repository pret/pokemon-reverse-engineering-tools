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

def translate_chars(charz):
    """
    Translate a string from the in-game format to readable form. This is
    accomplished through the same lookup table that the preprocessors use.
    """
    result = ""
    for each in charz:
        result += chars[each]
    return result

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

    def call(self, bank, address):
        """
        Jumps into a function at a certain address.

        Go into the start menu, pause the game and try call(1, 0x1078) to see a
        string printed to the screen.
        """
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

                self.vba.press("a", hold=10, after=1)

                # check if CurSFX is SFX_READ_TEXT_2
                if self.vba.read_memory_at(0xc2bf) == 0x8:
                    print "cursfx is set to SFX_READ_TEXT_2, looping.."
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
                    print "probably at a date/time box ? exiting."
                    break

                # "How many minutes?" selection box
                elif 0x4826 in stack:
                    print "probably at a \"How many minutes?\" box ? exiting."
                    break

                else:
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

    #@staticmethod
    #def set_enemy_level(level):
    #    vba.write_memory_at(0xd213, level)

    def nstep(self, steplimit=500):
        """
        Steps the CPU forward and calls some functions in between each step.

        (For example, to manipulate memory.) This is pretty slow.
        """
        for step_counter in range(0, steplimit):
            self.walk_through_walls()
            #call(0x1, 0x1078)
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

    def get_text(self, chars=chars):
        """
        Returns alphanumeric text on the screen.

        Other characters will not be shown.
        """
        output = ""
        tiles = self.vba.memory[0xc4a0:0xc4a0 + 1000]
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

    def broken_start_random_battle(self):
        self.push_stack([self.registers.pc])
        self.registers["pc"] = address % 0x4000
        self.call(address / 0x4000, address % 0x4000)

    def start_trainer_battle(self, trainer_group=0x1, trainer_id=0x1):
        """
        This will fail after the first mon is defeated.
        """
        Script_startbattle_address = 0x97436

        # setup the battle
        memory = self.vba.memory
        memory[0xd459] = 0x81
        memory[0xd22f] = trainer_group
        memory[0xd231] = trainer_id
        self.vba.memory = memory

        self.call(0x25, (Script_startbattle_address % 0x4000) + 0x4000)

    def broken_start_random_battle_by_rocksmash_battle_script(self):
        """
        This doesn't start a battle.
        """
        CallScript_address = 0x261f
        RockSmashBattleScript_address = 0x97cf9
        ScriptRunning = 0xd438
        ScriptBank = 0xd439
        ScriptPos = 0xd43a

        memory = self.vba.memory
        memory[ScriptBank] = RockSmashBattleScript_address / 0x4000
        memory[ScriptPos] = ((RockSmashBattleScript_address % 0x4000 + 0x4000) & 0xff00) >> 8
        memory[ScriptPos+1] = ((RockSmashBattleScript_address % 0x4000 + 0x4000) & 0xff)
        memory[ScriptRunning] = 0xff
        self.vba.memory = memory

        self.vba.registers["af"] = ((RockSmashBattleScript_address / 0x4000) << 8) | (self.vba.registers.af & 0xff)
        self.vba.registers["hl"] = (RockSmashBattleScript_address % 0x4000) + 0x4000
        self.call(0x0, CallScript_address)

    #def attempt_start_battle_by_startbattle(self):
    #    StartBattle_address = 0x3f4c1
    #    self.call(StartBattle_address / 0x4000, (StartBattle_address % 0x4000) + 0x4000)

    #def attempt_start_random_battle_by_wild_battle(self):
    #    start_wild_battle = 0x3f4dd
    #    #self.call(start_wild_battle / 0x4000, start_wild_battle % 0x4000)
    #    #self.vba.registers["pc"] = ...

    def old_crap(self):
        CallScript_address = 0x261f
        RockSmashBattleScript_address = 0x97cf9
        RockSmashEncounter_address = 0x97cc0
        StartBattle_address = 0x3f4c1
        ScriptRunning = 0xd438
        ScriptBank = 0xd439
        ScriptPos = 0xd43a
        start_wild_battle = 0x3f4dd
        script = 0x1a1dc6

        #self.call(StartBattle_address / 0x4000, StartBattle_address % 0x4000)
        #self.call(RockSmashEncounter_address / 0x4000, RockSmashEncounter_address % 0x4000)

        #self.push_stack([self.registers.pc])
        #memory[ScriptBank] = script / 0x4000
        #memory[ScriptPos] = ((script % 0x4000) & 0xff00) >> 8
        #memory[ScriptPos+1] = ((script % 0x4000) & 0xff)
        #memory[ScriptRunning] = 0xff

        #self.call(start_wild_battle / 0x4000, start_wild_battle % 0x4000)

        #self.vba.memory = memory
