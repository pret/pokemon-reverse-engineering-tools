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

if __name__ == "__main__":
    unittest.main()
