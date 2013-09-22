# -*- coding: utf-8 -*-
"""
Programmatic speedrun of Pokémon Crystal
"""
import os

import pokemontools.configuration as configuration

# bring in the emulator and basic tools
import vba as _vba

def skippable(func):
    """
    Makes a function skippable.

    Saves the state before and after the function runs. Pass "skip=True" to the
    function to load the previous save state from when the function finished.
    """
    def wrapped_function(*args, **kwargs):
        self = args[0]
        skip = True

        if "skip" in kwargs.keys():
            skip = kwargs["skip"]
            del kwargs["skip"]

        # override skip if there's no save
        if skip:
            full_name = func.__name__ + "-end.sav"
            if not os.path.exists(os.path.join(self.config.save_state_path, full_name)):
                skip = False

        return_value = None

        if not skip:
            self.cry.save_state(func.__name__ + "-start", override=True)
            return_value = func(*args, **kwargs)
            self.cry.save_state(func.__name__ + "-end", override=True)
        elif skip:
            self.cry.vba.state = self.cry.load_state(func.__name__ + "-end")

        return return_value
    return wrapped_function

class Runner(object):
    """
    ``Runner`` is used to represent a set of functions that control an instance
    of the emulator. This allows for automated runs of games.
    """
    pass

class SpeedRunner(Runner):
    def __init__(self, cry=None, config=None):
        self.cry = cry

        if not config:
            config = configuration.Config()

        self.config = config

    def setup(self):
        if not self.cry:
            self.cry = _vba.crystal(config=config)

    def main(self):
        """
        Start the game.
        """
        # get past the opening sequence
        self.skip_intro()

        # walk to mom and handle her text
        self.handle_mom()

        # walk outside into new bark town
        self.walk_into_new_bark_town()

        # walk to elm and do whatever he wants
        self.handle_elm("totodile")

        self.new_bark_level_grind(10, skip=False)

    @skippable
    def skip_intro(self):
        """
        Skip the game boot intro sequence.
        """

        # copyright sequence
        self.cry.nstep(400)

        # skip the ditto sequence
        self.cry.vba.press("a")
        self.cry.nstep(100)

        # skip the start screen
        self.cry.vba.press("start")
        self.cry.nstep(100)

        # click "new game"
        self.cry.vba.press("a", hold=50, after=1)

        # skip text up to "Are you a boy? Or are you a girl?"
        self.cry.text_wait()

        # select "Boy"
        self.cry.vba.press("a", hold=50, after=1)

        # text until "What time is it?"
        self.cry.text_wait()

        # select 10 o'clock
        self.cry.vba.press("a", hold=50, after=1)

        # yes i mean it
        self.cry.vba.press("a", hold=50, after=1)

        # "How many minutes?" 0 min.
        self.cry.vba.press("a", hold=50, after=1)

        # "Who! 0 min.?" yes/no select yes
        self.cry.vba.press("a", hold=50, after=1)

        # read text until name selection
        self.cry.text_wait()

        # select "Chris"
        self.cry.vba.press("d", hold=10, after=1)
        self.cry.vba.press("a", hold=50, after=1)

        def overworldcheck():
            """
            A basic check for when the game starts.
            """
            return self.cry.vba.memory[0xcfb1] != 0

        # go until the introduction is done
        self.cry.text_wait(callback=overworldcheck)

        return

    @skippable
    def handle_mom(self):
        """
        Walk to mom. Handle her speech and questions.
        """

        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")

        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")

        self.cry.move("d")
        self.cry.move("d")

        # move into mom's line of sight
        self.cry.move("d")

        # let mom talk until "What day is it?"
        self.cry.text_wait()

        # "What day is it?" Sunday
        self.cry.vba.press("a", hold=10) # Sunday

        self.cry.text_wait()

        # "SUNDAY, is it?" yes/no
        self.cry.vba.press("a", hold=10) # yes

        self.cry.text_wait()

        # "Is it Daylight Saving Time now?" yes/no
        self.cry.vba.press("a", hold=10) # yes

        self.cry.text_wait()

        # "AM DST, is that OK?" yes/no
        self.cry.vba.press("a", hold=10) # yes

        # text until "know how to use the PHONE?" yes/no
        self.cry.text_wait()

        # press yes
        self.cry.vba.press("a", hold=10)

        # wait until mom is done talking
        self.cry.text_wait()

        # wait until the script is done running
        self.cry.wait_for_script_running()

        return

    @skippable
    def walk_into_new_bark_town(self):
        """
        Walk outside after talking with mom.
        """

        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("l")
        self.cry.move("l")

        # walk outside
        self.cry.move("d")

    @skippable
    def handle_elm(self, starter_choice):
        """
        Walk to Elm's Lab and get a starter.
        """

        # walk to the lab
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("u")
        self.cry.move("u")

        # walk into the lab
        self.cry.move("u")

        # talk to elm
        self.cry.text_wait()

        # "that I recently caught." yes/no
        self.cry.vba.press("a", hold=10) # yes

        # talk to elm some more
        self.cry.text_wait()

        # talking isn't done yet..
        self.cry.text_wait()
        self.cry.text_wait()
        self.cry.text_wait()

        # wait until the script is done running
        self.cry.wait_for_script_running()

        # move toward the pokeballs
        self.cry.move("r")

        # move to cyndaquil
        self.cry.move("r")

        moves = 0

        if starter_choice.lower() == "cyndaquil":
            moves = 0
        if starter_choice.lower() == "totodile":
            moves = 1
        else:
            moves = 2

        for each in range(0, moves):
            self.cry.move("r")

        # face the pokeball
        self.cry.move("u")

        # select it
        self.cry.vba.press("a", hold=10, after=0)

        # wait for the image to pop up
        self.cry.text_wait()

        # wait for the image to close
        self.cry.text_wait()

        # wait for the yes/no box
        self.cry.text_wait()

        # press yes
        self.cry.vba.press("a", hold=10, after=0)

        # wait for elm to talk a bit
        self.cry.text_wait()

        # TODO: why didn't that finish his talking?
        self.cry.text_wait()

        # give a nickname? yes/no
        self.cry.vba.press("d", hold=10, after=0) # move to "no"
        self.cry.vba.press("a", hold=10, after=0) # no

        # TODO: why didn't this wait until he was completely done?
        self.cry.text_wait()
        self.cry.text_wait()

        # get the phone number
        self.cry.text_wait()

        # talk with elm a bit more
        self.cry.text_wait()

        # TODO: and again.. wtf?
        self.cry.text_wait()

        # wait until the script is done running
        self.cry.wait_for_script_running()

        # move down
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")

        # move into the researcher's line of sight
        self.cry.move("d")

        # get the potion from the person
        self.cry.text_wait()
        self.cry.text_wait()

        # wait for the script to end
        self.cry.wait_for_script_running()

        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")

        # go outside
        self.cry.move("d")

        return

    @skippable
    def new_bark_level_grind(self, level):
        """
        Do level grinding in New Bark.

        Starting just outside of Elm's Lab, do some level grinding until the
        first partymon level is equal to the given value..
        """

        # walk to the grass area
        self.new_bark_level_grind_walk_to_grass(skip=False)

        # TODO: walk around in grass, handle battles
        walk = ["d", "d", "u", "d", "u", "d"]
        for direction in walk:
            self.cry.move(direction)

        # wait for wild battle to completely start
        self.cry.text_wait()

        attacks = 5

        while attacks > 0:
            # FIGHT
            self.cry.vba.press("a", hold=10, after=1)

            # wait to select a move
            self.cry.text_wait()

            # SCRATCH
            self.cry.vba.press("a", hold=10, after=1)

            # wait for the move to be over
            self.cry.text_wait()

            hp = ((self.cry.vba.get_memory_at(0xd218) << 8) | self.cry.vba.get_memory_at(0xd217))
            print "enemy hp is: " + str(hp)

            if hp == 0:
                print "enemy hp is zero, exiting"
                break
            else:
                print "enemy hp is: " + str(hp)

            attacks = attacks - 1

        while self.cry.vba.get_memory_at(0xd22d) != 0:
            self.cry.vba.press("a", hold=10, after=1)

        # wait for the map to finish loading
        self.cry.vba.nstep(50)

        print "okay, back in the overworld"

        # move up
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")

        # move into new bark town
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")

        # move up
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")

        # move to the door
        self.cry.move("r")
        self.cry.move("r")
        self.cry.move("r")

        # walk in
        self.cry.move("u")

        # move up to the healing thing
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("u")
        self.cry.move("l")
        self.cry.move("l")

        # face it
        self.cry.move("u")

        # interact
        self.cry.vba.press("a", hold=10, after=1)

        # wait for yes/no box
        self.cry.text_wait()

        # press yes
        self.cry.vba.press("a", hold=10, after=1)

        # TODO: when is healing done?

        # wait until the script is done running
        self.cry.wait_for_script_running()

        # wait for it to be really really done
        self.cry.vba.nstep(50)

        self.cry.move("r")
        self.cry.move("r")

        # move to the door
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")

        # walk out
        self.cry.move("d")

        # check partymon1 level
        if self.cry.vba.get_memory_at(0xdcfe) < level:
            self.new_bark_level_grind(level, skip=False)
        else:
            return

    @skippable
    def new_bark_level_grind_walk_to_grass(self):
        """
        Move to just above the grass from outside Elm's lab.
        """

        self.cry.move("d")
        self.cry.move("d")

        self.cry.move("l")
        self.cry.move("l")

        self.cry.move("d")
        self.cry.move("d")

        self.cry.move("l")
        self.cry.move("l")

        # move to route 29 past the trees
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")
        self.cry.move("l")

        # move to just above the grass
        self.cry.move("d")
        self.cry.move("d")
        self.cry.move("d")

def main():
    runner = SpeedRunner()
    runner.setup()
    return runner.main()

if __name__ == "__main__":
    main()
