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

    def is_input_required(self):
        """
        Detects if the battle is waiting for player input.
        """
        return self.is_player_turn() or self.is_mandatory_switch()

    def is_fight_pack_run_menu(self):
        """
        Attempts to detect if the current menu is fight-pack-run. This is only
        for whether or not the player needs to choose what to do next.
        """
        signs = ["FIGHT", "PACK", "RUN"]
        screentext = self.emulator.get_text()
        return all([sign in screentext for sign in signs])

    def is_player_turn(self):
        """
        Detects if the battle is waiting for the player to choose an attack.
        """
        return self.is_fight_pack_run_menu()

    def is_mandatory_switch(self):
        """
        Detects if the battle is waiting for the player to choose a next
        pokemon.
        """
        # TODO: test when "no" fails to escape for wild battles.
        # trainer battles: menu asks to select the next mon
        # wild battles: yes/no box first
        # The following conditions are probably sufficient:
        #   1) current pokemon hp is 0
        #   2) game is polling for input

        if "CANCEL Which ?" in self.emulator.get_text():
            return True
        else:
            return False

    def skip_start_text(self, max_loops=20):
        """
        Skip any initial conversation until the player can select an action.
        This includes skipping any text that appears on a map from an NPC as
        well as text that appears prior to the first time the action selection
        menu appears.
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
        """
        Skip through any text that appears after the final attack.
        """
        if not self.is_in_battle():
            # TODO: keep talking until the character can move? A battle can be
            # triggered inside of a script, and after the battle is ver the
            # player may not be able to move until the script is done. The
            # script might only finish after other player input is given, so
            # using "text_wait() until the player can move" is a bad idea here.
            self.emulator.text_wait()
        else:
            while self.is_in_battle() and loops > 0:
                self.emulator.text_wait()
                loops -= 1

            if loops <= 0:
                raise Exception("Couldn't get out of the battle.")

    def skip_until_input_required(self):
        """
        Waits until the battle needs player input.
        """
        while not self.is_input_required():
            self.emulator.text_wait()

        # let the text draw so that the state is more obvious
        self.emulator.vba.step(count=10)

    def run(self):
        """
        Step through the entire battle.
        """
        # Advance to the battle from either of these states:
        #   1) the player is talking with an npc
        #   2) the battle has already started but there's initial text
        # xyz wants to battle, a wild foobar appeared
        self.skip_start_text()

        while self.is_in_battle():
            self.skip_until_input_required()

            if self.is_player_turn():
                # battle hook provides input to handle this situation
                self.handle_turn()
            elif self.is_mandatory_switch():
                # battle hook provides input to handle this situation too
                self.handle_mandatory_switch()
            else:
                raise BattleException("unknown state, aborting")

        # "how did i lose? wah"
        self.skip_end_text()

        # TODO: return should indicate win/loss (blackout)

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
        self.throw_pokeball()

class SimpleBattleStrategy(BattleStrategy):
    """
    Attack the enemy with the first move.
    """

    def handle_turn(self):
        """
        Always attack the enemy with the first move.
        """
        self.attack(self.battle.party[0].moves[0].name)
