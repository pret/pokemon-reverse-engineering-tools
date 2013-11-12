"""
Tests for the battle controller
"""

import unittest

from setup_vba import (
    vba,
    autoplayer,
)

from pokemontools.vba.battle import (
    Battle,
    BattleException,
)

from bootstrapping import (
    bootstrap,
    bootstrap_trainer_battle,
)

class BattleTests(unittest.TestCase):
    cry = None
    vba = None
    bootstrap_state = None

    @classmethod
    def setUpClass(cls):
        cls.cry = vba.crystal()
        cls.vba = cls.cry.vba

        cls.bootstrap_state = bootstrap_trainer_battle()
        cls.vba.state = cls.bootstrap_state

    @classmethod
    def tearDownClass(cls):
        cls.vba.shutdown()

    def setUp(self):
        # reset to whatever the bootstrapper created
        self.vba.state = self.bootstrap_state
        self.battle = Battle(emulator=self.cry)
        self.battle.skip_start_text()

    def test_is_in_battle(self):
        self.assertTrue(self.battle.is_in_battle())

    def test_is_player_turn(self):
        self.battle.skip_start_text()
        self.battle.skip_until_input_required()

        # the initial state should be the player's turn
        self.assertTrue(self.battle.is_player_turn())

    def test_is_mandatory_switch_initial(self):
        # should not be asking for a switch so soon in the battle
        self.assertFalse(self.battle.is_mandatory_switch())

    def test_is_mandatory_switch(self):
        self.battle.skip_start_text()
        self.battle.skip_until_input_required()

        # press "FIGHT"
        self.vba.press(["a"], after=20)

        # press the first move ("SCRATCH")
        self.vba.press(["a"], after=20)

        # set partymon1 hp to very low
        self.cry.set_battle_mon_hp(1)

        # let the enemy attack and kill the pokemon
        self.battle.skip_until_input_required()

        self.assertTrue(self.battle.is_mandatory_switch())

    def test_attack_loop(self):
        self.battle.skip_start_text()
        self.battle.skip_until_input_required()

        # press "FIGHT"
        self.vba.press(["a"], after=20)

        # press the first move ("SCRATCH")
        self.vba.press(["a"], after=20)

        self.battle.skip_until_input_required()

        self.assertTrue(self.battle.is_player_turn())

    def test_is_battle_switch_prompt(self):
        self.battle.skip_start_text()
        self.battle.skip_until_input_required()

        # press "FIGHT"
        self.vba.press(["a"], after=20)

        # press the first move ("SCRATCH")
        self.vba.press(["a"], after=20)

        # set enemy hp to very low
        self.cry.lower_enemy_hp()

        # attack the enemy and kill it
        self.battle.skip_until_input_required()

        # yes/no menu is present, should be detected
        self.assertTrue(self.battle.is_trainer_switch_prompt())

        # and input should be required
        self.assertTrue(self.battle.is_input_required())

        # but it's not mandatory
        self.assertFalse(self.battle.is_mandatory_switch())

if __name__ == "__main__":
    unittest.main()
