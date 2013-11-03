"""
Code that attempts to model a battle.
"""

from pokemontools.vba.vba import crystal as emulator
import pokemontools.vba.vba as vba

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

    def __init__(self, emulator=None):
        """
        Setup the battle.
        """
        self.emulator = emulator

    def is_in_battle(self):
        """
        @rtype: bool
        """
        return self.emulator.is_in_battle()

    def is_fight_pack_run_menu(self):
        """
        Attempts to detect if the current menu is fight-pack-run. This is only
        for whether or not the player needs to choose what to do next.
        """
        signs = ["FIGHT", "PACK", "RUN"]
        screentext = self.emulator.get_text()
        return all([sign in screentext for sign in signs])

    def is_player_turn(self):
        return is_fight_pack_run_menu()

    def is_mandatory_switch(self):
        return False # TODO

    def skip_start_text(self, max_loops=20):
        """
        Skip any initial conversation until the battle has begun.
        """
        if not self.is_in_battle():
            while not self.is_in_battle() and max_loops > 0:
                self.emulator.text_wait()
                max_loops -= 1

            if max_loops <= 0:
                raise Exception("Couldn't start the battle.")
        else:
            self.emulator.text_wait()

    def skip_end_text(self, loops=20):
        if not self.is_in_battle():
            # TODO: keep talking until the character can move?
            self.emulator.text_wait()
        else:
            while self.is_in_battle() and loops > 0:
                self.emulator.text_wait()
                loops -= 1

            if loops <= 0:
                raise Exception("Couldn't get out of the battle.")

    def skip_crap(self):
        while not self.is_flight_pack_run_menu():
            self.emulator.text_wait()

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
