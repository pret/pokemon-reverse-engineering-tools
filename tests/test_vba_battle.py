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

    def test_battle_is_player_turn(self):
        self.cry.vba.state = self.bootstrap_state

        battle = Battle(emulator=self.cry)

        self.assertTrue(battle.is_player_turn())

if __name__ == "__main__":
    unittest.main()
