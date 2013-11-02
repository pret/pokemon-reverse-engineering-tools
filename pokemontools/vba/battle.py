"""
Code that attempts to model a battle.
"""

from pokemontools.vba.vba import crystal as emulator

class BattleException(Exception):
    """
    Something went terribly wrong in a battle.
    """

class EmulatorController(object):
    """
    Controls the emulator. I don't have a good reason for this.
    """

class Battle(EmulatorController):
    """
    Wrapper around the battle routine inside of the game. This object controls
    the emulator and provides a sanitized interface for interacting with a
    battle through python.
    """

    # Maybe this should be an instance variable instead, but since there can
    # only be one emulator per instance (??) it doesn't really matter right
    # now.
    emulator = emulator

    def __init__(self, emulator=emulator):
        """
        Setup the battle.
        """
        self.emulator = emulator

    @classmethod
    def is_in_battle(cls):
        """
        @rtype: bool
        """
        return cls.emulator.is_in_battle()

    def run(self):
        """
        Step through the entire battle.
        """
        # xyz wants to battle
        self.skip_start_text()

        while self.is_in_battle():
            self.skip_crap()

            if self.is_player_turn():
                self.handle_turn()
            elif self.is_mandatory_switch():
                self.handle_mandatory_switch()
            else:
                raise BattleException("unknown state, aborting")

        # "how did i lose? wah"
        self.skip_end_text()

    def handle_mandatory_switch(self):
        """
        Something fainted, pick the next mon.
        """
        raise NotImplementedError

    def handle_turn(self):
        """
        Take actions inside of a battle based on the game state.
        """
        raise NotImplementedError

class BattleStrategy(Battle):
    """
    Throw a pokeball until everyone dies.
    """

    def handle_mandatory_switch(self):
        """
        Something fainted, pick the next mon.
        """
        for pokemon in self.emulator.party:
            if pokemon.hp > 0:
                break
        else:
            # the game failed to do a blackout.. not sure what to do now.
            raise BattleException("No partymons left. wtf?")

       return pokemon.id

    def handle_turn(self):
        """
        Take actions inside of a battle based on the game state.
        """
        self.battle.throw_pokeball()

class SimpleBattleStrategy(BattleStrategy):
    """
    Attack the enemy with the first move.
    """

    def handle_turn(self):
        """
        Always attack the enemy with the first move.
        """
        self.attack(self.battle.party[0].moves[0].name)
