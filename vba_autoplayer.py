# -*- coding: utf-8 -*-
"""
Programmatic speedrun of Pokémon Crystal
"""
import os

# bring in the emulator and basic tools
import vba

def main():
    """
    Start the game.
    """
    vba.load_rom()

    # get past the opening sequence
    skip_intro()

    # walk to mom and handle her text
    handle_mom()

    # walk outside into new bark town
    walk_into_new_bark_town()

    # walk to elm and do whatever he wants
    handle_elm("totodile")

    new_bark_level_grind(10, skip=False)

def skippable(func):
    """
    Makes a function skippable.

    Saves the state before and after the function runs.
    Pass "skip=True" to the function to load the previous save
    state from when the function finished.
    """
    def wrapped_function(*args, **kwargs):
        skip = True

        if "skip" in kwargs.keys():
            skip = kwargs["skip"]
            del kwargs["skip"]

        # override skip if there's no save
        if skip:
            full_name = func.__name__ + "-end.sav"
            if not os.path.exists(os.path.join(vba.save_state_path, full_name)):
                skip = False

        return_value = None

        if not skip:
            vba.save_state(func.__name__ + "-start", override=True)
            return_value = func(*args, **kwargs)
            vba.save_state(func.__name__ + "-end", override=True)
        elif skip:
            vba.set_state(vba.load_state(func.__name__ + "-end"))

        return return_value
    return wrapped_function

@skippable
def skip_intro():
    """
    Skip the game boot intro sequence.
    """

    # copyright sequence
    vba.nstep(400)

    # skip the ditto sequence
    vba.press("a")
    vba.nstep(100)

    # skip the start screen
    vba.press("start")
    vba.nstep(100)

    # click "new game"
    vba.press("a", holdsteps=50, aftersteps=1)

    # skip text up to "Are you a boy? Or are you a girl?"
    vba.crystal.text_wait()

    # select "Boy"
    vba.press("a", holdsteps=50, aftersteps=1)

    # text until "What time is it?"
    vba.crystal.text_wait()

    # select 10 o'clock
    vba.press("a", holdsteps=50, aftersteps=1)

    # yes i mean it
    vba.press("a", holdsteps=50, aftersteps=1)

    # "How many minutes?" 0 min.
    vba.press("a", holdsteps=50, aftersteps=1)

    # "Who! 0 min.?" yes/no select yes
    vba.press("a", holdsteps=50, aftersteps=1)

    # read text until name selection
    vba.crystal.text_wait()

    # select "Chris"
    vba.press("d", holdsteps=10, aftersteps=1)
    vba.press("a", holdsteps=50, aftersteps=1)

    def overworldcheck():
        """
        A basic check for when the game starts.
        """
        return vba.get_memory_at(0xcfb1) != 0

    # go until the introduction is done
    vba.crystal.text_wait(callback=overworldcheck)

    return

@skippable
def handle_mom():
    """
    Walk to mom. Handle her speech and questions.
    """

    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")

    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")

    vba.crystal.move("d")
    vba.crystal.move("d")

    # move into mom's line of sight
    vba.crystal.move("d")

    # let mom talk until "What day is it?"
    vba.crystal.text_wait()

    # "What day is it?" Sunday
    vba.press("a", holdsteps=10) # Sunday

    vba.crystal.text_wait()

    # "SUNDAY, is it?" yes/no
    vba.press("a", holdsteps=10) # yes

    vba.crystal.text_wait()

    # "Is it Daylight Saving Time now?" yes/no
    vba.press("a", holdsteps=10) # yes

    vba.crystal.text_wait()

    # "AM DST, is that OK?" yes/no
    vba.press("a", holdsteps=10) # yes

    # text until "know how to use the PHONE?" yes/no
    vba.crystal.text_wait()

    # press yes
    vba.press("a", holdsteps=10)

    # wait until mom is done talking
    vba.crystal.text_wait()

    # wait until the script is done running
    vba.crystal.wait_for_script_running()

    return

@skippable
def walk_into_new_bark_town():
    """
    Walk outside after talking with mom.
    """

    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("l")
    vba.crystal.move("l")

    # walk outside
    vba.crystal.move("d")

@skippable
def handle_elm(starter_choice):
    """
    Walk to Elm's Lab and get a starter.
    """

    # walk to the lab
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("u")
    vba.crystal.move("u")

    # walk into the lab
    vba.crystal.move("u")

    # talk to elm
    vba.crystal.text_wait()

    # "that I recently caught." yes/no
    vba.press("a", holdsteps=10) # yes

    # talk to elm some more
    vba.crystal.text_wait()

    # talking isn't done yet..
    vba.crystal.text_wait()
    vba.crystal.text_wait()
    vba.crystal.text_wait()

    # wait until the script is done running
    vba.crystal.wait_for_script_running()

    # move toward the pokeballs
    vba.crystal.move("r")

    # move to cyndaquil
    vba.crystal.move("r")

    moves = 0

    if starter_choice.lower() == "cyndaquil":
        moves = 0
    if starter_choice.lower() == "totodile":
        moves = 1
    else:
        moves = 2

    for each in range(0, moves):
        vba.crystal.move("r")

    # face the pokeball
    vba.crystal.move("u")

    # select it
    vba.press("a", holdsteps=10, aftersteps=0)

    # wait for the image to pop up
    vba.crystal.text_wait()

    # wait for the image to close
    vba.crystal.text_wait()

    # wait for the yes/no box
    vba.crystal.text_wait()

    # press yes
    vba.press("a", holdsteps=10, aftersteps=0)

    # wait for elm to talk a bit
    vba.crystal.text_wait()

    # TODO: why didn't that finish his talking?
    vba.crystal.text_wait()

    # give a nickname? yes/no
    vba.press("d", holdsteps=10, aftersteps=0) # move to "no"
    vba.press("a", holdsteps=10, aftersteps=0) # no

    # TODO: why didn't this wait until he was completely done?
    vba.crystal.text_wait()
    vba.crystal.text_wait()

    # get the phone number
    vba.crystal.text_wait()

    # talk with elm a bit more
    vba.crystal.text_wait()

    # TODO: and again.. wtf?
    vba.crystal.text_wait()

    # wait until the script is done running
    vba.crystal.wait_for_script_running()

    # move down
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")

    # move into the researcher's line of sight
    vba.crystal.move("d")

    # get the potion from the person
    vba.crystal.text_wait()
    vba.crystal.text_wait()

    # wait for the script to end
    vba.crystal.wait_for_script_running()

    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")

    # go outside
    vba.crystal.move("d")

    return

@skippable
def new_bark_level_grind(level):
    """
    Do level grinding in New Bark.

    Starting just outside of Elm's Lab, do some level grinding until the first
    partymon level is equal to the given value..
    """

    # walk to the grass area
    new_bark_level_grind_walk_to_grass(skip=False)

    # TODO: walk around in grass, handle battles
    walk = ["d", "d", "u", "d", "u", "d"]
    for direction in walk:
        vba.crystal.move(direction)

    # wait for wild battle to completely start
    vba.crystal.text_wait()

    attacks = 5

    while attacks > 0:
        # FIGHT
        vba.press("a", holdsteps=10, aftersteps=1)

        # wait to select a move
        vba.crystal.text_wait()

        # SCRATCH
        vba.press("a", holdsteps=10, aftersteps=1)

        # wait for the move to be over
        vba.crystal.text_wait()

        hp = ((vba.get_memory_at(0xd218) << 8) | vba.get_memory_at(0xd217))
        print "enemy hp is: " + str(hp)

        if hp == 0:
            print "enemy hp is zero, exiting"
            break
        else:
            print "enemy hp is: " + str(hp)

        attacks = attacks - 1

    while vba.get_memory_at(0xd22d) != 0:
        vba.press("a", holdsteps=10, aftersteps=1)

    # wait for the map to finish loading
    vba.nstep(50)

    print "okay, back in the overworld"

    # move up
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")

    # move into new bark town
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")

    # move up
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")

    # move to the door
    vba.crystal.move("r")
    vba.crystal.move("r")
    vba.crystal.move("r")

    # walk in
    vba.crystal.move("u")

    # move up to the healing thing
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("u")
    vba.crystal.move("l")
    vba.crystal.move("l")

    # face it
    vba.crystal.move("u")

    # interact
    vba.press("a", holdsteps=10, aftersteps=1)

    # wait for yes/no box
    vba.crystal.text_wait()

    # press yes
    vba.press("a", holdsteps=10, aftersteps=1)

    # TODO: when is healing done?

    # wait until the script is done running
    vba.crystal.wait_for_script_running()

    # wait for it to be really really done
    vba.nstep(50)

    vba.crystal.move("r")
    vba.crystal.move("r")

    # move to the door
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")

    # walk out
    vba.crystal.move("d")

    # check partymon1 level
    if vba.get_memory_at(0xdcfe) < level:
        new_bark_level_grind(level, skip=False)
    else:
        return

@skippable
def new_bark_level_grind_walk_to_grass():
    """
    Move to just above the grass from outside Elm's lab.
    """

    vba.crystal.move("d")
    vba.crystal.move("d")

    vba.crystal.move("l")
    vba.crystal.move("l")

    vba.crystal.move("d")
    vba.crystal.move("d")

    vba.crystal.move("l")
    vba.crystal.move("l")

    # move to route 29 past the trees
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")
    vba.crystal.move("l")

    # move to just above the grass
    vba.crystal.move("d")
    vba.crystal.move("d")
    vba.crystal.move("d")

if __name__ == "__main__":
    main()
