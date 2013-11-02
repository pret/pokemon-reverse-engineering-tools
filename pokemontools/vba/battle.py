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

    def __init__(self, hook):
        """
        Setup the battle.

        @param hook: object that implements handle_turn and handle_mandatory_switch
        @type hook: BattleHook
        """
        self.hook = hook

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
                self.hook.handle_turn()
            elif self.is_mandatory_switch():
                self.hook.handle_mandatory_switch()
            else:
                raise BattleException("unknown state, aborting")

        # "how did i lose? wah"
        self.skip_end_text()

class BattleHook(object):
    """
    Hooks that are called during a battle.
    """

    def __init__(self, battle):
        """
        Makes references to some common objects.
        """
        self.battle = battle
        self.emulator = battle.emulator

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

class SimpleBattleHook(BattleHook):
    """
    Attack the enemy with the first move.
    """

    def handle_turn(self):
        """
        Always attack the enemy with the first move.
        """
        self.battle.attack(self.battle.party[0].moves[0].name)
