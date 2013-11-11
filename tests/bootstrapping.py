"""
Functions to bootstrap the emulator state
"""

from setup_vba import (
    vba,
    autoplayer,
)

def bootstrap():
    """
    Every test needs to be run against a certain minimum context. That context
    is constructed by this function.
    """

    cry = vba.crystal(config=None)
    runner = autoplayer.SpeedRunner(cry=cry)

    # skip=False means run the skip_intro function instead of just skipping to
    # a saved state.
    runner.skip_intro(skip=True)

    state = cry.vba.state

    # clean everything up again
    cry.vba.shutdown()

    return state

def bootstrap_trainer_battle():
    """
    Start a trainer battle.
    """
    # setup
    cry = vba.crystal(config=None)
    runner = autoplayer.SpeedRunner(cry=cry)

    runner.skip_intro(skip=True)
    runner.handle_mom(skip=True)
    runner.walk_into_new_bark_town(skip=True)
    runner.handle_elm("totodile", skip=True)

    # levelgrind a pokemon
    # TODO: make new_bark_level_grind able to figure out how to construct its
    # initial state if none is provided.
    runner.new_bark_level_grind(17, skip=True)

    cry.givepoke(64, 31, "kAdAbRa")
    cry.givepoke(224, 60, "OcTiLlErY")
    cry.givepoke(126, 87, "magmar")

    cry.start_trainer_battle()

    return runner.cry.vba.state
