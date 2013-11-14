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
        return self.is_player_turn() or self.is_mandatory_switch() or self.is_trainer_switch_prompt()

    def is_fight_pack_run_menu(self):
        """
        Attempts to detect if the current menu is fight-pack-run. This is only
        for whether or not the player needs to choose what to do next.
        """
        signs = ["FIGHT", "PACK", "RUN"]
        screentext = self.emulator.get_text()
        return all([sign in screentext for sign in signs])

    def select_battle_menu_action(self, action, execute=True):
        """
        Moves the cursor to the requested action and selects it.

        :param action: fight, pkmn, pack, run
        """
        if not self.is_fight_pack_run_menu():
            raise Exception(
                "This isn't the fight-pack-run menu."
            )

        action = action.lower()

        action_map = {
            "fight": (1, 1),
            "pkmn":  (1, 2),
            "pack":  (2, 1),
            "run":   (2, 2),
        }

        if action not in action_map.keys():
            raise Exception(
                "Unexpected requested action {0}".format(action)
            )

        current_row = self.vba.read_memory_at(0xcfa9)
        current_column = self.vba.read_memory_at(0xcfaa)

        direction = None
        if current_row != action_map[action][0]:
            if current_row > action_map[action][0]:
                direction = "u"
            elif current_row < action_map[action][0]:
                direction = "d"

            self.vba.press(direction, hold=5, after=10)

        direction = None
        if current_column != action_map[action][1]:
            if current_column > action_map[action][1]:
                direction = "l"
            elif current_column < action_map[action][1]:
                direction = "r"

            self.vba.press(direction, hold=5, after=10)

        # now select the action
        if execute:
            self.vba.press(a, hold=5, after=100)

    def select_attack(self, move_number=1, hold=5, after=10):
        """
        Moves the cursor to the correct attack in the menu and presses the
        button.

        :param move_number: the attack number on the FIGHT menu. Note that this
        starts from 1.
        :param hold: how many frames to hold each button press
        :param after: how many frames to wait after each button press
        """
        # TODO: detect fight menu and make sure it's detected here.

        pp_address = 0xc634 + (move_number - 1)
        pp = self.vba.read_memory_at(pp_address)

        # detect zero pp because i don't want to write a way to inform the
        # caller that there was no more pp. Just check the pp yourself.
        if pp == 0:
            raise BattleException(
                "Move {num} has no more PP.".format(
                    num=move_number,
                )
            )

        valid_selection_states = (1, 2, 3, 4)

        selection = self.vba.read_memory_at(0xcfa9)

        while selection != move_number:
            if selection not in valid_selection_states:
                raise BattleException(
                    "The current selected attack is out of bounds: {num}".format(
                        num=selection,
                    )
                )

            direction = None

            if selection > move_number:
                direction = "d"
            elif selection < move_number:
                direction = "u"
            else:
                # probably never happens
                raise BattleException(
                    "Not sure what to do here."
                )

            # press the arrow button
            self.vba.press(direction, hold=hold, after=after)

            # let's see what the current selection is
            selection = self.vba.read_memory_at(0xcfa9)

        # press to choose the attack
        self.vba.press("a", hold=hold, after=after)

    def fight(self, move_number):
        """
        Select FIGHT from the flight-pack-run menu and select the move
        identified by move_number.
        """
        # make sure the menu is detected
        if not self.is_fight_pack_run_menu():
            raise BattleException(
                "Wrong menu. Can't press FIGHT here."
            )

        # select FIGHT
        self.select_battle_menu_action("fight")

        # select the requested attack
        self.select_attack(move_number)

    def is_player_turn(self):
        """
        Detects if the battle is waiting for the player to choose an attack.
        """
        return self.is_fight_pack_run_menu()

    def is_trainer_switch_prompt(self):
        """
        Detects if the battle is waiting for the player to choose whether or
        not to switch pokemon. This is the prompt that asks yes/no for whether
        to switch pokemon, like if the trainer is switching pokemon at the end
        of a turn set.
        """
        return self.emulator.is_trainer_switch_prompt()

    def is_wild_switch_prompt(self):
        """
        Detects if the battle is waiting for the player to choose whether or
        not to continue to fight the wild pokemon.
        """
        return self.emulator.is_wild_switch_prompt()

    def is_switch_prompt(self):
        """
        Detects both trainer and wild switch prompts (for prompting whether to
        switch pokemon). This is a yes/no box and not the actual pokemon
        selection menu.
        """
        return self.is_trainer_switch_prompt() or self.is_wild_switch_prompt()

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
            elif self.is_trainer_switch_prompt():
                self.handle_trainer_switch_prompt()
            elif self.is_wild_switch_prompt():
                self.handle_wild_switch_prompt()
            elif self.is_mandatory_switch():
                # battle hook provides input to handle this situation too
                self.handle_mandatory_switch()
            else:
                raise BattleException("unknown state, aborting")

        # "how did i lose? wah"
        # TODO: this doesn't happen for wild battles
        self.skip_end_text()

        # TODO: return should indicate win/loss (blackout)

    def handle_mandatory_switch(self):
        """
        Something fainted, pick the next mon.
        """
        raise NotImplementedError

    def handle_trainer_switch_prompt(self):
        """
        The trainer is switching pokemon. The game asks yes/no for whether or
        not the player would like to switch.
        """
        raise NotImplementedError

    def handle_wild_switch_prompt(self):
        """
        The wild pokemon defeated the party pokemon. This is the yes/no box for
        whether to switch pokemon or not.
        """
        raise NotImplementedError

    def handle_turn(self):
        """
        Take actions inside of a battle based on the game state.
        """
        raise NotImplementedError

class BattleStrategy(Battle):
    """
    This class shows the relevant methods to make a battle handler.
    """

    def handle_mandatory_switch(self):
        """
        Something fainted, pick the next mon.
        """
        raise NotImplementedError

    def handle_trainer_switch_prompt(self):
        """
        The trainer is switching pokemon. The game asks yes/no for whether or
        not the player would like to switch.
        """
        raise NotImplementedError

    def handle_wild_switch_prompt(self):
        """
        The wild pokemon defeated the party pokemon. This is the yes/no box for
        whether to switch pokemon or not.
        """
        raise NotImplementedError

    def handle_turn(self):
        """
        Take actions inside of a battle based on the game state.
        """
        raise NotImplementedError

class SpamBattleStrategy(BattleStrategy):
    """
    A really simple battle strategy that always picks the first move of the
    first pokemon to attack the enemy.
    """

    def handle_turn(self):
        """
        Always picks the first move of the current pokemon.
        """
        pass
